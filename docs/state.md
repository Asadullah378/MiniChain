# State & Data Model

## Transaction
```
{
  sender: <pubkey_hex>,
  to: <pubkey_hex>,
  amount: <int>,
  nonce: <int>,
  signature: <bytes>,
  tx_id: <sha256(body+sig) hex>
}
```
Rules:
- `signature` verifies over canonical msgpack of `{from, to, amount, nonce}` with sender's public key
- `nonce` strictly increases per sender
- `amount >= 0` and sender balance sufficient

## Block
```
{
  height: <int>,
  prev_hash: <hex>,
  timestamp: <float>,
  tx_list: [Transaction...],
  proposer_id: <validator_id>,
  signature: <bytes>,
  block_hash: <sha256(header+txs) hex>
}
```
Validity:
- `prev_hash` equals previous block's `block_hash`
- All transactions valid under account model
- `proposer_id` matches round-robin leader schedule for height (with view)

## Blockchain
- Append-only sequence from genesis
- `accounts` map pubkey_hex → balance
- `nonces` map pubkey_hex → last used nonce

## Genesis & Funding
- Prototype ships with empty balances; you can pre-fund in `ChainStore` instantiation (pass `genesis_balances`).
- Alternatively, grant balances via a custom genesis block or faucet logic.

## Serialization
- Canonical encoding uses msgpack with `use_bin_type=True, strict_types=True` to ensure deterministic hashing.
