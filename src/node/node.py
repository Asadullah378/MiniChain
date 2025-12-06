"""Main node implementation that coordinates all components."""

import threading
import time
import socket
import os
import signal
from typing import Optional, List, Dict, Set
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
        
        # Track ACKs sent to prevent duplicates - now tracked by (height, leader) pair
        self.acks_sent: Dict[str, bool] = {}  # "height:leader" -> whether ACK was sent
        
        # Track COMMIT messages being processed to prevent duplicates
        self.commits_processing: Dict[int, bool] = {}  # height -> whether COMMIT is being processed
        
        # Track COMMIT messages broadcast by leader to prevent duplicates
        self.commits_broadcast: Dict[int, bool] = {}  # height -> whether COMMIT was broadcast
        
        # Track active validators (for view change)
        self.active_validators: Set[str] = set()
        self.failed_validators: Set[str] = set()
        
        # View change tracking
        self.current_view = 0  # View number for leader election
        self.view_change_votes: Dict[int, Set[str]] = {}  # view -> set of voters
        self.view_change_lock = threading.Lock()
        self.view_change_in_progress = False  # Prevent multiple simultaneous view changes
        self.last_view_change_time = 0  # Cooldown for view changes
        self.view_change_cooldown = 15  # Minimum seconds between view changes
        self.view_change_initiated_for: Set[str] = set()  # Track which leaders we've initiated view change for
        
        # Sync and recovery state
        self.syncing = False
        self.sync_lock = threading.Lock()
        self.is_recovering = True  # True until initial sync is complete
        self.recovery_start_time = time.time()
        self.recovery_grace_period = 30  # Seconds to wait before running health checks
        self.initial_sync_complete = False
        
        # Shutdown flag
        self.shutdown_requested = False
        
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
        # Note: quorum is now dynamic (all active validators), not from config
        self.consensus = RoundRobinPoA(
            node_id=consensus_node_id,  # Must be in validator_ids
            validator_ids=validator_ids,
            block_interval=config.get('consensus.block_interval', 5),
            proposal_timeout=config.get('consensus.proposal_timeout', 10)
        )
        
        # Update consensus height from blockchain
        self.consensus.current_height = self.blockchain.get_height()
        
        # Initialize network manager with failure/recovery callbacks
        self.network = NetworkManager(
            node_id=config.get_node_id(),
            hostname=config.get_hostname(),
            port=config.get_port(),
            peers=config.get_peers(),
            message_handler=self._handle_message,
            logger=self.logger,
            failure_callback=self._on_peer_failure,
            recovery_callback=self._on_peer_recovery,
            is_recovering_check=self._is_still_recovering  # New: check if we should skip failure detection
        )
        
        self.running = False
        self.consensus_thread: Optional[threading.Thread] = None
        self.heartbeat_thread: Optional[threading.Thread] = None
        
        # Initialize active validators with all validators
        self.active_validators = set(validator_ids)
        
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
        self.logger.info(f" Received transaction submission: {tx.sender} -> {tx.recipient}, amount: {tx.amount} MC, tx_id: {tx.tx_id[:16]}...")
        
        if self.mempool.add_transaction(tx):
            self.logger.info(f" Transaction {tx.tx_id[:16]}... added to mempool (mempool size: {self.mempool.size()})")
            # Broadcast to peers
            self.logger.debug(f" Broadcasting transaction {tx.tx_id[:16]}... to peers")
            self.network.broadcast_transaction(tx)
            self.logger.info(f" Transaction {tx.tx_id[:16]}... broadcasted to network")
            return True
        else:
            self.logger.warning(f" Transaction {tx.tx_id[:16]}... already exists in mempool, ignoring duplicate")
            return False
    
    def start(self):
        """Start the node."""
        self.logger.info("Starting MiniChain node...")
        self.logger.info(f"Node ID: {self.config.get_node_id()}, Hostname: {self.config.get_hostname()}")
        self.logger.info(f"Initial blockchain height: {self.blockchain.get_height()}")
        self.logger.info(f"Initial mempool size: {self.mempool.size()}")
        self.logger.info(f"Validators: {self.consensus.validator_ids}")
        self.logger.info(f"Quorum: dynamic (all active validators), Block interval: {self.consensus.block_interval}s")
        
        self.running = True
        
        # Start network manager
        self.logger.info("Starting network manager...")
        self.network.start()
        self.logger.info("Network manager started")
        
        # Start consensus loop
        self.logger.info("Starting consensus loop...")
        self.consensus_thread = threading.Thread(target=self._consensus_loop, daemon=True)
        self.consensus_thread.start()
        self.logger.info("Consensus loop started")
        
        # Start heartbeat sender
        self.logger.info("Starting heartbeat sender...")
        self.heartbeat_thread = threading.Thread(target=self._heartbeat_loop, daemon=True)
        self.heartbeat_thread.start()
        self.logger.info("Heartbeat sender started")
        
        self.logger.info(f"Node started successfully. Current height: {self.blockchain.get_height()}")
        self.logger.info("Node is running. Press Ctrl+C to stop.")
        
        # Start recovery/sync process
        self.logger.info("Starting initial state sync with peers...")
        self.logger.info(f"My initial state: height={self.blockchain.get_height()}, view={self.current_view}")
        self.logger.info(f"Recovery mode: health checks disabled for {self.recovery_grace_period}s")
        
        # Start sync process in background
        def recovery_sync():
            time.sleep(3)  # Wait for connections to be established
            if self.running:
                self.logger.info(f"[RECOVERY] Sending sync request (height={self.blockchain.get_height()}, view={self.current_view})")
                self._request_sync()
            
            time.sleep(5)  # Wait for responses
            if self.running:
                self.logger.info(f"[RECOVERY] Current state: height={self.blockchain.get_height()}, view={self.current_view}")
                self.logger.info(f"[RECOVERY] Sending follow-up sync request...")
                self._request_sync()
            
            time.sleep(5)  # Wait for more responses
            if self.running:
                self.logger.info(f"[RECOVERY] Final state before completing: height={self.blockchain.get_height()}, view={self.current_view}")
                self.logger.info(f"[RECOVERY] Active validators: {list(self.active_validators)}")
                self.logger.info(f"[RECOVERY] Effective leader for next height: {self.get_effective_leader(self.blockchain.get_height() + 1)}")
                self._complete_recovery()
        
        threading.Thread(target=recovery_sync, daemon=True).start()
        
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
        self.logger.info("Stopping network manager...")
        self.network.stop()
        self.logger.info(f"Final state - Height: {self.blockchain.get_height()}, Mempool: {self.mempool.size()} transactions")
        self.logger.info("Node stopped gracefully.")
    
    def _cleanup_old_acks(self):
        """Clean up old ACK tracking entries to prevent memory leaks."""
        current_height = self.blockchain.get_height()
        # Keep only ACK tracking for heights within last 10 blocks
        # Key format is "height:leader"
        keys_to_remove = []
        for key in self.acks_sent.keys():
            try:
                height = int(key.split(':')[0])
                if height < current_height - 10:
                    keys_to_remove.append(key)
            except (ValueError, IndexError):
                keys_to_remove.append(key)  # Remove malformed keys
        for key in keys_to_remove:
            del self.acks_sent[key]
        
        # Also cleanup COMMIT processing flags
        heights_to_remove_commits = [h for h in self.commits_processing.keys() if h < current_height - 10]
        for h in heights_to_remove_commits:
            del self.commits_processing[h]
        
        # Cleanup COMMIT broadcast tracking
        heights_to_remove_broadcast = [h for h in self.commits_broadcast.keys() if h < current_height - 10]
        for h in heights_to_remove_broadcast:
            del self.commits_broadcast[h]
    
    def _heartbeat_loop(self):
        """Periodically broadcast heartbeat to peers with view and state info."""
        while self.running:
            try:
                height = self.blockchain.get_height()
                last_hash = self.blockchain.get_latest_hash()
                # Include view and failed validators for state sync
                self.network.broadcast_heartbeat(
                    height, 
                    last_hash,
                    self.current_view,
                    list(self.failed_validators)
                )
                time.sleep(3)  # Heartbeat every 3 seconds
            except Exception as e:
                if self.running:
                    self.logger.error(f"Error in heartbeat loop: {e}")
                time.sleep(1)
    
    def _on_peer_failure(self, peer_hostname: str):
        """Handle peer failure detection."""
        # Skip if we're still recovering - we don't know the real state yet
        if self.is_recovering:
            self.logger.debug(f"Ignoring peer failure for {peer_hostname} - still in recovery mode")
            return
        
        # Normalize hostname for matching
        short_hostname = peer_hostname.split('.')[0]
        matched_validator = None
        
        for validator in list(self.active_validators):
            if validator == peer_hostname or validator.split('.')[0] == short_hostname:
                matched_validator = validator
                break
        
        if not matched_validator:
            # Already removed or not a validator
            return
        
        # Check if already marked as failed
        if matched_validator in self.failed_validators:
            return
        
        self.logger.warning(f"Peer failure detected: {matched_validator}")
        self.active_validators.discard(matched_validator)
        self.failed_validators.add(matched_validator)
        self.logger.warning(f"Removed {matched_validator} from active validators")
        self.logger.info(f"Active validators: {list(self.active_validators)}")
        
        # Check if the failed peer is the effective leader (accounts for view changes)
        next_height = self.blockchain.get_height() + 1
        effective_leader = self.get_effective_leader(next_height)
        
        leader_short = effective_leader.split('.')[0]
        is_leader_failed = (matched_validator == effective_leader or 
                           short_hostname == leader_short)
        
        if is_leader_failed:
            # Clear ACK tracking for current height + failed leader since leader failed
            # Key format is "height:leader"
            ack_key = f"{next_height}:{matched_validator}"
            if ack_key in self.acks_sent:
                del self.acks_sent[ack_key]
                self.logger.debug(f"Cleared ACK tracking for {ack_key} due to leader failure")
            
            # Clear pending proposal from failed leader
            if self.consensus.pending_proposal and self.consensus.pending_proposal.height == next_height:
                self.consensus.pending_proposal = None
                self.logger.debug(f"Cleared pending proposal from failed leader")
            
            # Only initiate view change if we haven't already done so for this leader
            if matched_validator not in self.view_change_initiated_for:
                self.logger.warning(f"Failed peer {matched_validator} is the current leader! Initiating view change...")
                self._initiate_view_change(next_height, matched_validator, "leader_failure")
            else:
                self.logger.debug(f"View change already initiated for {matched_validator}, skipping")
    
    def _on_peer_recovery(self, peer_hostname: str):
        """Handle peer recovery detection."""
        self.logger.info(f"Peer recovery detected via network: {peer_hostname}")
        
        # Normalize hostname for matching
        short_hostname = peer_hostname.split('.')[0]
        matched_validator = None
        
        for validator in self.consensus.validator_ids:
            if validator == peer_hostname or validator.split('.')[0] == short_hostname:
                matched_validator = validator
                break
        
        if matched_validator:
            # Only process if this is actually a recovery (was previously failed)
            if matched_validator in self.failed_validators:
                # Add back to active validators - they're communicating again
                self.failed_validators.discard(matched_validator)
                self.active_validators.add(matched_validator)
                
                # Clear the view change flag so we can handle future failures
                self.view_change_initiated_for.discard(matched_validator)
                
                self.logger.info(f"Peer {matched_validator} recovered and added back to active validators")
                self.logger.info(f"Active validators: {list(self.active_validators)}")
    
    def _initiate_view_change(self, height: int, failed_leader: str, reason: str):
        """Initiate a view change due to leader failure."""
        with self.view_change_lock:
            # Check cooldown
            current_time = time.time()
            if current_time - self.last_view_change_time < self.view_change_cooldown:
                self.logger.debug(f"View change cooldown active, skipping (wait {self.view_change_cooldown - (current_time - self.last_view_change_time):.1f}s)")
                return
            
            # Check if already in progress
            if self.view_change_in_progress:
                self.logger.debug("View change already in progress, skipping")
                return
            
            # Mark this leader as having view change initiated
            self.view_change_initiated_for.add(failed_leader)
            self.view_change_in_progress = True
            
            new_view = self.current_view + 1
            
            # Broadcast view change
            self.network.broadcast_viewchange(new_view, height, failed_leader, reason)
            
            # Vote for the view change ourselves
            if new_view not in self.view_change_votes:
                self.view_change_votes[new_view] = set()
            self.view_change_votes[new_view].add(self.config.get_hostname())
            
            self.logger.info(f"Initiated view change to view {new_view} for height {height}")
            
            # Reset in_progress flag after a timeout (in case view change doesn't complete)
            def reset_view_change_flag():
                time.sleep(self.view_change_cooldown)
                with self.view_change_lock:
                    self.view_change_in_progress = False
            threading.Thread(target=reset_view_change_flag, daemon=True).start()
    
    def _request_sync(self):
        """Request sync from peers."""
        with self.sync_lock:
            if self.syncing:
                return
            self.syncing = True
        
        try:
            height = self.blockchain.get_height()
            latest_hash = self.blockchain.get_latest_hash().hex()
            self.logger.info(f"Requesting sync from peers (my height: {height})")
            self.network.broadcast_sync_request(height, latest_hash)
        finally:
            # Reset sync flag after a delay
            def reset_sync():
                time.sleep(5)
                with self.sync_lock:
                    self.syncing = False
            threading.Thread(target=reset_sync, daemon=True).start()
    
    def _is_still_recovering(self) -> bool:
        """Check if this node is still in recovery mode (should skip health checks)."""
        if not self.is_recovering:
            return False
        
        # Check if grace period has passed
        elapsed = time.time() - self.recovery_start_time
        if elapsed > self.recovery_grace_period:
            if self.is_recovering:
                self.logger.info(f"Recovery grace period ({self.recovery_grace_period}s) elapsed - enabling health checks")
                self.is_recovering = False
            return False
        
        return True
    
    def _complete_recovery(self):
        """Mark recovery as complete and enable normal operations."""
        if self.is_recovering:
            self.is_recovering = False
            self.initial_sync_complete = True
            self.logger.info("Initial sync complete - node is now fully operational")
            self.logger.info(f"State: height={self.blockchain.get_height()}, view={self.current_view}, active_validators={list(self.active_validators)}")
    
    def get_active_validators(self) -> List[str]:
        """Get list of currently active validators."""
        return sorted(list(self.active_validators))
    
    def get_effective_leader(self, height: int) -> str:
        """Get the effective leader for a height, skipping failed validators."""
        active = self.get_active_validators()
        if not active:
            # Fallback to all validators if none active
            active = self.consensus.validator_ids
        
        # Round-robin among active validators
        # Adjust index based on view changes
        adjusted_height = height + self.current_view
        return active[adjusted_height % len(active)]
    
    def request_shutdown(self):
        """Request graceful shutdown of the node."""
        self.logger.info("Shutdown requested...")
        self.shutdown_requested = True
        self.stop()
        
        # Give time for cleanup
        time.sleep(1)
        
        # Force exit
        self.logger.info("Forcing process exit...")
        os._exit(0)
    
    def _consensus_loop(self):
        """Main consensus loop running in background thread."""
        self.logger.info("Consensus loop started")
        while self.running:
            try:
                current_height = self.blockchain.get_height()
                next_height = current_height + 1
                
                # Use effective leader (accounts for view changes and failed validators)
                effective_leader = self.get_effective_leader(next_height)
                my_hostname = self.config.get_hostname()
                my_short = my_hostname.split('.')[0]
                leader_short = effective_leader.split('.')[0]
                
                is_effective_leader = (my_hostname == effective_leader or my_short == leader_short)
                
                if is_effective_leader:
                    self.logger.debug(f"I am the effective leader for height {next_height}")
                else:
                    self.logger.debug(f"Effective leader for height {next_height}: {effective_leader}")
                
                # Check if we should propose (using effective leader logic)
                # Only propose if:
                # 1. We are the effective leader
                # 2. Block interval has elapsed
                # 3. No pending proposal waiting for ACKs
                elapsed = time.time() - self.consensus.last_block_time
                has_pending = (self.consensus.pending_proposal is not None and 
                              self.consensus.pending_proposal.height == next_height)
                should_propose = is_effective_leader and elapsed >= self.consensus.block_interval and not has_pending
                
                if should_propose:
                    self.logger.info(f"Block interval elapsed, I am the effective leader - proposing for height {next_height}")
                    self._try_propose_block(next_height)
                elif is_effective_leader and has_pending:
                    self.logger.debug(f"Already have pending proposal for height {next_height}, waiting for ACKs")
                
                # Check for timeouts
                self._check_timeouts(next_height)
                
                time.sleep(1)  # Check every second
            except Exception as e:
                self.logger.error(f"Critical error in consensus loop: {e}", exc_info=True)
                time.sleep(1)
    
    def _try_propose_block(self, height: int):
        """Try to propose a new block if we're the effective leader."""
        # Use effective leader (accounts for view changes and failed validators)
        effective_leader = self.get_effective_leader(height)
        my_hostname = self.config.get_hostname()
        my_short = my_hostname.split('.')[0]
        leader_short = effective_leader.split('.')[0]
        
        is_effective_leader = (my_hostname == effective_leader or my_short == leader_short)
        
        if not is_effective_leader:
            self.logger.debug(f"Not effective leader for height {height}, skipping proposal")
            return
        
        # Check if we already have a pending proposal for this height
        if self.consensus.pending_proposal is not None and self.consensus.pending_proposal.height == height:
            self.logger.debug(f"Already have pending proposal for height {height}, waiting for ACKs")
            return
        
        self.logger.info(f"Creating block proposal for height {height} (I am effective leader)...")
        prev_hash = self.blockchain.get_latest_hash()
        self.logger.debug(f"Previous block hash: {prev_hash.hex()[:16]}...")
        self.logger.debug(f"Mempool has {self.mempool.size()} transactions available")
        
        # Get transactions from mempool
        txs = self.mempool.get_transactions(self.config.get('blockchain.max_block_size', 100))
        if not txs:
            self.logger.info(f"No transactions in mempool to propose for height {height}")
            return
        
        # Create block with our hostname as proposer
        block = Block(
            height=height,
            prev_hash=prev_hash,
            transactions=txs,
            timestamp=time.time(),
            proposer_id=my_hostname  # Use our hostname as proposer
        )
        
        tx_count = len(block.transactions)
        self.logger.info(f"Created block proposal for height {height}: {tx_count} transaction(s), hash: {block.block_hash.hex()[:16]}...")
        self.logger.debug(f"   Block details: proposer={block.proposer_id}, timestamp={block.timestamp}, prev_hash={block.prev_hash.hex()[:16]}...")
        
        self.consensus.pending_proposal = block
        
        # Broadcast PROPOSE message
        self.logger.info(f"Broadcasting PROPOSE message for height {height} to all peers...")
        self.network.broadcast_propose(block)
        self.logger.info(f"PROPOSE message for height {height} broadcasted successfully")
        
        # Leader self-ACKs (counts towards quorum)
        # Use the matching validator ID from active_validators for consistency
        my_short = my_hostname.split('.')[0]
        my_validator_id = my_hostname
        for validator in self.active_validators:
            if validator == my_hostname or validator.split('.')[0] == my_short:
                my_validator_id = validator
                break
        self.consensus.add_ack(height, my_validator_id)
        self.logger.info(f"Leader self-ACK added for height {height} (validator: {my_validator_id})")
    
    def _check_timeouts(self, expected_height: int):
        """Check for consensus timeouts and trigger view change if needed."""
        # Get the effective leader (accounts for view changes)
        effective_leader = self.get_effective_leader(expected_height)
        elapsed = time.time() - self.consensus.last_block_time
        
        # If block interval + proposal timeout has passed without a block
        timeout_threshold = self.consensus.block_interval + self.consensus.proposal_timeout
        
        if elapsed > timeout_threshold:
            # Check if the effective leader is in our failed validators list
            short_leader = effective_leader.split('.')[0]
            leader_failed = False
            matched_failed = None
            for failed in self.failed_validators:
                if failed == effective_leader or failed.split('.')[0] == short_leader:
                    leader_failed = True
                    matched_failed = failed
                    break
            
            if leader_failed and matched_failed:
                # Only initiate view change if not already initiated for this leader
                if matched_failed not in self.view_change_initiated_for:
                    self.logger.warning(f"Timeout waiting for proposal from failed leader {effective_leader}")
                    self._initiate_view_change(expected_height, matched_failed, "proposal_timeout")
    
    def _handle_message(self, message, peer_address):
        """Handle incoming messages from network."""
        try:
            msg_type = message.type
            sender_id = message.sender_id
            
            self.logger.debug(f"Received {msg_type.value} message from {sender_id} ({peer_address})")
            
            # Check if sender is a failed validator that's now back online
            # (Receiving any message means they're alive and functioning)
            # But only do this if we're NOT recovering ourselves
            if not self.is_recovering:
                sender_short = sender_id.split('.')[0]
                for validator in list(self.failed_validators):
                    if validator == sender_id or validator.split('.')[0] == sender_short:
                        self.logger.info(f"Received {msg_type.value} from previously-failed validator {validator} - re-activating")
                        self.failed_validators.discard(validator)
                        self.active_validators.add(validator)
                        self.network.record_heartbeat(sender_id)
                        self.logger.info(f"Re-activated {validator}, active validators: {list(self.active_validators)}")
                        break
            
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
            elif msg_type.value == "VIEWCHANGE":
                self._handle_viewchange(message)
            elif msg_type.value == "SYNC_REQUEST":
                self._handle_sync_request(message, peer_address)
            elif msg_type.value == "SYNC_RESPONSE":
                self._handle_sync_response(message)
            elif msg_type.value == "MEMPOOL_SYNC":
                self._handle_mempool_sync(message)
            elif msg_type.value == "GETHEADERS":
                self._handle_getheaders(message, peer_address)
            elif msg_type.value == "GETBLOCKS":
                self._handle_getblocks(message, peer_address)
            elif msg_type.value == "HEADERS":
                self._handle_headers(message)
            elif msg_type.value == "BLOCK":
                self._handle_blocks(message)
            else:
                self.logger.warning(f"Unhandled message type: {msg_type.value} from {sender_id}")
        
        except Exception as e:
            self.logger.error(f"Error handling {msg_type.value} message from {peer_address}: {e}", exc_info=True)
    
    def _handle_tx(self, message):
        """Handle incoming transaction."""
        from src.chain.block import Transaction
        
        try:
            sender_id = message.sender_id
            self.logger.debug(f"Processing TX message from {sender_id}")
            
            tx_bytes = bytes.fromhex(message.payload['tx_bytes'])
            tx = Transaction.deserialize(tx_bytes)
            
            self.logger.debug(f"   Transaction: {tx.sender} -> {tx.recipient}, amount: {tx.amount} MC, tx_id: {tx.tx_id[:16]}...")
            
            if self.mempool.add_transaction(tx):
                self.logger.info(f"Added transaction {tx.tx_id[:16]}... to mempool (size: {self.mempool.size()})")
                # Gossip to other peers
                self.logger.debug(f"Gossiping transaction {tx.tx_id[:16]}... to other peers")
                self.network.broadcast_transaction(tx)
            else:
                self.logger.debug(f"Transaction {tx.tx_id[:16]}... already in mempool, skipping")
        except Exception as e:
            self.logger.error(f"Error processing transaction from {sender_id}: {e}", exc_info=True)
    
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
            # Track ACKs by (height, leader) so we can send ACK to a new leader after view change
            leader_hostname = proposer_id  # The proposer is the leader
            ack_key = f"{height}:{leader_hostname}"
            
            if ack_key not in self.acks_sent or not self.acks_sent[ack_key]:
                self.acks_sent[ack_key] = True
                self.logger.info(f"Valid proposal received for height {height} from {leader_hostname}, sending ACK")
                self.logger.debug(f"   Block hash: {block.block_hash.hex()[:16]}..., Transactions: {len(block.transactions)}")
                self.network.send_ack(height, block.block_hash, self.config.get_hostname(), leader_hostname)
                self.logger.info(f"ACK for height {height} sent to leader {leader_hostname}")
            else:
                self.logger.debug(f"Already sent ACK for height {height} to {leader_hostname}, skipping duplicate")
        
        except Exception as e:
            self.logger.error(f"Error handling proposal: {e}", exc_info=True)
    
    def _handle_ack(self, message):
        """Handle ACK message. Only the leader processes ACKs and checks for quorum."""
        try:
            payload = message.payload
            height = payload['height']
            voter_id = payload['voter_id']
            block_hash_hex = payload.get('block_hash', 'unknown')
            sender_id = message.sender_id
            
            self.logger.debug(f"Received ACK message from {sender_id} (voter: {voter_id}) for height {height}")
            
            # Only process ACKs if we're the EFFECTIVE leader for this height
            # (accounts for view changes and failed validators)
            effective_leader = self.get_effective_leader(height)
            my_hostname = self.config.get_hostname()
            my_short = my_hostname.split('.')[0]
            leader_short = effective_leader.split('.')[0]
            
            is_effective_leader = (my_hostname == effective_leader or my_short == leader_short)
            
            if not is_effective_leader:
                # We're not the effective leader, ignore this ACK
                self.logger.debug(f"Received ACK for height {height} but we're not the effective leader (leader: {effective_leader}), ignoring")
                return
            
            # We're the effective leader, process the ACK
            # Normalize voter_id to match active validators format
            voter_short = voter_id.split('.')[0]
            normalized_voter = voter_id
            for validator in self.active_validators:
                if validator == voter_id or validator.split('.')[0] == voter_short:
                    normalized_voter = validator
                    break
            
            self.consensus.add_ack(height, normalized_voter)
            acks_received = self.consensus.acks_received.get(height, set())
            acks_count = len(acks_received)
            
            # Dynamic quorum: all active validators must ACK
            # This includes all active peers + ourselves (the leader)
            dynamic_quorum = len(self.active_validators)
            self.logger.info(f"Received ACK from {voter_id} (normalized: {normalized_voter}) for height {height} (total ACKs: {acks_count}/{dynamic_quorum})")
            self.logger.debug(f"ACKs received so far: {list(acks_received)}")
            self.logger.debug(f"Active validators: {list(self.active_validators)}")
            
            # Check if we have quorum (all active validators)
            if acks_count >= dynamic_quorum:
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
                    self.logger.debug(f" Block {height} was committed by another thread, ignoring")
                    return
                
                acks_count = len(self.consensus.acks_received.get(height, set()))
                self.logger.info(f"QUORUM REACHED for height {height}! (ACKs: {acks_count}/{dynamic_quorum})")
                self.logger.info(f" Committing block {height} to blockchain...")
                if self.consensus.pending_proposal:
                    # Save block hash before on_block_committed clears pending_proposal
                    block = self.consensus.pending_proposal
                    block_hash = block.block_hash
                    tx_ids = [tx.tx_id for tx in block.transactions]
                    
                    # Commit the block
                    self.logger.debug(f"   Block contains {len(tx_ids)} transaction(s)")
                    if self.blockchain.add_block(block):
                        self.logger.info(f" Block {height} successfully added to blockchain")
                        
                        # Remove transactions from mempool
                        self.mempool.remove_transactions(tx_ids)
                        self.logger.info(f" Removed {len(tx_ids)} transaction(s) from mempool (remaining: {self.mempool.size()})")
                        
                        # Update consensus state (this clears pending_proposal)
                        self.consensus.on_block_committed(height)
                        self.logger.debug(f" Consensus state updated: current_height={self.consensus.current_height}")
                        
                        # Clear ACK tracking for this height (all leaders) and cleanup old entries
                        # Key format is "height:leader"
                        keys_to_clear = [k for k in self.acks_sent.keys() if k.startswith(f"{height}:")]
                        for key in keys_to_clear:
                            del self.acks_sent[key]
                        self._cleanup_old_acks()
                        
                        # Broadcast COMMIT - use hostname for consistency
                        # Only broadcast once (check if already broadcast to prevent duplicates)
                        if height not in self.commits_broadcast or not self.commits_broadcast[height]:
                            self.commits_broadcast[height] = True
                            self.logger.info(f" Broadcasting COMMIT message for height {height} to all peers...")
                            self.network.broadcast_commit(
                                height,
                                block_hash,  # Use saved block_hash
                                self.config.get_hostname()
                            )
                            self.logger.info(f" Block {height} committed and COMMIT broadcast successfully")
                            self.logger.info(f" New blockchain height: {self.blockchain.get_height()}")
                        else:
                            self.logger.debug(f" COMMIT for height {height} already broadcast, skipping duplicate")
                            self.logger.info(f" Block {height} committed (COMMIT was already broadcast)")
                    else:
                        # Block validation failed - clear committing flag to allow retry
                        self.consensus.set_committing(height, False)
                        # Log details for debugging
                        current_height = self.blockchain.get_height()
                        expected_height = current_height + 1
                        latest_hash = self.blockchain.get_latest_hash()
                        self.logger.error(
                            f" CRITICAL: Failed to add block {height} to chain after quorum reached! "
                            f"current_height={current_height}, expected_height={expected_height}, "
                            f"block_height={block.height}, prev_hash_match={block.prev_hash == latest_hash}"
                        )
                        self.logger.error(f"   This should not happen - block validation failed after quorum")
                else:
                    # No pending proposal - clear committing flag
                    self.consensus.set_committing(height, False)
                    self.logger.warning(f" Quorum reached for height {height} but no pending proposal available")
                    self.logger.warning(f"   This may indicate a state inconsistency")
            else:
                acks_count = len(self.consensus.acks_received.get(height, set()))
                self.logger.debug(f"Quorum not yet reached for height {height} (ACKs: {acks_count}/{dynamic_quorum})")
        
        except Exception as e:
            self.logger.error(f" Error handling ACK: {e}", exc_info=True)
    
    def _handle_commit(self, message):
        """Handle COMMIT message."""
        from src.chain.block import Block
        
        try:
            payload = message.payload
            height = payload['height']
            block_hash = bytes.fromhex(payload['block_hash'])
            leader_id = payload.get('leader_id', 'unknown')
            sender_id = message.sender_id
            
            self.logger.info(f" Received COMMIT message from {sender_id} for height {height} (leader: {leader_id})")
            self.logger.debug(f"   Block hash: {block_hash.hex()[:16]}...")
            
            # Check if block is already committed (prevent duplicate commits)
            current_height = self.blockchain.get_height()
            if current_height >= height:
                # Block already committed, ignore duplicate COMMIT
                self.logger.debug(f" Block {height} already committed (current height: {current_height}), ignoring duplicate COMMIT")
                return
            
            # Check if we're already processing a COMMIT for this height (prevent concurrent processing)
            if self.commits_processing.get(height, False):
                self.logger.debug(f" Already processing COMMIT for height {height}, ignoring duplicate")
                return
            
            # Set flag to indicate we're processing this COMMIT
            self.commits_processing[height] = True
            self.logger.debug(f" Set processing flag for COMMIT at height {height}")
            
            try:
                # Double-check height after setting flag (in case another thread already committed)
                current_height = self.blockchain.get_height()
                if current_height >= height:
                    # Block was committed by another thread, clear flag and return
                    self.commits_processing[height] = False
                    self.logger.debug(f" Block {height} was committed by another thread, ignoring COMMIT")
                    return
                
                # If we have the pending proposal, commit it
                if (self.consensus.pending_proposal and 
                    self.consensus.pending_proposal.height == height and
                    self.consensus.pending_proposal.block_hash == block_hash):
                    
                    self.logger.info(f" Committing block {height} via COMMIT message...")
                    self.logger.debug(f"   Pending proposal matches COMMIT message")
                    
                    if self.blockchain.add_block(self.consensus.pending_proposal):
                        # Remove transactions from mempool
                        tx_ids = [tx.tx_id for tx in self.consensus.pending_proposal.transactions]
                        self.mempool.remove_transactions(tx_ids)
                        self.logger.info(f" Block {height} successfully committed via COMMIT message")
                        self.logger.info(f" Removed {len(tx_ids)} transaction(s) from mempool (remaining: {self.mempool.size()})")
                        
                        # Update consensus state
                        self.consensus.on_block_committed(height)
                        self.logger.debug(f" Consensus state updated: current_height={self.consensus.current_height}")
                        
                        # Clear ACK tracking for this height (all leaders)
                        # Key format is "height:leader"
                        keys_to_clear = [k for k in self.acks_sent.keys() if k.startswith(f"{height}:")]
                        for key in keys_to_clear:
                            del self.acks_sent[key]
                        # Clear COMMIT processing flag
                        if height in self.commits_processing:
                            del self.commits_processing[height]
                        self.logger.info(f" New blockchain height: {self.blockchain.get_height()}")
                    else:
                        # Block validation failed - clear flag to allow retry
                        self.commits_processing[height] = False
                        self.logger.error(f" Failed to commit block {height} - validation failed")
                        self.logger.error(f"   This may indicate a state mismatch")
                else:
                    # No matching pending proposal - might have been committed already or proposal was cleared
                    self.commits_processing[height] = False
                    if self.consensus.pending_proposal:
                        self.logger.warning(f" Received COMMIT for height {height} but pending proposal doesn't match")
                        self.logger.warning(f"   Expected hash: {block_hash.hex()[:16]}..., got: {self.consensus.pending_proposal.block_hash.hex()[:16]}...")
                    else:
                        self.logger.debug(f" Received COMMIT for height {height} but no pending proposal available")
            except Exception as e:
                # Clear flag on error
                if height in self.commits_processing:
                    self.commits_processing[height] = False
                raise
        
        except Exception as e:
            self.logger.error(f"Error handling COMMIT: {e}", exc_info=True)
    
    def _handle_heartbeat(self, message):
        """Handle heartbeat message with view and state sync."""
        sender_id = message.sender_id
        payload = message.payload
        peer_height = payload.get('height', 0)
        peer_view = payload.get('current_view', 0)
        peer_failed_validators = payload.get('failed_validators', [])
        
        # Record heartbeat for failure detection
        self.network.record_heartbeat(sender_id)
        
        # Log peer state for debugging
        self.logger.debug(f"Heartbeat from {sender_id}: height={peer_height}, view={peer_view}")
        
        # Get our height for comparison
        my_height = self.blockchain.get_height()
        
        # Check if sender is a failed validator that has now recovered
        # Only do this if we're NOT recovering ourselves
        if not self.is_recovering:
            sender_short = sender_id.split('.')[0]
            
            for validator in list(self.failed_validators):
                if validator == sender_id or validator.split('.')[0] == sender_short:
                    # This peer was failed but is now sending heartbeats
                    # Check if they're caught up on blocks (height is close)
                    height_diff = abs(peer_height - my_height)
                    if height_diff <= 2:  # Allow some tolerance
                        self.failed_validators.discard(validator)
                        self.active_validators.add(validator)
                        self.logger.info(f"Recovered peer {validator} is back online (view={peer_view}, height={peer_height}, my_height={my_height}) - added back to active validators")
                        self.logger.info(f"Active validators: {list(self.active_validators)}")
                    else:
                        self.logger.debug(f"Peer {validator} is recovering but still syncing (their height={peer_height}, my height={my_height})")
                    break
        
        # Sync view if peer has higher view (they know about view changes we missed)
        if peer_view > self.current_view:
            self.logger.info(f"Syncing view from {sender_id}: {self.current_view} -> {peer_view}")
            with self.view_change_lock:
                self.current_view = peer_view
                self.last_view_change_time = time.time()
            
            # NOTE: We do NOT sync failed_validators from peers during recovery
            # The recovering node should determine failures through its own health checks
            # This prevents issues where peer's stale info causes incorrect state
            if not self.is_recovering:
                my_hostname = self.config.get_hostname()
                my_short = my_hostname.split('.')[0]
                
                for failed in peer_failed_validators:
                    short_failed = failed.split('.')[0]
                    # Skip if it's our own hostname
                    if failed == my_hostname or short_failed == my_short:
                        continue
                    
                    for validator in self.consensus.validator_ids:
                        if validator == failed or validator.split('.')[0] == short_failed:
                            if validator not in self.failed_validators:
                                self.failed_validators.add(validator)
                                self.active_validators.discard(validator)
                                self.logger.info(f"Synced failed validator: {validator}")
                            break
            else:
                self.logger.debug(f"Skipping failed_validators sync during recovery")
        
        # Check if peer is ahead of us and we should sync blocks
        if peer_height > my_height + 1:
            self.logger.info(f"Peer {sender_id} is ahead (their height: {peer_height}, my height: {my_height})")
            # Request sync if not already syncing
            with self.sync_lock:
                if not self.syncing:
                    self._request_sync()
    
    def _handle_viewchange(self, message):
        """Handle VIEWCHANGE message."""
        payload = message.payload
        new_view = payload.get('new_view', 0)
        height = payload.get('height', 0)
        failed_leader = payload.get('failed_leader', '')
        reason = payload.get('reason', '')
        sender_id = message.sender_id
        
        self.logger.info(f"Received VIEWCHANGE from {sender_id}: new_view={new_view}, height={height}, failed_leader={failed_leader}")
        
        with self.view_change_lock:
            # Only process if this is a newer view
            if new_view <= self.current_view:
                self.logger.debug(f"Ignoring old view change (current view: {self.current_view}, received: {new_view})")
                return
            
            # Only accept view changes that are exactly one view ahead
            if new_view > self.current_view + 1:
                self.logger.debug(f"Ignoring view change too far ahead (current: {self.current_view}, received: {new_view})")
                return
            
            # Record vote
            if new_view not in self.view_change_votes:
                self.view_change_votes[new_view] = set()
            self.view_change_votes[new_view].add(sender_id)
            
            # Verify the failed leader is actually failed or unreachable
            short_failed = failed_leader.split('.')[0]
            leader_is_failed = False
            for validator in self.failed_validators:
                if validator == failed_leader or validator.split('.')[0] == short_failed:
                    leader_is_failed = True
                    break
            
            # Also add our vote if we agree that the leader has failed
            if leader_is_failed:
                self.view_change_votes[new_view].add(self.config.get_hostname())
            
            # Check if we have enough votes for view change
            # Need majority of ALL validators (not just active) to prevent split-brain
            total_validators = len(self.consensus.validator_ids)
            quorum_needed = (total_validators // 2) + 1
            vote_count = len(self.view_change_votes[new_view])
            
            self.logger.info(f"View change votes for view {new_view}: {vote_count}/{quorum_needed} needed")
            
            if vote_count >= quorum_needed:
                self.logger.info(f"VIEW CHANGE COMPLETE: Moving from view {self.current_view} to view {new_view}")
                self.current_view = new_view
                self.last_view_change_time = time.time()
                self.view_change_in_progress = False
                
                # Mark the failed leader as inactive (if not already)
                for validator in list(self.active_validators):
                    if validator == failed_leader or validator.split('.')[0] == short_failed:
                        self.active_validators.discard(validator)
                        self.failed_validators.add(validator)
                        self.view_change_initiated_for.add(validator)
                        break
                
                # Clear all view change votes (we've completed this round)
                self.view_change_votes.clear()
                
                # IMPORTANT: Clear ACK tracking for current and future heights
                # so we can send ACKs to the new leader
                # Key format is "height:leader"
                current_height = self.blockchain.get_height()
                keys_to_clear = []
                for key in self.acks_sent.keys():
                    try:
                        height = int(key.split(':')[0])
                        if height > current_height:
                            keys_to_clear.append(key)
                    except (ValueError, IndexError):
                        pass
                for key in keys_to_clear:
                    del self.acks_sent[key]
                self.logger.debug(f"Cleared ACK tracking keys: {keys_to_clear}")
                
                # Also clear pending proposal from old leader
                self.consensus.pending_proposal = None
                
                # Clear commit tracking for uncommitted heights
                heights_to_clear_commits = [h for h in self.commits_processing.keys() if h > current_height]
                for h in heights_to_clear_commits:
                    del self.commits_processing[h]
                heights_to_clear_broadcast = [h for h in self.commits_broadcast.keys() if h > current_height]
                for h in heights_to_clear_broadcast:
                    del self.commits_broadcast[h]
                
                # Log new leader
                next_height = current_height + 1
                new_leader = self.get_effective_leader(next_height)
                self.logger.info(f"New effective leader for height {next_height}: {new_leader}")
    
    def _handle_sync_request(self, message, peer_address: str):
        """Handle SYNC_REQUEST message - send our blocks and state to the requesting peer."""
        payload = message.payload
        peer_height = payload.get('height', 0)
        peer_hash = payload.get('latest_hash', '')
        sender_id = message.sender_id
        
        my_height = self.blockchain.get_height()
        self.logger.info(f"Received SYNC_REQUEST from {sender_id} at {peer_address}: their height={peer_height}, my height={my_height}")
        self.logger.info(f"My state: view={self.current_view}, failed_validators={list(self.failed_validators)}")
        
        # Always send sync response with view and failed validators (even if same height)
        # This helps recovering nodes sync their consensus state
        blocks = []
        if my_height > peer_height:
            # We have more blocks, send them
            self.logger.info(f"Will send {my_height - peer_height} blocks to {sender_id}")
            
            for h in range(peer_height + 1, my_height + 1):
                block = self.blockchain.get_block(h)
                if block:
                    blocks.append(block.to_dict())
        
        # Include view and failed validators in response
        self.network.send_sync_response(
            peer_address,
            my_height,
            self.blockchain.get_latest_hash().hex(),
            blocks,
            self.current_view,
            list(self.failed_validators)
        )
        self.logger.info(f"Sent SYNC_RESPONSE to {sender_id}: height={my_height}, view={self.current_view}, failed={list(self.failed_validators)}")
        
        # Also send mempool transactions
        txs = self.mempool.get_all_transactions()
        if txs:
            tx_list = [
                {
                    'tx_id': tx.tx_id,
                    'sender': tx.sender,
                    'recipient': tx.recipient,
                    'amount': tx.amount,
                    'timestamp': tx.timestamp
                }
                for tx in txs
            ]
            self.network.broadcast_mempool_sync(tx_list)
    
    def _handle_sync_response(self, message):
        """Handle SYNC_RESPONSE message - receive blocks and state from a peer."""
        payload = message.payload
        peer_height = payload.get('height', 0)
        blocks_data = payload.get('blocks', [])
        peer_view = payload.get('current_view', 0)
        peer_failed_validators = payload.get('failed_validators', [])
        sender_id = message.sender_id
        
        self.logger.info(f"Received SYNC_RESPONSE from {sender_id}: {len(blocks_data)} blocks, view={peer_view}, failed={peer_failed_validators}")
        
        # Sync view if peer has higher view
        if peer_view > self.current_view:
            self.logger.info(f"Syncing view from SYNC_RESPONSE: {self.current_view} -> {peer_view}")
            with self.view_change_lock:
                self.current_view = peer_view
                self.last_view_change_time = time.time()
        
        # NOTE: We do NOT sync failed_validators from peers during recovery
        # The recovering node should determine failures through its own health checks
        if not self.is_recovering:
            my_hostname = self.config.get_hostname()
            my_short = my_hostname.split('.')[0]
            
            for failed in peer_failed_validators:
                short_failed = failed.split('.')[0]
                
                # Skip if it's our own hostname
                if failed == my_hostname or short_failed == my_short:
                    continue
                
                for validator in self.consensus.validator_ids:
                    if validator == failed or validator.split('.')[0] == short_failed:
                        if validator not in self.failed_validators:
                            self.failed_validators.add(validator)
                            self.active_validators.discard(validator)
                            self.logger.info(f"Synced failed validator from SYNC_RESPONSE: {validator}")
                        break
        else:
            self.logger.debug(f"Skipping failed_validators sync during recovery (peer reported: {peer_failed_validators})")
        
        my_height = self.blockchain.get_height()
        
        if peer_height <= my_height and len(blocks_data) == 0:
            self.logger.debug(f"Already at or ahead of peer (my height: {my_height}, peer height: {peer_height})")
            return
        
        # Process blocks in order
        blocks_added = 0
        for block_dict in blocks_data:
            try:
                block = Block.from_dict(block_dict)
                
                # Verify block height is what we expect
                expected_height = self.blockchain.get_height() + 1
                if block.height != expected_height:
                    self.logger.warning(f"Block height mismatch in sync: expected {expected_height}, got {block.height}")
                    continue
                
                # Verify previous hash
                expected_prev_hash = self.blockchain.get_latest_hash()
                if block.prev_hash != expected_prev_hash:
                    self.logger.warning(f"Block prev_hash mismatch in sync at height {block.height}")
                    continue
                
                # Add block
                if self.blockchain.add_block(block):
                    blocks_added += 1
                    
                    # Remove synced transactions from mempool
                    tx_ids = [tx.tx_id for tx in block.transactions]
                    self.mempool.remove_transactions(tx_ids)
                    
                    # Update consensus state
                    self.consensus.on_block_committed(block.height)
                    
                    self.logger.info(f"Synced block {block.height} from {sender_id}")
                else:
                    self.logger.warning(f"Failed to add synced block {block.height}")
            except Exception as e:
                self.logger.error(f"Error processing synced block: {e}")
        
        self.logger.info(f"Sync complete: added {blocks_added} blocks, new height: {self.blockchain.get_height()}, view: {self.current_view}")
        
        # If we received blocks, we're making progress - might be ready to complete recovery
        if blocks_added > 0 or peer_view >= self.current_view:
            # Check if we're now caught up
            if self.blockchain.get_height() >= peer_height:
                self.logger.info("Sync brought us up to date with peer")
                if self.is_recovering:
                    self._complete_recovery()
    
    def _handle_mempool_sync(self, message):
        """Handle MEMPOOL_SYNC message - receive mempool transactions from a peer."""
        payload = message.payload
        transactions = payload.get('transactions', [])
        sender_id = message.sender_id
        
        self.logger.info(f"Received MEMPOOL_SYNC from {sender_id}: {len(transactions)} transactions")
        
        added = 0
        for tx_data in transactions:
            try:
                tx = Transaction(
                    tx_id=tx_data['tx_id'],
                    sender=tx_data['sender'],
                    recipient=tx_data['recipient'],
                    amount=tx_data['amount'],
                    timestamp=tx_data['timestamp']
                )
                
                # Check if already in blockchain
                if self.blockchain.get_transaction(tx.tx_id):
                    continue
                
                if self.mempool.add_transaction(tx):
                    added += 1
            except Exception as e:
                self.logger.debug(f"Error processing synced transaction: {e}")
        
        if added > 0:
            self.logger.info(f"Added {added} transactions from mempool sync")
    
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
        
        # Check proposer is the effective leader (accounts for view changes)
        effective_leader = self.get_effective_leader(block.height)
        proposer_short = block.proposer_id.split('.')[0]
        leader_short = effective_leader.split('.')[0]
        
        # Match by full hostname or short hostname
        is_valid_proposer = (block.proposer_id == effective_leader or proposer_short == leader_short)
        
        if not is_valid_proposer:
            self.logger.debug(f"Leader mismatch: expected {effective_leader}, got {block.proposer_id}")
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

