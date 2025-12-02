import time

from src.chain.block import Block, Transaction
from src.consensus.poa import RoundRobinPoA
from src.mempool.mempool import Mempool


VALIDATORS = ["node-a", "node-b", "node-c"]


def _poa(node_id: str = "node-b", block_interval: int = 1) -> RoundRobinPoA:
    return RoundRobinPoA(
        node_id=node_id,
        validator_ids=VALIDATORS,
        block_interval=block_interval,
        proposal_timeout=5,
        quorum_size=2,
    )


def _tx(tx_id: str) -> Transaction:
    return Transaction(
        tx_id=tx_id,
        sender="alice",
        recipient="bob",
        amount=1.0,
        timestamp=time.time(),
    )


def test_leader_rotation_is_deterministic():
    poa = _poa()
    leaders = [poa.get_current_leader(h) for h in range(6)]
    assert leaders == ["node-a", "node-b", "node-c", "node-a", "node-b", "node-c"]


def test_should_propose_when_interval_elapsed():
    poa = _poa()
    poa.last_block_time = 0  # Force elapsed >= block_interval
    assert poa.should_propose() is True


def test_create_proposal_uses_mempool_transactions():
    poa = _poa()
    mempool = Mempool()
    for i in range(3):
        mempool.add_transaction(_tx(f"tx-{i}"))

    proposal = poa.create_proposal(mempool, prev_hash=b"\x00" * 32, max_txs=2)
    assert proposal is not None
    assert proposal.height == poa.current_height + 1
    assert len(proposal.transactions) == 2
    assert proposal.prev_hash == b"\x00" * 32


def test_quorum_tracking_and_commit_state_reset():
    poa = _poa()
    height = 1

    poa.add_ack(height, "node-b")
    poa.add_ack(height, "node-c")
    assert poa.has_quorum(height) is True

    block = Block(
        height=height,
        prev_hash=b"\x00" * 32,
        transactions=[],
        timestamp=time.time(),
        proposer_id="node-b",
    )
    poa.pending_proposal = block
    poa.acks_received[height] = {"node-b", "node-c"}
    poa.committing[height] = True

    poa.on_block_committed(height)
    assert poa.current_height == height
    assert poa.pending_proposal is None
    assert height not in poa.acks_received
    assert poa.committing.get(height) is None
