# MiniChain

A permissioned blockchain intended to support enterprise‑grade, append‑only logging and asset transfers across tens to hundreds of nodes. Each node maintains a replicated ledger (the blockchain), participates in consensus to order blocks, and enforces validation rules for transactions and blocks. The prototype demonstrates shared global state, synchronization/consistency, and consensus over 3 or more nodes communicating via TCP sockets or RPC. In a larger deployment, MiniChain scales with gossip‑style dissemination, leader rotation, and simple fork‑choice rules.
