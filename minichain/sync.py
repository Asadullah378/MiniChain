from __future__ import annotations

import asyncio
from . import messages
from .logging_utils import info


class SyncManager:
    def __init__(self, node):
        self.node = node

    async def initial_sync(self):
        # ask peers for latest height; naive approach: first peer only
        for pid in self.node.peer_addresses.keys():
            try:
                # send GETHEADERS for a wide range
                payload = {"from_height": 0, "to_height": 10_000_000}
                msg = messages.pack_message(messages.MSG["GETHEADERS"], self.node.node_id, self.node.signing_key, payload)
                await self.node.send_to(pid, msg)
            except Exception:
                pass
        info("sync_requested")

    async def handle_headers(self, payload: dict, sender: str):
        # simplistic: if remote height > local, request full blocks
        remote_height = max([h["height"] for h in payload.get("headers", [])] or [0])
        if remote_height > self.node.store.height():
            req = {"from_height": self.node.store.height() + 1, "to_height": remote_height}
            msg = messages.pack_message(messages.MSG["GETBLOCKS"], self.node.node_id, self.node.signing_key, req)
            await self.node.send_to(sender, msg)

    async def handle_blocks(self, payload: dict, sender: str):
        blocks = payload.get("blocks", [])
        for b in blocks:
            from .models import Block
            blk = Block.unpack(b)
            if blk.height == self.node.store.height() + 1:
                ok, _ = self.node.store.append_block(blk)
                if ok:
                    tx_ids = [t["tx_id"] for t in blk.tx_list]
                    self.node.mempool.remove_many(tx_ids)
        info("sync_applied", new_height=self.node.store.height())
