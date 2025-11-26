# MiniChain TODO

Backlog aligned with `PRD.md` (v1.0 – Nov 26, 2025). Update statuses at the end of every sprint/demo rehearsal.

## ✅ Completed Foundations

- [x] P2P transport (listener, outbound connectors, HELLO handshake)
- [x] Round-robin PoA pipeline (propose → ACK → commit)
- [x] On-disk chain persistence + deterministic genesis validation

## 🎯 Milestones & Demos

- [ ] **M3 – Fault Handling & Sync (Week 7)**
  - [ ] Implement leader timeout + VIEWCHANGE path in `Node._check_timeouts`
  - [ ] Demonstrate node restart catching up via GETHEADERS/GETBLOCKS
- [ ] **M4 – Observability & Polish (Week 9)**
  - [ ] Metrics/health endpoint (HTTP or CLI) exposing block time + mempool size
  - [ ] Finalize demo script + multi-node walkthrough video

## 🔐 Consensus & Protocol Hardening

- [ ] Sign and verify ACK/COMMIT messages using `src/common/crypto.KeyPair`
- [ ] Enforce proposer schedule validation on follower ACK path (log + reject mismatches)
- [ ] Add quorum/timeout counters to logs for auditability

## 🌐 Networking & Sync

- [ ] Finish header/block sync (`send_headers`, `send_block`, HEADERS/BLOCK handlers)
- [ ] Retry/backoff strategy for outbound connections + message sends
- [ ] Detect peer list divergence at startup (compare `peers.txt` signatures/hash)

## 🧪 Reliability & Testing

- [ ] Node restart during in-flight commit (ensure idempotent add_block)
- [ ] Simulate network partition / delayed ACK quorum handling
- [ ] Stress test mempool when `MAX_TX_PER_BLOCK` << inbound rate (starvation prevention)
- [ ] Document expected recovery time after forced leader crash

## 📚 Documentation & Tooling

- [ ] Link `docs/ARCHITECTURE.md` and `PRD.md` from `README.md`
- [ ] Author quick-start walkthrough for three-node deployment (include `start.sh` examples)
- [ ] Troubleshooting matrix for networking/consensus issues (timeouts, hostname mismatches)
- [ ] Add `make` or shell helper to tail logs from all nodes simultaneously (optional)

_Use checkbox IDs in commits (e.g., "TODO: completed VIEWCHANGE timeout"), and keep sections in sync with PRD milestones._
