from __future__ import annotations

import time
from typing import Any, Dict, Tuple
import msgpack
from . import crypto


MSG = {
    "HELLO": "HELLO",
    "PEERLIST": "PEERLIST",
    "HEARTBEAT": "HEARTBEAT",
    "TX": "TX",
    "INV": "INV",
    "GETHEADERS": "GETHEADERS",
    "HEADERS": "HEADERS",
    "GETBLOCKS": "GETBLOCKS",
    "BLOCK": "BLOCK",
    "PROPOSE": "PROPOSE",
    "ACK": "ACK",
    "COMMIT": "COMMIT",
    "VIEWCHANGE": "VIEWCHANGE",
    "STATUS": "STATUS",
}


def pack_message(msg_type: str, sender_id: str, signer, payload: Dict[str, Any]) -> bytes:
    ts = time.time()
    header = {"type": msg_type, "sender_id": sender_id, "timestamp": ts}
    payload_bytes = crypto.canonical_pack(payload)
    sig = crypto.sign_bytes(signer, crypto.sha256(crypto.canonical_pack({**header, "payload": payload_bytes})))
    envelope = {"header": header, "signature": sig, "payload": payload_bytes}
    return msgpack.packb(envelope, use_bin_type=True, strict_types=True)


def unpack_message(raw: bytes) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    env = msgpack.unpackb(raw, raw=True)
    header = env[b"header"] if b"header" in env else env["header"]
    payload_bytes = env[b"payload"] if b"payload" in env else env["payload"]
    signature = env[b"signature"] if b"signature" in env else env["signature"]
    payload = msgpack.unpackb(payload_bytes, raw=False)
    return {"header": header, "signature": signature}, payload
