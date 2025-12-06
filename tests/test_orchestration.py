import time
import os
import threading

from src.chain.block import Block
from src.chain.blockchain import Blockchain
from src.node.node import Node
from src.common.config import Config


def _build_block(blockchain: Blockchain, height: int) -> Block:
    return Block(
        height=height,
        prev_hash=blockchain.get_latest_hash(),
        transactions=[],
        timestamp=time.time(),
        proposer_id="validator-1",
    )
    
def test_send_and_receive_blocks():
    try:
        os.remove("data/test1/chain.json") if os.path.exists("data/test1/chain.json") else None
        os.remove("data/test2/chain.json") if os.path.exists("data/test2/chain.json") else None
        blockchain1 = Blockchain(data_dir="data/test1")
        blockchain2 = Blockchain(data_dir="data/test2")
        
        block = _build_block(blockchain1, height=1)
        assert blockchain1.add_block(block)
        
        config = Config(config_path="config.yaml")
        
        peers = [
            {
                "hostname": config.get_hostname(), 
                "port": 8090
            },
            {
                "hostname": config.get_hostname(), 
                "port": 8091
            },
        ]
        
        config['network']['peers'] = peers
        
        config.config['node']['port'] = 8090
        node_1 = Node(config)
        
        config.config['node']['port'] = 8091
        node_2 = Node(config)
        
        t1 = threading.Thread(target=node_1.start, daemon=True)
        t2 = threading.Thread(target=node_2.start, daemon=True)
        
        t1.start()
        t2.start()
        
        time.sleep(1.5)
        
        node_1.blockchain = blockchain1
        node_2.blockchain = blockchain2
        
        node_1_blocks = node_1.blockchain.get_block_headers(1, 2)
        node_2_address = f"{node_2.network.hostname}:{node_2.network.port}"
        
        node_2_height_before = len(node_2.blockchain.chain)
        
        node_1.network.send_block(node_1_blocks, node_2_address)
        
        time.sleep(1.5)
        
        assert len(node_2.blockchain.chain) != node_2_height_before
        
        node_1.stop()
        node_2.stop()
        
        os.remove("data/test1/chain.json") if os.path.exists("data/test1/chain.json") else None
        os.remove("data/test2/chain.json") if os.path.exists("data/test2/chain.json") else None
    except Exception as e:
        os.remove("data/test1/chain.json") if os.path.exists("data/test1/chain.json") else None
        os.remove("data/test2/chain.json") if os.path.exists("data/test2/chain.json") else None
        raise e