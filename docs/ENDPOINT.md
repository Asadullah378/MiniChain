# API Documentation for Frontend Developers

Base URL: `http://localhost:8080` (or configured port)

## Overview

This API allows the frontend to interact with the MiniChain node. All responses are in JSON format.

## Endpoints

| Method | Endpoint                | Description                                    | Auth |
| ------ | ----------------------- | ---------------------------------------------- | ---- |
| `GET`  | `/status`               | Get current node status                        | No   |
| `GET`  | `/blocks`               | List recent blocks (paginated)                 | No   |
| `GET`  | `/blocks/{height}`      | Get details of a specific block                | No   |
| `GET`  | `/mempool`              | List pending transactions                      | No   |
| `POST` | `/submit`               | Submit a new transaction                       | No   |
| `GET`  | `/transactions/{tx_id}` | Get a transaction by id (pending or confirmed) | No   |
| `GET`  | `/peers/status`         | Get peer connection and validator status       | No   |
| `POST` | `/sync/request`         | Manually trigger a sync with peers             | No   |
| `GET`  | `/logs`                 | Fetch recent log entries (filterable)          | No   |
| `GET`  | `/logs/stream`          | Stream logs via SSE                            | No   |
| `POST` | `/shutdown`             | Gracefully shutdown the node                   | No   |

---

## Detailed Specifications

### 1. Get Node Status

Returns the current state of the node, including sync status and peer connections.

- **Endpoint**: `/status`
- **Method**: `GET`

**Response:**

```json
{
  "node_id": "string", // Unique ID of this node
  "height": "number", // Current blockchain height
  "peers_count": "number", // Number of connected peers
  "mempool_size": "number", // Number of pending transactions
  "leader": "string" // Current consensus leader ID
}
```

**Example:**

```json
{
  "node_id": "svm-11.cs.helsinki.fi",
  "height": 42,
  "peers_count": 2,
  "mempool_size": 0,
  "leader": "svm-11-2.cs.helsinki.fi"
}
```

---

### 2. List Blocks

Retrieve a list of blocks, useful for displaying the blockchain history.

- **Endpoint**: `/blocks`
- **Method**: `GET`
- **Query Parameters**:
  - `start` (optional): Start height (default: 0)
  - `limit` (optional): Number of blocks to return (default: 10)

**Response:**
Array of Block objects.

```json
[
  {
    "height": "number",
    "block_hash": "string (hex)",
    "prev_hash": "string (hex)",
    "proposer_id": "string",
    "timestamp": "number (unix)",
    "tx_count": "number"
  }
]
```

**Example:**

```json
[
  {
    "height": 5,
    "block_hash": "a1b2...",
    "prev_hash": "c3d4...",
    "proposer_id": "node-1",
    "timestamp": 1678901234,
    "tx_count": 2
  }
]
```

---

### 3. Get Block Details

Get full details of a specific block, including all transactions.

- **Endpoint**: `/blocks/{height}`
- **Method**: `GET`
- **Path Parameters**:
  - `height`: The block number (integer)

**Response:**

```json
{
  "height": "number",
  "block_hash": "string (hex)",
  "prev_hash": "string (hex)",
  "proposer_id": "string",
  "timestamp": "number",
  "transactions": [
    {
      "id": "string (uuid)",
      "sender": "string",
      "recipient": "string",
      "amount": "number",
      "timestamp": "number",
      "signature": "string"
    }
  ]
}
```

**Error (404):**

```json
{
  "detail": "Block not found"
}
```

---

### 4. Get Mempool

Get list of pending transactions waiting to be included in a block.

- **Endpoint**: `/mempool`
- **Method**: `GET`

**Response:**
Array of transactions.

```json
[
  {
    "id": "string",
    "sender": "string",
    "recipient": "string",
    "amount": "number",
    "timestamp": "number"
  }
]
```

---

### 5. Submit Transaction

Submit a new transaction to the network.

- **Endpoint**: `/submit`
- **Method**: `POST`
- **Content-Type**: `application/json`

**Request Body:**

```json
{
  "sender": "string", // Sender ID (e.g., "alice")
  "recipient": "string", // Recipient ID (e.g., "bob")
  "amount": "number" // Amount to transfer
}
```

**Response (200):**

```json
{
  "status": "submitted",
  "tx_id": "string"
}
```

### 6. Get Transaction Details

Return transaction info whether it's still pending (mempool) or confirmed on-chain.

- **Endpoint**: `/transactions/{tx_id}`
- **Method**: `GET`

**Response (200):**

```json
{
  "id": "string",
  "sender": "string",
  "recipient": "string",
  "amount": "number",
  "timestamp": "number",
  "status": "Pending | Confirmed",
  "block_height": "number | null"
}
```

**Error (404):**

```json
{
  "detail": "Transaction not found"
}
```

---

## Node Control & Logs

### Peers Status

- **Endpoint**: `/peers/status`
- **Method**: `GET`

Returns connectivity and validator status.

### Request Sync

- **Endpoint**: `/sync/request`
- **Method**: `POST`

Triggers a manual synchronization with peers.

### Fetch Logs

- **Endpoint**: `/logs`
- **Method**: `GET`
- **Query**: `lines`, `level`, `tail`

Returns parsed log entries, optionally filtered.

### Stream Logs (SSE)

- **Endpoint**: `/logs/stream`
- **Method**: `GET`
- **Query**: `level`

Streams log entries in real-time via Server-Sent Events.

### Shutdown Node

- **Endpoint**: `/shutdown`
- **Method**: `POST`

Initiates graceful shutdown of the node.

**Error (400):**

```json
{
  "detail": "Transaction rejected (duplicate?)"
}
```

---

## Debug Endpoints (Dev Only)

These endpoints are for testing and debugging purposes.

| Method | Endpoint                    | Description                                       |
| ------ | --------------------------- | ------------------------------------------------- |
| `POST` | `/debug/mempool/clear`      | Clear all pending transactions                    |
| `POST` | `/debug/network/disconnect` | Disconnect from all peers to simulate a partition |
| `POST` | `/debug/network/reconnect`  | Reconnect to peers after a partition              |
| `POST` | `/debug/consensus/timeout`  | Trigger a consensus timeout (force view change)   |
| `POST` | `/debug/network/disconnect` | Disconnect from all peers                         |
| `POST` | `/debug/network/reconnect`  | Reconnect to peers                                |
| `POST` | `/debug/consensus/timeout`  | Trigger consensus timeout                         |
