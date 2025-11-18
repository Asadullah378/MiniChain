from __future__ import annotations

import asyncio
import os
from typing import Dict, Tuple
from nacl.signing import SigningKey

from . import config, messages
from .crypto import derive_signing_key
from .store import ChainStore
from .mempool import Mempool
from .consensus import ConsensusEngine
from .sync import SyncManager
from .network import P2PServer, PeerClient
from .models import Transaction
from .logging_utils import info, warn


class MiniChainNode:
    def __init__(self, node_id: str, validators=None, genesis_balances=None, peers: Dict[str, Tuple[str, int]] | None = None):
        self.node_id = node_id
        self.validators = validators or config.DEFAULT_VALIDATORS
        seed = ("seed_" + node_id).encode()
        self.signing_key: SigningKey = derive_signing_key(seed)
        self.store = ChainStore(node_id, self.validators, genesis_balances)
        self.mempool = Mempool()
        self.consensus = ConsensusEngine(self)
        self.sync = SyncManager(self)
        self.peer_client = PeerClient()
        self.peer_addresses: Dict[str, Tuple[str, int]] = peers or {}
        self.running = False
        self.server: P2PServer | None = None

    async def start(self):
        self.running = True
        port = config.get_node_port(self.node_id)
        self.server = P2PServer("0.0.0.0", port, self._on_client)
        await self.server.start()
        await self._connect_peers()
        asyncio.create_task(self.consensus.tick())
        asyncio.create_task(self._heartbeat_loop())
        await self.sync.initial_sync()
        info("node_started", node=self.node_id, height=self.store.height())

    async def stop(self):
        self.running = False
        if self.server:
            await self.server.stop()
        info("node_stopped", node=self.node_id)

    async def _connect_peers(self):
        for pid, (host, port) in self.peer_addresses.items():
            if pid == self.node_id:
                continue
            await self.peer_client.connect(pid, host, port)

    async def _on_client(self, conn, peer_str: str):
        while self.running:
            try:
                raw = await conn.recv()
                if not raw:
                    break
                envelope, payload = messages.unpack_message(raw)
                msg_type = envelope["header"]["type"]
                sender_id = envelope["header"]["sender_id"]
                await self._dispatch_message(msg_type, sender_id, payload)
            except asyncio.IncompleteReadError:
                break
            except Exception as e:
                warn("recv_error", error=str(e))
                break

    async def _dispatch_message(self, msg_type: str, sender_id: str, payload: dict):
        if msg_type == messages.MSG["PROPOSE"]:
            await self.consensus.handle_propose(payload, sender_id)
        elif msg_type == messages.MSG["ACK"]:
            await self.consensus.handle_ack(payload, sender_id)
        elif msg_type == messages.MSG["COMMIT"]:
            await self.consensus.handle_commit(payload, sender_id)
        elif msg_type == messages.MSG["VIEWCHANGE"]:
            await self.consensus.handle_viewchange(payload, sender_id)
        elif msg_type == messages.MSG["GETHEADERS"]:
            headers = self.store.headers_range(payload["from_height"], payload["to_height"])
            resp = {"headers": headers}
            msg = messages.pack_message(messages.MSG["HEADERS"], self.node_id, self.signing_key, resp)
            await self.send_to(sender_id, msg)
        elif msg_type == messages.MSG["HEADERS"]:
            await self.sync.handle_headers(payload, sender_id)
        elif msg_type == messages.MSG["GETBLOCKS"]:
            blocks = self.store.blocks_range(payload["from_height"], payload["to_height"])
            resp = {"blocks": blocks}
            msg = messages.pack_message(messages.MSG["BLOCK"], self.node_id, self.signing_key, resp)
            await self.send_to(sender_id, msg)
        elif msg_type == messages.MSG["BLOCK"]:
            await self.sync.handle_blocks(payload, sender_id)
        elif msg_type == messages.MSG["TX"]:
            tx = Transaction.unpack(payload)
            self.mempool.add(tx)
        elif msg_type == messages.MSG["HEARTBEAT"]:
            pass
        else:
            warn("unknown_message", type=msg_type)

    async def send_to(self, peer_id: str, data: bytes):
        c = self.peer_client.get(peer_id)
        if c:
            await c.send(data)

    async def broadcast(self, data: bytes):
        for pid in self.peer_addresses.keys():
            if pid == self.node_id:
                continue
            await self.send_to(pid, data)

    async def _heartbeat_loop(self):
        while self.running:
            payload = {"node_id": self.node_id, "height": self.store.height(), "last_block_hash": self.store.head_hash()}
            msg = messages.pack_message(messages.MSG["HEARTBEAT"], self.node_id, self.signing_key, payload)
            await self.broadcast(msg)
            await asyncio.sleep(config.HEARTBEAT_INTERVAL_SEC)

    def on_commit(self, blk: Block):
        ok, _ = self.store.append_block(blk)
        if ok:
            tx_ids = [t["tx_id"] for t in blk.tx_list]
            self.mempool.remove_many(tx_ids)
