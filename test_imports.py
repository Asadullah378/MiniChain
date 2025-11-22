#!/usr/bin/env python3
"""Quick test to verify all imports work correctly."""

import sys

def test_imports():
    """Test that all modules can be imported."""
    print("Testing imports...")
    
    try:
        from src.common.config import Config
        print("✓ Config imported")
        
        from src.common.logger import setup_logger
        print("✓ Logger imported")
        
        from src.common.crypto import KeyPair, hash_data
        print("✓ Crypto imported")
        
        from src.chain.block import Block, Transaction, create_genesis_block
        print("✓ Block/Transaction imported")
        
        from src.chain.blockchain import Blockchain
        print("✓ Blockchain imported")
        
        from src.mempool.mempool import Mempool
        print("✓ Mempool imported")
        
        from src.consensus.poa import RoundRobinPoA
        print("✓ Consensus imported")
        
        from src.p2p.messages import Message, MessageType
        print("✓ Messages imported")
        
        from src.p2p.network import NetworkManager
        print("✓ Network imported")
        
        from src.node.node import Node
        print("✓ Node imported")
        
        print("\n✅ All imports successful!")
        return True
    
    except ImportError as e:
        print(f"\n❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = test_imports()
    sys.exit(0 if success else 1)

