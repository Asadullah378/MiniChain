# MiniChain Pytest Guide

This document explains how to run and extend the automated test suite for MiniChain.

## Prerequisites

1. Python 3.11+ recommended (minimum 3.8).
2. Project virtual environment created via `setup.sh` (`.venv/` in repo root).
3. Dependencies installed from `requirements.txt` (includes `pytest`, `msgpack`, `cryptography`, etc.).

If you need to set up from scratch:

```bash
chmod +x setup.sh
./setup.sh
```

## Running the Test Suite

Activate the project virtual environment first:

```bash
source .venv/bin/activate
```

Then run pytest from the repository root so the `pytest.ini` (which adds the root to `PYTHONPATH`) is honored:

```bash
python -m pytest
```

Useful flags:

- `python -m pytest -k quorum` – run tests whose names match `quorum`.
- `python -m pytest tests/test_poa.py -vv` – verbose output for a single module.
- `python -m pytest --maxfail=1` – stop on first failure.

## Test Layout

```
tests/
├── test_block.py        # Transaction/block serialization and determinism
├── test_blockchain.py   # Persistence and validation checks
├── test_mempool.py      # Mempool dedupe and removal semantics
└── test_poa.py          # Round-robin PoA leader rotation, quorum, commit state
```

`pytest.ini` pins the project root on `PYTHONPATH` and enables concise `-ra` summaries.

## Writing New Tests

1. Place new test modules under `tests/` with filenames that start with `test_`.
2. Import modules using `from src...` thanks to `pytest.ini`.
3. Prefer focused unit tests that operate on in-memory structures; rely on `tmp_path` for filesystem isolation.
4. When touching networking or node orchestration, consider using dependency injection/mocks to avoid real sockets.

### Example Skeleton

```python
from src.node.node import Node

def test_custom_behavior(tmp_path):
    # Arrange
    ...
    # Act
    ...
    # Assert
    ...
```

## CI / Quality Gate

Before merges or milestone demos, ensure:

1. `python -m pytest` passes on a clean workspace.
2. New features include tests covering the behavior or regressions addressed.
3. Documentation (`README.md`, `docs/ARCHITECTURE.md`, `PRD.md`) references the updated testing expectations if scope changes.

## Troubleshooting

- **ImportError (msgpack/cryptography)**: Run `pip install -r requirements.txt` inside `.venv`.
- **Tests not discovered**: Ensure files are named `test_*.py` and the repo root is current working directory.
- **Path issues**: `pytest.ini` sets `pythonpath = .`; confirm you are not running pytest from a subdirectory.

For additional context on architecture and requirements, see `docs/ARCHITECTURE.md` and `PRD.md`.
