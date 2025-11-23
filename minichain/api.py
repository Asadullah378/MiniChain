from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Dict, List, Optional

from fastapi import APIRouter, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from . import config

DATA_DIR = Path(config.DATA_DIR)
CONFIGURED_NODES = [n.strip() for n in os.environ.get("MINICHAIN_DASHBOARD_NODES", "").split(",") if n.strip()]


def _node_dir(node_id: str) -> Path:
    return DATA_DIR / f"node_{node_id}"


def _chain_file(node_id: str) -> Path:
    return _node_dir(node_id) / "chain.json"


def list_known_nodes() -> List[str]:
    discovered = {p.name.split("node_")[-1] for p in DATA_DIR.glob("node_*") if p.is_dir()}
    seeds = CONFIGURED_NODES or config.DEFAULT_VALIDATORS
    return sorted(set(seeds).union(discovered))


def _load_chain_snapshot(node_id: str) -> Dict:
    path = _chain_file(node_id)
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"No chain data for node {node_id}")
    raw = path.read_text().strip()
    if not raw:
        raise HTTPException(status_code=500, detail=f"Chain file empty for node {node_id}")
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=500, detail=f"Invalid chain JSON for node {node_id}: {exc}") from exc
    data.setdefault("blocks", [])
    data.setdefault("accounts", {})
    data.setdefault("nonces", {})
    return data


def _default_node() -> str:
    nodes = list_known_nodes()
    if not nodes:
        raise HTTPException(status_code=404, detail="No nodes available in data directory")
    return nodes[0]


class NodeOverview(BaseModel):
    node_id: str
    height: int
    head_hash: str
    last_block_time: float
    total_accounts: int
    total_balance: int


class BlockSummary(BaseModel):
    height: int
    block_hash: str
    prev_hash: str
    timestamp: float
    proposer_id: str
    tx_count: int


class BlockDetail(BlockSummary):
    tx_list: List[Dict]


class BlocksResponse(BaseModel):
    node_id: str
    total: int
    items: List[BlockSummary]


class AccountsResponse(BaseModel):
    node_id: str
    total: int
    items: List[Dict[str, int]]


class TransactionView(BaseModel):
    tx_id: str
    sender: str
    to: str
    amount: int
    nonce: int
    block_height: int
    block_hash: str


class TransactionsResponse(BaseModel):
    node_id: str
    items: List[TransactionView]


app = FastAPI(title="MiniChain Dashboard API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

router = APIRouter(prefix="/api")


@router.get("/health")
def healthcheck():
    return {"status": "ok"}


@router.get("/nodes", response_model=List[NodeOverview])
def get_nodes():
    nodes = []
    for node_id in list_known_nodes():
        try:
            snapshot = _load_chain_snapshot(node_id)
        except HTTPException:
            continue
        blocks = snapshot["blocks"]
        height = len(blocks) - 1 if blocks else 0
        head_hash = blocks[-1]["block_hash"] if blocks else "GENESIS"
        last_block_time = blocks[-1]["timestamp"] if blocks else 0.0
        accounts = snapshot["accounts"]
        nodes.append(
            NodeOverview(
                node_id=node_id,
                height=max(0, height),
                head_hash=head_hash,
                last_block_time=last_block_time,
                total_accounts=len(accounts),
                total_balance=sum(accounts.values()),
            )
        )
    if not nodes:
        raise HTTPException(status_code=404, detail="No node snapshots could be loaded")
    return nodes


@router.get("/blocks", response_model=BlocksResponse)
def get_blocks(node_id: Optional[str] = None, limit: int = Query(20, ge=1, le=200), offset: int = Query(0, ge=0)):
    target = node_id or _default_node()
    snapshot = _load_chain_snapshot(target)
    blocks = snapshot["blocks"]
    blocks_sorted = sorted(blocks, key=lambda b: b.get("height", 0), reverse=True)
    sliced = blocks_sorted[offset: offset + limit]
    summaries = [
        BlockSummary(
            height=b["height"],
            block_hash=b["block_hash"],
            prev_hash=b["prev_hash"],
            timestamp=b["timestamp"],
            proposer_id=b["proposer_id"],
            tx_count=len(b.get("tx_list", [])),
        )
        for b in sliced
    ]
    return BlocksResponse(node_id=target, total=len(blocks_sorted), items=summaries)


@router.get("/blocks/{height}", response_model=BlockDetail)
def get_block(height: int, node_id: Optional[str] = None):
    target = node_id or _default_node()
    snapshot = _load_chain_snapshot(target)
    for b in snapshot["blocks"]:
        if b.get("height") == height:
            return BlockDetail(
                height=b["height"],
                block_hash=b["block_hash"],
                prev_hash=b["prev_hash"],
                timestamp=b["timestamp"],
                proposer_id=b["proposer_id"],
                tx_count=len(b.get("tx_list", [])),
                tx_list=b.get("tx_list", []),
            )
    raise HTTPException(status_code=404, detail=f"Block {height} not found for node {target}")


@router.get("/accounts", response_model=AccountsResponse)
def get_accounts(
    node_id: Optional[str] = None,
    q: Optional[str] = Query(default=None, description="Case sensitive substring filter"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    target = node_id or _default_node()
    snapshot = _load_chain_snapshot(target)
    accounts = snapshot["accounts"]
    rows = sorted(accounts.items(), key=lambda kv: kv[0])
    if q:
        rows = [kv for kv in rows if q in kv[0]]
    total = len(rows)
    sliced = rows[offset: offset + limit]
    items = [{"address": addr, "balance": bal} for addr, bal in sliced]
    return AccountsResponse(node_id=target, total=total, items=items)


@router.get("/transactions", response_model=TransactionsResponse)
def get_transactions(node_id: Optional[str] = None, limit: int = Query(25, ge=1, le=200)):
    target = node_id or _default_node()
    snapshot = _load_chain_snapshot(target)
    blocks = sorted(snapshot["blocks"], key=lambda b: b.get("height", 0), reverse=True)
    collected: List[TransactionView] = []
    for block in blocks:
        for tx in block.get("tx_list", []):
            collected.append(
                TransactionView(
                    tx_id=tx.get("tx_id", ""),
                    sender=tx.get("sender", ""),
                    to=tx.get("to", ""),
                    amount=tx.get("amount", 0),
                    nonce=tx.get("nonce", 0),
                    block_height=block.get("height", 0),
                    block_hash=block.get("block_hash", ""),
                )
            )
            if len(collected) >= limit:
                break
        if len(collected) >= limit:
            break
    return TransactionsResponse(node_id=target, items=collected)


app.include_router(router)

__all__ = ["app", "list_known_nodes"]
