"""Message types and serialization for P2P communication."""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from enum import Enum
import msgpack
import time


class MessageType(Enum):
    """Types of messages in the P2P network."""
    # Transaction messages
    TX = "TX"
    INV = "INV"
    GETTX = "GETTX"
    
    # Block synchronization
    GETHEADERS = "GETHEADERS"
    HEADERS = "HEADERS"
    GETBLOCKS = "GETBLOCKS"
    BLOCK = "BLOCK"
    
    # Consensus
    PROPOSE = "PROPOSE"
    ACK = "ACK"
    COMMIT = "COMMIT"
    VIEWCHANGE = "VIEWCHANGE"
    
    # Network maintenance
    HELLO = "HELLO"
    PEERLIST = "PEERLIST"
    HEARTBEAT = "HEARTBEAT"
    STATUS = "STATUS"
    
    # Sync and recovery
    SYNC_REQUEST = "SYNC_REQUEST"
    SYNC_RESPONSE = "SYNC_RESPONSE"
    MEMPOOL_SYNC = "MEMPOOL_SYNC"


@dataclass
class Message:
    """Base message structure for P2P communication."""
    
    type: MessageType
    sender_id: str
    timestamp: float = field(default_factory=time.time)
    signature: bytes = field(default=b'')
    payload: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert message to dictionary."""
        return {
            'type': self.type.value,
            'sender_id': self.sender_id,
            'timestamp': self.timestamp,
            'signature': self.signature.hex() if isinstance(self.signature, bytes) else self.signature,
            'payload': self.payload
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Message':
        """Create message from dictionary."""
        msg_type = MessageType(data['type'])
        signature = data.get('signature', b'')
        if isinstance(signature, str):
            signature = bytes.fromhex(signature)
        
        return cls(
            type=msg_type,
            sender_id=data['sender_id'],
            timestamp=data.get('timestamp', time.time()),
            signature=signature,
            payload=data.get('payload', {})
        )
    
    def serialize(self) -> bytes:
        """Serialize message to bytes."""
        return msgpack.packb(self.to_dict())
    
    @classmethod
    def deserialize(cls, data: bytes) -> 'Message':
        """Deserialize message from bytes."""
        return cls.from_dict(msgpack.unpackb(data, raw=False))
    
    @classmethod
    def create_tx(cls, sender_id: str, tx_bytes: bytes) -> 'Message':
        """Create a transaction message."""
        return cls(
            type=MessageType.TX,
            sender_id=sender_id,
            payload={'tx_bytes': tx_bytes.hex()}
        )
    
    @classmethod
    def create_propose(cls, sender_id: str, height: int, prev_hash: bytes, 
                      tx_list: List[bytes], proposer_id: str, 
                      block_hash: bytes, timestamp: float, signature: bytes) -> 'Message':
        """Create a block proposal message."""
        return cls(
            type=MessageType.PROPOSE,
            sender_id=sender_id,
            payload={
                'height': height,
                'prev_hash': prev_hash.hex(),
                'tx_list': [tx.hex() for tx in tx_list],
                'proposer_id': proposer_id,
                'block_hash': block_hash.hex(),
                'timestamp': timestamp,
                'signature': signature.hex()
            }
        )
    
    @classmethod
    def create_ack(cls, sender_id: str, height: int, block_hash: bytes, 
                  voter_id: str, signature: bytes) -> 'Message':
        """Create an ACK message."""
        return cls(
            type=MessageType.ACK,
            sender_id=sender_id,
            payload={
                'height': height,
                'block_hash': block_hash.hex(),
                'voter_id': voter_id,
                'signature': signature.hex()
            }
        )
    
    @classmethod
    def create_commit(cls, sender_id: str, height: int, block_hash: bytes,
                     leader_id: str, signature: bytes) -> 'Message':
        """Create a COMMIT message."""
        return cls(
            type=MessageType.COMMIT,
            sender_id=sender_id,
            payload={
                'height': height,
                'block_hash': block_hash.hex(),
                'leader_id': leader_id,
                'signature': signature.hex()
            }
        )
    
    @classmethod
    def create_hello(cls, sender_id: str, version: str, port: int) -> 'Message':
        """Create a HELLO message."""
        return cls(
            type=MessageType.HELLO,
            sender_id=sender_id,
            payload={
                'version': version,
                'listening_port': port
            }
        )
    
    @classmethod
    def create_heartbeat(cls, sender_id: str, height: int, last_block_hash: bytes,
                        current_view: int = 0, failed_validators: list = None) -> 'Message':
        """Create a HEARTBEAT message with view and failed validators info."""
        return cls(
            type=MessageType.HEARTBEAT,
            sender_id=sender_id,
            payload={
                'height': height,
                'last_block_hash': last_block_hash.hex(),
                'current_view': current_view,
                'failed_validators': failed_validators or []
            }
        )
    
    @classmethod
    def create_getheaders(cls, sender_id: str, from_height: int, to_height: int) -> 'Message':
        """Create a GETHEADERS message."""
        return cls(
            type=MessageType.GETHEADERS,
            sender_id=sender_id,
            payload={
                'from_height': from_height,
                'to_height': to_height
            }
        )
    
    @classmethod
    def create_getblocks(cls, sender_id: str, from_height: int, to_height: int) -> 'Message':
        """Create a GETBLOCKS message."""
        return cls(
            type=MessageType.GETBLOCKS,
            sender_id=sender_id,
            payload={
                'from_height': from_height,
                'to_height': to_height
            }
        )

    @classmethod
    def create_headers(cls, sender_id: str, headers: List[Dict[str, Any]]) -> 'Message':
        """Create a HEADERS message."""
        return cls(
            type=MessageType.HEADERS,
            sender_id=sender_id,
            payload={
                'headers': headers
            }
        )
        
    @classmethod
    def create_block(cls, sender_id: str, block: List[Dict[str, Any]]) -> 'Message':
        """Create a BLOCKS message."""
        return cls(
            type=MessageType.BLOCK,
            sender_id=sender_id,
            payload={
                'block': block
            }
        )
    
    @classmethod
    def create_viewchange(cls, sender_id: str, new_view: int, height: int, 
                          failed_leader: str, reason: str) -> 'Message':
        """Create a VIEWCHANGE message."""
        return cls(
            type=MessageType.VIEWCHANGE,
            sender_id=sender_id,
            payload={
                'new_view': new_view,
                'height': height,
                'failed_leader': failed_leader,
                'reason': reason
            }
        )
    
    @classmethod
    def create_sync_request(cls, sender_id: str, my_height: int, 
                            my_latest_hash: str) -> 'Message':
        """Create a SYNC_REQUEST message."""
        return cls(
            type=MessageType.SYNC_REQUEST,
            sender_id=sender_id,
            payload={
                'height': my_height,
                'latest_hash': my_latest_hash
            }
        )
    
    @classmethod
    def create_sync_response(cls, sender_id: str, height: int, 
                             latest_hash: str, blocks: List[Dict[str, Any]],
                             current_view: int = 0, failed_validators: list = None) -> 'Message':
        """Create a SYNC_RESPONSE message with view and failed validators info."""
        return cls(
            type=MessageType.SYNC_RESPONSE,
            sender_id=sender_id,
            payload={
                'height': height,
                'latest_hash': latest_hash,
                'blocks': blocks,
                'current_view': current_view,
                'failed_validators': failed_validators or []
            }
        )
    
    @classmethod
    def create_mempool_sync(cls, sender_id: str, 
                            transactions: List[Dict[str, Any]]) -> 'Message':
        """Create a MEMPOOL_SYNC message."""
        return cls(
            type=MessageType.MEMPOOL_SYNC,
            sender_id=sender_id,
            payload={
                'transactions': transactions
            }
        )