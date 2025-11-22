# Quick Start Guide

This guide will help you quickly set up and run MiniChain nodes on your three VMs.

## Prerequisites

- Python 3.8+ installed on all VMs
- Network connectivity between VMs
- SSH access to all three VMs

## Setup Steps

### 1. On Each VM, Clone and Setup

```bash
# Clone the repository (or copy files)
cd ~
git clone <your-repo-url> MiniChain
cd MiniChain

# Install dependencies
pip3 install -r requirements.txt

# Or use the setup script
chmod +x setup.sh
./setup.sh
```

### 2. Run Nodes

The easiest way is to use command-line arguments. The node will auto-detect its hostname.

#### On svm-11.cs.helsinki.fi:

```bash
python3 src/main.py \
  --node-id svm-11 \
  --port 8000 \
  --peers "svm-11-2.cs.helsinki.fi:8000,svm-11-3.cs.helsinki.fi:8000"
```

#### On svm-11-2.cs.helsinki.fi:

```bash
python3 src/main.py \
  --node-id svm-11-2 \
  --port 8000 \
  --peers "svm-11.cs.helsinki.fi:8000,svm-11-3.cs.helsinki.fi:8000"
```

#### On svm-11-3.cs.helsinki.fi:

```bash
python3 src/main.py \
  --node-id svm-11-3 \
  --port 8000 \
  --peers "svm-11.cs.helsinki.fi:8000,svm-11-2.cs.helsinki.fi:8000"
```

### 3. Alternative: Using Environment Variables

You can also set environment variables:

```bash
export NODE_ID="svm-11"
export NODE_PORT=8000
export PEERS="svm-11-2.cs.helsinki.fi:8000,svm-11-3.cs.helsinki.fi:8000"
python3 src/main.py
```

### 4. Alternative: Using Configuration File

Create a `config.yaml` file on each VM:

```yaml
node:
  id: "svm-11"  # Change for each VM
  hostname: "svm-11.cs.helsinki.fi"  # Change for each VM
  port: 8000

network:
  peers:
    - hostname: "svm-11-2.cs.helsinki.fi"
      port: 8000
    - hostname: "svm-11-3.cs.helsinki.fi"
      port: 8000
```

Then run:
```bash
python3 src/main.py
```

## Verification

Once all nodes are running, you should see:
- Connection messages in the logs
- Nodes discovering each other
- Consensus messages (PROPOSE, ACK, COMMIT) when blocks are created

## Troubleshooting

### Port Already in Use
If port 8000 is in use, change it:
```bash
python3 src/main.py --port 8001
```
(And update peer configurations accordingly)

### Connection Refused
- Check firewall settings
- Verify hostnames are resolvable: `ping svm-11-2.cs.helsinki.fi`
- Ensure nodes are started in the correct order (they'll retry connections)

### Hostname Detection
The node auto-detects hostname. To override:
```bash
python3 src/main.py --node-id custom-id
```

## Next Steps

- Add transactions (CLI interface coming soon)
- Monitor blockchain state
- Test fault tolerance (kill leader, restart node)

