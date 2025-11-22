"""Blockchain management and validation."""

from typing import List, Optional, Dict, Any
from pathlib import Path
import json
import time
from src.chain.block import Block, Transaction, create_genesis_block


class Blockchain:
    """Manages the blockchain state and operations."""
    
    def __init__(self, data_dir: str = "data"):
        """
        Initialize blockchain.
        
        Args:
            data_dir: Directory to store blockchain data
        """
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.chain: List[Block] = []
        self._load_chain()
    
    def _load_chain(self):
        """Load blockchain from disk or create genesis block."""
        chain_file = self.data_dir / "chain.json"
        
        if chain_file.exists():
            try:
                with open(chain_file, 'r') as f:
                    chain_data = json.load(f)
                    self.chain = [Block.from_dict(block_data) for block_data in chain_data]
                
                # Validate genesis block matches expected deterministic genesis
                if len(self.chain) > 0:
                    expected_genesis = create_genesis_block(proposer_id="genesis")
                    if self.chain[0].block_hash != expected_genesis.block_hash:
                        print(f"Warning: Genesis block doesn't match expected. Recreating chain.")
                        self._create_genesis()
                    else:
                        print(f"Loaded blockchain with {len(self.chain)} blocks")
                else:
                    self._create_genesis()
            except Exception as e:
                print(f"Error loading chain: {e}. Creating new chain.")
                self._create_genesis()
        else:
            self._create_genesis()
    
    def _create_genesis(self):
        """Create and add genesis block."""
        # Use fixed proposer_id for deterministic genesis block
        genesis = create_genesis_block(proposer_id="genesis")
        self.chain = [genesis]
        self._save_chain()
    
    def _save_chain(self):
        """Save blockchain to disk."""
        chain_file = self.data_dir / "chain.json"
        chain_data = [block.to_dict() for block in self.chain]
        
        with open(chain_file, 'w') as f:
            json.dump(chain_data, f, indent=2)
    
    def get_height(self) -> int:
        """Get current blockchain height."""
        return len(self.chain) - 1
    
    def get_latest_block(self) -> Block:
        """Get the latest block in the chain."""
        return self.chain[-1]
    
    def get_latest_hash(self) -> bytes:
        """Get hash of the latest block."""
        return self.get_latest_block().block_hash
    
    def add_block(self, block: Block) -> bool:
        """
        Add a block to the blockchain if valid.
        
        Args:
            block: Block to add
        
        Returns:
            True if block was added, False otherwise
        """
        if not self._validate_block(block):
            return False
        
        self.chain.append(block)
        self._save_chain()
        return True
    
    def _validate_block(self, block: Block) -> bool:
        """
        Validate a block before adding to chain.
        
        Args:
            block: Block to validate
        
        Returns:
            True if valid, False otherwise
        """
        # Check block structure
        if not block.is_valid():
            return False
        
        # Check height
        expected_height = self.get_height() + 1
        if block.height != expected_height:
            return False
        
        # Check previous hash
        if block.prev_hash != self.get_latest_hash():
            return False
        
        return True
    
    def get_block(self, height: int) -> Optional[Block]:
        """Get block at specific height."""
        if 0 <= height < len(self.chain):
            return self.chain[height]
        return None
    
    def get_blocks(self, from_height: int, to_height: int) -> List[Block]:
        """Get range of blocks."""
        return self.chain[from_height:to_height + 1]
    
    def get_block_headers(self, from_height: int, to_height: int) -> List[Dict[str, Any]]:
        """Get block headers (metadata only) for a range."""
        blocks = self.get_blocks(from_height, to_height)
        return [
            {
                'height': block.height,
                'block_hash': block.block_hash.hex(),
                'prev_hash': block.prev_hash.hex(),
                'proposer_id': block.proposer_id,
                'timestamp': block.timestamp,
                'tx_count': len(block.transactions)
            }
            for block in blocks
        ]
    
    def find_fork_point(self, other_chain: List[Block]) -> int:
        """
        Find the height where this chain and another chain diverge.
        
        Args:
            other_chain: Another blockchain to compare
        
        Returns:
            Height of the last common block
        """
        min_len = min(len(self.chain), len(other_chain))
        
        for i in range(min_len):
            if self.chain[i].block_hash != other_chain[i].block_hash:
                return i - 1
        
        return min_len - 1
    
    def replace_chain(self, new_chain: List[Block]) -> bool:
        """
        Replace current chain with a new one if it's longer and valid.
        
        Args:
            new_chain: New blockchain to replace current one
        
        Returns:
            True if chain was replaced, False otherwise
        """
        # Check if new chain is longer
        if len(new_chain) <= len(self.chain):
            return False
        
        # Validate new chain
        if not self._validate_chain(new_chain):
            return False
        
        # Replace chain
        self.chain = new_chain
        self._save_chain()
        return True
    
    def _validate_chain(self, chain: List[Block]) -> bool:
        """Validate an entire chain."""
        if not chain:
            return False
        
        # Check genesis block
        if chain[0].height != 0:
            return False
        
        # Check each block links to previous
        for i in range(1, len(chain)):
            if not chain[i].is_valid():
                return False
            if chain[i].prev_hash != chain[i - 1].block_hash:
                return False
            if chain[i].height != i:
                return False
        
        return True
    
    def get_all_transactions(self) -> List[Transaction]:
        """Get all transactions in the blockchain."""
        transactions = []
        for block in self.chain:
            transactions.extend(block.transactions)
        return transactions

