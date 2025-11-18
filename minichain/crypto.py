from __future__ import annotations

import hashlib
from nacl.signing import SigningKey, VerifyKey
from nacl.exceptions import BadSignatureError
import msgpack


def sha256(data: bytes) -> bytes:
    return hashlib.sha256(data).digest()


def canonical_pack(obj) -> bytes:
    return msgpack.packb(obj, use_bin_type=True, strict_types=True)


def derive_signing_key(seed: bytes) -> SigningKey:
    h = sha256(seed)
    return SigningKey(h)


def pubkey_hex(vk: VerifyKey | bytes) -> str:
    if isinstance(vk, VerifyKey):
        return vk.encode().hex()
    return bytes(vk).hex()


def sign_bytes(sk: SigningKey, payload: bytes) -> bytes:
    return sk.sign(payload).signature


def verify_bytes(vk_hex: str, payload: bytes, signature: bytes) -> bool:
    try:
        vk = VerifyKey(bytes.fromhex(vk_hex))
        vk.verify(payload, signature)
        return True
    except BadSignatureError:
        return False


def tx_id(tx_body: dict, signature: bytes) -> str:
    data = canonical_pack({"body": tx_body, "sig": signature})
    return sha256(data).hex()


def block_hash(header: dict, tx_list: list[dict]) -> str:
    data = canonical_pack({"header": header, "txs": tx_list})
    return sha256(data).hex()
