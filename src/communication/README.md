# Communication Module

This module provides functions for sending and receiving messages between nodes in the MiniChain network using **TCP sockets** and **msgpack** serialization.

## Protocol

Messages are sent over TCP sockets with the following format:
1. **Message length** (4 bytes, big-endian): Length of the serialized message
2. **Message data** (variable length): msgpack-serialized dictionary
3. **Acknowledgment** (1 byte, optional): 1 = success, 0 = failure

## Functions

### `send_message(peer_address, message, timeout=5)`

Send a message to a specific peer using TCP socket with msgpack serialization.

**Parameters:**
- `peer_address` (str): Address of the peer in format "host:port" (e.g., "localhost:5001")
- `message` (dict): Dictionary containing the message data (will be serialized with msgpack)
- `timeout` (int): Connection timeout in seconds (default: 5)

**Returns:**
- `bool`: True if message was sent successfully, False otherwise

**Example:**
```python
from communication import send_message

message = {
    "type": "transaction",
    "data": {"from": "alice", "to": "bob", "amount": 10.5}
}

success = send_message("localhost:5001", message)
```

### `broadcast_message(message, exclude_self=True, timeout=5)`

Broadcast a message to all peers listed in `seed_addresses.json` using TCP sockets.

**Parameters:**
- `message` (dict): Dictionary containing the message data
- `exclude_self` (bool): If True, exclude the current node from broadcast (default: True)
- `timeout` (int): Connection timeout in seconds for each peer (default: 5)

**Returns:**
- `dict`: Dictionary mapping peer addresses to success status (True/False)

**Example:**
```python
from communication import broadcast_message

message = {
    "type": "block_proposal",
    "data": {"block_hash": "abc123", "height": 5}
}

results = broadcast_message(message)
print(results)  # {"localhost:5001": True, "localhost:5002": False}
```

### `MessageReceiver(host="0.0.0.0", port=5000, message_handler=None)`

TCP server class for receiving messages from peers using msgpack deserialization.

**Parameters:**
- `host` (str): Host to bind to (default: "0.0.0.0" for all interfaces)
- `port` (int): Port to listen on (default: 5000)
- `message_handler` (callable): Optional callback function to handle incoming messages.
                                Should accept (sender_address, message) as arguments.

**Methods:**
- `start(run_in_thread=True)`: Start the message receiver server
- `set_message_handler(handler)`: Set or update the message handler callback
- `stop()`: Stop the message receiver server

**Example:**
```python
from communication import MessageReceiver

def handle_message(sender_address, message):
    print(f"Received from {sender_address}: {message}")

receiver = MessageReceiver(host="0.0.0.0", port=5000, message_handler=handle_message)
receiver.start(run_in_thread=True)
```