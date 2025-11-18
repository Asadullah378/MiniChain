# MiniChain

A permissioned blockchain intended to support enterprise‑grade, append‑only logging and asset transfers across tens to hundreds of nodes. Each node maintains a replicated ledger (the blockchain), participates in consensus to order blocks, and enforces validation rules for transactions and blocks. The prototype demonstrates shared global state, synchronization/consistency, and consensus over 3 or more nodes communicating via TCP sockets or RPC. In a larger deployment, MiniChain scales with gossip‑style dissemination, leader rotation, and simple fork‑choice rules.

Key links: see `docs/architecture.md`, `docs/consensus.md`, and `docs/protocol.md` for details.

## Features

- Round‑robin PoA consensus with quorum ACKs and COMMITs
- Append‑only persistent chain with account balances and nonces
- Gossip-style TX propagation and catch‑up sync (headers + blocks)
- Async TCP networking with length‑prefixed msgpack frames
- Structured JSON logs for proposals, ACKs, commits, timeouts

## Install

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Quick Start (3 local validators)

Run in three terminals:

```bash
python -m minichain.cli start N0 --peers N0:127.0.0.1:48000,N1:127.0.0.1:48001,N2:127.0.0.1:48002
python -m minichain.cli start N1 --peers N0:127.0.0.1:48000,N1:127.0.0.1:48001,N2:127.0.0.1:48002
python -m minichain.cli start N2 --peers N0:127.0.0.1:48000,N1:127.0.0.1:48001,N2:127.0.0.1:48002
```

Submit a transaction (nonce must increment per sender):

```bash
python -m minichain.cli tx <sender_pubkey_hex> <recipient_pubkey_hex> 10 1 \
  --target N0 \
  --peer N0:127.0.0.1:48000 --peer N1:127.0.0.1:48001 --peer N2:127.0.0.1:48002
```

Tip: derive a public key hex deterministically with Python:

```bash
python - <<'PY'
from minichain.crypto import derive_signing_key
sk = derive_signing_key(b'seed_alice')
print(sk.verify_key.encode().hex())
PY
```

## Repo Structure

- `minichain/` core modules: config, crypto, models, messages, store, mempool, network, consensus, sync, node, cli, logging_utils
- `examples/demo_three_nodes.sh` quick local run script
- `docs/` architecture, protocol, consensus, state model, runbook, roadmap

## Notes & Limits

- Prototype security: no TLS, minimal peer auth; add before production
- Simple majority quorum; no weights; no BFT slashing
- Basic view change; proposals may need re‑issuance post‑timeout
- Simplified discovery; static peer list provided via CLI

For deeper design docs, see the `docs/` directory.
