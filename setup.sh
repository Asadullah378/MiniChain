#!/bin/bash
# Setup script for MiniChain
# Installs dependencies and creates necessary directories

echo "Setting up MiniChain..."

# Check Python version
python_version=$(python3 --version 2>&1 | awk '{print $2}')
echo "Python version: $python_version"

# Create virtual environment (optional but recommended)
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate 2>/dev/null || true

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# Create data directory
mkdir -p data

# Make run script executable
chmod +x run_node.sh 2>/dev/null || true

echo "Setup complete!"
echo ""
echo "To run a node, use:"
echo "  python src/main.py --node-id <id> --port <port> --peers <peer1>,<peer2>,..."
echo "Or use the helper script:"
echo "  ./run_node.sh <node_id> <port> <peer1> <peer2> ..."

