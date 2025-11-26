# MiniChain Product Requirements Document (PRD)

**Course:** Distributed Systems – Fall 2025  
**Version:** 1.0 (November 26, 2025)  
**Repository:** `Asadullah378/MiniChain`

| Role                      | Member                   | Student Number |
| ------------------------- | ------------------------ | -------------- |
| Project Lead / Networking | Vien Ha                  | 018563555      |
| Consensus & Reliability   | Asadullah Nawaz Warraich | 021538988      |
| Storage & Tooling         | Kiril                    | 020005991      |
| Observability & QA        | Aarni Rechardt           | 015398862      |

---

## 1. Problem Statement & Vision

MiniChain is a permissioned blockchain intended for enterprise-grade append-only logging and lightweight asset transfers across tens to hundreds of validator nodes. Each node must:

1. Maintain a replicated, validated blockchain ledger.
2. Participate in consensus to order blocks deterministically.
3. Provide a usable interface (CLI/API) for submitting transactions and inspecting state.

The Fall 2025 prototype demonstrates these core distributed-systems learnings on a 3-node cluster while laying the groundwork for horizontal scalability through gossip, leader rotation, and deterministic fork choice.

### 1.1 Goals

- Showcase shared global state, synchronization, and leader-based consensus in a real network.
- Provide clear operational scripts (`setup.sh`, `start.sh`) for repeatable deployments on VM clusters.
- Deliver a debuggable system with structured logging, CLI introspection, and architecture documentation.
- Support basic fault tolerance: a stalled leader must not halt the network permanently.

### 1.2 Non-Goals

- Implementing a fully permissionless or Byzantine fault tolerant protocol (PBFT, Tendermint, etc.).
- Handling arbitrary smart contract logic; focus is on transfers/logging transactions.
- Strong cryptoeconomic security (staking, slashing) beyond authenticated messaging.
- A production-ready wallet or UX—CLI suffices for the course deliverable.

---

## 2. User Personas & Success Metrics

| Persona                       | Needs                                                                                    | Success Signals                                                                                |
| ----------------------------- | ---------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------- |
| **Course Staff / Evaluators** | Ability to run ≥3 nodes, submit transactions, observe consensus progress/fault handling. | `README.md` quick start + deterministic demo scenario works first try.                         |
| **Team Developers**           | Clear module responsibilities, debugging hooks, prioritized backlog.                     | Fewer than 10 minutes to identify fault causes using logs/CLI; TODO list mirrors PRD sections. |
| **Future Extenders**          | Documentation on architecture and message schemas to extend features.                    | `docs/ARCHITECTURE.md` + `PRD.md` enable onboarding within a day.                              |

Quantitative targets:

- Block finalization under normal load: ≤ block interval + 2 s (default block interval 30 s).
- Recovery after leader crash: ≤ 2 proposal timeouts before new leader produces a block.
- Transaction propagation latency across 3 nodes: ≤ 2 seconds median (TCP gossip).

---

## 3. System Architecture

### 3.1 Deployment Overview

Three validator VMs (VM1, VM2, VM3) run identical MiniChain stacks. Each node hosts:

- **P2P Server (`src/p2p/network.py`)** – TCP listener + outgoing connectors.
- **Message Codec (`src/p2p/messages.py`)** – MsgPack-encoded envelopes with typed payloads.
- **Mempool (`src/mempool/mempool.py`)** – Validated pending transactions.
- **Blockchain Store (`src/chain/blockchain.py`)** – JSON-backed append-only chain with deterministic genesis.
- **Consensus Engine (`src/consensus/poa.py`)** – Round-robin PoA coordinator.
- **Synchronization Manager (stubbed via GETHEADERS/GETBLOCKS)** – catch-up logic.
- **Logger (`src/common/logger.py`)** + **Config Loader (`src/common/config.py`)**.
- **CLI (`src/cli/cli.py`) / optional API** for user interaction.

Leader responsibility rotates deterministically by block height, ensuring every node can act as proposer once quorum is satisfied.

### 3.2 Runtime Flow

1. `start.sh` normalizes node identity from `peers.txt` and launches `src/main.py`.
2. `main.py` loads YAML config, configures logging, instantiates `Node`, and optionally the CLI.
3. `Node` spins up networking + consensus threads, then idles in `_consensus_loop`.
4. CLI or remote peers submit transactions → mempool → gossip.
5. When `RoundRobinPoA.should_propose()` is true, the leader creates a block and broadcasts `PROPOSE`.
6. Followers validate, respond with `ACK`. Leader commits when quorum is reached and publishes `COMMIT`.
7. Followers finalize the block, prune mempool entries, and persist to disk.

### 3.3 Scaling Considerations

- **Gossip dissemination** ensures O(log n) propagation latency as cluster size increases.
- **Fork resolution** uses longest-chain followed by lowest-hash tie breaker to stay deterministic.
- **State sync** uses header-first catch-up to avoid transferring full blocks unnecessarily.
- **Horizontal scaling** targets tens to hundreds of validators by decoupling networking, consensus timers, and storage; CPU-bound work remains light.

---

## 4. Detailed Design & Selected Techniques

### 4.1 Data Model

| Entity      | Fields                                                                        | Notes                                                                                                                 |
| ----------- | ----------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------- |
| Transaction | `{tx_id, sender, recipient, amount, nonce?, timestamp, signature}`            | Current prototype enforces sender/recipient/amount/timestamp; nonce & signature hooks exist for future account model. |
| Block       | `{height, prev_hash, timestamp, tx_list, proposer_id, block_hash, signature}` | `block_hash` = SHA-256 over header; `signature` placeholder for Ed25519 signing.                                      |
| Blockchain  | Append-only list of blocks persisted to `data/chain.json`.                    | Valid block must match expected height, parent hash, proposer schedule, and hash integrity.                           |

Validation rules (target state):

1. `prev_hash` equals hash of block at `height-1`.
2. All transaction signatures valid; nonce increases per sender; balances never negative (account-based semantics).
3. `proposer_id` matches round-robin leader for `height`.
4. Fork choice: highest height wins; tie broken by lexicographically lowest `block_hash`.

### 4.2 Consensus (Leader-Based PoA)

- Validator set `V = [N0, N1, …, N(k-1)]` configured via peers + node metadata.
- Leader at height `h` is `V[h mod k]`.
- Protocol:
  1. Leader collects up to `MAX_TX_PER_BLOCK` txs.
  2. Broadcasts `PROPOSE` with serialized txs.
  3. Followers validate; on success, send `ACK` to leader.
  4. Leader commits upon quorum `Q` (default majority) and broadcasts `COMMIT`.
  5. On timeout, trigger `VIEWCHANGE` → next leader.
- **Safety**: Block enters chain only after the proposer sees quorum ACKs.
- **Liveness**: Timeouts ensure stalled leaders relinquish control.

### 4.3 Synchronization & Consistency

- **State Sync:** Nodes send `GETHEADERS/GETBLOCKS` when starting or when discrepancy detected; apply missing blocks sequentially.
- **Fork Handling:** Maintain highest height; in ties, choose deterministic lowest hash.
- **Mempool Hygiene:** Remove txs once confirmed or if seen in higher fork.

### 4.4 Networking & Messaging

- Transport: TCP sockets (`NetworkManager`).
- Serialization: MsgPack; protobuf optional for future.
- Reliability: Length-prefixed framing, per-connection threads, automatic reconnection.
- Security (prototype): shared-trust cluster + optional TLS; transactions signed via Ed25519.
- Backoff/retry planned for outbound messages.

### 4.5 Logging, Observability, Testing

- Structured timestamps via `logger`. Aim for JSON or colorized console with file persistence.
- Key events: inbound/outbound messages, proposal lifecycle, ACK quorum, timeouts, leader rotation, sync events.
- Metrics (stretch goal): expose HTTP/Prometheus endpoint for block time, mempool size, propagation delay, ACK latency.
- Testing hooks: CLI commands (`status`, `chain`, `block`, `logs`) and TODO items for targeted fault-injection scenarios.
- Automated regression suite: `pytest` tests cover block serialization, blockchain persistence, mempool semantics, and PoA quorum bookkeeping. Passing the suite (`python -m pytest`) is required before each milestone demo.

---

## 5. Node Roles & Functionalities

Despite symmetrical deployment, runtime roles differ per consensus phase. Each node implements the following subsystems:

1. **Networking Layer** – Manage TCP peers, gossip TX/BLOCK data, maintain heartbeats, auto-reconnect.
2. **Mempool Manager** – Validate/queue txs, deduplicate, serve leaders and followers alike, gossip new txs.
3. **Consensus Module** – Determine leader/follower role, handle timers, construct proposals, collect ACKs, trigger view changes.
4. **Blockchain Storage** – Persist chain, expose query APIs, verify linkage, ensure crash recovery by replaying `chain.json`.
5. **Sync & Recovery Manager** – Compare heights, fetch headers/blocks, resolve forks, clear confirmed txs.
6. **Logging / Monitoring** – Emit events and metrics, support aggregation, track peer health.
7. **CLI / External API** – Accept tx submissions, display status/chain/mempool/peers, tail logs.

Every node must be capable of assuming leadership, validating foreign proposals, and recovering after downtime using the sync protocol.

---

## 6. Message Definitions (Prototype Scope)

All envelope headers include: `{type, sender_id, timestamp, signature, payload}`.

### 6.1 Transaction Propagation

- **TX** `{tx_id, tx_bytes}` – gossip serialized transaction.
- **INV** `{type, hash}` – announce availability; peers fetch via `GETTX`/`GETBLOCKS`.

### 6.2 Data Synchronization

- **GETHEADERS** `{from_height, to_height}` – request metadata.
- **HEADERS** `{headers[]}` – respond with `(height, hash, prev_hash, proposer_id, timestamp, tx_count)`.
- **GETBLOCKS** `{from_height, to_height}` – request full blocks.
- **BLOCK** `{block_bytes}` – send serialized block(s).

### 6.3 Consensus & Coordination

- **PROPOSE** `{height, prev_hash, tx_list, proposer_id, block_hash, signature}`.
- **ACK** `{height, block_hash, voter_id, signature}` – direct to leader.
- **COMMIT** `{height, block_hash, leader_id, signature}` – finalize.
- **VIEWCHANGE** `{current_height, new_leader_id, reason, signature}` – rotate leadership on timeout/failure.

### 6.4 Maintenance & Utility

- **HELLO** `{node_id, version, listening_port}` – handshake.
- **PEERLIST** `{peers[]}` – share topology.
- **HEARTBEAT** `{node_id, height, last_block_hash}` – liveness.
- **STATUS** `{height, mempool_size, role, leader_id}` – monitoring convenience.

### 6.5 Reliability & Error Handling

- Deduplicate via message IDs/tx hashes.
- Retry lost messages after configurable intervals; exponential backoff for repeated failures.
- Invalid/corrupted payloads logged and dropped.
- Prioritize consensus-critical messages (PROPOSE/ACK/COMMIT) to minimize commitment delay.

---

## 7. Implementation Scope & Milestones

| Milestone                   | When   | Deliverables                                                                                           |
| --------------------------- | ------ | ------------------------------------------------------------------------------------------------------ |
| M1 – Baseline Networking    | Week 3 | TCP server/client, HELLO handshake, CLI transaction submission, log plumbing.                          |
| M2 – PoA Consensus MVP      | Week 5 | Deterministic leader rotation, PROPOSE/ACK/COMMIT round-trip, on-disk chain.                           |
| M3 – Fault Handling & Sync  | Week 7 | Timeout-triggered view change, GETHEADERS/GETBLOCKS flow, restart recovery demo.                       |
| M4 – Observability & Polish | Week 9 | Metrics/health hooks, documentation (`README`, `ARCHITECTURE`, `PRD`), automated tests for edge cases. |

Stretch goals: signature enforcement for ACK/COMMIT, metrics endpoint, packaging scripts for multi-node deployment.

---

## 8. Risks & Mitigations

| Risk                                   | Impact                             | Mitigation                                                                                  |
| -------------------------------------- | ---------------------------------- | ------------------------------------------------------------------------------------------- |
| Leader timeout logic incomplete        | Consensus stalls after a crash     | TODO: Implement `_check_timeouts` + VIEWCHANGE handling; unit-test with simulated failures. |
| Sync stubs unfinished                  | Rejoining nodes may never catch up | Prioritize `send_headers`/`send_block` implementation; add CLI command to trigger sync.     |
| Missing signatures on control messages | Spoofed ACK/COMMIT possible        | Integrate `KeyPair` signing for consensus messages; document trust assumptions until then.  |
| Peer configuration drift               | Nodes disagree on validator set    | Enforce `start.sh` validation + add TODO to detect divergence at runtime.                   |

---

## 9. Documentation & Deliverables

- `README.md` – quick start + CLI usage.
- `docs/ARCHITECTURE.md` – implementation deep dive.
- `PRD.md` (this file) – requirements/lifecycle reference.
- `TODO.md` – living backlog linked to PRD sections.
- Demo script – step-by-step flow for grading (upcoming).
- Optional video/walkthrough.

---

## 10. Prototype Scope Note

This course project emphasizes distributed processing and communication behavior rather than full-featured blockchain economics. Certain blockchain mechanics (Ethereum-style account balances, smart contracts, advanced cryptography) may be simplified or simulated. The PRD and backlog clearly flag such simplifications so evaluators understand intentional trade-offs.

---

_This PRD should be updated whenever requirements shift or milestones are completed. Link it from `README.md` for visibility._
