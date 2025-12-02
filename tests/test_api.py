import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch
import sys
import os

# Add src to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.api.server import app, node
from src.node.node import Node
from src.common.config import Config

# Mock Node for testing
@pytest.fixture
def mock_node():
    # Create a mock config
    config = MagicMock(spec=Config)
    config.get_node_id.return_value = "test-node"
    config.get_hostname.return_value = "test-host"
    config.get_port.return_value = 8000
    
    # Create a mock node
    node_mock = MagicMock()
    node_mock.config = config
    
    # Mock blockchain
    node_mock.blockchain = MagicMock()
    node_mock.blockchain.get_height.return_value = 10
    node_mock.blockchain.get_latest_hash.return_value = b'latest_hash'
    
    # Mock mempool
    node_mock.mempool = MagicMock()
    node_mock.mempool.size.return_value = 5
    node_mock.mempool.get_all_transactions.return_value = []
    
    # Mock consensus
    node_mock.consensus = MagicMock()
    node_mock.consensus.get_current_leader.return_value = "leader-node"
    node_mock.consensus.is_leader.return_value = False
    
    # Mock network
    node_mock.network = MagicMock()
    node_mock.network.connections = {}
    
    return node_mock

@pytest.fixture
def client(mock_node):
    # Patch the global node variable in server.py
    with patch('src.api.server.node', mock_node):
        yield TestClient(app)

def test_get_status(client, mock_node):
    response = client.get("/status")
    assert response.status_code == 200
    data = response.json()
    assert data["node_id"] == "test-node"
    assert data["height"] == 10
    assert data["mempool_size"] == 5

def test_get_blocks(client, mock_node):
    # Mock get_block to return a dummy block
    mock_block = MagicMock()
    mock_block.height = 5
    mock_block.block_hash = b'hash'
    mock_block.prev_hash = b'prev'
    mock_block.proposer_id = "proposer"
    mock_block.timestamp = 1234567890
    mock_block.transactions = []
    
    mock_node.blockchain.get_block.return_value = mock_block
    
    response = client.get("/blocks?limit=5")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    # Since we mock get_block to always return something, we might get multiple
    # But our loop in server.py depends on range.
    # range(0, 11) -> 11 calls.
    # If get_block returns mock_block, we get 11 items.
    assert len(data) > 0
    assert data[0]["height"] == 5

def test_submit_transaction(client, mock_node):
    mock_node.submit_transaction.return_value = True
    
    payload = {
        "sender": "alice",
        "recipient": "bob",
        "amount": 10.0
    }
    response = client.post("/submit", json=payload)
    assert response.status_code == 200
    assert response.json()["status"] == "submitted"
    assert "tx_id" in response.json()

def test_submit_transaction_failure(client, mock_node):
    mock_node.submit_transaction.return_value = False
    
    payload = {
        "sender": "alice",
        "recipient": "bob",
        "amount": 10.0
    }
    response = client.post("/submit", json=payload)
    assert response.status_code == 400

def test_debug_clear_mempool(client, mock_node):
    response = client.post("/debug/mempool/clear")
    assert response.status_code == 200
    mock_node.mempool.transactions.clear.assert_called_once()

def test_debug_disconnect(client, mock_node):
    # Setup some connections
    mock_node.network.connections = {"peer1": "conn1", "peer2": "conn2"}
    
    response = client.post("/debug/network/disconnect")
    assert response.status_code == 200
    
    # Verify connections are cleared
    assert len(mock_node.network.connections) == 0
