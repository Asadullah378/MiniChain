# MiniChain TODO

Well-scoped priorities for coordinating development and validation work. Keep this file current as tasks move between sections.

## ✅ Completed Foundations

- [x] Peer-to-peer communication plumbing (listener + outbound connectors)
- [x] Round-robin PoA consensus pipeline (propose → ACK → commit)
- [x] Chain persistence and consistency validation

## 🚧 In Progress / Next Up

- [ ] Sign and verify ACK/COMMIT messages (replace placeholder signatures)
- [ ] Finish block/header sync (`send_headers`, `send_block`, GET\* flows)
- [ ] Implement leader timeout + view-change handling in `_check_timeouts`
- [ ] Optional: expose richer metrics/health endpoints for observability

## 🧪 Edge Cases & Testing

- [ ] Node restart during an in-flight commit (ensure no duplicate blocks)
- [ ] Network partition / delayed ACK quorum handling
- [ ] Peer list divergence between nodes (detect + warn early)
- [ ] Large mempool flush (max block size, starvation scenarios)

## 📚 Documentation & Tooling

- [ ] Link `docs/ARCHITECTURE.md` from `README.md`
- [ ] Author a quick-start walkthrough covering multi-node demos
- [ ] Add troubleshooting matrix for common networking/consensus issues
