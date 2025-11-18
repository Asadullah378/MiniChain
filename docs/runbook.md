# Runbook

This guide helps you run a local 3-node MiniChain cluster for demos and testing.

## Prerequisites
- Python 3.10+
- Linux/macOS (Windows works but `uvloop` is skipped)

## Setup
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Start Three Nodes
Run each command in its own terminal:
```bash
python -m minichain.cli start N0 --peers N0:127.0.0.1:48000,N1:127.0.0.1:48001,N2:127.0.0.1:48002
python -m minichain.cli start N1 --peers N0:127.0.0.1:48000,N1:127.0.0.1:48001,N2:127.0.0.1:48002
python -m minichain.cli start N2 --peers N0:127.0.0.1:48000,N1:127.0.0.1:48001,N2:127.0.0.1:48002
```
Alternatively use the script:
```bash
bash examples/demo_three_nodes.sh
```

## Submit Transactions
Get two deterministic public keys (for demo only):
```bash
python - <<'PY'
from minichain.crypto import derive_signing_key
print('alice', derive_signing_key(b'seed_alice').verify_key.encode().hex())
print('bob  ', derive_signing_key(b'seed_bob').verify_key.encode().hex())
PY
```
Send 10 units from alice → bob with nonce 1 via N0:
```bash
python -m minichain.cli tx <alice_pub> <bob_pub> 10 1 \
  --target N0 \
  --peer N0:127.0.0.1:48000 --peer N1:127.0.0.1:48001 --peer N2:127.0.0.1:48002
```

## Inspect State
- Blocks and state live under `./data/node_<id>/chain.json`.
- Logs are printed as JSON (one line per event).

## Reset
Stop nodes and delete `./data/node_*` folders to reset state.

## Troubleshooting
- Ports in use: change `MINICHAIN_BASE_PORT` env var or peer list ports.
- No progress: ensure all three nodes are running and interconnected; check logs for `propose_sent`, `ack_sent`, `commit_broadcast`.
- Nonce errors: increment nonce per sender (1, 2, 3, ...).
