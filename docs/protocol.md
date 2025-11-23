# Protocol

MiniChain message protocol uses length-prefixed TCP frames with msgpack-encoded envelopes.

## Envelope Format

```
{
  "header": {"type": <string>, "sender_id": <string>, "timestamp": <float>},
  "signature": <bytes>,
  "payload": <bytes msgpack-serialized body>
}
```

Signature = Ed25519 over sha256(msgpack({header, payload})).

## Core Message Types

| Type       | Purpose                        | Key Fields                            |
| ---------- | ------------------------------ | ------------------------------------- |
| HELLO      | Handshake (future)             | node_id, version                      |
| PEERLIST   | Peer discovery (future)        | peers[]                               |
| HEARTBEAT  | Liveness/height advert         | node_id, height, last_block_hash      |
| TX         | Gossip transaction             | tx fields                             |
| INV        | Announce availability (future) | kind, id                              |
| GETHEADERS | Request range of headers       | from_height, to_height                |
| HEADERS    | Respond with headers           | headers[]                             |
| GETBLOCKS  | Request blocks                 | from_height, to_height                |
| BLOCK      | Respond with blocks            | blocks[]                              |
| PROPOSE    | Leader proposes block          | full block fields                     |
| ACK        | Follower validates proposal    | height, block_hash, voter_id          |
| COMMIT     | Leader finalizes block         | block object                          |
| VIEWCHANGE | Rotate leader after timeout    | current_height, new_leader_id, reason |
| STATUS     | Diagnostics (future)           | height, role, leader_id               |

## Consensus Flow Messages

1. `PROPOSE` → candidate block
2. `ACK` (majority) → quorum reached
3. `COMMIT` → finalize; append
4. Timeout → `VIEWCHANGE` and new proposal

## Synchronization

- Late joiner sends `GETHEADERS` (0..large_number)
- Compares highest header to local height
- Requests missing full blocks via `GETBLOCKS`
- Applies sequentially; resolves forks by highest height then lowest hash

## Reliability

- Length prefix guard prevents partial read errors.
- Retries can be added with backoff and message ID tracking (future).
- Deduplication: tx_id and block_hash serve as unique identifiers.

## Validation Summary

- Block linkage: `prev_hash` must equal previous block's `block_hash`
- Leader identity: `proposer_id` matches `validators[h mod k]`
- Transaction checks: signature valid, nonce monotonic, sufficient balance

## Security (Prototype)

- Deterministic seeds for keys are insecure; replace with securely generated keys.
- Add transport encryption (TLS) and peer auth.
- Sign and verify all message envelopes (currently only signed on send; verification logic to be expanded).

## Future Enhancements

- Inventory (INV/GET) path for efficient large-network diffusion
- Compression for large block batches
- Versioned protocol negotiation
- Merkle roots for block tx integrity
