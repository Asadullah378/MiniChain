from __future__ import annotations

import asyncio
import struct
from typing import Callable, Dict, Optional
from .logging_utils import info, warn, debug


class FramedConnection:
    def __init__(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        self.reader = reader
        self.writer = writer

    async def send(self, data: bytes):
        self.writer.write(struct.pack(">I", len(data)))
        self.writer.write(data)
        await self.writer.drain()

    async def recv(self) -> Optional[bytes]:
        hdr = await self.reader.readexactly(4)
        if not hdr:
            return None
        (n,) = struct.unpack(">I", hdr)
        if n <= 0 or n > 16 * 1024 * 1024:
            return None
        return await self.reader.readexactly(n)

    def close(self):
        try:
            self.writer.close()
        except Exception:
            pass


class P2PServer:
    def __init__(self, host: str, port: int, on_client: Callable[[FramedConnection, str], None]):
        self.host = host
        self.port = port
        self.on_client = on_client
        self.server: Optional[asyncio.AbstractServer] = None

    async def start(self):
        self.server = await asyncio.start_server(self._handle, self.host, self.port)
        info("server_listening", host=self.host, port=self.port)

    async def _handle(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        conn = FramedConnection(reader, writer)
        peer = writer.get_extra_info("peername")
        peer_str = f"{peer[0]}:{peer[1]}" if peer else "?"
        await self.on_client(conn, peer_str)

    async def stop(self):
        if self.server:
            self.server.close()
            await self.server.wait_closed()


class PeerClient:
    def __init__(self):
        self.conns: Dict[str, FramedConnection] = {}

    async def connect(self, peer_id: str, host: str, port: int) -> Optional[FramedConnection]:
        try:
            reader, writer = await asyncio.open_connection(host, port)
            conn = FramedConnection(reader, writer)
            self.conns[peer_id] = conn
            info("peer_connected", peer_id=peer_id, host=host, port=port)
            return conn
        except Exception as e:
            warn("peer_connect_failed", peer_id=peer_id, host=host, port=port, error=str(e))
            return None

    def get(self, peer_id: str) -> Optional[FramedConnection]:
        return self.conns.get(peer_id)

    def remove(self, peer_id: str):
        c = self.conns.pop(peer_id, None)
        if c:
            c.close()
