# MiniChain

A simple blockchain implementation for distributed systems demonstration.

## Overview

MiniChain is a minimal blockchain implementation that demonstrates key distributed systems concepts:
- **Shared distributed state**: Replicated blockchain ledger across nodes
- **Data consistency**: Block validation and chain synchronization
- **Consensus**: Round-robin Proof-of-Authority (PoA) consensus
- **Fault tolerance**: Leader crash recovery and node rejoin

## Architecture

The project is organized into the following modules:

- `src/common/`: Configuration, logging, and cryptographic utilities
- `src/chain/`: Blockchain data structures (Block, Transaction) and chain management
- `src/mempool/`: Transaction mempool for pending transactions
- `src/consensus/`: Consensus mechanism (round-robin PoA)
- `src/p2p/`: Peer-to-peer networking and message passing
- `src/node/`: Main node implementation that orchestrates all components

## Requirements

- Python 3.8+
- Dependencies listed in `requirements.txt`

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd MiniChain
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

## Configuration

The node can be configured in multiple ways:

### 1. Configuration File

Create a `config.yaml` file or use `config/default.yaml`:

```yaml
node:
  id: "svm-11"
  hostname: "svm-11.cs.helsinki.fi"
  port: 8000
  data_dir: "data"

network:
  peers:
    - hostname: "svm-11-2.cs.helsinki.fi"
      port: 8000
    - hostname: "svm-11-3.cs.helsinki.fi"
      port: 8000
```

### 2. Environment Variables

```bash
export NODE_ID="svm-11"
export NODE_PORT=8000
export NODE_HOSTNAME="svm-11.cs.helsinki.fi"
export PEERS="svm-11-2.cs.helsinki.fi:8000,svm-11-3.cs.helsinki.fi:8000"
```

### 3. Command-Line Arguments

```bash
python src/main.py --port 8000 --peers "svm-11-2.cs.helsinki.fi:8000,svm-11-3.cs.helsinki.fi:8000"
```

## Running Nodes

### On VM 1 (svm-11.cs.helsinki.fi):

```bash
python src/main.py \
  --node-id svm-11 \
  --port 8000 \
  --peers "svm-11-2.cs.helsinki.fi:8000,svm-11-3.cs.helsinki.fi:8000"
```

### On VM 2 (svm-11-2.cs.helsinki.fi):

```bash
python src/main.py \
  --node-id svm-11-2 \
  --port 8000 \
  --peers "svm-11.cs.helsinki.fi:8000,svm-11-3.cs.helsinki.fi:8000"
```

### On VM 3 (svm-11-3.cs.helsinki.fi):

```bash
python src/main.py \
  --node-id svm-11-3 \
  --port 8000 \
  --peers "svm-11.cs.helsinki.fi:8000,svm-11-2.cs.helsinki.fi:8000"
```

## Auto-Configuration

The node automatically:
- Detects hostname from the system
- Uses hostname as node ID if not specified
- Can discover peers from configuration or environment

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

- **Genesis block**: Automatically created on first run
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
│   └── main.py          # Entry point
├── config/              # Configuration files
├── data/                # Blockchain data (created at runtime)
├── requirements.txt     # Python dependencies
└── README.md           # This file
```

## Development

The codebase is designed to be:
- **Modular**: Each component is independent
- **Configurable**: Easy to adjust for different deployments
- **Extensible**: Easy to add new features

## License

[Your License Here]

