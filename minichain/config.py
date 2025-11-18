from __future__ import annotations

import os


DEFAULT_VALIDATORS = ["N0", "N1", "N2"]
MAX_TX_PER_BLOCK = 50
ACK_QUORUM_FRACTION = 0.51  # simple majority
PROPOSE_INTERVAL_SEC = 3.0  # leader propose tick
ACK_TIMEOUT_SEC = 5.0
VIEWCHANGE_TIMEOUT_SEC = 7.0
HEARTBEAT_INTERVAL_SEC = 2.0
SYNC_BATCH_SIZE = 100

DATA_DIR = os.environ.get("MINICHAIN_DATA", "./data")
LOG_LEVEL = os.environ.get("MINICHAIN_LOG", "INFO")

def get_node_port(node_id: str) -> int:
    base = int(os.environ.get("MINICHAIN_BASE_PORT", "48000"))
    try:
        idx = DEFAULT_VALIDATORS.index(node_id)
    except ValueError:
        idx = 10  # arbitrary offset for non-validator clients
    return base + idx

def quorum_size(validators: list[str] | None = None) -> int:
    v = validators or DEFAULT_VALIDATORS
    return max(1, int(len(v) * ACK_QUORUM_FRACTION + 0.0001))
