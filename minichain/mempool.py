from __future__ import annotations

from typing import Dict, List
from .models import Transaction


class Mempool:
    def __init__(self):
        self._txs: Dict[str, Transaction] = {}

    def add(self, tx: Transaction):
        if tx.tx_id not in self._txs:
            self._txs[tx.tx_id] = tx

    def remove_many(self, tx_ids: List[str]):
        for tid in tx_ids:
            self._txs.pop(tid, None)

    def list_for_block(self, limit: int) -> List[Transaction]:
        return list(self._txs.values())[:limit]

    def size(self) -> int:
        return len(self._txs)
