# MiniChain CLI Guide

The MiniChain CLI provides an interactive interface to interact with your blockchain node. When you start a node, the CLI automatically launches and allows you to submit transactions, view blockchain state, and monitor node status.

## Starting the Node with CLI

By default, the CLI is enabled:

```bash
python src/main.py --node-id svm-11 --port 8000 --peers "..."
```

To run without CLI (background mode):

```bash
python src/main.py --node-id svm-11 --port 8000 --peers "..." --no-cli
```

## Available Commands

### `help` or `h`
Show help message with all available commands.

```
minichain> help
```

### `submit` or `tx`
Submit a new transaction to the blockchain.

**Usage:** `submit <sender> <recipient> <amount>`

**Example:**
```
minichain> submit alice bob 10.5
✓ Transaction submitted: a1b2c3d4e5f6g7h8
  alice -> bob: 10.5
```

The transaction will be:
- Added to the local mempool
- Broadcast to all connected peers
- Included in the next block when the leader proposes

### `status` or `info`
Display current node status and blockchain information.

```
minichain> status
============================================================
Node Status
============================================================
Node ID:        svm-11
Hostname:       svm-11.cs.helsinki.fi
Port:           8000
Blockchain Height: 5
Latest Block Hash: 1a2b3c4d5e6f7g8h9...
Mempool Size:   3 transactions
Connected Peers: 2
Current Leader: svm-11-2
I am Leader:    No (for next block)
============================================================
```

### `chain` or `blocks`
Show a summary of recent blocks in the blockchain.

**Usage:** `chain [limit]` (default: 10)

**Example:**
```
minichain> chain 5
Blockchain (showing last 5 blocks):
================================================================================
Height   Hash                 Prev Hash            TXs    Proposer        Time
--------------------------------------------------------------------------------
2        a1b2c3d4e5f6g7h8i9   z9y8x7w6v5u4t3s2r1   3      svm-11         14:23:15
3        b2c3d4e5f6g7h8i9j0   a1b2c3d4e5f6g7h8i9   2      svm-11-2       14:23:20
4        c3d4e5f6g7h8i9j0k1   b2c3d4e5f6g7h8i9j0   1      svm-11-3       14:23:25
5        d4e5f6g7h8i9j0k1l2   c3d4e5f6g7h8i9j0k1   4      svm-11         14:23:30
6        e5f6g7h8i9j0k1l2m3   d4e5f6g7h8i9j0k1l2   2      svm-11-2       14:23:35
================================================================================
```

### `block <height>`
Show detailed information about a specific block.

**Usage:** `block <height>`

**Example:**
```
minichain> block 5

Block #5:
============================================================
Height:      5
Hash:        d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0u1v2
Prev Hash:   c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0u1
Proposer:    svm-11
Timestamp:   Mon Dec 15 14:23:30 2025
Transactions: 4

Transactions:
------------------------------------------------------------
  1. a1b2c3d4e5f6g7h8... | alice -> bob: 10.5
  2. b2c3d4e5f6g7h8i9... | charlie -> dave: 25.0
  3. c3d4e5f6g7h8i9j0... | eve -> alice: 5.0
  4. d4e5f6g7h8i9j0k1... | bob -> charlie: 15.0
============================================================
```

### `mempool` or `pool`
Show all pending transactions in the mempool (waiting to be included in a block).

```
minichain> mempool

Mempool (3 transactions):
================================================================================
TX ID                Sender          Recipient       Amount     Time
--------------------------------------------------------------------------------
a1b2c3d4e5f6g7h8i9   alice           bob             10.50      14:25:10
b2c3d4e5f6g7h8i9j0   charlie         dave            25.00      14:25:15
c3d4e5f6g7h8i9j0k1   eve             alice           5.00       14:25:20
================================================================================
```

### `peers`
Show all connected peer nodes.

```
minichain> peers

Connected Peers (2):
============================================================
  - svm-11-2.cs.helsinki.fi:8000
  - svm-11-3.cs.helsinki.fi:8000
============================================================
```

### `clear`
Clear the screen (simple version - prints blank lines).

### `exit`, `quit`, or `q`
Exit the node and CLI. This will gracefully shut down the node.

## Example Session

Here's a complete example of using the CLI:

```
$ python src/main.py --node-id svm-11 --port 8000 --peers "svm-11-2.cs.helsinki.fi:8000,svm-11-3.cs.helsinki.fi:8000"

[Node startup logs...]

============================================================
MiniChain CLI - Type 'help' for commands
============================================================

minichain> status
[Shows node status]

minichain> submit alice bob 10.5
✓ Transaction submitted: a1b2c3d4e5f6g7h8
  alice -> bob: 10.5

minichain> submit charlie dave 25.0
✓ Transaction submitted: b2c3d4e5f6g7h8i9
  charlie -> dave: 25.0

minichain> mempool
[Shows pending transactions]

minichain> chain
[Shows recent blocks]

minichain> block 1
[Shows block details]

minichain> exit
Exiting...
[Node shuts down]
```

## Tips

1. **Transaction IDs**: Each transaction gets a unique ID based on its content. You'll see this ID when you submit a transaction.

2. **Block Creation**: Blocks are created automatically by the leader node based on the consensus algorithm. You don't need to manually create blocks.

3. **Mempool**: Transactions stay in the mempool until they're included in a block. Once included, they're removed from the mempool.

4. **Leader Rotation**: The leader rotates based on block height. Use `status` to see who the current leader is.

5. **Network**: Transactions are automatically broadcast to all connected peers when submitted.

## Troubleshooting

- **CLI not appearing**: Make sure you didn't use `--no-cli` flag
- **Commands not working**: Check that the node is running and hasn't crashed
- **Transactions not appearing**: Wait a few seconds for the transaction to propagate, then check `mempool`
- **Blocks not appearing**: Wait for the leader to propose a block (check `status` to see who the leader is)

