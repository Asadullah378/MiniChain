"""Main entry point for MiniChain node."""

import sys
import argparse
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.common.config import Config
from src.common.logger import setup_logger
from src.node.node import Node


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='MiniChain - Simple Blockchain Node')
    parser.add_argument(
        '--config',
        type=str,
        help='Path to configuration file (default: config.yaml or config/default.yaml)'
    )
    parser.add_argument(
        '--port',
        type=int,
        help='Listening port (overrides config)'
    )
    parser.add_argument(
        '--peers',
        type=str,
        help='Comma-separated list of peers (hostname:port or just hostname)'
    )
    parser.add_argument(
        '--node-id',
        type=str,
        help='Node ID (overrides config)'
    )
    
    args = parser.parse_args()
    
    # Load configuration
    config = Config(config_path=args.config)
    
    # Override with command-line arguments
    if args.port:
        config.config['node']['port'] = args.port
    if args.node_id:
        config.config['node']['id'] = args.node_id
        config.config['node']['hostname'] = args.node_id
    if args.peers:
        peers = []
        for peer_str in args.peers.split(','):
            peer_str = peer_str.strip()
            if ':' in peer_str:
                hostname, port = peer_str.rsplit(':', 1)
                peers.append({'hostname': hostname, 'port': int(port)})
            else:
                peers.append({'hostname': peer_str, 'port': config.get_port()})
        config.config['network']['peers'] = peers
    
    # Setup logger
    logger = setup_logger(
        'minichain',
        level=config.get('logging.level', 'INFO'),
        log_file=config.get('logging.file'),
        console=config.get('logging.console', True)
    )
    
    logger.info(f"Starting MiniChain node: {config.get_node_id()}")
    logger.info(f"Hostname: {config.get_hostname()}")
    logger.info(f"Port: {config.get_port()}")
    logger.info(f"Peers: {config.get_peers()}")
    
    # Create and start node
    try:
        node = Node(config)
        node.start()
    except KeyboardInterrupt:
        logger.info("Shutting down node...")
        node.stop()
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()

