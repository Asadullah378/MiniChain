"""Interactive CLI for MiniChain node."""

import threading
import time
from typing import Optional
from src.node.node import Node
from src.chain.block import Transaction
from src.common.crypto import hash_string


class CLI:
    """Command-line interface for interacting with a MiniChain node."""
    
    def __init__(self, node: Node, log_file: Optional[str] = None):
        """
        Initialize CLI with a node instance.
        
        Args:
            node: Node instance to interact with
            log_file: Path to log file for viewing logs
        """
        self.node = node
        self.log_file = log_file
        self.running = False
        self.cli_thread: Optional[threading.Thread] = None
    
    def start(self):
        """Start the CLI in a separate thread."""
        self.running = True
        self.cli_thread = threading.Thread(target=self._cli_loop, daemon=True)
        self.cli_thread.start()
    
    def stop(self):
        """Stop the CLI."""
        self.running = False
    
    def _cli_loop(self):
        """Main CLI loop."""
        time.sleep(2)  # Give node time to start
        
        # Check if stdin is available (not available in some background scenarios)
        try:
            import sys
            if not sys.stdin.isatty():
                self.node.logger.info("CLI disabled: stdin not available (running in background mode)")
                return
        except:
            pass
        
        print("\n" + "="*60)
        print("MiniChain CLI - Type 'help' for commands")
        print("="*60 + "\n")
        
        while self.running and self.node.running:
            try:
                command = input("minichain> ").strip()
                if not command:
                    continue
                
                self._handle_command(command)
            except EOFError:
                # EOF on stdin - exit gracefully
                print("\nExiting CLI (EOF)...")
                break
            except KeyboardInterrupt:
                print("\nExiting CLI...")
                break
            except Exception as e:
                print(f"Error: {e}")
                import traceback
                traceback.print_exc()
    
    def _handle_command(self, command: str):
        """Handle a CLI command."""
        parts = command.split()
        if not parts:
            return
        
        cmd = parts[0].lower()
        args = parts[1:]
        
        if cmd == 'help' or cmd == 'h':
            self._print_help()
        elif cmd == 'submit' or cmd == 'tx':
            self._submit_transaction(args)
        elif cmd == 'status' or cmd == 'info':
            self._show_status()
        elif cmd == 'chain' or cmd == 'blocks':
            self._show_chain(args)
        elif cmd == 'block':
            self._show_block(args)
        elif cmd == 'mempool' or cmd == 'pool':
            self._show_mempool()
        elif cmd == 'peers':
            self._show_peers()
        elif cmd == 'logs':
            self._show_logs(args)
        elif cmd == 'clear':
            print("\n" * 50)  # Clear screen (simple version)
        elif cmd == 'exit' or cmd == 'quit' or cmd == 'q':
            print("Exiting...")
            self.node.stop()
            self.running = False
        else:
            print(f"Unknown command: {cmd}. Type 'help' for available commands.")
    
    def _print_help(self):
        """Print help message."""
        help_text = """
Available Commands:
  help, h              - Show this help message
  submit, tx           - Submit a transaction
                         Usage: submit <sender> <recipient> <amount>
                         Example: submit alice bob 10.5
  status, info         - Show node status and blockchain info
  chain, blocks        - Show blockchain summary
                         Usage: chain [limit] (default: 10)
  block <height>       - Show details of a specific block
                         Example: block 5
  mempool, pool        - Show pending transactions in mempool
  peers                - Show connected peers
  logs [n]             - Show last n lines from log file (default: 20)
                         Example: logs 50
                         Note: Use --log-level DEBUG to see debug logs
  clear                - Clear screen
  exit, quit, q        - Exit the node

Examples:
  submit alice bob 25.0
  block 0
  chain 5
"""
        print(help_text)
    
    def _submit_transaction(self, args):
        """Submit a transaction."""
        if len(args) < 3:
            print("Usage: submit <sender> <recipient> <amount>")
            print("Example: submit alice bob 10.5")
            return
        
        try:
            sender = args[0]
            recipient = args[1]
            amount = float(args[2])
            
            if amount <= 0:
                print("Error: Amount must be positive")
                return
            
            # Generate transaction ID
            tx_id = hash_string(f"{sender}{recipient}{amount}{time.time()}")[:16]
            
            # Create transaction
            tx = Transaction(
                tx_id=tx_id,
                sender=sender,
                recipient=recipient,
                amount=amount,
                timestamp=time.time()
            )
            
            # Submit to node
            success = self.node.submit_transaction(tx)
            
            if success:
                print(f"✓ Transaction submitted: {tx_id}")
                print(f"  {sender} -> {recipient}: {amount}")
            else:
                print(f"✗ Failed to submit transaction (may already exist)")
        
        except ValueError:
            print("Error: Invalid amount. Must be a number.")
        except Exception as e:
            print(f"Error submitting transaction: {e}")
    
    def _show_status(self):
        """Show node status."""
        height = self.node.blockchain.get_height()
        latest_block = self.node.blockchain.get_latest_block()
        mempool_size = self.node.mempool.size()
        is_leader = self.node.consensus.is_leader(height + 1)
        current_leader = self.node.consensus.get_current_leader(height + 1)
        connected_peers = len(self.node.network.connections)
        
        print("\n" + "="*60)
        print("Node Status")
        print("="*60)
        print(f"Node ID:        {self.node.config.get_node_id()}")
        print(f"Hostname:       {self.node.config.get_hostname()}")
        print(f"Port:           {self.node.config.get_port()}")
        print(f"Blockchain Height: {height}")
        print(f"Latest Block Hash: {latest_block.block_hash.hex()[:16]}...")
        print(f"Mempool Size:   {mempool_size} transactions")
        print(f"Connected Peers: {connected_peers}")
        print(f"Current Leader: {current_leader}")
        print(f"I am Leader:    {'Yes' if is_leader else 'No'} (for next block)")
        print("="*60 + "\n")
    
    def _show_chain(self, args):
        """Show blockchain summary."""
        limit = 10
        if args:
            try:
                limit = int(args[0])
            except ValueError:
                print("Error: Limit must be a number")
                return
        
        height = self.node.blockchain.get_height()
        start = max(0, height - limit + 1)
        
        print(f"\nBlockchain (showing last {min(limit, height + 1)} blocks):")
        print("="*80)
        print(f"{'Height':<8} {'Hash':<20} {'Prev Hash':<20} {'TXs':<6} {'Proposer':<15} {'Time'}")
        print("-"*80)
        
        for h in range(start, height + 1):
            block = self.node.blockchain.get_block(h)
            if block:
                time_str = time.strftime('%H:%M:%S', time.localtime(block.timestamp))
                print(f"{block.height:<8} {block.block_hash.hex()[:18]:<20} "
                      f"{block.prev_hash.hex()[:18]:<20} {len(block.transactions):<6} "
                      f"{block.proposer_id:<15} {time_str}")
        
        print("="*80 + "\n")
    
    def _show_block(self, args):
        """Show details of a specific block."""
        if not args:
            print("Usage: block <height>")
            print("Example: block 5")
            return
        
        try:
            height = int(args[0])
            block = self.node.blockchain.get_block(height)
            
            if not block:
                print(f"Block at height {height} not found")
                return
            
            print(f"\nBlock #{height}:")
            print("="*60)
            print(f"Height:      {block.height}")
            print(f"Hash:        {block.block_hash.hex()}")
            print(f"Prev Hash:   {block.prev_hash.hex()}")
            print(f"Proposer:    {block.proposer_id}")
            print(f"Timestamp:   {time.ctime(block.timestamp)}")
            print(f"Transactions: {len(block.transactions)}")
            
            if block.transactions:
                print("\nTransactions:")
                print("-"*60)
                for i, tx in enumerate(block.transactions, 1):
                    print(f"  {i}. {tx.tx_id[:16]}... | {tx.sender} -> {tx.recipient}: {tx.amount}")
            else:
                print("  (No transactions)")
            
            print("="*60 + "\n")
        
        except ValueError:
            print("Error: Height must be a number")
        except Exception as e:
            print(f"Error: {e}")
    
    def _show_mempool(self):
        """Show mempool contents."""
        transactions = self.node.mempool.get_all_transactions()
        
        print(f"\nMempool ({len(transactions)} transactions):")
        print("="*80)
        
        if not transactions:
            print("  (Empty)")
        else:
            print(f"{'TX ID':<20} {'Sender':<15} {'Recipient':<15} {'Amount':<10} {'Time'}")
            print("-"*80)
            for tx in transactions[:20]:  # Show first 20
                time_str = time.strftime('%H:%M:%S', time.localtime(tx.timestamp))
                print(f"{tx.tx_id[:18]:<20} {tx.sender:<15} {tx.recipient:<15} "
                      f"{tx.amount:<10.2f} {time_str}")
            
            if len(transactions) > 20:
                print(f"... and {len(transactions) - 20} more")
        
        print("="*80 + "\n")
    
    def _show_peers(self):
        """Show connected peers."""
        connections = self.node.network.connections
        
        print(f"\nConnected Peers ({len(connections)}):")
        print("="*60)
        
        if not connections:
            print("  (No peers connected)")
        else:
            for peer_address in connections:
                print(f"  - {peer_address}")
        
        print("="*60 + "\n")
    
    def _show_logs(self, args):
        """Show last n lines from log file."""
        if not self.log_file:
            print("No log file configured.")
            return
        
        try:
            from pathlib import Path
            log_path = Path(self.log_file)
            
            if not log_path.exists():
                print(f"Log file not found: {self.log_file}")
                return
            
            # Default to 20 lines if not specified
            num_lines = 20
            if args:
                try:
                    num_lines = int(args[0])
                    if num_lines <= 0:
                        print("Error: Number of lines must be positive")
                        return
                except ValueError:
                    print("Error: Number of lines must be a number")
                    return
            
            # Read last n lines from file
            with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
                last_lines = lines[-num_lines:] if len(lines) > num_lines else lines
            
            print(f"\nLast {len(last_lines)} lines from {self.log_file}:")
            print("="*80)
            for line in last_lines:
                print(line.rstrip())
            print("="*80 + "\n")
        
        except Exception as e:
            print(f"Error reading log file: {e}")
    
    def _show_logs(self, args):
        """Show last n lines from log file."""
        if not self.log_file:
            print("No log file configured.")
            return
        
        try:
            from pathlib import Path
            log_path = Path(self.log_file)
            
            if not log_path.exists():
                print(f"Log file not found: {self.log_file}")
                return
            
            # Default to 20 lines if not specified
            num_lines = 20
            if args:
                try:
                    num_lines = int(args[0])
                    if num_lines <= 0:
                        print("Error: Number of lines must be positive")
                        return
                except ValueError:
                    print("Error: Number of lines must be a number")
                    return
            
            # Read last n lines from file
            with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
                last_lines = lines[-num_lines:] if len(lines) > num_lines else lines
            
            print(f"\nLast {len(last_lines)} lines from {self.log_file}:")
            print("="*80)
            for line in last_lines:
                print(line.rstrip())
            print("="*80 + "\n")
        
        except Exception as e:
            print(f"Error reading log file: {e}")

