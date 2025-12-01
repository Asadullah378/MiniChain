"""Main entry point for MiniChain node."""

import sys
import argparse
from pathlib import Path

# Add src to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.common.config import Config
from src.common.logger import setup_logger
from src.node.node import Node
from src.cli.cli import CLI


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
    parser.add_argument(
        '--no-cli',
        action='store_true',
        help='Disable interactive CLI (run in background mode)'
    )
    parser.add_argument(
        '--log-level',
        type=str,
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
        help='Set logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)'
    )
    parser.add_argument(
        '--api-port',
        type=int,
        help='Port to run HTTP API server on'
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
    
    # Determine if CLI will be enabled
    cli_enabled = not args.no_cli
    
    # Override log level if specified
    log_level = args.log_level or config.get('logging.level', 'INFO')
    
    # Setup logger - disable console output if CLI is enabled
    logger = setup_logger(
        'minichain',
        level=log_level,
        log_file=config.get('logging.file'),
        console=config.get('logging.console', True) and not cli_enabled  # Disable console if CLI enabled
    )
    
    logger.info(f"Starting MiniChain node: {config.get_node_id()}")
    logger.info(f"Hostname: {config.get_hostname()}")
    logger.info(f"Port: {config.get_port()}")
    logger.info(f"Peers: {config.get_peers()}")
    
    # Create and start node
    try:
        node = Node(config, disable_console_logging=cli_enabled, log_level=log_level)
        
        # Start API server if requested
        api_server = None
        if args.api_port:
            from src.api.server import start_api_server
            logger.info(f"Starting API server on port {args.api_port}")
            api_server = start_api_server(node, args.api_port)
        
        # Start CLI in interactive mode (unless disabled)
        cli = None
        if cli_enabled:
            cli = CLI(node, log_file=config.get('logging.file'))
            cli.start()
        
        # Start node (this will block until interrupted)
        node.start()
        
        # Stop CLI when node stops
        if cli:
            cli.stop()
            
    except KeyboardInterrupt:
        logger.info("Shutting down node...")
        if 'node' in locals():
            node.stop()
        if 'cli' in locals():
            cli.stop()
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()

