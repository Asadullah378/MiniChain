# MiniChain Architecture & Internals

This document explains how the MiniChain codebase fits together so you can navigate it without diving into every module first. Source paths below are relative to the repository root.

## High-Level Mental Model

1. `start.sh` builds the runtime configuration (node id, peers, ports) from `peers.txt`, then executes `src/main.py`.
2. `src/main.py` loads YAML configuration (`src/common/config.py`), configures logging (`src/common/logger.py`), instantiates a `Node`, and optionally starts the interactive CLI (`src/cli/cli.py`).
3. `Node` (`src/node/node.py`) wires together:
   - Persistent blockchain storage (`src/chain/blockchain.py`).
   - The in-memory mempool (`src/mempool/mempool.py`).
   - Round-robin PoA consensus (`src/consensus/poa.py`).
   - TCP networking and message handling (`src/p2p/network.py`).
4. Once running, the node alternates between proposing blocks (if it is leader) and validating/committing proposals from other validators while gossiping transactions and blocks.

## Startup Flow

1. **Configuration**
   - `Config` loads `config.yaml` (or defaults) and merges command-line and environment overrides.
   - Hostname/node id auto-detection happens here; peers from CLI/`peers.txt` are normalized into `[{'hostname': str, 'port': int}]`.
2. **Logging**
   - `setup_logger` wires console/file handlers. When the CLI is enabled, console logging is suppressed to keep the prompt clean; logs still stream to `minichain.log`.
3. **Node Initialization**
   - Blockchain state is loaded from `data/chain.json` (created on first run with a deterministic genesis block).
   - `Mempool` starts empty but remembers seen transaction ids to avoid rebroadcast storms.
   - Validator ids are derived from peers + self, normalized (short name vs FQDN) and sorted for deterministic leader rotation.
   - `RoundRobinPoA` receives timing/quorum parameters and the validator list and seeds its `current_height` from the blockchain.
   - `NetworkManager` binds the TCP listener (`0.0.0.0:<port>`), accepts inbound sockets, and connects to each configured peer in the background.
4. **CLI (optional)**
   - Runs on a background thread so the node main loop can block. Commands call back into the live `Node` instance.

## Core Components

### Blockchain Layer (`src/chain`)

- **`block.py`** defines the canonical `Transaction` and `Block` dataclasses. Hashes use SHA-256 (`src/common/crypto.py`). Blocks compute their hash over height, prev hash, ordered tx hashes, timestamp, and proposer id.
- **`blockchain.py`** keeps an in-memory list of `Block` objects and persists the chain as JSON. Validation enforces height monotonicity, parent hash linkage, and per-block structural checks. Persistence happens after every accepted block.
- **Genesis block** always uses height 0, a zero hash parent, and timestamp `0.0`, so every node starts from identical history.

### Mempool (`src/mempool/mempool.py`)

- Stores pending transactions keyed by `tx_id` and tracks every id ever seen. This makes `has_seen` useful for deduplicating gossip.
- `get_transactions(count)` returns the first `count` transactions (in insertion order) for block assembly.

### Consensus (`src/consensus/poa.py`)

- Deterministic leader selection: `validator_ids[height % len(validator_ids)]`.
- Timing knobs:
  - `block_interval` controls how often the leader _may_ attempt to propose.
  - `proposal_timeout` is reserved for view-change logic (currently a stub).
- `create_proposal` pulls up to `max_txs` from the mempool, stamps the block, and leaves signing hooks for future extensions.
- ACK handling stores voters per height; once `quorum_size` votes are present, the leader commits and broadcasts `COMMIT`.
- `committing` flags prevent duplicate commit attempts when multiple ACKs arrive concurrently.

### Networking (`src/p2p`)

- **Transport (`network.py`)**
  - Single threaded listener + per-connection handler threads.
  - All messages are length-prefixed then MsgPack-encoded objects (`messages.py`).
  - Connections are indexed by `"host:port"`. ACKs are routed directly to the expected leader by matching either full or short hostnames and dialing a fresh socket if needed.
  - Gossip helpers exist for transactions, block proposals, ACKs, COMMITs; header/block sync stubs are placeholders (`send_headers`, `send_block`).
- **Messaging (`messages.py`)** centralizes payload formats so serialization stays consistent between peers.

### Node Orchestration (`src/node/node.py`)

- Maintains the event loop:
  - `_consensus_loop` wakes every second, asking consensus whether to propose (`should_propose`) for `height = current_height + 1`.
  - Incoming network messages fan out to `_handle_tx`, `_handle_propose`, `_handle_ack`, `_handle_commit`, etc.
- Proposal handling path:
  1. Leader builds a block, caches it in `consensus.pending_proposal`, and sends `PROPOSE`.
  2. Followers reconstruct the block, validate expected height/parent hash/leader/hash, and send a direct ACK back to the proposer.
  3. Leader aggregates ACKs. On quorum, it commits locally, prunes mempool transactions, flips consensus state (`on_block_committed`), and broadcasts `COMMIT`.
  4. Followers receiving `COMMIT` finalize the matching pending proposal if they have it cached.
- Height/bookkeeping fields: `blockchain.get_height()` surfaces persisted chain length, while consensus keeps a mirror in `current_height` and `last_block_time` to enforce spacing between leadership terms.

### CLI (`src/cli/cli.py`)

- Provides real-time inspection (`status`, `chain`, `block`, `mempool`, `peers`, `logs`) and transaction submission (`submit`).
- Uses the node's public API (`node.submit_transaction`, blockchain getters) so it doubles as a thin usage example for scripting or testing.

## Message & Data Lifecycles

### Transaction

1. User runs `submit alice bob 5`. CLI builds a `Transaction` with a hash-based id and passes it to `Node.submit_transaction`.
2. Node inserts it into the mempool (dedupe via `tx_id`), then gossips it with `NetworkManager.broadcast_transaction`.
3. Other nodes reconstruct the transaction (`Transaction.deserialize`) and repeat the mempool + gossip step unless they have already seen the id.

### Block

1. Leader calls `RoundRobinPoA.create_proposal`, pulling up to `blockchain.max_block_size` transactions.
2. Proposed block travels via `PROPOSE`, containing serialized transactions and metadata.
3. Followers validate structure, height, parent hash, and leader identity, then ACK.
4. Once quorum is met, leader commits locally and broadcasts `COMMIT`; followers finalize with the cached proposal and delete included transactions from their mempool.
5. Blocks persist immediately to `data/chain.json`, so a restart continues from the last committed height.

## Scripts & Configuration

- **`setup.sh`** bootstraps Python env + dependencies and is intended to run once per VM.
- **`start.sh`** is the canonical way to launch a node because it enforces `hostname` alignment with `peers.txt`, optionally purges `data/` and `*.log`, and passes the normalized peer list to `src/main.py`.
- **`config.yaml`** contains consensus/blockchain/logging defaults. Node identity and peer lists are purposely _not_ stored here to avoid accidental divergence between machines.
- **`peers.txt`** must be identical across nodes. Order is irrelevant after normalization, but hostnames must match what each machine passes as `--node-id`.

## Extensibility Pointers

- **Signatures**: ACK/COMMIT currently ship an empty signature. The plumbing in `messages.py` is ready—wire up `src/common/crypto.KeyPair` to populate and verify these fields.
- **State sync**: `GETHEADERS`, `GETBLOCKS`, `send_headers`, and `send_block` are stubs. A pragmatic next step is to ship compact headers first, then request missing blocks.
- **View change**: `_check_timeouts` in `Node` and `should_trigger_view_change` in `RoundRobinPoA` are placeholders. Implementing them would enable automatic rotation when leaders stall.
- **Persistence**: For higher throughput, consider swapping `chain.json` for a lightweight database (SQLite/LMDB) while keeping the `Blockchain` interface intact.

Refer back to this document whenever you need to trace a runtime behavior to the specific module responsible.
