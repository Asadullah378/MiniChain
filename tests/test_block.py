from src.chain.block import Transaction, Block, create_genesis_block


def _sample_tx(tx_id: str = "tx-1") -> Transaction:
    return Transaction(
        tx_id=tx_id,
        sender="alice",
        recipient="bob",
        amount=10.5,
        timestamp=1234567890.0,
        signature=b"signature-bytes",
    )


def test_transaction_serialization_roundtrip():
    tx = _sample_tx()
    serialized = tx.serialize()
    restored = Transaction.deserialize(serialized)

    assert restored.tx_id == tx.tx_id
    assert restored.sender == tx.sender
    assert restored.recipient == tx.recipient
    assert restored.amount == tx.amount
    assert restored.signature == tx.signature


def test_block_hash_is_deterministic():
    tx = _sample_tx()
    block = Block(
        height=1,
        prev_hash=b"\x00" * 32,
        transactions=[tx],
        timestamp=1234567890.5,
        proposer_id="node-a",
    )

    assert block.block_hash == block.compute_hash()

    # Mutating the transactions should change the computed hash
    block.transactions.append(_sample_tx("tx-2"))
    assert block.block_hash != block.compute_hash()


def test_create_genesis_block_is_deterministic():
    g1 = create_genesis_block()
    g2 = create_genesis_block()

    assert g1.height == 0
    assert g1.prev_hash == b"\x00" * 32
    assert g1.block_hash == g2.block_hash
    assert g1.timestamp == 0.0
