"""Configuration management for MiniChain nodes."""

import os
import socket
import yaml
from pathlib import Path
from typing import Dict, List, Optional, Any


class Config:
    """Manages node configuration from file and environment variables."""
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize configuration.
        
        Args:
            config_path: Path to YAML config file. If None, uses default locations.
        """
        self.config_path = config_path or self._find_config_file()
        self.config = self._load_config()
        self._apply_environment_overrides()
        self._auto_detect_hostname()
    
    def _find_config_file(self) -> str:
        """Find configuration file in standard locations."""
        # Check current directory first (preferred)
        local_config = Path("config.yaml")
        if local_config.exists():
            return str(local_config)
        
        # Check config directory
        config_dir = Path("config")
        if config_dir.exists():
            default_config = config_dir / "default.yaml"
            if default_config.exists():
                return str(default_config)
        
        # Return default path (will use defaults if file doesn't exist)
        return "config.yaml"
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from YAML file."""
        if not Path(self.config_path).exists():
            return self._default_config()
        
        try:
            with open(self.config_path, 'r') as f:
                config = yaml.safe_load(f) or {}
            return {**self._default_config(), **config}
        except Exception as e:
            print(f"Warning: Could not load config from {self.config_path}: {e}")
            print("Using default configuration.")
            return self._default_config()
    
    def _default_config(self) -> Dict[str, Any]:
        """Return default configuration."""
        hostname = socket.gethostname()
        return {
            'node': {
                'id': hostname,
                'hostname': hostname,
                'port': 8000,
                'data_dir': 'data',
            },
            'network': {
                'peers': [],
                'listen_address': '0.0.0.0',
                'connection_timeout': 5,
                'heartbeat_interval': 10,
            },
            'consensus': {
                'type': 'poa_round_robin',
                'block_interval': 5,  # seconds
                'proposal_timeout': 10,  # seconds
                'quorum_size': 2,  # minimum ACKs needed (for 3 nodes: 2/3)
            },
            'blockchain': {
                'genesis_block': True,
                'max_block_size': 100,  # max transactions per block
            },
            'logging': {
                'level': 'INFO',
                'file': 'minichain.log',
                'console': True,
            }
        }
    
    def _apply_environment_overrides(self):
        """Apply environment variable overrides."""
        # Node ID
        if os.getenv('NODE_ID'):
            self.config['node']['id'] = os.getenv('NODE_ID')
        
        # Port
        if os.getenv('NODE_PORT'):
            self.config['node']['port'] = int(os.getenv('NODE_PORT'))
        
        # Hostname
        if os.getenv('NODE_HOSTNAME'):
            self.config['node']['hostname'] = os.getenv('NODE_HOSTNAME')
        
        # Peers (comma-separated list of hostname:port)
        if os.getenv('PEERS'):
            peers = []
            for peer_str in os.getenv('PEERS').split(','):
                peer_str = peer_str.strip()
                if ':' in peer_str:
                    hostname, port = peer_str.rsplit(':', 1)
                    peers.append({'hostname': hostname, 'port': int(port)})
                else:
                    peers.append({'hostname': peer_str, 'port': self.config['node']['port']})
            self.config['network']['peers'] = peers
    
    def _auto_detect_hostname(self):
        """Auto-detect and set hostname if not explicitly configured."""
        if not self.config['node'].get('hostname'):
            self.config['node']['hostname'] = socket.getfqdn()
        
        # Auto-detect node ID from hostname if not set
        if not self.config['node'].get('id') or self.config['node']['id'] == socket.gethostname():
            self.config['node']['id'] = self.config['node']['hostname']
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value using dot notation (e.g., 'node.port')."""
        keys = key.split('.')
        value = self.config
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
                if value is None:
                    return default
            else:
                return default
        return value
    
    def get_node_id(self) -> str:
        """Get the node's unique identifier."""
        return self.config['node']['id']
    
    def get_hostname(self) -> str:
        """Get the node's hostname."""
        return self.config['node']['hostname']
    
    def get_port(self) -> int:
        """Get the node's listening port."""
        return self.config['node']['port']
    
    def get_peers(self) -> List[Dict[str, Any]]:
        """Get list of peer nodes."""
        return self.config['network'].get('peers', [])
    
    def get_data_dir(self) -> str:
        """Get data directory path."""
        return self.config['node']['data_dir']
    
    def add_peer(self, hostname: str, port: Optional[int] = None):
        """Add a peer to the configuration."""
        if port is None:
            port = self.get_port()
        
        peer = {'hostname': hostname, 'port': port}
        if peer not in self.config['network']['peers']:
            self.config['network']['peers'].append(peer)
    
    def __getitem__(self, key: str) -> Any:
        """Allow dictionary-style access."""
        return self.config[key]
    
    def __contains__(self, key: str) -> bool:
        """Check if key exists in config."""
        return key in self.config

