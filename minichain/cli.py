import asyncio
import click
from .node import MiniChainNode
from . import config, messages
from .models import Transaction
from .crypto import derive_signing_key, canonical_pack, sign_bytes
from .logging_utils import info


def parse_peers(peers: str):
    # format: N1:127.0.0.1:48001,N2:127.0.0.1:48002
    out = {}
    if not peers:
        return out
    for part in peers.split(","):
        pid, host, port = part.split(":")
        out[pid] = (host, int(port))
    return out


@click.group()
def cli():
    """MiniChain CLI"""


@cli.command()
@click.argument("node_id")
@click.option("--peers", default="", help="Comma list N1:host:port,...")
def start(node_id, peers):
    """Start a MiniChain node."""
    peer_map = parse_peers(peers)
    node = MiniChainNode(node_id=node_id, peers=peer_map)

    async def run():
        await node.start()
        # keep running until Ctrl+C
        try:
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            await node.stop()

    asyncio.run(run())


@cli.command(name="serve-api")
@click.option("--host", default="0.0.0.0", help="HTTP host to bind")
@click.option("--port", default=8000, type=int, help="HTTP port to bind")
def serve_api(host, port):
    """Launch the MiniChain dashboard REST API."""
    try:
        import uvicorn
    except ImportError as exc:
        raise click.ClickException("uvicorn is required. Install dashboard dependencies first.") from exc
    from .api import app

    uvicorn.run(app, host=host, port=port, log_level="info")


@cli.command()
@click.argument("sender")
@click.argument("to")
@click.argument("amount", type=int)
@click.argument("nonce", type=int)
@click.option("--sign-seed", default=None, help="Seed for deterministic key")
@click.option("--target", required=True, help="Target peer ID")
@click.option("--peer", multiple=True, help="Peer mapping like N1:host:port; can repeat")
def tx(sender, to, amount, nonce, sign_seed, target, peer):
    """Send a transaction to a peer."""
    peers = {}
    for p in peer:
        pid, host, port = p.split(":")
        peers[pid] = (host, int(port))
    sk = derive_signing_key((sign_seed or sender).encode())
    body = {"from": sender, "to": to, "amount": amount, "nonce": nonce}
    sig = sign_bytes(sk, canonical_pack(body))
    tx_obj = Transaction(sender, to, amount, nonce, sig)
    import asyncio
    from .network import PeerClient
    pc = PeerClient()
    async def send():
        host, port = peers[target]
        conn = await pc.connect(target, host, port)
        if not conn:
            return
        msg = messages.pack_message(messages.MSG["TX"], sender, sk, tx_obj.pack())
        await conn.send(msg)
        info("tx_sent", tx_id=tx_obj.tx_id, to=target)
    asyncio.run(send())


@cli.command()
@click.argument("node_id")
@click.option("--peer", multiple=True, help="Peer mapping N1:host:port")
def status(node_id, peer):
    """Query heartbeat status from a peer (simplistic placeholder)."""
    # This could open connection and request STATUS; currently heartbeats are passive.
    click.echo("Status querying not implemented in prototype.")


if __name__ == "__main__":
    cli()