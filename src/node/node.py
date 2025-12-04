"""Main node implementation that coordinates all components."""

import threading
import time
import socket
from typing import Optional, List, Dict
from src.common.config import Config
from src.common.logger import setup_logger
from src.chain.blockchain import Blockchain
from src.chain.block import Transaction, Block
from src.mempool.mempool import Mempool
from src.consensus.poa import RoundRobinPoA
from src.p2p.network import NetworkManager


class Node:
    """Main node that coordinates blockchain, consensus, and networking."""
    
    def __init__(self, config: Config, disable_console_logging: bool = False, log_level: Optional[str] = None):
        """
        Initialize node with configuration.
        
        Args:
            config: Node configuration
            disable_console_logging: If True, disable console output for loggers
            log_level: Override log level (if None, uses config value)
        """
        self.config = config
        # Use provided log_level or fall back to config
        level = log_level or config.get('logging.level', 'INFO')
        self.logger = setup_logger(
            'minichain.node',
            level=level,
            log_file=config.get('logging.file'),
            console=config.get('logging.console', True) and not disable_console_logging
        )
        
        # Track ACKs sent to prevent duplicates
        self.acks_sent: Dict[int, bool] = {}  # height -> whether ACK was sent
        
        # Track COMMIT messages being processed to prevent duplicates
        self.commits_processing: Dict[int, bool] = {}  # height -> whether COMMIT is being processed
        
        # Track COMMIT messages broadcast by leader to prevent duplicates
        self.commits_broadcast: Dict[int, bool] = {}  # height -> whether COMMIT was broadcast
        
        # Initialize components
        self.blockchain = Blockchain(data_dir=config.get_data_dir())
        self.mempool = Mempool()
        
        # Get validator list - CRITICAL: All nodes must have the EXACT same validator list
        # Strategy: Build from peers + self, normalize to ensure consistency
        my_hostname = config.get_hostname()
        my_node_id = config.get_node_id()
        
        # Collect all validator hostnames
        validator_hostnames: List[str] = []
        
        # Add all peer hostnames (these are explicitly configured, so use as-is)
        for peer in config.get_peers():
            peer_hostname = peer.get('hostname', peer.get('node_id', 'unknown'))
            if peer_hostname and peer_hostname != 'unknown':
                validator_hostnames.append(peer_hostname)
        
        # Add our own hostname
        validator_hostnames.append(my_hostname)
        
        # Normalize: If we have a mix of FQDNs and short names, prefer FQDNs
        # Extract short names (part before first dot)
        short_to_full: dict = {}
        for hostname in validator_hostnames:
            short = hostname.split('.')[0]
            if '.' in hostname:
                # It's a FQDN - prefer this over short name
                if short not in short_to_full or '.' not in short_to_full[short]:
                    short_to_full[short] = hostname
        
        # Build normalized list: use FQDN if available, otherwise short name
        normalized_validators = []
        seen_shorts = set()
        for hostname in validator_hostnames:
            short = hostname.split('.')[0]
            if short in short_to_full and short_to_full[short] != hostname:
                # We have a FQDN version, use that instead
                if short_to_full[short] not in normalized_validators:
                    normalized_validators.append(short_to_full[short])
                    seen_shorts.add(short)
            elif short not in seen_shorts:
                # Use as-is (either it's already FQDN or we don't have FQDN)
                normalized_validators.append(hostname)
                seen_shorts.add(short)
        
        # Sort for deterministic ordering - CRITICAL for consistent leader selection
        validator_ids = sorted(normalized_validators)
        
        # Log validator list for debugging
        self.logger.info(f"Validator list (sorted, normalized): {validator_ids}")
        self.logger.info(f"My node ID: {my_node_id}, My hostname: {my_hostname}")
        
        # Determine which identifier to use for consensus - must match one in validator_ids
        consensus_node_id = my_hostname
        
        # Try to find our hostname in the normalized list
        if my_hostname not in validator_ids:
            # Try to match (handle short name vs FQDN)
            my_short = my_hostname.split('.')[0]
            matched = False
            for vid in validator_ids:
                vid_short = vid.split('.')[0]
                if vid == my_hostname or my_short == vid_short:
                    consensus_node_id = vid
                    matched = True
                    self.logger.info(f"Matched '{my_hostname}' to normalized validator '{vid}'")
                    break
            
            if not matched:
                self.logger.error(
                    f"ERROR: Cannot match '{my_hostname}' to any validator in {validator_ids}. "
                    f"Please ensure --node-id matches one of the peer hostnames."
                )
                self.logger.error(f"  Valid options: {', '.join(validator_ids)}")
        
        self.logger.info(f"Using consensus node_id: {consensus_node_id}")
        
        # Use the matched node_id for consensus
        self.consensus = RoundRobinPoA(
            node_id=consensus_node_id,  # Must be in validator_ids
            validator_ids=validator_ids,
            block_interval=config.get('consensus.block_interval', 5),
            proposal_timeout=config.get('consensus.proposal_timeout', 10),
            quorum_size=config.get('consensus.quorum_size', 2)
        )
        
        # Update consensus height from blockchain
        self.consensus.current_height = self.blockchain.get_height()
        
        # Initialize network manager
        self.network = NetworkManager(
            node_id=config.get_node_id(),
            hostname=config.get_hostname(),
            port=config.get_port(),
            peers=config.get_peers(),
            message_handler=self._handle_message,
            logger=self.logger
        )
        
        self.running = False
        self.consensus_thread: Optional[threading.Thread] = None
        
        # Clean up old ACK tracking entries periodically (keep only last 10 heights)
        self._cleanup_old_acks()
    
    def submit_transaction(self, tx: Transaction) -> bool:
        """
        Submit a transaction to the mempool and broadcast it.
        
        Args:
            tx: Transaction to submit
        
        Returns:
            True if transaction was added, False if it already exists
        """
        if self.mempool.add_transaction(tx):
            self.logger.info(f"Transaction {tx.tx_id} added to mempool: {tx.sender} -> {tx.recipient}: {tx.amount}")
            # Broadcast to peers
            self.network.broadcast_transaction(tx)
            return True
        return False
    
    def start(self):
        """Start the node."""
        self.logger.info("Starting node...")
        self.running = True
        
        # Start network manager
        self.network.start()
        
        # Start consensus loop
        self.consensus_thread = threading.Thread(target=self._consensus_loop, daemon=True)
        self.consensus_thread.start()
        
        self.logger.info(f"Node started. Height: {self.blockchain.get_height()}")
        self.logger.info("Node is running. Press Ctrl+C to stop.")
        
        # Keep main thread alive
        try:
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            self.stop()
    
    def stop(self):
        """Stop the node."""
        self.logger.info("Stopping node...")
        self.running = False
        self.network.stop()
        self.logger.info("Node stopped.")
    
    def _cleanup_old_acks(self):
        """Clean up old ACK tracking entries to prevent memory leaks."""
        current_height = self.blockchain.get_height()
        # Keep only ACK tracking for heights within last 10 blocks
        heights_to_remove = [h for h in self.acks_sent.keys() if h < current_height - 10]
        for h in heights_to_remove:
            del self.acks_sent[h]
        
        # Also cleanup COMMIT processing flags
        heights_to_remove_commits = [h for h in self.commits_processing.keys() if h < current_height - 10]
        for h in heights_to_remove_commits:
            del self.commits_processing[h]
        
        # Cleanup COMMIT broadcast tracking
        heights_to_remove_broadcast = [h for h in self.commits_broadcast.keys() if h < current_height - 10]
        for h in heights_to_remove_broadcast:
            del self.commits_broadcast[h]
    
    def _consensus_loop(self):
        """Main consensus loop running in background thread."""
        while self.running:
            try:
                current_height = self.blockchain.get_height()
                next_height = current_height + 1
                
                # Check if we should propose
                if self.consensus.should_propose():
                    self._try_propose_block(next_height)
                
                # Check for timeouts
                self._check_timeouts(next_height)
                
                time.sleep(1)  # Check every second
            except Exception as e:
                self.logger.error(f"Error in consensus loop: {e}", exc_info=True)
                time.sleep(1)
    
    def _try_propose_block(self, height: int):
        """Try to propose a new block if we're the leader."""
        if not self.consensus.is_leader(height):
            return
        
        prev_hash = self.blockchain.get_latest_hash()
        block = self.consensus.create_proposal(
            self.mempool,
            prev_hash,
            max_txs=self.config.get('blockchain.max_block_size', 100)
        )
        
        if block is None:
            self.logger.debug("No transactions to propose")
            return
        
        self.logger.info(f"Proposing block at height {height}")
        self.consensus.pending_proposal = block
        
        # Broadcast PROPOSE message
        self.network.broadcast_propose(block)
    
    def _check_timeouts(self, expected_height: int):
        """Check for consensus timeouts and trigger view change if needed."""
        # This is a simplified version - full implementation would track proposal times
        pass
    
    def _handle_message(self, message, peer_address):
        """Handle incoming messages from network."""
        try:
            msg_type = message.type
            
            if msg_type.value == "TX":
                self._handle_tx(message)
            elif msg_type.value == "PROPOSE":
                self._handle_propose(message)
            elif msg_type.value == "ACK":
                self._handle_ack(message)
            elif msg_type.value == "COMMIT":
                self._handle_commit(message)
            elif msg_type.value == "HEARTBEAT":
                self._handle_heartbeat(message)
            elif msg_type.value == "GETHEADERS":
                self._handle_getheaders(message, peer_address)
            elif msg_type.value == "GETBLOCKS":
                self._handle_getblocks(message, peer_address)
            elif msg_type.value == "HEADERS":
                self._handle_headers(message)
            elif msg_type.value == "BLOCK":
                self._handle_blocks(message)
            else:
                self.logger.debug(f"Unhandled message type: {msg_type.value}")
        
        except Exception as e:
            self.logger.error(f"Error handling message: {e}", exc_info=True)
    
    def _handle_tx(self, message):
        """Handle incoming transaction."""
        from src.chain.block import Transaction
        
        try:
            tx_bytes = bytes.fromhex(message.payload['tx_bytes'])
            tx = Transaction.deserialize(tx_bytes)
            
            if self.mempool.add_transaction(tx):
                self.logger.info(f"Added transaction {tx.tx_id} to mempool")
                # Gossip to other peers
                self.network.broadcast_transaction(tx)
            else:
                self.logger.debug(f"Transaction {tx.tx_id} already in mempool")
        except Exception as e:
            self.logger.error(f"Error processing transaction: {e}")
    
    def _handle_propose(self, message):
        """Handle block proposal."""
        from src.chain.block import Transaction, Block
        
        try:
            payload = message.payload
            height = payload['height']
            prev_hash = bytes.fromhex(payload['prev_hash'])
            tx_list = [bytes.fromhex(tx_hex) for tx_hex in payload['tx_list']]
            proposer_id = payload['proposer_id']
            block_hash = bytes.fromhex(payload['block_hash'])
            timestamp = payload.get('timestamp', time.time())  # Use timestamp from message
            
            # Deserialize transactions
            transactions = [Transaction.deserialize(tx_bytes) for tx_bytes in tx_list]
            
            # Create block with the original timestamp from the proposal
            block = Block(
                height=height,
                prev_hash=prev_hash,
                transactions=transactions,
                timestamp=timestamp,
                proposer_id=proposer_id,
                block_hash=block_hash
            )
            
            # Validate block
            if not self._validate_proposal(block):
                # Get validation details for logging
                expected_height = self.blockchain.get_height() + 1
                expected_prev_hash = self.blockchain.get_latest_hash()
                expected_leader = self.consensus.get_current_leader(height)
                computed_hash = block.compute_hash()
                
                # Log warning with key details
                self.logger.warning(
                    f"Invalid proposal at height {height}: "
                    f"expected_height={expected_height}, got={height}; "
                    f"expected_leader={expected_leader}, got={proposer_id}; "
                    f"prev_hash_match={block.prev_hash == expected_prev_hash}; "
                    f"hash_match={block.block_hash == computed_hash}"
                )
                
                # Log detailed debug information
                self.logger.debug(f"  Expected height: {expected_height}, got: {height}")
                self.logger.debug(f"  Expected prev_hash: {expected_prev_hash.hex()[:32]}..., got: {prev_hash.hex()[:32]}...")
                self.logger.debug(f"  Expected leader: {expected_leader}, got: {proposer_id}")
                self.logger.debug(f"  Computed hash: {computed_hash.hex()[:32]}...")
                self.logger.debug(f"  Block hash: {block.block_hash.hex()[:32]}...")
                self.logger.debug(f"  Block hash matches computed: {block.block_hash == computed_hash}")
                self.logger.debug(f"  Block is_valid(): {block.is_valid()}")
                return
            
            # Store pending proposal
            self.consensus.pending_proposal = block
            
            # Send ACK directly to leader only (prevent duplicate ACKs)
            leader_hostname = proposer_id  # The proposer is the leader
            if height not in self.acks_sent or not self.acks_sent[height]:
                self.acks_sent[height] = True
                self.logger.info(f"ACKing proposal at height {height} to leader {leader_hostname}")
                self.network.send_ack(height, block_hash, self.config.get_hostname(), leader_hostname)
            else:
                self.logger.debug(f"Already ACKed proposal at height {height}, skipping duplicate ACK")
        
        except Exception as e:
            self.logger.error(f"Error handling proposal: {e}", exc_info=True)
    
    def _handle_ack(self, message):
        """Handle ACK message. Only the leader processes ACKs and checks for quorum."""
        try:
            payload = message.payload
            height = payload['height']
            voter_id = payload['voter_id']
            
            # Only process ACKs if we're the leader for this height
            expected_leader = self.consensus.get_current_leader(height)
            my_hostname = self.config.get_hostname()
            
            if expected_leader != my_hostname:
                # We're not the leader, ignore this ACK
                self.logger.debug(f"Received ACK for height {height} but we're not the leader (leader: {expected_leader})")
                return
            
            # We're the leader, process the ACK
            self.consensus.add_ack(height, voter_id)
            self.logger.info(f"Received ACK from {voter_id} for height {height}")
            
            # Check if we have quorum (only leader checks)
            if self.consensus.has_quorum(height):
                # Check if we've already committed this block (prevent duplicate commits)
                current_height = self.blockchain.get_height()
                if current_height >= height:
                    # Block already committed, ignore this ACK
                    self.logger.debug(f"Block {height} already committed (current height: {current_height}), ignoring ACK")
                    return
                
                # Check and set committing flag atomically to prevent race conditions
                # This prevents multiple threads from processing quorum simultaneously
                if self.consensus.is_committing(height):
                    self.logger.debug(f"Block {height} is already being committed, ignoring duplicate ACK")
                    return
                
                # Set committing flag BEFORE processing to prevent race conditions
                self.consensus.set_committing(height, True)
                
                # Double-check height after setting flag (in case another thread already committed)
                current_height = self.blockchain.get_height()
                if current_height >= height:
                    # Another thread already committed, clear flag and return
                    self.consensus.set_committing(height, False)
                    self.logger.debug(f"Block {height} was committed by another thread, ignoring")
                    return
                
                self.logger.info(f"Quorum reached for height {height}, committing block")
                if self.consensus.pending_proposal:
                    # Save block hash before on_block_committed clears pending_proposal
                    block = self.consensus.pending_proposal
                    block_hash = block.block_hash
                    tx_ids = [tx.tx_id for tx in block.transactions]
                    
                    # Commit the block
                    if self.blockchain.add_block(block):
                        # Remove transactions from mempool
                        self.mempool.remove_transactions(tx_ids)
                        
                        # Update consensus state (this clears pending_proposal)
                        self.consensus.on_block_committed(height)
                        
                        # Clear ACK tracking for this height and cleanup old entries
                        if height in self.acks_sent:
                            del self.acks_sent[height]
                        self._cleanup_old_acks()
                        
                        # Broadcast COMMIT - use hostname for consistency
                        # Only broadcast once (check if already broadcast to prevent duplicates)
                        if height not in self.commits_broadcast or not self.commits_broadcast[height]:
                            self.commits_broadcast[height] = True
                            self.network.broadcast_commit(
                                height,
                                block_hash,  # Use saved block_hash
                                self.config.get_hostname()
                            )
                            self.logger.info(f"Block {height} committed and COMMIT broadcast")
                        else:
                            self.logger.debug(f"COMMIT for height {height} already broadcast, skipping duplicate")
                            self.logger.info(f"Block {height} committed")
                    else:
                        # Block validation failed - clear committing flag to allow retry
                        self.consensus.set_committing(height, False)
                        # Log details for debugging
                        current_height = self.blockchain.get_height()
                        expected_height = current_height + 1
                        latest_hash = self.blockchain.get_latest_hash()
                        self.logger.error(
                            f"Failed to add block {height} to chain: "
                            f"current_height={current_height}, expected_height={expected_height}, "
                            f"block_height={block.height}, prev_hash_match={block.prev_hash == latest_hash}"
                        )
                else:
                    # No pending proposal - clear committing flag
                    self.consensus.set_committing(height, False)
                    self.logger.warning(f"Quorum reached for height {height} but no pending proposal")
        
        except Exception as e:
            self.logger.error(f"Error handling ACK: {e}", exc_info=True)
    
    def _handle_commit(self, message):
        """Handle COMMIT message."""
        from src.chain.block import Block
        
        try:
            payload = message.payload
            height = payload['height']
            block_hash = bytes.fromhex(payload['block_hash'])
            
            # Check if block is already committed (prevent duplicate commits)
            current_height = self.blockchain.get_height()
            if current_height >= height:
                # Block already committed, ignore duplicate COMMIT
                self.logger.debug(f"Block {height} already committed (current height: {current_height}), ignoring duplicate COMMIT")
                return
            
            # Check if we're already processing a COMMIT for this height (prevent concurrent processing)
            if self.commits_processing.get(height, False):
                self.logger.debug(f"Already processing COMMIT for height {height}, ignoring duplicate")
                return
            
            # Set flag to indicate we're processing this COMMIT
            self.commits_processing[height] = True
            
            try:
                # Double-check height after setting flag (in case another thread already committed)
                current_height = self.blockchain.get_height()
                if current_height >= height:
                    # Block was committed by another thread, clear flag and return
                    self.commits_processing[height] = False
                    self.logger.debug(f"Block {height} was committed by another thread, ignoring COMMIT")
                    return
                
                # If we have the pending proposal, commit it
                if (self.consensus.pending_proposal and 
                    self.consensus.pending_proposal.height == height and
                    self.consensus.pending_proposal.block_hash == block_hash):
                    
                    if self.blockchain.add_block(self.consensus.pending_proposal):
                        # Remove transactions from mempool
                        tx_ids = [tx.tx_id for tx in self.consensus.pending_proposal.transactions]
                        self.mempool.remove_transactions(tx_ids)
                        
                        # Update consensus state
                        self.consensus.on_block_committed(height)
                        # Clear ACK tracking for this height
                        if height in self.acks_sent:
                            del self.acks_sent[height]
                        # Clear COMMIT processing flag
                        if height in self.commits_processing:
                            del self.commits_processing[height]
                        self.logger.info(f"Block {height} committed via COMMIT message")
                    else:
                        # Block validation failed - clear flag to allow retry
                        self.commits_processing[height] = False
                        self.logger.error(f"Failed to commit block {height}")
                else:
                    # No matching pending proposal - might have been committed already or proposal was cleared
                    self.commits_processing[height] = False
                    self.logger.debug(f"Received COMMIT for height {height} but no matching pending proposal")
            except Exception as e:
                # Clear flag on error
                if height in self.commits_processing:
                    self.commits_processing[height] = False
                raise
        
        except Exception as e:
            self.logger.error(f"Error handling COMMIT: {e}", exc_info=True)
    
    def _handle_heartbeat(self, message):
        """Handle heartbeat message."""
        # For now, just log - could be used for peer health tracking
        pass
    
    def _handle_getheaders(self, message, peer_address):
        """Handle GETHEADERS request."""
        try:
            payload = message.payload
            from_height = payload['from_height']
            to_height = payload.get('to_height', self.blockchain.get_height())
            
            headers = self.blockchain.get_block_headers(from_height, to_height)
            self.network.send_headers(headers, peer_address)
            
            self.logger.info(f"Sent headers {from_height} to {to_height} to {peer_address}")
        
        except Exception as e:
            self.logger.error(f"Error handling GETHEADERS: {e}", exc_info=True)
    
    def _handle_getblocks(self, message, peer_address):
        """Handle GETBLOCKS request."""
        try:
            payload = message.payload
            from_height = payload['from_height']
            to_height = payload.get('to_height', self.blockchain.get_height())
            
            blocks = self.blockchain.get_blocks(from_height, to_height)
            for block in blocks:
                self.network.send_block(block, peer_address)
                
            self.logger.info(f"Sent blocks {from_height} to {to_height} to {peer_address}")
        
        except Exception as e:
            self.logger.error(f"Error handling GETBLOCKS: {e}", exc_info=True)
            
    def _handle_headers(self, message):
        """Handle HEADERS message."""
        try:
            payload = message.payload
            headers = payload['headers']
            
            for header_dict in headers:
                self.logger.info(f"Received {header_dict.keys()} from HEADERS message")
        
        except Exception as e:
            self.logger.error(f"Error handling GETHEADERS: {e}", exc_info=True)
    
    def _handle_blocks(self, message):
        """Handle BLOCKS message."""
        try:
            payload = message.payload
            blocks = payload['block']
            
            for block_dict in blocks:
                block = Block.from_dict(block_dict)
                if self.blockchain.add_block(block):
                    self.logger.info(f"Added block {block.height} from BLOCKS message")
                else:
                    self.logger.warning(f"Failed to add block {block.height} from BLOCKS message")
        
        except Exception as e:
            self.logger.error(f"Error handling GETBLOCKS: {e}", exc_info=True)
    
    def _validate_proposal(self, block: 'Block') -> bool:
        """Validate a block proposal."""
        # Check height
        expected_height = self.blockchain.get_height() + 1
        if block.height != expected_height:
            self.logger.debug(f"Height mismatch: expected {expected_height}, got {block.height}")
            return False
        
        # Check previous hash
        expected_prev_hash = self.blockchain.get_latest_hash()
        if block.prev_hash != expected_prev_hash:
            self.logger.debug(f"Prev hash mismatch: expected {expected_prev_hash.hex()[:16]}..., got {block.prev_hash.hex()[:16]}...")
            return False
        
        # Check proposer is correct leader
        expected_leader = self.consensus.get_current_leader(block.height)
        if block.proposer_id != expected_leader:
            self.logger.debug(f"Leader mismatch: expected {expected_leader}, got {block.proposer_id}")
            return False
        
        # Check block hash matches computed hash
        computed_hash = block.compute_hash()
        if block.block_hash != computed_hash:
            self.logger.debug(f"Block hash mismatch: expected {computed_hash.hex()[:16]}..., got {block.block_hash.hex()[:16]}...")
            return False
        
        # Check block structure
        if not block.is_valid():
            self.logger.debug("Block structure validation failed")
            return False
        
        return True

