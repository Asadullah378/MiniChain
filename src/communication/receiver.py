"""
Message receiver module for handling incoming messages via TCP sockets and msgpack.
"""
import socket
import msgpack
import struct
import threading
from typing import Callable, Optional


class MessageReceiver:
    """
    TCP server for receiving messages from peers using msgpack deserialization.
    """
    
    def __init__(self, host: str = "0.0.0.0", port: int = 5000, message_handler: Optional[Callable] = None):
        """
        Initialize the message receiver.
        
        Args:
            host: Host to bind to (default: "0.0.0.0" for all interfaces)
            port: Port to listen on (default: 5000)
            message_handler: Optional callback function to handle incoming messages.
                            Should accept (sender_address, message) as arguments.
        """
        self.host = host
        self.port = port
        self.message_handler = message_handler
        self.server_socket: Optional[socket.socket] = None
        self.server_thread: Optional[threading.Thread] = None
        self.running = False
    
    def _handle_client(self, client_socket: socket.socket, client_address: tuple):
        """
        Handle a single client connection.
        
        Args:
            client_socket: The client socket
            client_address: Tuple of (host, port) of the client
        """
        try:
            # Receive message length (4 bytes, big-endian)
            length_data = b''
            while len(length_data) < 4:
                chunk = client_socket.recv(4 - len(length_data))
                if not chunk:
                    return
                length_data += chunk
            
            message_length = struct.unpack('>I', length_data)[0]
            
            # Receive message data
            message_data = b''
            while len(message_data) < message_length:
                chunk = client_socket.recv(message_length - len(message_data))
                if not chunk:
                    return
                message_data += chunk
            
            # Deserialize message using msgpack
            try:
                message = msgpack.unpackb(message_data, raw=False)
            except Exception as e:
                print(f"Error deserializing message from {client_address}: {e}")
                return
            
            # Format sender address
            sender_address = f"{client_address[0]}:{client_address[1]}"
            
            # Call message handler if provided
            if self.message_handler:
                try:
                    self.message_handler(sender_address, message)
                except Exception as e:
                    print(f"Error in message handler: {e}")
            
            # Send acknowledgment (1 byte: 1 = success)
            try:
                client_socket.sendall(b'\x01')
            except:
                pass
                
        except socket.error as e:
            print(f"Socket error handling client {client_address}: {e}")
        except Exception as e:
            print(f"Error handling client {client_address}: {e}")
        finally:
            try:
                client_socket.close()
            except:
                pass
    
    def _run_server(self):
        """Run the TCP server."""
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(10)  # Allow up to 10 pending connections
            self.server_socket.settimeout(1.0)  # Allow periodic checking of self.running
            
            print(f"Message receiver started on {self.host}:{self.port}")
            
            while self.running:
                try:
                    client_socket, client_address = self.server_socket.accept()
                    # Handle each client in a separate thread
                    client_thread = threading.Thread(
                        target=self._handle_client,
                        args=(client_socket, client_address),
                        daemon=True
                    )
                    client_thread.start()
                except socket.timeout:
                    # Timeout is expected, continue loop to check self.running
                    continue
                except Exception as e:
                    if self.running:
                        print(f"Error accepting connection: {e}")
                    break
                    
        except Exception as e:
            if self.running:
                print(f"Error running server: {e}")
        finally:
            if self.server_socket:
                try:
                    self.server_socket.close()
                except:
                    pass
    
    def start(self, run_in_thread: bool = True):
        """
        Start the message receiver server.
        
        Args:
            run_in_thread: If True, run server in a separate thread (default: True)
        """
        if self.running:
            print("Server is already running")
            return
        
        self.running = True
        
        if run_in_thread:
            self.server_thread = threading.Thread(
                target=self._run_server,
                daemon=True
            )
            self.server_thread.start()
            print(f"Message receiver started on {self.host}:{self.port} (running in thread)")
        else:
            self._run_server()
    
    def stop(self):
        """Stop the message receiver server."""
        self.running = False
        if self.server_socket:
            try:
                self.server_socket.close()
            except:
                pass
        print("Message receiver stopped")
    
    def set_message_handler(self, handler: Callable):
        """
        Set or update the message handler callback.
        
        Args:
            handler: Callback function that accepts (sender_address, message) as arguments
        """
        self.message_handler = handler
