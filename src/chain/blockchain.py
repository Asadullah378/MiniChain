"""Blockchain management and validation."""

from typing import List, Optional, Dict, Any, Tuple
from pathlib import Path
import json
import time
from src.chain.block import Block, Transaction, create_genesis_block
from src.common.logger import setup_logger
from src.common.config import Config

config = Config()

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
        # Initialize logger BEFORE calling _load_chain() since it uses self.logger
        self.logger = setup_logger(
            'minichain.blockchain',
            level='INFO',
            log_file=config.get('logging.file'),
            console=config.get('logging.console', True)
        )
        self._load_chain()
    
    def _load_chain(self):
        """Load blockchain from disk or create genesis block."""
        chain_file = self.data_dir / "chain.json"
        
        if chain_file.exists():
            try:
                self.logger.info(f" Loading blockchain from {chain_file}...")
                with open(chain_file, 'r') as f:
                    chain_data = json.load(f)
                    self.chain = [Block.from_dict(block_data) for block_data in chain_data]
                
                # Validate genesis block matches expected deterministic genesis
                if len(self.chain) > 0:
                    expected_genesis = create_genesis_block(proposer_id="genesis")
                    if self.chain[0].block_hash != expected_genesis.block_hash:
                        self.logger.warning(f" Genesis block doesn't match expected. Recreating chain.")
                        self._create_genesis()
                    else:
                        self.logger.info(f" Loaded blockchain with {len(self.chain)} block(s) from disk")
                        self.logger.debug(f"   Latest block: height={self.chain[-1].height}, hash={self.chain[-1].block_hash.hex()[:16]}...")
                else:
                    self.logger.warning(f" Chain file exists but is empty, creating genesis block")
                    self._create_genesis()
            except Exception as e:
                self.logger.error(f" Error loading chain from {chain_file}: {e}", exc_info=True)
                self.logger.info(f" Recreating blockchain with genesis block...")
                self._create_genesis()
        else:
            self.logger.info(f" Chain file not found, creating new blockchain with genesis block...")
            self._create_genesis()
    
    def _create_genesis(self):
        """Create and add genesis block."""
        # Use fixed proposer_id for deterministic genesis block
        self.logger.info(f" Creating genesis block...")
        genesis = create_genesis_block(proposer_id="genesis")
        self.chain = [genesis]
        self._save_chain()
        self.logger.info(f" Genesis block created: height=0, hash={genesis.block_hash.hex()[:16]}...")
    
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
        self.logger.debug(f" Validating block {block.height} before adding to chain...")
        if not self._validate_block(block):
            self.logger.warning(f" Block {block.height} validation failed, not adding to chain")
            return False
        
        self.logger.info(f" Adding block {block.height} to blockchain...")
        self.chain.append(block)
        self._save_chain()
        self.logger.info(f" Block {block.height} successfully added to blockchain (chain length: {len(self.chain)})")
        self.logger.debug(f"   Block hash: {block.block_hash.hex()[:16]}..., Transactions: {len(block.transactions)}")
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
            self.logger.warning(f" Block {block.height} structure validation failed")
            return False
        
        # Check height
        expected_height = self.get_height() + 1
        if block.height != expected_height:
            self.logger.warning(f" Height mismatch for block {block.height}: expected {expected_height}, got {block.height}")
            return False
        
        # Check previous hash
        latest_hash = self.get_latest_hash()
        if block.prev_hash != latest_hash:
            self.logger.warning(f" Previous hash mismatch for block {block.height}")
            self.logger.warning(f"   Expected: {latest_hash.hex()[:32]}...")
            self.logger.warning(f"   Got:      {block.prev_hash.hex()[:32]}...")
            return False
        
        self.logger.debug(f" Block {block.height} validation passed")
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

    def get_transaction(self, tx_id: str) -> Optional[Tuple[Transaction, int]]:
        """
        Find a transaction by ID in the blockchain.
        
        Args:
            tx_id: Transaction ID to find
            
        Returns:
            Tuple of (Transaction, block_height) if found, None otherwise
        """
        # This is a linear search, which is inefficient for large chains.
        # In a real blockchain, we'd use a transaction index (e.g., LevelDB/RocksDB).
        # For MiniChain, this is acceptable.
        for block in reversed(self.chain):
            for tx in block.transactions:
                if tx.tx_id == tx_id:
                    return tx, block.height
        return None

