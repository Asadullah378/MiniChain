# Architecture

MiniChain nodes are symmetric validator processes composed of modular subsystems:

- Networking (TCP framed, msgpack payloads)
- Mempool (validated pending transactions)
- Chain Store (persistent append-only blocks + account state)
- Consensus Engine (round-robin PoA leader rotation, proposal, ACK quorum, commit)
- Sync Manager (headers/blocks catch-up; simple fork choice by height then hash)
- Logging/Monitoring (structured JSON events; metrics placeholders)
- CLI/API (start nodes, submit transactions)

## Data Flow Overview
1. Client sends TX to any node via CLI command.
2. Node validates TX quickly (signature, nonce monotonic, balances) then adds to mempool and gossips (prototype: direct send placeholder).
3. Current leader (height h) aggregates up to MAX_TX_PER_BLOCK from mempool and constructs block candidate.
4. Leader broadcasts PROPOSE message with block payload; followers validate link, leader identity, transactions.
5. Followers send ACK if valid. Leader gathers ACKs until quorum.
6. On quorum, leader broadcasts COMMIT; nodes append block and purge included transactions from mempool.
7. State changes (balances, nonces) applied atomically with block append.
8. If timeout/no quorum, leader triggers VIEWCHANGE (increment view counter); new leader proposes again.

## Control Flow Components
- Periodic leader tick triggers proposals (`consensus.tick`).
- Heartbeat loop broadcasts liveness + height.
- Sync Manager responds to GETHEADERS/GETBLOCKS for late joiners.
- Message dispatch in `MiniChainNode._dispatch_message` routes to subsystem handlers.

## Persistence Model
`chain.json` holds:
```
{
  "blocks": [ {height, prev_hash, timestamp, tx_list, proposer_id, signature, block_hash}, ... ],
  "accounts": {public_key_hex: balance},
  "nonces": {public_key_hex: last_nonce}
}
```
Genesis block preloaded with empty tx_list and sentinel prev_hash.

## Extensibility Points
- Replace JSON file with LevelDB/RocksDB for efficient range queries.
- Modular plugin for alternative consensus (e.g., Raft, HotStuff subset).
- Pluggable serialization (protobuf vs msgpack) with version negotiation.
- Observability: integrate Prometheus exporter.

## Fault Tolerance & Scaling
- Leader rotation ensures eventual progress if a leader fails (simple liveness assumption).
- Gossip can replace direct broadcast for large networks (fan-out + INV/GET pattern).
- Sharding (future) by partitioning keyspace and running multiple consensus groups.

## Security Considerations
- Prototype uses deterministic seed-derived keys (not for production).
- Future: TLS for transport, authenticated validator set, replay protection via sequence numbers.

## Deployment Notes
- Each node runs as independent process with its own data directory.
- For containerization, mount persistent volume for `./data/node_<id>`.
