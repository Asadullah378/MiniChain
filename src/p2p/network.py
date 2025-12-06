"""Network manager for P2P communication."""

import socket
import threading
import time
from typing import Dict, List, Optional, Callable, Tuple
from src.p2p.messages import Message, MessageType
from src.chain.block import Block, Transaction


class NetworkManager:
    """Manages peer-to-peer network connections."""
    
    # Heartbeat and failure detection settings
    HEARTBEAT_INTERVAL = 3  # Send heartbeat every 3 seconds
    HEARTBEAT_TIMEOUT = 10  # Consider peer dead after 10 seconds of no heartbeat
    RECONNECT_INTERVAL = 5  # Try to reconnect every 5 seconds
    
    def __init__(self, node_id: str, hostname: str, port: int,
                 peers: List[Dict], message_handler: Callable,
                 logger=None, failure_callback: Callable = None,
                 recovery_callback: Callable = None,
                 is_recovering_check: Callable = None):
        """
        Initialize network manager.
        
        Args:
            node_id: This node's ID
            hostname: This node's hostname
            port: Listening port
            peers: List of peer configurations [{'hostname': ..., 'port': ...}]
            message_handler: Callback function(message, peer_address) for incoming messages
            logger: Logger instance
            failure_callback: Callback function(peer_hostname) when a peer fails
            recovery_callback: Callback function(peer_hostname) when a peer recovers
            is_recovering_check: Callback function() -> bool, returns True if node is recovering (skip health checks)
        """
        self.node_id = node_id
        self.hostname = hostname
        self.port = port
        self.peers = peers
        self.message_handler = message_handler
        self.logger = logger or __import__('logging').getLogger('network')
        self.failure_callback = failure_callback
        self.recovery_callback = recovery_callback
        self.is_recovering_check = is_recovering_check
        
        self.running = False
        self.listener_socket: Optional[socket.socket] = None
        self.connections: Dict[str, socket.socket] = {}  # peer_address -> socket
        self.connection_lock = threading.Lock()
        self.listener_thread: Optional[threading.Thread] = None
        
        # Peer health tracking
        self.peer_last_heartbeat: Dict[str, float] = {}  # peer_hostname -> last heartbeat time
        self.peer_status: Dict[str, bool] = {}  # peer_hostname -> is_alive
        self.heartbeat_thread: Optional[threading.Thread] = None
        self.health_check_thread: Optional[threading.Thread] = None
    
    def start(self):
        """Start network manager."""
        self.logger.info(f"Starting network manager on {self.hostname}:{self.port}")
        self.logger.info(f"Configured peers: {len(self.peers)}")
        self.running = True
        
        # Initialize peer status
        for peer in self.peers:
            hostname = peer.get('hostname')
            if hostname and hostname != self.hostname:
                self.peer_status[hostname] = False
                self.peer_last_heartbeat[hostname] = 0
        
        # Start listener
        self.logger.info(f"Starting listener on port {self.port}...")
        self.listener_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.listener_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.listener_socket.bind(('0.0.0.0', self.port))
        self.listener_socket.listen(10)
        self.listener_socket.settimeout(1.0)  # Allow periodic checks
        self.logger.info(f"Listener started on {self.hostname}:{self.port}")
        
        self.listener_thread = threading.Thread(target=self._listener_loop, daemon=True)
        self.listener_thread.start()
        self.logger.info(f"Listener thread started")
        
        # Connect to peers
        self.logger.info(f"Initiating connections to {len(self.peers)} peer(s)...")
        time.sleep(0.5)  # Give listener time to start
        self._connect_to_peers()
        
        # Start heartbeat sender
        self.heartbeat_thread = threading.Thread(target=self._heartbeat_loop, daemon=True)
        self.heartbeat_thread.start()
        self.logger.info("Heartbeat sender started")
        
        # Start health check
        self.health_check_thread = threading.Thread(target=self._health_check_loop, daemon=True)
        self.health_check_thread.start()
        self.logger.info("Health check monitor started")
    
    def stop(self):
        """Stop network manager."""
        self.logger.info("Stopping network manager...")
        self.running = False
        
        if self.listener_socket:
            self.logger.debug("Closing listener socket...")
            self.listener_socket.close()
        
        with self.connection_lock:
            connection_count = len(self.connections)
            self.logger.info(f"Closing {connection_count} peer connection(s)...")
            for sock in self.connections.values():
                try:
                    sock.close()
                except:
                    pass
            self.connections.clear()
        self.logger.info("Network manager stopped")
    
    def _heartbeat_loop(self):
        """Periodically send heartbeat to all peers."""
        while self.running:
            try:
                self._broadcast_heartbeat()
                time.sleep(self.HEARTBEAT_INTERVAL)
            except Exception as e:
                if self.running:
                    self.logger.error(f"Error in heartbeat loop: {e}")
                time.sleep(1)
    
    def _health_check_loop(self):
        """Periodically check peer health and detect failures."""
        # Track which peers we've already notified about failure
        notified_failures = set()
        
        # Wait a bit before starting health checks to allow initial connections
        time.sleep(5)
        
        while self.running:
            try:
                # Skip health checks if node is still recovering
                if self.is_recovering_check and self.is_recovering_check():
                    self.logger.debug("Skipping health checks - node is still recovering")
                    time.sleep(2)
                    continue
                
                current_time = time.time()
                
                for peer in self.peers:
                    hostname = peer.get('hostname')
                    if not hostname or hostname == self.hostname:
                        continue
                    
                    last_heartbeat = self.peer_last_heartbeat.get(hostname, 0)
                    was_alive = self.peer_status.get(hostname, False)
                    
                    # Check if peer has timed out
                    # Only check if we've received at least one heartbeat (last_heartbeat > 0)
                    # AND we previously considered them alive
                    if last_heartbeat > 0 and was_alive and (current_time - last_heartbeat) > self.HEARTBEAT_TIMEOUT:
                        # Peer just failed
                        self.peer_status[hostname] = False
                        self.logger.warning(f"PEER FAILURE DETECTED: {hostname} (no heartbeat for {current_time - last_heartbeat:.1f}s)")
                        
                        # Only notify callback once per failure (not repeatedly)
                        if hostname not in notified_failures:
                            notified_failures.add(hostname)
                            if self.failure_callback:
                                try:
                                    self.failure_callback(hostname)
                                except Exception as e:
                                    self.logger.error(f"Error in failure callback: {e}")
                        
                        # Try to reconnect (but not too frequently)
                        self._try_reconnect(hostname, peer.get('port', self.port))
                    
                    # If peer recovered, clear the notified flag
                    elif was_alive and hostname in notified_failures:
                        notified_failures.discard(hostname)
                
                time.sleep(2)  # Check every 2 seconds
            except Exception as e:
                if self.running:
                    self.logger.error(f"Error in health check loop: {e}")
                time.sleep(1)
    
    def _try_reconnect(self, hostname: str, port: int):
        """Try to reconnect to a failed peer."""
        thread = threading.Thread(
            target=self._reconnect_peer,
            args=(hostname, port),
            daemon=True
        )
        thread.start()
    
    def _reconnect_peer(self, hostname: str, port: int):
        """Attempt to reconnect to a peer."""
        peer_address = f"{hostname}:{port}"
        
        # Check if already connected
        with self.connection_lock:
            if peer_address in self.connections:
                return
        
        try:
            self.logger.info(f"Attempting to reconnect to {hostname}:{port}...")
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            sock.connect((hostname, port))
            sock.settimeout(None)
            
            with self.connection_lock:
                self.connections[peer_address] = sock
            
            # Send HELLO message
            hello = Message.create_hello(self.node_id, "0.1.0", self.port)
            self._send_message(sock, hello)
            
            # Mark peer as alive
            self.peer_status[hostname] = True
            self.peer_last_heartbeat[hostname] = time.time()
            
            self.logger.info(f"Reconnected to {hostname}:{port}")
            
            # Notify recovery callback
            if self.recovery_callback:
                try:
                    self.recovery_callback(hostname)
                except Exception as e:
                    self.logger.error(f"Error in recovery callback: {e}")
            
            # Handle incoming messages from this peer
            self._handle_connection(sock, (hostname, port))
            
        except Exception as e:
            self.logger.debug(f"Failed to reconnect to {hostname}:{port}: {e}")
    
    def record_heartbeat(self, peer_hostname: str):
        """Record a heartbeat from a peer."""
        # Normalize hostname for matching
        short_hostname = peer_hostname.split('.')[0]
        
        # Find matching peer
        for peer in self.peers:
            hostname = peer.get('hostname', '')
            if hostname == peer_hostname or hostname.split('.')[0] == short_hostname:
                was_alive = self.peer_status.get(hostname, False)
                self.peer_last_heartbeat[hostname] = time.time()
                self.peer_status[hostname] = True
                
                # If peer was previously dead, notify recovery
                if not was_alive and self.recovery_callback:
                    self.logger.info(f"PEER RECOVERY DETECTED: {hostname}")
                    try:
                        self.recovery_callback(hostname)
                    except Exception as e:
                        self.logger.error(f"Error in recovery callback: {e}")
                break
    
    def get_active_peers(self) -> List[str]:
        """Get list of currently active peer hostnames."""
        return [hostname for hostname, is_alive in self.peer_status.items() if is_alive]
    
    def get_peer_status(self) -> Dict[str, bool]:
        """Get status of all peers."""
        return dict(self.peer_status)
    
    def _broadcast_heartbeat(self):
        """Broadcast heartbeat to all peers."""
        # This will be called by node to include height and hash
        pass  # Implemented in Node class
    
    def _listener_loop(self):
        """Listen for incoming connections."""
        self.logger.info(" Listener loop started, waiting for incoming connections...")
        while self.running:
            try:
                client_socket, address = self.listener_socket.accept()
                self.logger.info(f" New incoming connection from {address[0]}:{address[1]}")
                
                # Handle connection in separate thread
                thread = threading.Thread(
                    target=self._handle_connection,
                    args=(client_socket, address),
                    daemon=True
                )
                thread.start()
                self.logger.debug(f" Started handler thread for connection from {address[0]}:{address[1]}")
            except socket.timeout:
                continue
            except Exception as e:
                if self.running:
                    self.logger.error(f" Error in listener: {e}", exc_info=True)
    
    def _handle_connection(self, sock: socket.socket, address: Tuple[str, int]):
        """Handle a connection from a peer."""
        peer_address = f"{address[0]}:{address[1]}"
        
        with self.connection_lock:
            self.connections[peer_address] = sock
        self.logger.info(f" Connection established with {peer_address} (total connections: {len(self.connections)})")
        
        try:
            while self.running:
                # Receive message length (4 bytes)
                length_data = sock.recv(4)
                if not length_data or len(length_data) < 4:
                    self.logger.debug(f" Connection closed by {peer_address} (no length data)")
                    break
                
                length = int.from_bytes(length_data, 'big')
                self.logger.debug(f" Receiving message from {peer_address} (length: {length} bytes)")
                
                # Receive message data
                data = b''
                while len(data) < length:
                    chunk = sock.recv(length - len(data))
                    if not chunk:
                        self.logger.debug(f" Connection closed by {peer_address} during data receive")
                        break
                    data += chunk
                
                if len(data) < length:
                    self.logger.warning(f" Incomplete message received from {peer_address} (expected {length}, got {len(data)})")
                    break
                
                # Deserialize and handle message
                message = Message.deserialize(data)
                self.logger.debug(f" Message received and deserialized from {peer_address}: {message.type.value}")
                self.message_handler(message, peer_address)
        
        except (ConnectionResetError, BrokenPipeError, ConnectionAbortedError) as e:
            # These are expected when a peer disconnects - not an error
            if self.running:
                self.logger.debug(f"Peer {peer_address} disconnected: {e}")
        except OSError as e:
            # Handle other socket errors gracefully (e.g., "Transport endpoint is not connected")
            if self.running:
                self.logger.debug(f"Connection to {peer_address} closed: {e}")
        except Exception as e:
            if self.running:
                self.logger.error(f"Error handling connection from {peer_address}: {e}", exc_info=True)
        finally:
            with self.connection_lock:
                if peer_address in self.connections:
                    del self.connections[peer_address]
                    self.logger.info(f" Connection closed with {peer_address} (remaining connections: {len(self.connections)})")
            try:
                sock.close()
            except:
                pass
    
    def _connect_to_peers(self):
        """Connect to all configured peers."""
        self.logger.info(f" Attempting to connect to {len(self.peers)} peer(s)...")
        for peer in self.peers:
            hostname = peer.get('hostname')
            port = peer.get('port', self.port)
            
            if hostname == self.hostname and port == self.port:
                self.logger.debug(f" Skipping self ({hostname}:{port})")
                continue  # Skip self
            
            self.logger.debug(f" Starting connection thread to {hostname}:{port}")
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
            self.logger.debug(f" Already connected to {peer_address}, skipping")
            return  # Already connected
        
        try:
            self.logger.info(f" Connecting to peer {hostname}:{port}...")
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            sock.connect((hostname, port))
            sock.settimeout(None)
            self.logger.info(f" Socket connection established to {hostname}:{port}")
            
            with self.connection_lock:
                self.connections[peer_address] = sock
                self.logger.debug(f" Added {peer_address} to connections (total: {len(self.connections)})")
            
            # Send HELLO message
            self.logger.debug(f"👋 Sending HELLO message to {hostname}:{port}")
            hello = Message.create_hello(self.node_id, "0.1.0", self.port)
            self._send_message(sock, hello)
            self.logger.info(f" Connected to {hostname}:{port} and sent HELLO")
            
            # Handle incoming messages from this peer
            self._handle_connection(sock, (hostname, port))
        
        except Exception as e:
            self.logger.warning(f" Failed to connect to {hostname}:{port}: {e}")
            with self.connection_lock:
                if peer_address in self.connections:
                    del self.connections[peer_address]
    
    def _send_message(self, sock: socket.socket, message: Message):
        """Send a message over a socket."""
        try:
            data = message.serialize()
            length = len(data).to_bytes(4, 'big')
            sock.sendall(length + data)
            self.logger.debug(f" Sent {message.type.value} message ({len(data)} bytes)")
        except (ConnectionResetError, BrokenPipeError, ConnectionAbortedError, OSError) as e:
            # Connection-related errors are expected when peer disconnects - don't log as error
            self.logger.debug(f"Failed to send {message.type.value} message (peer disconnected): {e}")
            raise  # Re-raise so caller knows send failed
        except Exception as e:
            self.logger.error(f"Error sending {message.type.value} message: {e}", exc_info=True)
            raise
    
    def _broadcast(self, message: Message, exclude: Optional[str] = None):
        """Broadcast message to all connected peers."""
        with self.connection_lock:
            connections = list(self.connections.items())
            self.logger.debug(f" Broadcasting {message.type.value} to {len(connections)} peer(s)...")
            success_count = 0
            for peer_address, sock in connections:
                if peer_address == exclude:
                    self.logger.debug(f" Skipping {peer_address} (excluded)")
                    continue
                try:
                    self._send_message(sock, message)
                    success_count += 1
                except Exception as e:
                    self.logger.warning(f" Failed to send {message.type.value} to {peer_address}: {e}")
            self.logger.debug(f" Broadcast complete: {success_count}/{len(connections)} successful")
    
    def broadcast_transaction(self, tx: Transaction):
        """Broadcast a transaction to all peers."""
        self.logger.debug(f" Broadcasting transaction {tx.tx_id[:16]}... to all peers")
        message = Message.create_tx(self.node_id, tx.serialize())
        self._broadcast(message)
        self.logger.debug(f" Transaction {tx.tx_id[:16]}... broadcasted")
    
    def broadcast_propose(self, block: Block):
        """Broadcast a block proposal."""
        self.logger.debug(f" Broadcasting PROPOSE for height {block.height} with {len(block.transactions)} transaction(s)")
        tx_list = [tx.serialize() for tx in block.transactions]
        message = Message.create_propose(
            self.node_id,
            block.height,
            block.prev_hash,
            tx_list,
            block.proposer_id,
            block.block_hash,
            block.timestamp,
            block.signature
        )
        self._broadcast(message)
        self.logger.debug(f" PROPOSE for height {block.height} broadcasted")
    
    def send_ack(self, height: int, block_hash: bytes, voter_id: str, leader_hostname: str):
        """
        Send ACK message to the leader (broadcast to all peers to ensure delivery).
        
        Args:
            height: Block height
            block_hash: Block hash
            voter_id: Voter's identifier
            leader_hostname: Hostname of the leader (for logging)
        """
        # For simplicity, we'll sign with empty signature for now
        # In production, this should be signed with node's private key
        message = Message.create_ack(
            self.node_id,
            height,
            block_hash,
            voter_id,
            b''  # TODO: Add proper signature
        )
        # Broadcast ACK to all peers to ensure leader receives it
        # (The leader will process it, other nodes will ignore it)
        self.logger.info(f"Broadcasting ACK for height {height} to leader {leader_hostname}")
        self._broadcast(message)
    
    def _send_to_leader(self, message: Message, leader_hostname: str):
        """Send a message to a specific leader node. Only sends once even if multiple connections exist."""
        # Extract short hostname for matching (e.g., "svm-11-3" from "svm-11-3.cs.helsinki.fi")
        leader_short = leader_hostname.split('.')[0]
        sent = False
        
        # First, try to find in existing connections
        with self.connection_lock:
            for peer_address, sock in self.connections.items():
                # Extract hostname from peer_address (format: "hostname:port")
                peer_hostname = peer_address.split(':')[0]
                peer_short = peer_hostname.split('.')[0]
                
                # Match by full hostname or short hostname
                if (leader_hostname == peer_hostname or 
                    leader_short == peer_short or
                    leader_hostname in peer_hostname or
                    peer_hostname in leader_hostname):
                    if not sent:  # Only send once, even if multiple connections match
                        try:
                            self._send_message(sock, message)
                            self.logger.debug(f"Sent ACK to leader {leader_hostname} at {peer_address}")
                            sent = True
                            return  # Successfully sent, exit early
                        except Exception as e:
                            self.logger.warning(f"Failed to send to leader {leader_hostname} at {peer_address}: {e}")
        
        # If not found in connections, try to find by hostname in peers list
        if not sent:
            for peer in self.peers:
                peer_hostname = peer.get('hostname', '')
                peer_short = peer_hostname.split('.')[0] if peer_hostname else ''
                
                if (leader_hostname == peer_hostname or 
                    leader_short == peer_short or
                    leader_hostname in peer_hostname):
                    # Try to connect and send
                    try:
                        hostname = peer.get('hostname')
                        port = peer.get('port', self.port)
                        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                        sock.settimeout(5)
                        sock.connect((hostname, port))
                        sock.settimeout(None)
                        self._send_message(sock, message)
                        sock.close()
                        self.logger.debug(f"Sent ACK to leader {leader_hostname} via new connection")
                        sent = True
                        return  # Successfully sent, exit early
                    except Exception as e:
                        self.logger.warning(f"Failed to send ACK to leader {leader_hostname}: {e}")
        
        if not sent:
            self.logger.warning(f"Could not find connection to leader {leader_hostname} for ACK")
    
    def broadcast_commit(self, height: int, block_hash: bytes, leader_id: str):
        """Broadcast COMMIT message."""
        self.logger.debug(f" Broadcasting COMMIT for height {height} (leader: {leader_id})")
        message = Message.create_commit(
            self.node_id,
            height,
            block_hash,
            leader_id,
            b''  # TODO: Add proper signature
        )
        self._broadcast(message)
        self.logger.debug(f" COMMIT for height {height} broadcasted")
    
    def send_headers(self, headers: List[Dict], peer_address: str):
        """Send block headers to a peer."""
        message = Message.create_headers(
            self.node_id,
            headers
        )
        if peer_address in self.connections:
            try:
                sock = self.connections[peer_address]
                self._send_message(sock, message)
            except Exception as e:
                self.logger.warning(f"Failed to send headers to {peer_address}: {e}")
        else:
            self.logger.warning(f"Cannot send headers, no connection to {peer_address}")
    
    def send_block(self, block: Block, peer_address: str):
        """Send a block to a peer."""
        message = Message.create_block(
            self.node_id,
            block
        )
        if peer_address in self.connections:
            try:
                sock = self.connections[peer_address]
                self._send_message(sock, message)
            except Exception as e:
                self.logger.warning(f"Failed to send block to {peer_address}: {e}")
        else:
            self.logger.warning(f"Cannot send block, no connection to {peer_address}")
    
    def broadcast_heartbeat(self, height: int, last_block_hash: bytes,
                            current_view: int = 0, failed_validators: list = None):
        """Broadcast heartbeat with current state and view info."""
        message = Message.create_heartbeat(
            self.node_id,
            height,
            last_block_hash,
            current_view,
            failed_validators or []
        )
        self._broadcast(message)
    
    def broadcast_viewchange(self, new_view: int, height: int, 
                             failed_leader: str, reason: str):
        """Broadcast view change message."""
        self.logger.info(f"Broadcasting VIEWCHANGE: new_view={new_view}, height={height}, failed_leader={failed_leader}, reason={reason}")
        message = Message.create_viewchange(
            self.node_id,
            new_view,
            height,
            failed_leader,
            reason
        )
        self._broadcast(message)
    
    def broadcast_sync_request(self, my_height: int, my_latest_hash: str):
        """Request sync from all peers."""
        self.logger.info(f"Broadcasting SYNC_REQUEST: height={my_height}")
        message = Message.create_sync_request(
            self.node_id,
            my_height,
            my_latest_hash
        )
        self._broadcast(message)
    
    def send_sync_response(self, peer_address: str, height: int, 
                           latest_hash: str, blocks: list,
                           current_view: int = 0, failed_validators: list = None):
        """Send sync response to a specific peer with view and state info."""
        message = Message.create_sync_response(
            self.node_id,
            height,
            latest_hash,
            blocks,
            current_view,
            failed_validators or []
        )
        if peer_address in self.connections:
            try:
                sock = self.connections[peer_address]
                self._send_message(sock, message)
                self.logger.debug(f"Sent SYNC_RESPONSE to {peer_address}")
            except Exception as e:
                self.logger.warning(f"Failed to send sync response to {peer_address}: {e}")
        else:
            self.logger.warning(f"Cannot send sync response, no connection to {peer_address}")
    
    def broadcast_mempool_sync(self, transactions: list):
        """Broadcast mempool transactions for sync."""
        message = Message.create_mempool_sync(
            self.node_id,
            transactions
        )
        self._broadcast(message)
    
    def get_connection_count(self) -> int:
        """Get number of active connections."""
        with self.connection_lock:
            return len(self.connections)

