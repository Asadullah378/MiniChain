# Consensus: Round-Robin PoA

MiniChain uses a simple leader-based Proof-of-Authority (PoA) with a fixed validator set `V = [N0, N1, ..., N(k-1)]`.

## Leader Selection
- Leader at height `h` is `V[(h + view) mod k]` where `view` counts timeouts/view changes.

## Per-Height Protocol
1. Leader collects up to `MAX_TX_PER_BLOCK` transactions from mempool.
2. Leader builds block (height, prev_hash, timestamp, proposer_id, tx_list) and computes `block_hash`.
3. Leader broadcasts `PROPOSE`.
4. Followers validate: link, leader identity, all tx rules; reply with `ACK` on success.
5. Leader collects ACKs; on quorum (simple majority) broadcasts `COMMIT`.
6. All nodes append the block and evict included transactions from mempool.

## Timeouts and View Change
- If insufficient ACKs by `ACK_TIMEOUT_SEC`, increment `view` and broadcast `VIEWCHANGE`.
- New leader for the same height will attempt a new proposal.

## Safety & Liveness (Informal)
- Safety: A block is committed only after majority ACK, preventing divergent commits at same height under benign conditions.
- Liveness: Timeouts and leader rotation ensure progress if a leader fails or is partitioned.

## Quorum
- Quorum size = ceil(0.51 * |V|) (prototype majority). Configurable via `ACK_QUORUM_FRACTION`.

## Fork Choice
- Prefer highest chain height; if tied, pick lowest block hash for determinism.

## Limitations & Future
- No byzantine equivocation handling (e.g., double-propose) beyond majority assumption.
- No slashing or reputation; validators assumed known and permissioned.
- Potential upgrade to weighted voting or PBFT-style 3-phase.
