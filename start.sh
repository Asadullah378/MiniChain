#!/bin/bash
# Start script for MiniChain node
# Usage: ./start.sh <hostname> [--clean]
#   hostname: The hostname of this node (must match one in peers.txt) - REQUIRED
#   --clean:  Optional flag to clear data and logs before starting
#
# Example: ./start.sh svm-11.cs.helsinki.fi
# Example: ./start.sh svm-11.cs.helsinki.fi --clean

set -e  # Exit on error

# Parse arguments
CLEAN_DATA=false
NODE_HOSTNAME=""

EXTRA_ARGS=()

for arg in "$@"; do
    if [ "$arg" == "--clean" ] || [ "$arg" == "-c" ]; then
        CLEAN_DATA=true
    elif [ -z "$NODE_HOSTNAME" ] && [[ "$arg" != -* ]]; then
        # First non-flag argument is hostname
        NODE_HOSTNAME="$arg"
    else
        # Collect other arguments to pass to python script
        EXTRA_ARGS+=("$arg")
    fi
done

# Validate hostname is provided
if [ -z "$NODE_HOSTNAME" ]; then
    echo "ERROR: Hostname is required!"
    echo ""
    echo "Usage: ./start.sh <hostname> [--clean]"
    echo ""
    echo "Example: ./start.sh svm-11.cs.helsinki.fi"
    echo "Example: ./start.sh svm-11.cs.helsinki.fi --clean"
    exit 1
fi

# Clean data and logs if requested
if [ "$CLEAN_DATA" = true ]; then
    echo "Cleaning data and logs..."
    
    # Remove blockchain data
    if [ -d "data" ]; then
        rm -rf data/*
        echo "✓ Cleared data directory"
    fi
    
    # Remove log files
    if [ -f "minichain.log" ]; then
        rm -f minichain.log
        echo "✓ Removed log file"
    fi
    
    # Remove any other log files
    rm -f *.log 2>/dev/null || true
    
    echo "✓ Cleanup complete"
    echo ""
fi

# Activate virtual environment if it exists
if [ -d ".venv" ]; then
    source .venv/bin/activate
elif [ -d "venv" ]; then
    source venv/bin/activate
fi

# Use the provided hostname
CURRENT_HOSTNAME="$NODE_HOSTNAME"
CURRENT_SHORT=$(echo "$NODE_HOSTNAME" | cut -d'.' -f1)

echo "Using hostname: $CURRENT_HOSTNAME"
echo ""

# Check if peers file exists
if [ ! -f "peers.txt" ]; then
    echo "ERROR: peers.txt file not found!"
    echo "Please create peers.txt with all peers in format: hostname:port"
    echo "Example:"
    echo "  svm-11.cs.helsinki.fi:8000"
    echo "  svm-11-2.cs.helsinki.fi:8000"
    echo "  svm-11-3.cs.helsinki.fi:8000"
    exit 1
fi

# Read peers from file
ALL_PEERS=()
while IFS= read -r line || [ -n "$line" ]; do
    # Skip empty lines and comments
    line=$(echo "$line" | sed 's/#.*//' | xargs)
    if [ -n "$line" ]; then
        ALL_PEERS+=("$line")
    fi
done < peers.txt

if [ ${#ALL_PEERS[@]} -eq 0 ]; then
    echo "ERROR: No peers found in peers.txt"
    exit 1
fi

echo "Found ${#ALL_PEERS[@]} peer(s) in peers.txt:"
for peer in "${ALL_PEERS[@]}"; do
    echo "  - $peer"
done
echo ""

# Find current node in peers list and determine other peers
NODE_ID=""
PEERS_LIST=""
FOUND=false

for peer in "${ALL_PEERS[@]}"; do
    peer_hostname=$(echo "$peer" | cut -d':' -f1)
    peer_short=$(echo "$peer_hostname" | cut -d'.' -f1)
    
    # Check if this peer is the current machine
    if [ "$peer_hostname" == "$CURRENT_HOSTNAME" ] || \
       [ "$peer_short" == "$CURRENT_SHORT" ] || \
       [ "$CURRENT_HOSTNAME" == "$peer_hostname" ] || \
       [ "$CURRENT_HOSTNAME" == "$peer_short" ]; then
        # This is the current machine
        NODE_ID="$peer_hostname"
        FOUND=true
        echo "✓ Identified as: $NODE_ID"
    else
        # This is a peer (not self)
        if [ -n "$PEERS_LIST" ]; then
            PEERS_LIST="$PEERS_LIST,$peer"
        else
            PEERS_LIST="$peer"
        fi
    fi
done

if [ "$FOUND" = false ]; then
    echo "ERROR: Hostname '$CURRENT_HOSTNAME' not found in peers.txt"
    echo ""
    echo "Available peers in peers.txt:"
    for peer in "${ALL_PEERS[@]}"; do
        echo "  - $peer"
    done
    echo ""
    echo "Please provide a valid hostname that matches one in peers.txt"
    echo "Usage: ./start.sh <hostname> [--clean]"
    exit 1
fi

echo "Node ID: $NODE_ID"
echo "Peers: $PEERS_LIST"
echo ""

# Extract port (default 8000)
PORT=$(echo "$PEERS_LIST" | cut -d',' -f1 | cut -d':' -f2)
if [ -z "$PORT" ] || [ "$PORT" == "$PEERS_LIST" ]; then
    PORT=8000
fi

# Check if config file exists
CONFIG_FILE="config.yaml"
if [ ! -f "$CONFIG_FILE" ]; then
    echo "WARNING: config.yaml not found, using defaults"
    CONFIG_FILE=""
fi

# Start the node
echo "Starting MiniChain node..."
echo "=========================================="
echo ""

# Determine python executable
PYTHON="python3"
if [ ! -f "/.dockerenv" ]; then
    if [ -d ".venv" ]; then
        PYTHON=".venv/bin/python3"
    elif [ -d "venv" ]; then
        PYTHON="venv/bin/python3"
    fi
fi




if [ -n "$CONFIG_FILE" ]; then
    $PYTHON src/main.py \
        --config "$CONFIG_FILE" \
        --node-id "$NODE_ID" \
        --port "$PORT" \
        --peers "$PEERS_LIST" \
        "${EXTRA_ARGS[@]}"
else
    $PYTHON src/main.py \
        --node-id "$NODE_ID" \
        --port "$PORT" \
        --peers "$PEERS_LIST" \
        "${EXTRA_ARGS[@]}"
fi

