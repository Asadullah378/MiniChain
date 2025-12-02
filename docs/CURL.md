# MiniChain API Guide

This guide provides detailed `curl` examples for interacting with the MiniChain HTTP API.

## Prerequisites

Ensure the node is running with the API enabled:

```bash
# Start node with API on port 8080
./start.sh <hostname> --api-port 8080
```

All examples below assume the API is running at `http://localhost:8080`.

## Remote Access

To access the API from your local machine (e.g., laptop) while the node runs on a remote server (e.g., `svm-11`):

1.  **SSH with Port Forwarding**:
    ```bash
    ssh -L 8080:localhost:8080 user@svm-11.cs.helsinki.fi
    ```
2.  **Start Node on Remote**:
    ```bash
    ./start.sh svm-11.cs.helsinki.fi --api-port 8080
    ```
3.  **Access Locally**:
    Open `http://localhost:8080/status` in your local browser or use `curl`.

## Multi-Node Setup

To run a full network, you need to start nodes on different machines. Here is an example workflow using `melkki` as a jump host:

### 1. Start Node 1 (svm-11)
```bash
# Terminal 1 (Local)
ssh -L 8080:localhost:8080 -J user@melkki.cs.helsinki.fi user@svm-11.cs.helsinki.fi

# On svm-11
cd MiniChain
./start.sh svm-11.cs.helsinki.fi --api-port 8080
```

### 2. Start Node 2 (svm-11-2)
```bash
# Terminal 2 (Local)
ssh -J user@melkki.cs.helsinki.fi user@svm-11-2.cs.helsinki.fi

# On svm-11-2
cd MiniChain
./start.sh svm-11-2.cs.helsinki.fi
```

### 3. Start Node 3 (svm-11-3)
```bash
# Terminal 3 (Local)
ssh -J user@melkki.cs.helsinki.fi user@svm-11-3.cs.helsinki.fi

# On svm-11-3
cd MiniChain
./start.sh svm-11-3.cs.helsinki.fi
```

## Endpoint Summary

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/status` | Get node status (height, peers, leader) |
| `POST` | `/submit` | Submit a transaction |
| `GET` | `/blocks` | List recent blocks |
| `GET` | `/blocks/{height}` | Get block details |
| `GET` | `/mempool` | View pending transactions |
| `POST` | `/debug/mempool/clear` | Clear mempool (Debug) |
| `POST` | `/debug/network/disconnect` | Simulate network partition (Debug) |
| `POST` | `/debug/network/reconnect` | Reconnect network (Debug) |
| `POST` | `/debug/consensus/timeout` | Trigger consensus timeout (Debug) |

## Standard Endpoints

### 1. Check Node Status

Get the current status of the node, including block height, peer count, and leadership status.

```bash
curl -s http://localhost:8080/status | jq .
```

**Response:**
```json
{
  "node_id": "node1",
  "hostname": "node1",
  "height": 42,
  "latest_hash": "a1b2...",
  "peers": 2,
  "mempool_size": 0,
  "leader": "node2",
  "is_leader": false
}
```

### 2. Submit Transaction

Submit a new transaction to the network.

```bash
curl -s -X POST http://localhost:8080/submit \
  -H "Content-Type: application/json" \
  -d '{
    "sender": "alice",
    "recipient": "bob",
    "amount": 10.5
  }' | jq .
```

**Response:**
```json
{
  "status": "submitted",
  "tx_id": "f7e8..."
}
```

### 3. List Blocks

Retrieve a list of recent blocks.

**Parameters:**
- `start`: Starting block height (default: 0)
- `limit`: Number of blocks to retrieve (default: 10)

```bash
# Get last 5 blocks (assuming height is 100, start at 95)
curl -s "http://localhost:8080/blocks?start=95&limit=5" | jq .
```

### 4. Get Block Details

Get detailed information about a specific block, including its transactions.

```bash
# Get block at height 0 (Genesis)
curl -s http://localhost:8080/blocks/0 | jq .
```

### 5. Inspect Mempool

View all pending transactions currently in the mempool.

```bash
curl -s http://localhost:8080/mempool | jq .
```

## Debug Endpoints

These endpoints are useful for testing and simulating network conditions.

### 1. Clear Mempool

Remove all transactions from the mempool.

```bash
curl -s -X POST http://localhost:8080/debug/mempool/clear
```

### 2. Simulate Network Partition

Disconnect the node from all peers to simulate a network partition.

```bash
curl -s -X POST http://localhost:8080/debug/network/disconnect
```

### 3. Reconnect Network

Reconnect to peers after a simulated partition.

```bash
curl -s -X POST http://localhost:8080/debug/network/reconnect
```

### 4. Trigger Consensus Timeout

Simulate a consensus timeout (e.g., to force a view change).

```bash
curl -s -X POST http://localhost:8080/debug/consensus/timeout
```
