"""Main node implementation that coordinates all components."""

import threading
import time
from typing import Optional
from src.common.config import Config
from src.common.logger import setup_logger
from src.chain.blockchain import Blockchain
from src.chain.block import Transaction, Block
from src.mempool.mempool import Mempool
from src.consensus.poa import RoundRobinPoA
from src.p2p.network import NetworkManager


class Node:
    """Main node that coordinates blockchain, consensus, and networking."""
    
    def __init__(self, config: Config, disable_console_logging: bool = False):
        """
        Initialize node with configuration.
        
        Args:
            config: Node configuration
            disable_console_logging: If True, disable console output for loggers
        """
        self.config = config
        self.logger = setup_logger(
            'minichain.node',
            level=config.get('logging.level', 'INFO'),
            log_file=config.get('logging.file'),
            console=config.get('logging.console', True) and not disable_console_logging
        )
        
        # Initialize components
        self.blockchain = Blockchain(data_dir=config.get_data_dir())
        self.mempool = Mempool()
        
        # Get validator list (for now, use peers + self)
        validator_ids = [config.get_node_id()]
        for peer in config.get_peers():
            # Use hostname as validator ID
            validator_ids.append(peer.get('hostname', peer.get('node_id', 'unknown')))
        validator_ids = sorted(list(set(validator_ids)))  # Remove duplicates and sort
        
        self.consensus = RoundRobinPoA(
            node_id=config.get_node_id(),
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
            
            # Deserialize transactions
            transactions = [Transaction.deserialize(tx_bytes) for tx_bytes in tx_list]
            
            # Create block
            block = Block(
                height=height,
                prev_hash=prev_hash,
                transactions=transactions,
                timestamp=time.time(),
                proposer_id=proposer_id,
                block_hash=block_hash
            )
            
            # Validate block
            if not self._validate_proposal(block):
                self.logger.warning(f"Invalid proposal at height {height}")
                return
            
            # Store pending proposal
            self.consensus.pending_proposal = block
            
            # Send ACK
            self.logger.info(f"ACKing proposal at height {height}")
            self.network.send_ack(height, block_hash, self.config.get_node_id())
        
        except Exception as e:
            self.logger.error(f"Error handling proposal: {e}", exc_info=True)
    
    def _handle_ack(self, message):
        """Handle ACK message."""
        try:
            payload = message.payload
            height = payload['height']
            voter_id = payload['voter_id']
            
            self.consensus.add_ack(height, voter_id)
            
            # Check if we have quorum
            if self.consensus.has_quorum(height):
                self.logger.info(f"Quorum reached for height {height}, committing block")
                if self.consensus.pending_proposal:
                    # Commit the block
                    if self.blockchain.add_block(self.consensus.pending_proposal):
                        # Remove transactions from mempool
                        tx_ids = [tx.tx_id for tx in self.consensus.pending_proposal.transactions]
                        self.mempool.remove_transactions(tx_ids)
                        
                        # Update consensus state
                        self.consensus.on_block_committed(height)
                        
                        # Broadcast COMMIT
                        self.network.broadcast_commit(
                            height,
                            self.consensus.pending_proposal.block_hash,
                            self.config.get_node_id()
                        )
                        self.logger.info(f"Block {height} committed")
                    else:
                        self.logger.error(f"Failed to add block {height} to chain")
        
        except Exception as e:
            self.logger.error(f"Error handling ACK: {e}", exc_info=True)
    
    def _handle_commit(self, message):
        """Handle COMMIT message."""
        from src.chain.block import Block
        
        try:
            payload = message.payload
            height = payload['height']
            block_hash = bytes.fromhex(payload['block_hash'])
            
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
                    self.logger.info(f"Block {height} committed via COMMIT message")
                else:
                    self.logger.error(f"Failed to commit block {height}")
        
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
        
        except Exception as e:
            self.logger.error(f"Error handling GETBLOCKS: {e}", exc_info=True)
    
    def _validate_proposal(self, block: 'Block') -> bool:
        """Validate a block proposal."""
        # Check height
        expected_height = self.blockchain.get_height() + 1
        if block.height != expected_height:
            return False
        
        # Check previous hash
        if block.prev_hash != self.blockchain.get_latest_hash():
            return False
        
        # Check proposer is correct leader
        if block.proposer_id != self.consensus.get_current_leader(block.height):
            return False
        
        # Check block structure
        if not block.is_valid():
            return False
        
        return True

