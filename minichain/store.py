from __future__ import annotations

import os
import json
import time
from typing import Dict, List, Tuple, Any
from .models import Block, Transaction, genesis_block
from . import config, crypto
from .logging_utils import info, warn


class ChainStore:
    def __init__(self, node_id: str, validators: List[str], genesis_balances: Dict[str, int] | None = None):
        self.node_id = node_id
        self.validators = validators
        self.blocks: List[dict] = []
        self.accounts: Dict[str, int] = dict(genesis_balances or {})
        self._genesis_accounts: Dict[str, int] = dict(self.accounts)
        self.nonces: Dict[str, int] = {}
        self.path = os.path.join(config.DATA_DIR, f"node_{node_id}")
        os.makedirs(self.path, exist_ok=True)
        self.file = os.path.join(self.path, "chain.json")
        self._load()

    def _init_genesis_state(self) -> None:
        g = genesis_block()
        self.blocks = [g.pack()]
        self.accounts = dict(self._genesis_accounts)
        self.nonces = {}
        self._persist()

    def _backup_corrupt_store(self) -> None:
        ts = int(time.time())
        backup_path = f"{self.file}.bak.{ts}"
        try:
            os.replace(self.file, backup_path)
            warn("store_backed_up", node=self.node_id, file=self.file, backup=backup_path)
        except OSError as exc:
            warn("store_backup_failed", node=self.node_id, file=self.file, error=str(exc))

    def _load(self):
        if not os.path.exists(self.file):
            self._init_genesis_state()
            return

        try:
            with open(self.file, "r") as f:
                raw = f.read().strip()
            if not raw:
                raise ValueError("empty_store_file")
            data = json.loads(raw)
        except (json.JSONDecodeError, ValueError) as exc:
            warn("store_load_failed", node=self.node_id, file=self.file, error=str(exc))
            self._backup_corrupt_store()
            self._init_genesis_state()
            return

        blocks = [self._decode_block(b) for b in data.get("blocks", [])]
        accounts = data.get("accounts", {})
        nonces = data.get("nonces", {})

        if not blocks:
            warn("store_missing_blocks", node=self.node_id, file=self.file)
            self._init_genesis_state()
            return

        self.blocks = blocks
        self.accounts = accounts
        self.nonces = nonces

    def _persist(self):
        encoded_blocks = [self._encode_block(block) for block in self.blocks]
        with open(self.file, "w") as f:
            json.dump({"blocks": encoded_blocks, "accounts": self.accounts, "nonces": self.nonces}, f)

    @staticmethod
    def _encode_tx(tx: Dict[str, Any]) -> Dict[str, Any]:
        encoded = dict(tx)
        sig = encoded.get("signature")
        if isinstance(sig, (bytes, bytearray)):
            encoded["signature"] = sig.hex()
        return encoded

    @staticmethod
    def _decode_tx(tx: Dict[str, Any]) -> Dict[str, Any]:
        decoded = dict(tx)
        sig = decoded.get("signature")
        if isinstance(sig, str):
            decoded["signature"] = bytes.fromhex(sig)
        return decoded

    @classmethod
    def _encode_block(cls, block: Dict[str, Any]) -> Dict[str, Any]:
        encoded = dict(block)
        sig = encoded.get("signature")
        if isinstance(sig, (bytes, bytearray)):
            encoded["signature"] = sig.hex()
        encoded["tx_list"] = [cls._encode_tx(tx) for tx in encoded.get("tx_list", [])]
        return encoded

    @classmethod
    def _decode_block(cls, block: Dict[str, Any]) -> Dict[str, Any]:
        decoded = dict(block)
        sig = decoded.get("signature")
        if isinstance(sig, str):
            decoded["signature"] = bytes.fromhex(sig)
        decoded["tx_list"] = [cls._decode_tx(tx) for tx in decoded.get("tx_list", [])]
        return decoded

    def height(self) -> int:
        return len(self.blocks) - 1

    def head_hash(self) -> str:
        return self.blocks[-1]["block_hash"] if self.blocks else "GENESIS"

    def get_block(self, height: int) -> dict | None:
        if height < 0 or height >= len(self.blocks):
            return None
        return self.blocks[height]

    def apply_tx(self, tx: Transaction) -> bool:
        bal = self.accounts.get(tx.sender, 0)
        nonce = self.nonces.get(tx.sender, 0)
        if tx.nonce != nonce + 1:
            return False
        if tx.amount < 0:
            return False
        if bal < tx.amount:
            return False
        if not crypto.verify_bytes(tx.sender, crypto.canonical_pack(tx.body()), tx.signature):
            return False
        self.accounts[tx.sender] = bal - tx.amount
        self.accounts[tx.to] = self.accounts.get(tx.to, 0) + tx.amount
        self.nonces[tx.sender] = nonce + 1
        return True

    def check_block_valid(self, blk: Block) -> Tuple[bool, str]:
        if blk.prev_hash != self.head_hash():
            return False, "prev_hash_mismatch"
        expected_leader = self.validators[(blk.height) % len(self.validators)]
        if blk.proposer_id != expected_leader:
            return False, "bad_leader"
        # validate transactions on a snapshot copy
        snapshot_bal = dict(self.accounts)
        snapshot_nonce = dict(self.nonces)
        for tdict in blk.tx_list:
            tx = Transaction.unpack(tdict)
            bal = snapshot_bal.get(tx.sender, 0)
            nonce = snapshot_nonce.get(tx.sender, 0)
            if tx.nonce != nonce + 1:
                return False, "bad_nonce"
            if bal < tx.amount or tx.amount < 0:
                return False, "insufficient_balance"
            if not crypto.verify_bytes(tx.sender, crypto.canonical_pack(tx.body()), tx.signature):
                return False, "bad_tx_sig"
            snapshot_bal[tx.sender] = bal - tx.amount
            snapshot_bal[tx.to] = snapshot_bal.get(tx.to, 0) + tx.amount
            snapshot_nonce[tx.sender] = nonce + 1
        return True, "ok"

    def append_block(self, blk: Block) -> Tuple[bool, str]:
        ok, reason = self.check_block_valid(blk)
        if not ok:
            return False, reason
        for tdict in blk.tx_list:
            _ = self.apply_tx(Transaction.unpack(tdict))
        self.blocks.append(blk.pack())
        self._persist()
        info("block_committed", node=self.node_id, height=blk.height, hash=blk.block_hash)
        return True, "committed"

    def headers_range(self, start: int, end: int) -> List[dict]:
        start = max(0, start)
        end = min(end, self.height())
        res = []
        for i in range(start, end + 1):
            b = self.blocks[i]
            res.append({
                "height": b["height"],
                "hash": b["block_hash"],
                "prev_hash": b["prev_hash"],
                "proposer_id": b["proposer_id"],
            })
        return res

    def blocks_range(self, start: int, end: int) -> List[dict]:
        start = max(0, start)
        end = min(end, self.height())
        return [self.blocks[i] for i in range(start, end + 1)]
