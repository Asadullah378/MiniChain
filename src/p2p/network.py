"""Network manager for P2P communication."""

import socket
import threading
import time
from typing import Dict, List, Optional, Callable, Tuple
from src.p2p.messages import Message, MessageType
from src.chain.block import Block, Transaction


class NetworkManager:
    """Manages peer-to-peer network connections."""
    
    def __init__(self, node_id: str, hostname: str, port: int,
                 peers: List[Dict], message_handler: Callable,
                 logger=None):
        """
        Initialize network manager.
        
        Args:
            node_id: This node's ID
            hostname: This node's hostname
            port: Listening port
            peers: List of peer configurations [{'hostname': ..., 'port': ...}]
            message_handler: Callback function(message, peer_address) for incoming messages
            logger: Logger instance
        """
        self.node_id = node_id
        self.hostname = hostname
        self.port = port
        self.peers = peers
        self.message_handler = message_handler
        self.logger = logger or __import__('logging').getLogger('network')
        
        self.running = False
        self.listener_socket: Optional[socket.socket] = None
        self.connections: Dict[str, socket.socket] = {}  # peer_address -> socket
        self.connection_lock = threading.Lock()
        self.listener_thread: Optional[threading.Thread] = None
    
    def start(self):
        """Start network manager."""
        self.logger.info(f"Starting network manager on {self.hostname}:{self.port}")
        self.running = True
        
        # Start listener
        self.listener_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.listener_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.listener_socket.bind(('0.0.0.0', self.port))
        self.listener_socket.listen(10)
        self.listener_socket.settimeout(1.0)  # Allow periodic checks
        
        self.listener_thread = threading.Thread(target=self._listener_loop, daemon=True)
        self.listener_thread.start()
        
        # Connect to peers
        time.sleep(0.5)  # Give listener time to start
        self._connect_to_peers()
    
    def stop(self):
        """Stop network manager."""
        self.logger.info("Stopping network manager...")
        self.running = False
        
        if self.listener_socket:
            self.listener_socket.close()
        
        with self.connection_lock:
            for sock in self.connections.values():
                try:
                    sock.close()
                except:
                    pass
            self.connections.clear()
    
    def _listener_loop(self):
        """Listen for incoming connections."""
        while self.running:
            try:
                client_socket, address = self.listener_socket.accept()
                self.logger.info(f"New connection from {address}")
                
                # Handle connection in separate thread
                thread = threading.Thread(
                    target=self._handle_connection,
                    args=(client_socket, address),
                    daemon=True
                )
                thread.start()
            except socket.timeout:
                continue
            except Exception as e:
                if self.running:
                    self.logger.error(f"Error in listener: {e}")
    
    def _handle_connection(self, sock: socket.socket, address: Tuple[str, int]):
        """Handle a connection from a peer."""
        peer_address = f"{address[0]}:{address[1]}"
        
        with self.connection_lock:
            self.connections[peer_address] = sock
        
        try:
            while self.running:
                # Receive message length (4 bytes)
                length_data = sock.recv(4)
                if not length_data or len(length_data) < 4:
                    break
                
                length = int.from_bytes(length_data, 'big')
                
                # Receive message data
                data = b''
                while len(data) < length:
                    chunk = sock.recv(length - len(data))
                    if not chunk:
                        break
                    data += chunk
                
                if len(data) < length:
                    break
                
                # Deserialize and handle message
                message = Message.deserialize(data)
                self.message_handler(message, peer_address)
        
        except Exception as e:
            if self.running:
                self.logger.error(f"Error handling connection from {peer_address}: {e}")
        finally:
            with self.connection_lock:
                if peer_address in self.connections:
                    del self.connections[peer_address]
            try:
                sock.close()
            except:
                pass
    
    def _connect_to_peers(self):
        """Connect to all configured peers."""
        for peer in self.peers:
            hostname = peer.get('hostname')
            port = peer.get('port', self.port)
            
            if hostname == self.hostname and port == self.port:
                continue  # Skip self
            
            thread = threading.Thread(
                target=self._connect_to_peer,
                args=(hostname, port),
                daemon=True
            )
            thread.start()
    
    def _connect_to_peer(self, hostname: str, port: int):
        """Connect to a specific peer."""
        peer_address = f"{hostname}:{port}"
        
        if peer_address in self.connections:
            return  # Already connected
        
        try:
            self.logger.info(f"Connecting to peer {hostname}:{port}")
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            sock.connect((hostname, port))
            sock.settimeout(None)
            
            with self.connection_lock:
                self.connections[peer_address] = sock
            
            # Send HELLO message
            hello = Message.create_hello(self.node_id, "0.1.0", self.port)
            self._send_message(sock, hello)
            
            self.logger.info(f"Connected to {hostname}:{port}")
            
            # Handle incoming messages from this peer
            self._handle_connection(sock, (hostname, port))
        
        except Exception as e:
            self.logger.warning(f"Failed to connect to {hostname}:{port}: {e}")
            with self.connection_lock:
                if peer_address in self.connections:
                    del self.connections[peer_address]
    
    def _send_message(self, sock: socket.socket, message: Message):
        """Send a message over a socket."""
        try:
            data = message.serialize()
            length = len(data).to_bytes(4, 'big')
            sock.sendall(length + data)
        except Exception as e:
            self.logger.error(f"Error sending message: {e}")
    
    def _broadcast(self, message: Message, exclude: Optional[str] = None):
        """Broadcast message to all connected peers."""
        with self.connection_lock:
            for peer_address, sock in list(self.connections.items()):
                if peer_address == exclude:
                    continue
                try:
                    self._send_message(sock, message)
                except Exception as e:
                    self.logger.warning(f"Failed to send to {peer_address}: {e}")
    
    def broadcast_transaction(self, tx: Transaction):
        """Broadcast a transaction to all peers."""
        message = Message.create_tx(self.node_id, tx.serialize())
        self._broadcast(message)
    
    def broadcast_propose(self, block: Block):
        """Broadcast a block proposal."""
        tx_list = [tx.serialize() for tx in block.transactions]
        message = Message.create_propose(
            self.node_id,
            block.height,
            block.prev_hash,
            tx_list,
            block.proposer_id,
            block.block_hash,
            block.signature
        )
        self._broadcast(message)
    
    def send_ack(self, height: int, block_hash: bytes, voter_id: str):
        """Send ACK message (broadcast to all, but typically only leader processes it)."""
        # For simplicity, we'll sign with empty signature for now
        # In production, this should be signed with node's private key
        message = Message.create_ack(
            self.node_id,
            height,
            block_hash,
            voter_id,
            b''  # TODO: Add proper signature
        )
        self._broadcast(message)
    
    def broadcast_commit(self, height: int, block_hash: bytes, leader_id: str):
        """Broadcast COMMIT message."""
        message = Message.create_commit(
            self.node_id,
            height,
            block_hash,
            leader_id,
            b''  # TODO: Add proper signature
        )
        self._broadcast(message)
    
    def send_headers(self, headers: List[Dict], peer_address: str):
        """Send block headers to a peer."""
        # TODO: Implement HEADERS message
        pass
    
    def send_block(self, block: Block, peer_address: str):
        """Send a block to a peer."""
        # TODO: Implement BLOCK message
        pass

