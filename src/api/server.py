import threading
import uvicorn
from fastapi import FastAPI, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Optional, Any
import time
import asyncio
import json
from pathlib import Path

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
        "peers": len(node.network.peers),
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

@app.get("/transactions/{tx_id}")
async def get_transaction_details(tx_id: str):
    if not node:
        raise HTTPException(status_code=503, detail="Node not initialized")
    
    # 1. Check Mempool
    tx = node.mempool.get_transaction(tx_id)
    if tx:
        return {
            "id": tx.tx_id,
            "sender": tx.sender,
            "recipient": tx.recipient,
            "amount": tx.amount,
            "timestamp": tx.timestamp,
            "status": "Pending",
            "block_height": None
        }
    
    # 2. Check Blockchain
    result = node.blockchain.get_transaction(tx_id)
    if result:
        tx, height = result
        return {
            "id": tx.tx_id,
            "sender": tx.sender,
            "recipient": tx.recipient,
            "amount": tx.amount,
            "timestamp": tx.timestamp,
            "status": "Confirmed",
            "block_height": height
        }
        
    raise HTTPException(status_code=404, detail="Transaction not found")

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

@app.get("/logs")
async def get_logs(lines: int = 100, level: Optional[str] = None, tail: bool = True):
    """
    Get log entries from the log file.
    
    Args:
        lines: Number of lines to return (default: 100)
        level: Filter by log level (DEBUG, INFO, WARNING, ERROR, CRITICAL). If None, returns all.
        tail: If True, return last N lines. If False, return first N lines (default: True)
    
    Returns:
        Dictionary with log entries and metadata
    """
    if not node:
        raise HTTPException(status_code=503, detail="Node not initialized")
    
    log_file = node.config.get('logging.file', 'minichain.log')
    if not log_file:
        raise HTTPException(status_code=404, detail="No log file configured")
    
    from pathlib import Path
    import os
    
    log_path = Path(log_file)
    
    # Handle relative paths - try in current directory and data directory
    if not log_path.is_absolute():
        # Try current directory first
        if not log_path.exists():
            # Try in data directory
            data_dir = node.config.get_data_dir()
            log_path = Path(data_dir) / log_file
        else:
            log_path = Path(log_file)
    
    if not log_path.exists():
        raise HTTPException(status_code=404, detail=f"Log file not found: {log_file}")
    
    try:
        # Read log file
        with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
            all_lines = f.readlines()
        
        # Filter by level if specified
        if level:
            level_upper = level.upper()
            filtered_lines = []
            for line in all_lines:
                # Log format: "YYYY-MM-DD HH:MM:SS - logger_name - LEVEL - message"
                if f" - {level_upper} -" in line or f" - {level_upper} " in line:
                    filtered_lines.append(line)
            all_lines = filtered_lines
        
        # Get requested lines (tail or head)
        if tail:
            log_lines = all_lines[-lines:] if len(all_lines) > lines else all_lines
        else:
            log_lines = all_lines[:lines] if len(all_lines) > lines else all_lines
        
        # Parse log entries
        log_entries = []
        for line in log_lines:
            line = line.strip()
            if not line:
                continue
            
            # Parse log line: "YYYY-MM-DD HH:MM:SS - logger_name - LEVEL - message"
            parts = line.split(' - ', 3)
            if len(parts) >= 4:
                timestamp = parts[0]
                logger_name = parts[1]
                log_level = parts[2]
                message = parts[3]
                
                log_entries.append({
                    "timestamp": timestamp,
                    "logger": logger_name,
                    "level": log_level,
                    "message": message,
                    "raw": line
                })
            else:
                # If parsing fails, include as raw line
                log_entries.append({
                    "timestamp": "",
                    "logger": "",
                    "level": "UNKNOWN",
                    "message": line,
                    "raw": line
                })
        
        return {
            "total_lines": len(all_lines),
            "returned_lines": len(log_entries),
            "level_filter": level,
            "entries": log_entries
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading log file: {str(e)}")


@app.get("/logs/stream")
async def stream_logs(level: Optional[str] = None):
    """
    Stream log entries in real-time using Server-Sent Events (SSE).
    
    Args:
        level: Filter by log level (DEBUG, INFO, WARNING, ERROR, CRITICAL). If None, streams all.
    
    Returns:
        StreamingResponse with SSE format
    """
    if not node:
        raise HTTPException(status_code=503, detail="Node not initialized")
    
    log_file = node.config.get('logging.file', 'minichain.log')
    if not log_file:
        raise HTTPException(status_code=404, detail="No log file configured")
    
    log_path = Path(log_file)
    
    # Handle relative paths
    if not log_path.is_absolute():
        if not log_path.exists():
            data_dir = node.config.get_data_dir()
            log_path = Path(data_dir) / log_file
        else:
            log_path = Path(log_file)
    
    if not log_path.exists():
        raise HTTPException(status_code=404, detail=f"Log file not found: {log_file}")
    
    async def generate_log_stream():
        """Generator function that yields log entries as SSE events."""
        last_position = log_path.stat().st_size if log_path.exists() else 0
        
        # Send initial batch of recent logs (last 50 lines)
        try:
            with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
                # Send last 50 lines in reverse order (newest first)
                for line in reversed(lines[-50:]):
                    line = line.strip()
                    if not line:
                        continue
                    
                    # Filter by level if specified
                    if level:
                        level_upper = level.upper()
                        if f" - {level_upper} -" not in line and f" - {level_upper} " not in line:
                            continue
                    
                    # Parse log line
                    parts = line.split(' - ', 3)
                    if len(parts) >= 4:
                        entry = {
                            "timestamp": parts[0],
                            "logger": parts[1],
                            "level": parts[2],
                            "message": parts[3],
                            "raw": line
                        }
                    else:
                        entry = {
                            "timestamp": "",
                            "logger": "",
                            "level": "UNKNOWN",
                            "message": line,
                            "raw": line
                        }
                    
                    yield f"data: {json.dumps(entry)}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
            return
        
        # Now stream new log entries as they appear
        while True:
            try:
                if not log_path.exists():
                    await asyncio.sleep(1)
                    continue
                
                current_size = log_path.stat().st_size
                
                if current_size > last_position:
                    # New content available
                    try:
                        with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
                            f.seek(last_position)
                            new_content = f.read()
                            
                            # Split into lines, handling partial lines
                            lines = new_content.split('\n')
                            
                            # Process complete lines (all except possibly the last one)
                            for line in lines[:-1]:
                                line = line.strip()
                                if not line:
                                    continue
                                
                                # Filter by level if specified
                                if level:
                                    level_upper = level.upper()
                                    if f" - {level_upper} -" not in line and f" - {level_upper} " not in line:
                                        continue
                                
                                # Parse log line
                                parts = line.split(' - ', 3)
                                if len(parts) >= 4:
                                    entry = {
                                        "timestamp": parts[0],
                                        "logger": parts[1],
                                        "level": parts[2],
                                        "message": parts[3],
                                        "raw": line
                                    }
                                else:
                                    entry = {
                                        "timestamp": "",
                                        "logger": "",
                                        "level": "UNKNOWN",
                                        "message": line,
                                        "raw": line
                                    }
                                
                                yield f"data: {json.dumps(entry)}\n\n"
                            
                            # Update position (including partial line if any)
                            last_position = f.tell()
                    except (IOError, OSError) as e:
                        # File might be locked or deleted, wait and retry
                        await asyncio.sleep(0.5)
                        continue
                else:
                    # No new content, send keepalive periodically
                    yield ": keepalive\n\n"
                
                # Wait before checking again
                await asyncio.sleep(0.3)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                yield f"data: {json.dumps({'error': str(e)})}\n\n"
                await asyncio.sleep(1)
    
    return StreamingResponse(
        generate_log_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"  # Disable nginx buffering
        }
    )


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
