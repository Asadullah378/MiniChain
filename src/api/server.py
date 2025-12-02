import threading
import uvicorn
from fastapi import FastAPI, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Any
import time

from src.node.node import Node
from src.chain.block import Transaction

app = FastAPI(title="MiniChain API")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global node instance
node: Optional[Node] = None

class TransactionModel(BaseModel):
    sender: str
    recipient: str
    amount: float

@app.get("/status")
async def get_status():
    if not node:
        raise HTTPException(status_code=503, detail="Node not initialized")
    
    height = node.blockchain.get_height()
    return {
        "node_id": node.config.get_node_id(),
        "hostname": node.config.get_hostname(),
        "height": height,
        "latest_hash": node.blockchain.get_latest_hash().hex(),
        "peers": len(node.network.connections),
        "mempool_size": node.mempool.size(),
        "leader": node.consensus.get_current_leader(height + 1),
        "is_leader": node.consensus.is_leader(height + 1)
    }

@app.get("/blocks")
async def get_blocks(start: int = 0, limit: int = 10):
    if not node:
        raise HTTPException(status_code=503, detail="Node not initialized")
    
    height = node.blockchain.get_height()
    # Adjust start to be 0-indexed logic if needed, but blockchain usually 0-indexed
    # If user wants "last 10", they might need to calculate, or we provide reverse order
    # For now, simple range
    
    blocks = []
    for h in range(start, min(start + limit, height + 1)):
        block = node.blockchain.get_block(h)
        if block:
            blocks.append({
                "height": block.height,
                "hash": block.block_hash.hex(),
                "prev_hash": block.prev_hash.hex(),
                "proposer": block.proposer_id,
                "timestamp": block.timestamp,
                "tx_count": len(block.transactions)
            })
    return blocks

@app.get("/blocks/{height}")
async def get_block(height: int):
    if not node:
        raise HTTPException(status_code=503, detail="Node not initialized")
    
    block = node.blockchain.get_block(height)
    if not block:
        raise HTTPException(status_code=404, detail="Block not found")
    
    return {
        "height": block.height,
        "hash": block.block_hash.hex(),
        "prev_hash": block.prev_hash.hex(),
        "proposer": block.proposer_id,
        "timestamp": block.timestamp,
        "transactions": [
            {
                "id": tx.tx_id,
                "sender": tx.sender,
                "recipient": tx.recipient,
                "amount": tx.amount,
                "timestamp": tx.timestamp
            }
            for tx in block.transactions
        ]
    }

@app.get("/mempool")
async def get_mempool():
    if not node:
        raise HTTPException(status_code=503, detail="Node not initialized")
    
    txs = node.mempool.get_all_transactions()
    return [
        {
            "id": tx.tx_id,
            "sender": tx.sender,
            "recipient": tx.recipient,
            "amount": tx.amount,
            "timestamp": tx.timestamp
        }
        for tx in txs
    ]

@app.post("/submit")
async def submit_transaction(tx_data: TransactionModel):
    if not node:
        raise HTTPException(status_code=503, detail="Node not initialized")
    
    from src.common.crypto import hash_string
    
    # Generate ID
    tx_id = hash_string(f"{tx_data.sender}{tx_data.recipient}{tx_data.amount}{time.time()}")[:16]
    
    tx = Transaction(
        tx_id=tx_id,
        sender=tx_data.sender,
        recipient=tx_data.recipient,
        amount=tx_data.amount,
        timestamp=time.time()
    )
    
    if node.submit_transaction(tx):
        return {"status": "submitted", "tx_id": tx_id}
    else:
        raise HTTPException(status_code=400, detail="Transaction rejected (duplicate?)")

# --- Debug Endpoints ---

@app.post("/debug/mempool/clear")
async def clear_mempool():
    if not node:
        raise HTTPException(status_code=503, detail="Node not initialized")
    
    # Access private attribute directly for debug
    node.mempool.transactions.clear()
    return {"status": "mempool cleared"}

@app.post("/debug/consensus/timeout")
async def trigger_timeout():
    if not node:
        raise HTTPException(status_code=503, detail="Node not initialized")
    
    # Force a view change by manipulating last_block_time or similar?
    # Or just skip the current leader?
    # For RoundRobinPoA, it's deterministic based on height.
    # To simulate a timeout, we might need to fake a "skip" or just wait.
    # Actually, RoundRobin doesn't really "timeout" in the same way PBFT does unless we implement view change.
    # The current implementation (checked in node.py) has a placeholder _check_timeouts.
    # So this might be a no-op unless we implement that logic.
    # Let's just log for now.
    node.logger.warning("DEBUG: Triggered timeout simulation (not fully implemented in consensus)")
    return {"status": "timeout triggered (check logs)"}

@app.post("/debug/network/disconnect")
async def disconnect_network():
    if not node:
        raise HTTPException(status_code=503, detail="Node not initialized")
    
    # Close all connections
    count = len(node.network.connections)
    # We need to access the network manager's connection list
    # This is a bit hacky, but it's for debug
    for peer_addr, conn in list(node.network.connections.items()):
        try:
            conn.close()
        except:
            pass
    node.network.connections.clear()
    return {"status": "disconnected", "peers_removed": count}

@app.post("/debug/network/reconnect")
async def reconnect_network():
    if not node:
        raise HTTPException(status_code=503, detail="Node not initialized")
    
    # Trigger connection logic
    node.network.connect_to_peers()
    return {"status": "reconnection triggered"}


def start_api_server(node_instance: Node, port: int):
    """Start the API server."""
    global node
    node = node_instance
    
    # Run uvicorn
    # We run this in the main thread usually, but node.start() blocks.
    # So we'll run uvicorn in a thread or vice versa.
    # Since uvicorn handles signals well, it's often better to run it in main.
    # But Node has its own loop.
    # Let's run uvicorn in a thread for now to keep main.py logic similar.
    
    config = uvicorn.Config(app, host="0.0.0.0", port=port, log_level="info")
    server = uvicorn.Server(config)
    
    # Run in a separate thread
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    return server
