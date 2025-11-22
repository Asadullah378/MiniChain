#!/bin/bash
# Helper script to run a MiniChain node
# Usage: ./run_node.sh [node_id] [port] [peer1] [peer2] ...

NODE_ID=${1:-$(hostname)}
PORT=${2:-8000}
PEERS=${3:-""}

# Build peers string from remaining arguments
if [ -z "$PEERS" ] && [ $# -gt 3 ]; then
    shift 2
    PEERS=$(IFS=','; echo "$*")
fi

echo "Starting MiniChain node:"
echo "  Node ID: $NODE_ID"
echo "  Port: $PORT"
echo "  Peers: $PEERS"
echo ""

python src/main.py \
    --node-id "$NODE_ID" \
    --port "$PORT" \
    --peers "$PEERS"

