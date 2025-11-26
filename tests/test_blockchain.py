import time

from src.chain.block import Block
from src.chain.blockchain import Blockchain


def _build_block(blockchain: Blockchain, height: int) -> Block:
    return Block(
        height=height,
        prev_hash=blockchain.get_latest_hash(),
        transactions=[],
        timestamp=time.time(),
        proposer_id="validator-1",
    )


def test_blockchain_adds_and_persists_blocks(tmp_path):
    data_dir = tmp_path / "chain"
    blockchain = Blockchain(data_dir=str(data_dir))

    block = _build_block(blockchain, height=1)
    assert blockchain.add_block(block)

    reloaded = Blockchain(data_dir=str(data_dir))
    assert reloaded.get_height() == 1
    assert reloaded.get_latest_hash() == block.block_hash


def test_blockchain_rejects_invalid_prev_hash(tmp_path):
    blockchain = Blockchain(data_dir=str(tmp_path / "invalid"))

    bad_block = Block(
        height=1,
        prev_hash=b"\x01" * 32,
        transactions=[],
        timestamp=time.time(),
        proposer_id="validator-1",
    )

    assert not blockchain.add_block(bad_block)
    assert blockchain.get_height() == 0
