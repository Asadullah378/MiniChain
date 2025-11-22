"""Cryptographic utilities for MiniChain."""

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
from cryptography.hazmat.primitives import serialization
from typing import Tuple, Optional
import hashlib


class KeyPair:
    """Ed25519 key pair for signing and verification."""
    
    def __init__(self, private_key: Optional[Ed25519PrivateKey] = None):
        """
        Initialize key pair.
        
        Args:
            private_key: Existing private key. If None, generates a new one.
        """
        if private_key is None:
            self.private_key = Ed25519PrivateKey.generate()
        else:
            self.private_key = private_key
        self.public_key = self.private_key.public_key()
    
    @classmethod
    def from_private_bytes(cls, private_bytes: bytes) -> 'KeyPair':
        """Load key pair from private key bytes."""
        private_key = Ed25519PrivateKey.from_private_bytes(private_bytes)
        return cls(private_key)
    
    def get_private_bytes(self) -> bytes:
        """Get private key as bytes."""
        return self.private_key.private_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PrivateFormat.Raw,
            encryption_algorithm=serialization.NoEncryption()
        )
    
    def get_public_bytes(self) -> bytes:
        """Get public key as bytes."""
        return self.public_key.public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw
        )
    
    def sign(self, data: bytes) -> bytes:
        """Sign data with private key."""
        return self.private_key.sign(data)
    
    def verify(self, signature: bytes, data: bytes) -> bool:
        """Verify signature against data."""
        try:
            self.public_key.verify(signature, data)
            return True
        except Exception:
            return False


def hash_data(data: bytes) -> bytes:
    """Compute SHA-256 hash of data."""
    return hashlib.sha256(data).digest()


def hash_string(data: str) -> str:
    """Compute SHA-256 hash of string and return hex digest."""
    return hashlib.sha256(data.encode()).hexdigest()

