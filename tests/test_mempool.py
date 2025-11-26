import time

from src.chain.block import Transaction
from src.mempool.mempool import Mempool


def _tx(tx_id: str) -> Transaction:
    return Transaction(
        tx_id=tx_id,
        sender="alice",
        recipient="bob",
        amount=1.0,
        timestamp=time.time(),
    )


def test_mempool_adds_and_deduplicates_transactions():
    mempool = Mempool()
    tx = _tx("tx-1")

    assert mempool.add_transaction(tx) is True
    assert mempool.add_transaction(tx) is False
    assert mempool.size() == 1
    assert mempool.has_transaction("tx-1") is True


def test_mempool_remove_and_get_transactions():
    mempool = Mempool()
    tx_ids = [f"tx-{i}" for i in range(3)]
    for tx_id in tx_ids:
        mempool.add_transaction(_tx(tx_id))

    fetched = mempool.get_transactions(2)
    assert len(fetched) == 2
    assert all(tx.tx_id in tx_ids for tx in fetched)

    mempool.remove_transactions([tx.tx_id for tx in fetched])
    assert mempool.size() == 1
    assert mempool.has_seen(tx_ids[0]) is True
    assert mempool.has_transaction(tx_ids[0]) is False
