# Roadmap

## Near-Term

- Message signature verification on receive
- STATUS request/response and metrics endpoint (Prometheus)
- Peer reconnection & dynamic discovery (HELLO + PEERLIST exchange)
- INV / GETTX / GETBLOCK for efficient diffusive gossip
- Configurable quorum fraction and dynamic validator set reload

## Medium-Term

- Proper fork resolution with alternative chain buffering
- Merkle tree for block transactions; receipts API
- TLS transport and authenticated validator key registry
- Persistent key storage separate from process (e.g., HSM integration mock)
- Load testing scripts for propagation & latency measurement

## Long-Term

- Pluggable consensus (Raft / PBFT-lite / HotStuff phases)
- Sharding / partitioning strategy for horizontal scaling
- Smart contract / programmable transaction layer (WASM sandbox)
- Formal verification of consensus safety properties
- Advanced monitoring dashboard (Grafana + traces)
