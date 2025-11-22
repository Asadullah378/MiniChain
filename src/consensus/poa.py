"""Proof-of-Authority consensus with round-robin leader selection."""

from typing import List, Dict, Optional, Set
import time
from src.chain.block import Block, Transaction
from src.mempool.mempool import Mempool


class RoundRobinPoA:
    """Round-robin Proof-of-Authority consensus."""
    
    def __init__(self, node_id: str, validator_ids: List[str], 
                 block_interval: int = 5, proposal_timeout: int = 10,
                 quorum_size: int = 2):
        """
        Initialize PoA consensus.
        
        Args:
            node_id: This node's ID
            validator_ids: List of all validator node IDs (must include node_id)
            block_interval: Seconds between block proposals
            proposal_timeout: Seconds to wait for ACKs before timeout
            quorum_size: Minimum number of ACKs needed (including proposer)
        """
        self.node_id = node_id
        self.validator_ids = sorted(validator_ids)  # Deterministic ordering
        self.block_interval = block_interval
        self.proposal_timeout = proposal_timeout
        self.quorum_size = quorum_size
        
        if node_id not in validator_ids:
            raise ValueError(f"Node {node_id} must be in validator list")
        
        self.current_height = 0
        self.pending_proposal: Optional[Block] = None
        self.acks_received: Dict[int, Set[str]] = {}  # height -> set of voter IDs
        self.last_block_time = time.time()
    
    def get_current_leader(self, height: int) -> str:
        """
        Get the leader for a given height using round-robin.
        
        Args:
            height: Block height
        
        Returns:
            Leader node ID
        """
        if not self.validator_ids:
            return self.node_id
        return self.validator_ids[height % len(self.validator_ids)]
    
    def is_leader(self, height: int) -> bool:
        """Check if this node is the leader for the given height."""
        return self.get_current_leader(height) == self.node_id
    
    def should_propose(self) -> bool:
        """Check if it's time to propose a new block."""
        if not self.is_leader(self.current_height + 1):
            return False
        
        elapsed = time.time() - self.last_block_time
        return elapsed >= self.block_interval
    
    def create_proposal(self, mempool: Mempool, prev_hash: bytes, 
                       max_txs: int = 100) -> Optional[Block]:
        """
        Create a block proposal from mempool transactions.
        
        Args:
            mempool: Mempool to get transactions from
            prev_hash: Hash of previous block
            max_txs: Maximum transactions to include
        
        Returns:
            Proposed block or None if no transactions
        """
        txs = mempool.get_transactions(max_txs)
        if not txs:
            return None
        
        height = self.current_height + 1
        block = Block(
            height=height,
            prev_hash=prev_hash,
            transactions=txs,
            timestamp=time.time(),
            proposer_id=self.node_id
        )
        
        return block
    
    def add_ack(self, height: int, voter_id: str):
        """Record an ACK vote for a block proposal."""
        if height not in self.acks_received:
            self.acks_received[height] = set()
        self.acks_received[height].add(voter_id)
    
    def has_quorum(self, height: int) -> bool:
        """
        Check if we have enough ACKs for a block at given height.
        
        Args:
            height: Block height
        
        Returns:
            True if quorum reached
        """
        if height not in self.acks_received:
            return False
        
        # Quorum includes the proposer (leader)
        acks = self.acks_received[height]
        leader = self.get_current_leader(height)
        
        # Count unique validators who ACKed (including leader if they self-ACK)
        unique_voters = len(acks)
        if leader in acks:
            # Leader counts as 1 vote
            return unique_voters >= self.quorum_size
        else:
            # Need quorum_size - 1 other validators + leader = quorum_size total
            return unique_voters >= (self.quorum_size - 1)
    
    def clear_acks(self, height: int):
        """Clear ACKs for a given height."""
        if height in self.acks_received:
            del self.acks_received[height]
    
    def on_block_committed(self, height: int):
        """Called when a block is committed to update state."""
        self.current_height = height
        self.last_block_time = time.time()
        self.pending_proposal = None
        self.clear_acks(height)
    
    def get_next_leader(self, current_height: int) -> str:
        """Get the next leader after current height."""
        return self.get_current_leader(current_height + 1)
    
    def should_trigger_view_change(self, height: int, timeout_elapsed: bool) -> bool:
        """
        Determine if view change should be triggered.
        
        Args:
            height: Expected block height
            timeout_elapsed: Whether proposal timeout has elapsed
        
        Returns:
            True if view change should be triggered
        """
        if not timeout_elapsed:
            return False
        
        # Check if current leader is still expected leader
        expected_leader = self.get_current_leader(height)
        return expected_leader == self.get_current_leader(height - 1)

