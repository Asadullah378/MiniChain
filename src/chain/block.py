"""Block data structure for MiniChain."""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
import time
import msgpack
from src.common.crypto import hash_data


@dataclass
class Transaction:
    """Represents a transaction in the blockchain."""
    
    tx_id: str
    sender: str
    recipient: str
    amount: float
    timestamp: float
    signature: bytes = field(default=b'')
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert transaction to dictionary."""
        return {
            'tx_id': self.tx_id,
            'sender': self.sender,
            'recipient': self.recipient,
            'amount': self.amount,
            'timestamp': self.timestamp,
            'signature': self.signature.hex() if isinstance(self.signature, bytes) else self.signature
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Transaction':
        """Create transaction from dictionary."""
        sig = data.get('signature', b'')
        if isinstance(sig, str):
            sig = bytes.fromhex(sig)
        return cls(
            tx_id=data['tx_id'],
            sender=data['sender'],
            recipient=data['recipient'],
            amount=data['amount'],
            timestamp=data['timestamp'],
            signature=sig
        )
    
    def serialize(self) -> bytes:
        """Serialize transaction to bytes."""
        return msgpack.packb(self.to_dict())
    
    @classmethod
    def deserialize(cls, data: bytes) -> 'Transaction':
        """Deserialize transaction from bytes."""
        return cls.from_dict(msgpack.unpackb(data, raw=False))
    
    def get_hash(self) -> bytes:
        """Get hash of transaction."""
        # Hash everything except signature for consistency
        data = f"{self.tx_id}{self.sender}{self.recipient}{self.amount}{self.timestamp}".encode()
        return hash_data(data)


@dataclass
class Block:
    """Represents a block in the blockchain."""
    
    height: int
    prev_hash: bytes
    transactions: List[Transaction]
    timestamp: float
    proposer_id: str
    block_hash: bytes = field(default=b'')
    signature: bytes = field(default=b'')
    
    def __post_init__(self):
        """Compute block hash after initialization."""
        if not self.block_hash:
            self.block_hash = self.compute_hash()
    
    def compute_hash(self) -> bytes:
        """Compute hash of the block."""
        # Hash block header (excluding signature)
        tx_hashes = [tx.get_hash().hex() for tx in self.transactions]
        data = (
            f"{self.height}"
            f"{self.prev_hash.hex()}"
            f"{''.join(tx_hashes)}"
            f"{self.timestamp}"
            f"{self.proposer_id}"
        ).encode()
        return hash_data(data)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert block to dictionary."""
        return {
            'height': self.height,
            'prev_hash': self.prev_hash.hex() if isinstance(self.prev_hash, bytes) else self.prev_hash,
            'transactions': [tx.to_dict() for tx in self.transactions],
            'timestamp': self.timestamp,
            'proposer_id': self.proposer_id,
            'block_hash': self.block_hash.hex() if isinstance(self.block_hash, bytes) else self.block_hash,
            'signature': self.signature.hex() if isinstance(self.signature, bytes) else self.signature
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Block':
        """Create block from dictionary."""
        prev_hash = data.get('prev_hash', b'')
        if isinstance(prev_hash, str):
            prev_hash = bytes.fromhex(prev_hash)
        
        block_hash = data.get('block_hash', b'')
        if isinstance(block_hash, str):
            block_hash = bytes.fromhex(block_hash)
        
        signature = data.get('signature', b'')
        if isinstance(signature, str):
            signature = bytes.fromhex(signature)
        
        transactions = [Transaction.from_dict(tx) for tx in data.get('transactions', [])]
        
        block = cls(
            height=data['height'],
            prev_hash=prev_hash,
            transactions=transactions,
            timestamp=data['timestamp'],
            proposer_id=data['proposer_id'],
            block_hash=block_hash,
            signature=signature
        )
        return block
    
    def serialize(self) -> bytes:
        """Serialize block to bytes."""
        return msgpack.packb(self.to_dict())
    
    @classmethod
    def deserialize(cls, data: bytes) -> 'Block':
        """Deserialize block from bytes."""
        return cls.from_dict(msgpack.unpackb(data, raw=False))
    
    def is_valid(self) -> bool:
        """Validate block structure."""
        # Check hash matches
        computed_hash = self.compute_hash()
        if computed_hash != self.block_hash:
            return False
        
        # Check height is non-negative
        if self.height < 0:
            return False
        
        # Check transactions list
        if not isinstance(self.transactions, list):
            return False
        
        return True


def create_genesis_block(proposer_id: str = "genesis") -> Block:
    """Create the genesis block."""
    # Use fixed timestamp for deterministic genesis block across all nodes
    # This ensures all nodes have the same genesis block hash
    genesis_timestamp = 0.0  # Fixed timestamp for genesis
    return Block(
        height=0,
        prev_hash=b'\x00' * 32,  # All zeros for genesis
        transactions=[],
        timestamp=genesis_timestamp,
        proposer_id=proposer_id,
        block_hash=b''  # Will be computed in __post_init__
    )

