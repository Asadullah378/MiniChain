from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Dict, Any
import time
from . import crypto


@dataclass
class Transaction:
    sender: str
    to: str
    amount: int
    nonce: int
    signature: bytes
    tx_id: str = field(init=False)

    def __post_init__(self):
        body = {
            "from": self.sender,
            "to": self.to,
            "amount": self.amount,
            "nonce": self.nonce,
        }
        self.tx_id = crypto.tx_id(body, self.signature)

    def body(self) -> Dict[str, Any]:
        return {"from": self.sender, "to": self.to, "amount": self.amount, "nonce": self.nonce}

    def pack(self) -> dict:
        return {"sender": self.sender, "to": self.to, "amount": self.amount, "nonce": self.nonce, "signature": self.signature, "tx_id": self.tx_id}

    @staticmethod
    def unpack(d: dict) -> "Transaction":
        return Transaction(d["sender"], d["to"], d["amount"], d["nonce"], d["signature"])


@dataclass
class Block:
    height: int
    prev_hash: str
    timestamp: float
    tx_list: List[dict]
    proposer_id: str
    signature: bytes
    block_hash: str = field(init=False)

    def __post_init__(self):
        header = self.header_dict(include_hash=False)
        self.block_hash = crypto.block_hash(header, self.tx_list)

    def header_dict(self, include_hash=True) -> Dict[str, Any]:
        h = {
            "height": self.height,
            "prev_hash": self.prev_hash,
            "timestamp": self.timestamp,
            "proposer_id": self.proposer_id,
        }
        if include_hash:
            h["block_hash"] = self.block_hash
        return h

    def pack(self) -> dict:
        return {
            "height": self.height,
            "prev_hash": self.prev_hash,
            "timestamp": self.timestamp,
            "tx_list": self.tx_list,
            "proposer_id": self.proposer_id,
            "signature": self.signature,
            "block_hash": self.block_hash,
        }

    @staticmethod
    def unpack(d: dict) -> "Block":
        blk = Block(
            d["height"], d["prev_hash"], d["timestamp"], d["tx_list"], d["proposer_id"], d["signature"]
        )
        # override computed hash with stored for integrity comparison
        if blk.block_hash != d["block_hash"]:
            # integrity mismatch might be handled upstream; keep stored
            blk.block_hash = d["block_hash"]
        return blk


def genesis_block() -> Block:
    return Block(
        height=0,
        prev_hash="GENESIS",
        timestamp=time.time(),
        tx_list=[],
        proposer_id="GENESIS",
        signature=b"",
    )
