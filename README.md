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

## Dashboard API

Each node persists its state to `data/node_<ID>/chain.json`. A lightweight FastAPI server exposes this data under `/api/*` so that external UIs can consume it without touching the raw files.

```bash
python -m minichain.cli serve-api --host 127.0.0.1 --port 8000
```

Optional env vars:

- `MINICHAIN_DATA` – override the directory that stores `node_*` folders (defaults to `./data`).
- `MINICHAIN_DASHBOARD_NODES` – comma list of node IDs to surface (defaults to `config.DEFAULT_VALIDATORS`).

Once running, the following endpoints are available (JSON responses):

- `GET /api/health` – readiness probe.
- `GET /api/nodes` – validator overviews.
- `GET /api/blocks?node_id=N0&limit=20` – paginated block summaries.
- `GET /api/blocks/{height}?node_id=N0` – detailed block payload.
- `GET /api/accounts?node_id=N0&q=alice` – account balances with filtering.
- `GET /api/transactions?node_id=N0&limit=25` – recent confirmed transfers.

## React Frontend

A professional single-page dashboard lives in `dashboard/` (Vite + React + Chakra UI). It consumes the API above and offers overview, blocks, transactions, accounts, and network topology pages.

```bash
cd dashboard
npm install
VITE_API_BASE_URL=http://localhost:8000/api npm run dev
```

The `VITE_API_BASE_URL` defaults to `http://localhost:8000/api`, but you can point it at any reachable API server. Build for production with `npm run build`; a static bundle will appear in `dashboard/dist/`.

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
