"""
Message sender module for sending messages to peers using TCP sockets and msgpack.
"""
import socket
import msgpack
import struct
from typing import Dict, Any
from communication.get_addresses import get_peer_addresses
from storage.json_operations import read_json_file


def send_message(peer_address: str, message: Dict[str, Any], timeout: int = 5) -> bool:
    """
    Send a message to a specific peer using TCP socket with msgpack serialization.
    
    Args:
        peer_address: Address of the peer in format "host:port" (e.g., "localhost:5001" or "client_a:5000")
                      For Docker containers, use service names from compose.yaml (e.g., "client_a:5000")
        message: Dictionary containing the message data
        timeout: Connection timeout in seconds (default: 5)
    
    Returns:
        True if message was sent successfully, False otherwise
    """
    sock = None
    try:
        # Parse host and port from address
        if ':' in peer_address:
            host, port = peer_address.split(':')
            port = int(port)
        else:
            host = peer_address
            port = 5000
        
        # Serialize message using msgpack
        packed_message = msgpack.packb(message)
        
        # Create socket and connect
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        sock.connect((host, port))
        
        # Send message length (4 bytes, big-endian) followed by message data
        message_length = len(packed_message)
        sock.sendall(struct.pack('>I', message_length))
        sock.sendall(packed_message)
        
        # Optionally receive acknowledgment (1 byte: 1 = success, 0 = failure)
        # For now, we'll just check if connection was successful
        sock.close()
        return True
        
    except socket.timeout:
        print(f"Timeout sending message to {peer_address}")
        return False
    except socket.error as e:
        print(f"Socket error sending message to {peer_address}: {e}")
        return False
    except Exception as e:
        print(f"Error sending message to {peer_address}: {e}")
        return False
    finally:
        if sock:
            try:
                sock.close()
            except:
                pass


def broadcast_message(message: Dict[str, Any], exclude_self: bool = True, timeout: int = 5) -> Dict[str, bool]:
    """
    Broadcast a message to all peers using TCP sockets with msgpack.
    
    Args:
        message: Dictionary containing the message data
        exclude_self: If True, exclude the current node from broadcast (default: True)
        timeout: Connection timeout in seconds for each peer (default: 5)
    
    Returns:
        Dictionary mapping peer addresses to success status (True/False)
    """
    results = {}
    
    try:
        # Get all peer addresses
        peer_addresses = get_peer_addresses()
        
        # Optionally get current client address to exclude it
        current_address = None
        if exclude_self:
            try:
                addresses = read_json_file("seed_addresses.json")
                if addresses and "client" in addresses:
                    current_address = addresses["client"]
            except Exception:
                pass
        
        # Send message to each peer
        for peer_address in peer_addresses:
            # Skip self if exclude_self is True
            if exclude_self and peer_address == current_address:
                continue
            
            success = send_message(peer_address, message, timeout)
            results[peer_address] = success
        
        return results
        
    except Exception as e:
        print(f"Error during broadcast: {e}")
        return results
