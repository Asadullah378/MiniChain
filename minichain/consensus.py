from __future__ import annotations

import asyncio
import time
from typing import Dict, List, Optional, Set
from . import config, messages, crypto
from .models import Transaction, Block
from .logging_utils import info, warn, debug


class ConsensusEngine:
    def __init__(self, node):
        self.node = node
        self.acks: Dict[int, Set[str]] = {}
        self.proposed_for_height: Set[int] = set()
        self.view: int = 0
        self.waiting_commit: Dict[int, str] = {}  # height -> block_hash

    def leader_for(self, height: int) -> str:
        v = self.node.validators
        return v[(height + self.view) % len(v)]

    async def tick(self):
        while self.node.running:
            try:
                await self._leader_actions()
            except Exception as e:
                warn("consensus_tick_error", error=str(e))
            await asyncio.sleep(config.PROPOSE_INTERVAL_SEC)

    async def _leader_actions(self):
        height = self.node.store.height() + 1
        leader = self.leader_for(height)
        if leader != self.node.node_id:
            return
        if height in self.proposed_for_height:
            return
        txs = self.node.mempool.list_for_block(config.MAX_TX_PER_BLOCK)
        tx_list = [t.pack() for t in txs]
        prev_hash = self.node.store.head_hash()
        header = {"height": height, "prev_hash": prev_hash, "timestamp": time.time(), "proposer_id": self.node.node_id}
        blk_hash = crypto.block_hash(header, tx_list)
        sig = crypto.sign_bytes(self.node.signing_key, crypto.canonical_pack({**header, "block_hash": blk_hash, "txs": tx_list}))
        blk = Block(height, prev_hash, header["timestamp"], tx_list, self.node.node_id, sig)
        payload = blk.pack()
        msg = messages.pack_message(messages.MSG["PROPOSE"], self.node.node_id, self.node.signing_key, payload)
        await self.node.broadcast(msg)
        info("propose_sent", height=height, hash=blk.block_hash, txs=len(tx_list))
        self.proposed_for_height.add(height)
        self.acks[height] = set([self.node.node_id])
        self.waiting_commit[height] = blk.block_hash
        asyncio.create_task(self._await_quorum_and_commit(height, blk))

    async def _await_quorum_and_commit(self, height: int, blk: Block):
        deadline = time.time() + config.ACK_TIMEOUT_SEC
        needed = config.quorum_size(self.node.validators)
        while time.time() < deadline and self.node.running:
            if len(self.acks.get(height, set())) >= needed:
                payload = {"height": height, "block": blk.pack(), "leader_id": self.node.node_id}
                msg = messages.pack_message(messages.MSG["COMMIT"], self.node.node_id, self.node.signing_key, payload)
                await self.node.broadcast(msg)
                info("commit_broadcast", height=height, hash=blk.block_hash)
                self.node.on_commit(blk)
                return
            await asyncio.sleep(0.1)
        # timeout
        self.view += 1
        payload = {"current_height": height, "new_leader_id": self.leader_for(height), "reason": "timeout"}
        msg = messages.pack_message(messages.MSG["VIEWCHANGE"], self.node.node_id, self.node.signing_key, payload)
        await self.node.broadcast(msg)
        warn("view_change", height=height, new_leader=self.leader_for(height))

    async def handle_propose(self, payload: dict, sender_id: str):
        blk = Block.unpack(payload)
        height = blk.height
        if self.leader_for(height) != blk.proposer_id:
            warn("propose_wrong_leader", height=height, proposer=blk.proposer_id)
            return
        ok, reason = self.node.store.check_block_valid(blk)
        if not ok:
            warn("propose_invalid", height=height, reason=reason)
            return
        ack = {"height": height, "block_hash": blk.block_hash, "voter_id": self.node.node_id}
        msg = messages.pack_message(messages.MSG["ACK"], self.node.node_id, self.node.signing_key, ack)
        await self.node.send_to(blk.proposer_id, msg)
        info("ack_sent", height=height, leader=blk.proposer_id, hash=blk.block_hash)
        self.waiting_commit[height] = blk.block_hash

    async def handle_ack(self, payload: dict, sender_id: str):
        height = payload["height"]
        if height not in self.waiting_commit:
            return
        if payload.get("block_hash") != self.waiting_commit[height]:
            return
        self.acks.setdefault(height, set()).add(sender_id)
        debug("ack_received", height=height, count=len(self.acks[height]))

    async def handle_commit(self, payload: dict, sender_id: str):
        blk = Block.unpack(payload["block"])
        if blk.height != self.node.store.height() + 1:
            return
        ok, _ = self.node.store.append_block(blk)
        if ok:
            tx_ids = [t["tx_id"] for t in blk.tx_list]
            self.node.mempool.remove_many(tx_ids)
            self.acks.pop(blk.height, None)
            self.waiting_commit.pop(blk.height, None)
            self.proposed_for_height.discard(blk.height)

    async def handle_viewchange(self, payload: dict, sender_id: str):
        self.view += 1
        info("viewchange_applied", new_leader=self.leader_for(self.node.store.height() + 1))
