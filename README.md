# MiniChain

A simple blockchain implementation for distributed systems demonstration.

## Overview

MiniChain is a minimal blockchain implementation that demonstrates key distributed systems concepts:

- **Shared distributed state**: Replicated blockchain ledger across nodes
- **Data consistency**: Block validation and chain synchronization
- **Consensus**: Round-robin Proof-of-Authority (PoA) consensus
- **Fault tolerance**: Leader crash recovery and node rejoin

## Quick Start

### 1. Setup (Run once on each VM)

```bash
chmod +x setup.sh
./setup.sh
```

This will:

- Check Python 3.8+ installation
- Create virtual environment
- Install all dependencies

### 2. Configure Peers

Edit `peers.txt` to include all nodes in your network:

```
svm-11.cs.helsinki.fi:8000
svm-11-2.cs.helsinki.fi:8000
svm-11-3.cs.helsinki.fi:8000
```

**Important**: All nodes must have the same `peers.txt` file with all peers listed.

### 3. Start Node (Run on each VM)

```bash
chmod +x start.sh
./start.sh <hostname> [--clean]
```

**Usage:**

```bash
./start.sh <hostname> [--clean]
```

**Parameters:**

- `hostname`: **REQUIRED** - The hostname of this node (must match one in `peers.txt`)
- `--clean`: Optional flag to clear all data and logs before starting

**Examples:**

On svm-11.cs.helsinki.fi:

```bash
./start.sh svm-11.cs.helsinki.fi
```

On svm-11-2.cs.helsinki.fi:

```bash
./start.sh svm-11-2.cs.helsinki.fi
```

On svm-11-3.cs.helsinki.fi:

```bash
./start.sh svm-11-3.cs.helsinki.fi
```

**Clean Start**: To clear all data and logs before starting:

```bash
./start.sh svm-11.cs.helsinki.fi --clean
```

The script will:

- Use the provided hostname (no auto-detection)
- Find the hostname in `peers.txt`
- Configure node_id and peers automatically
- Start the node

**Note**: Hostname is **required**. The script will exit with an error if not provided.

This will remove:

- All blockchain data (`data/` directory)
- All log files (`minichain.log`)

## Configuration

### `config.yaml` - Blockchain Settings

Edit `config.yaml` to adjust blockchain and consensus parameters:

```yaml
consensus:
  block_interval: 5 # Seconds between block proposals
  proposal_timeout: 10 # Seconds to wait for ACKs
  quorum_size: 2 # Minimum ACKs needed (for 3 nodes: 2/3)

blockchain:
  max_block_size: 100 # Max transactions per block

logging:
  level: "INFO" # DEBUG, INFO, WARNING, ERROR, CRITICAL
  file: "minichain.log"
  console: true
```

**Note**: This file contains only blockchain settings. Node-specific settings (node_id, peers) are auto-detected from `peers.txt`.

### `peers.txt` - Network Configuration

List all nodes in your network (one per line, format: `hostname:port`):

```
svm-11.cs.helsinki.fi:8000
svm-11-2.cs.helsinki.fi:8000
svm-11-3.cs.helsinki.fi:8000
```

The `start.sh` script automatically:

- Detects which machine it's running on
- Sets node_id to the matching hostname
- Configures peers (all other nodes in the list)

## CLI Interface

When you start a node, an interactive CLI automatically launches. Use it to submit transactions and monitor the blockchain.

### Available Commands

#### `help` or `h`

Show help message with all available commands.

#### `submit <sender> <recipient> <amount>`

Submit a new transaction to the blockchain.

**Example:**

```
minichain> submit alice bob 10.5
✓ Transaction submitted: a1b2c3d4e5f6g7h8
  alice -> bob: 10.5
```

#### `status` or `info`

Display current node status and blockchain information.

```
minichain> status
============================================================
Node Status
============================================================
Node ID:        svm-11.cs.helsinki.fi
Hostname:       svm-11.cs.helsinki.fi
Port:           8000
Blockchain Height: 5
Latest Block Hash: 1a2b3c4d5e6f7g8h9...
Mempool Size:   3 transactions
Connected Peers: 2
Current Leader: svm-11-2.cs.helsinki.fi
I am Leader:    No (for next block)
============================================================
```

#### `chain [limit]`

Show a summary of recent blocks (default: 10).

```
minichain> chain 5
```

#### `block <height>`

Show detailed information about a specific block.

```
minichain> block 5
```

#### `mempool` or `pool`

Show pending transactions in mempool.

#### `peers`

Show connected peer nodes.

#### `logs [n]`

Show last n lines from log file (default: 20).

```
minichain> logs 50
```

**Note**: Use `--log-level DEBUG` when starting to see debug logs:

```bash
./start.sh --log-level DEBUG
```

#### `clear`

Clear screen.

#### `exit`, `quit`, or `q`

Exit the node.

## Architecture

The project is organized into the following modules:

- `src/common/`: Configuration, logging, and cryptographic utilities
- `src/chain/`: Blockchain data structures (Block, Transaction) and chain management
- `src/mempool/`: Transaction mempool for pending transactions
- `src/consensus/`: Consensus mechanism (round-robin PoA)
- `src/p2p/`: Peer-to-peer networking and message passing
- `src/node/`: Main node implementation that orchestrates all components
- `src/cli/`: Interactive command-line interface

## Features

### Consensus

- **Round-robin PoA**: Leaders rotate based on block height
- **Quorum-based**: Requires majority ACKs before committing blocks
- **View change**: Automatic leader rotation on timeout

### Networking

- **TCP-based**: Reliable message delivery
- **Gossip protocol**: Transaction and block propagation
- **State synchronization**: Catch-up sync for new/rejoining nodes

### Blockchain

- **Genesis block**: Automatically created on first run (deterministic)
- **Block validation**: Height, hash, and linkage checks
- **Fork resolution**: Longest chain wins

## Project Structure

```
MiniChain/
├── src/
│   ├── common/          # Utilities (config, logging, crypto)
│   ├── chain/           # Blockchain data structures
│   ├── mempool/         # Transaction mempool
│   ├── consensus/       # Consensus algorithms
│   ├── p2p/             # Network communication
│   ├── node/            # Main node implementation
│   ├── cli/             # CLI interface
│   └── main.py          # Entry point
├── config.yaml          # Blockchain configuration
├── peers.txt            # Network peers (all nodes)
├── setup.sh             # Setup script
├── start.sh             # Start script (auto-configures)
├── requirements.txt     # Python dependencies
└── README.md           # This file
```

## How It Works

### Transaction Flow

1. **Transaction Submission**: User submits transaction via CLI
2. **Gossip Propagation**: Transaction is broadcast to all peers
3. **Mempool**: All nodes add transaction to their mempool
4. **Block Proposal**: Leader creates block from mempool transactions
5. **Validation**: Followers validate and ACK the proposal
6. **Commit**: Leader commits block after quorum is reached
7. **Finalization**: All nodes add block to their blockchain

### Message Types

- **TX**: Transaction propagation (gossip)
- **PROPOSE**: Block proposal from leader
- **ACK**: Acknowledgment from followers (sent to leader only)
- **COMMIT**: Final commit message from leader
- **HELLO**: Connection handshake

### Consensus Process

1. Leader rotates based on block height (round-robin)
2. Leader proposes block when `block_interval` elapsed
3. Followers validate and send ACK to leader
4. Leader waits for quorum (majority of validators)
5. Leader commits and broadcasts COMMIT
6. All nodes finalize the block

## Troubleshooting

### Node Not Starting

- Check Python version: `python3 --version` (needs 3.8+)
- Ensure virtual environment is activated
- Check `peers.txt` contains the current machine's hostname

### Connection Issues

- Verify hostnames in `peers.txt` are resolvable: `ping <hostname>`
- Check firewall settings allow connections on port 8000
- Ensure all nodes are running

### Consensus Issues

- Verify all nodes have the same `peers.txt` file
- Check that hostnames match exactly (FQDN vs short name)
- Use `--log-level DEBUG` to see detailed logs

### View Logs

```bash
# View logs via CLI
minichain> logs 50

# Or view log file directly
tail -f minichain.log
```

## Advanced Usage

### Run Without CLI

```bash
python3 src/main.py --no-cli --node-id <id> --peers "..."
```

### Custom Configuration

You can still override settings via command-line:

```bash
python3 src/main.py \
  --node-id custom-id \
  --port 8001 \
  --peers "peer1:8000,peer2:8000" \
  --log-level DEBUG \
  --config custom_config.yaml
```

## Testing

MiniChain ships with a lightweight `pytest` suite that exercises the block/mempool primitives, blockchain persistence, and consensus helpers. Run it from the repo root **after activating the project virtual environment** so that dependencies such as `msgpack`, `cryptography`, and `pytest` are available:

```bash
source .venv/bin/activate  # created via ./setup.sh
pip install -r requirements.txt  # no-op if already installed
pytest -q                      # or python -m pytest
```

Tests live under `tests/` and can be filtered (e.g., `pytest tests/test_poa.py -k quorum`). The suite expects the dependencies listed in `requirements.txt`—rerun `setup.sh` if the environment gets out of sync.

## Documentation

- `docs/ARCHITECTURE.md` – runtime wiring, lifecycles, and extension points.
- `PRD.md` – product requirements, personas, milestones, and risks.
- `TODO.md` – backlog aligned with the PRD milestones.
- `PYTEST.md` – detailed instructions for running/extending the automated test suite.

Keep these documents in sync when features land so reviewers can trace code back to the design intent.

## Development

The codebase is designed to be:

- **Modular**: Each component is independent
- **Configurable**: Easy to adjust for different deployments
- **Extensible**: Easy to add new features

## License

[Your License Here]

## API Reference

MiniChain includes an HTTP API for interacting with the node and debugging. To enable it, start the node with the `--api-port` flag:

```bash
./start.sh <hostname> --api-port 8080
# OR
python3 src/main.py --node-id <id> --api-port 8080
```

### Standard Endpoints

#### Check Node Status
```bash
curl http://localhost:8080/status
```

#### List Blocks
```bash
curl "http://localhost:8080/blocks?limit=5"
```

#### Get Block Details
```bash
curl http://localhost:8080/blocks/0
```

#### Submit Transaction
```bash
curl -X POST http://localhost:8080/submit \
  -H "Content-Type: application/json" \
  -d '{"sender": "alice", "recipient": "bob", "amount": 10.5}'
```

### Debug Endpoints

These endpoints are for testing edge cases and simulating network conditions.

#### Clear Mempool
Remove all pending transactions from the mempool.
```bash
curl -X POST http://localhost:8080/debug/mempool/clear
```

#### Simulate Network Partition
Disconnect from all peers to simulate a network partition.
```bash
curl -X POST http://localhost:8080/debug/network/disconnect
```

#### Reconnect Network
Reconnect to peers after a partition.
```bash
curl -X POST http://localhost:8080/debug/network/reconnect
```

#### Trigger Consensus Timeout
Simulate a consensus timeout (e.g., to force a view change).
```bash
curl -X POST http://localhost:8080/debug/consensus/timeout
```
