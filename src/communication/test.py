import time
import argparse
import socket
import sys
import os

# add the path to the communication module
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


from communication.sender import send_message, broadcast_message
from communication.receiver import MessageReceiver


# Pre-known peers list
KNOWN_PEERS = [
    "localhost:5000",
    "localhost:5001",
    "localhost:5002"
]


class MiniChainCLI:
    """Interactive CLI for MiniChain node communication."""
    
    def __init__(self, receiver: MessageReceiver, port: int, peers: list):
        self.receiver = receiver
        self.port = port
        self.peers = peers
        self.running = True
    
    def print_help(self):
        """Print help message."""
        print("\n" + "="*60)
        print("MiniChain CLI - Commands")
        print("="*60)
        print("  send <peer> <message>  - Send message to specific peer")
        print("  broadcast <message>   - Broadcast message to all peers")
        print("  peers                  - List known peers")
        print("  connect               - Try to connect to all peers")
        print("  help                   - Show this help message")
        print("  status                 - Show node status")
        print("  exit/quit              - Exit the CLI")
        print("="*60 + "\n")
    
    def handle_message(self, sender_address: str, message: dict):
        """
        Handle incoming messages from peers.
        
        Args:
            sender_address: Address of the sender
            message: The message dictionary
        """
        print(f"\n[RECEIVED] From {sender_address}:")
        print(f"  Type: {message.get('type', 'unknown')}")
        print(f"  Data: {message.get('data', message)}")
        if 'timestamp' in message:
            print(f"  Time: {time.strftime('%H:%M:%S', time.localtime(message['timestamp']))}")
        print("> ", end="", flush=True)  # Restore prompt
    
    def show_status(self):
        """Show current node status."""
        print(f"\nNode Port: {self.port}")
        print(f"Known Peers: {', '.join(self.peers)}")
        print(f"Receiver Status: {'Running' if self.receiver.running else 'Stopped'}")
        print()
    
    def list_peers(self):
        """List all known peers."""
        print(f"\nKnown Peers ({len(self.peers)}):")
        for i, peer in enumerate(self.peers, 1):
            print(f"  {i}. {peer}")
        print()
    
    def connect_to_peers(self):
        """Try to connect to all known peers (send a hello message)."""
        print("\nConnecting to peers...")
        current_address = f"localhost:{self.port}"
        
        hello_message = {
            "type": "hello",
            "data": f"Hello from node on port {self.port}",
            "timestamp": time.time()
        }
        
        results = {}
        for peer in self.peers:
            # Skip self
            if peer == current_address:
                continue
            
            print(f"  Connecting to {peer}...", end=" ")
            success = send_message(peer, hello_message, timeout=2)
            results[peer] = success
            if success:
                print("✓")
            else:
                print("✗")
        
        print("\nConnection results:")
        for peer, success in results.items():
            status = "✓" if success else "✗"
            print(f"  {status} {peer}")
        print()
    
    def run(self):
        """Run the CLI loop."""
        print("\n" + "="*60)
        print("MiniChain Node - Communication Test")
        print("="*60)
        print(f"Listening on port: {self.port}")
        print(f"Known peers: {len(self.peers)}")
        print("Type 'help' for available commands")
        print("="*60 + "\n")
        
        while self.running:
            try:
                command = input("> ").strip()
                
                if not command:
                    continue
                
                parts = command.split(maxsplit=1)
                cmd = parts[0].lower()
                
                if cmd in ['exit', 'quit', 'q']:
                    print("Shutting down...")
                    self.running = False
                    self.receiver.stop()
                    break
                
                elif cmd == 'help' or cmd == 'h':
                    self.print_help()
                
                elif cmd == 'status' or cmd == 'info':
                    self.show_status()
                
                elif cmd == 'peers':
                    self.list_peers()
                
                elif cmd == 'connect':
                    self.connect_to_peers()
                
                elif cmd == 'send':
                    if len(parts) < 2:
                        print("Usage: send <peer_address> <message>")
                        print("Example: send localhost:5001 Hello!")
                        continue
                    
                    send_parts = parts[1].split(maxsplit=1)
                    if len(send_parts) < 2:
                        print("Usage: send <peer_address> <message>")
                        continue
                    
                    peer_address = send_parts[0]
                    message_text = send_parts[1]
                    
                    message = {
                        "type": "direct_message",
                        "data": message_text,
                        "timestamp": time.time()
                    }
                    
                    print(f"Sending to {peer_address}...")
                    success = send_message(peer_address, message)
                    if success:
                        print(f"✓ Message sent successfully to {peer_address}")
                    else:
                        print(f"✗ Failed to send message to {peer_address}")
                
                elif cmd == 'broadcast' or cmd == 'bcast':
                    if len(parts) < 2:
                        print("Usage: broadcast <message>")
                        print("Example: broadcast Hello everyone!")
                        continue
                    
                    message_text = parts[1]
                    
                    message = {
                        "type": "broadcast_message",
                        "data": message_text,
                        "timestamp": time.time()
                    }
                    
                    print("Broadcasting to all peers...")
                    # Broadcast to all known peers except self
                    current_address = f"localhost:{self.port}"
                    results = {}
                    for peer in self.peers:
                        if peer == current_address:
                            continue
                        success = send_message(peer, message)
                        results[peer] = success
                    
                    print("\nBroadcast results:")
                    for peer, success in results.items():
                        status = "✓" if success else "✗"
                        print(f"  {status} {peer}")
                
                else:
                    print(f"Unknown command: {cmd}")
                    print("Type 'help' for available commands")
            
            except EOFError:
                # Handle Ctrl+D
                print("\nShutting down...")
                self.running = False
                self.receiver.stop()
                break
            except KeyboardInterrupt:
                # Handle Ctrl+C
                print("\n\nShutting down...")
                self.running = False
                self.receiver.stop()
                break
            except Exception as e:
                print(f"Error: {e}")


def is_port_available(port: int) -> bool:
    """Check if a port is available."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.bind(('localhost', port))
        sock.close()
        return True
    except OSError:
        return False


def main():
    """Main function to start the MiniChain node."""
    parser = argparse.ArgumentParser(description='MiniChain Node - P2P Communication')
    parser.add_argument(
        '--port', '-p',
        type=int,
        default=5000,
        help='Port to listen on (default: 5000)'
    )
    args = parser.parse_args()
    
    port = args.port
    
    # Check if port is available
    if not is_port_available(port):
        print(f"ERROR: Port {port} is already in use or not available")
        print("Please choose a different port using --port <port_number>")
        return
    
    print(f"Starting MiniChain node on port {port}")
    print(f"Known peers: {', '.join(KNOWN_PEERS)}")
    
    # Filter out self from peers list for broadcasting
    current_address = f"localhost:{port}"
    other_peers = [p for p in KNOWN_PEERS if p != current_address]
    
    # Create message receiver
    receiver = MessageReceiver(host="0.0.0.0", port=port)
    
    # Create CLI
    cli = MiniChainCLI(receiver, port, KNOWN_PEERS)
    
    # Set message handler
    receiver.set_message_handler(cli.handle_message)
    
    # Start receiver in background thread
    receiver.start(run_in_thread=True)
    
    # Give server a moment to start
    time.sleep(0.5)
    
    # Optionally try to connect to peers on startup
    print("\nTip: Use 'connect' command to test connections to all peers")
    
    # Run CLI (blocking)
    cli.run()
    
    print("Node stopped.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nShutting down...")
    except Exception as e:
        print(f"Fatal error: {e}")
        import traceback
        traceback.print_exc()
