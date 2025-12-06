# MiniChain TODO

## ✅ Completed

- [x] **Core P2P Transport**: Listener, outbound connectors, HELLO handshake.
- [x] **Consensus Engine**: Round-robin PoA pipeline (propose → ACK → commit).
- [x] **Persistence**: On-disk chain persistence + deterministic genesis validation.
- [x] **Basic API**: FastAPI server with status, blocks, and mempool endpoints.
- [x] **Frontend Dashboard**: React-based dashboard with real-time status polling.
- [x] **Transaction Submission**: Dedicated "Send Transaction" page and flow.

---

## 🚀 Backend Improvements

### API & Server (`src/api/server.py`)
- [x] **Structured Error Handling**: Replace generic `HTTPException` with a custom error handler to return consistent JSON error responses (e.g., `{"error": "code", "message": "..."}`).
- [x] **Remove Global State**: Refactor `server.py` to avoid using the global `node` variable. Pass the node instance via dependency injection or app state.
- [x] **Disable Debug Endpoints**: specific `/debug/*` endpoints should be disabled in production or protected by a flag/auth.
- [ ] **Pagination**: Implement proper pagination for `/blocks` and `/mempool` (currently hardcoded limit=10).
- [ ] **Input Validation**: Enhance `TransactionModel` validation (e.g., prevent negative amounts, enforce address format).

### Core Logic
- [ ] **Decimal Precision**: Stop using `float` for transaction amounts. Use `Decimal` or integer subunits (satoshis) to avoid floating-point errors.
- [ ] **Graceful Shutdown**: Improve signal handling to ensure the API server and Node threads shut down cleanly.
- [ ] **Configuration**: Add validation for `config.yaml` loading.

### Testing
- [ ] **Integration Tests**: Add real integration tests that spin up a node and test API endpoints without mocking internal components.
- [ ] **Unit Tests**: Increase coverage for `consensus` and `p2p` modules.

---

## 🎨 Frontend Improvements

### UI/UX

- [x] **Transaction Details**: Add a dedicated page to view transaction details (by ID).

---

## 🔐 Protocol & Consensus (Backlog)

*From previous roadmap*

- [ ] **M3 – Fault Handling & Sync**: Implement leader timeout + VIEWCHANGE path.
- [ ] **M4 – Observability**: Metrics/health endpoint exposing block time + mempool size.
- [ ] **Signatures**: Sign and verify ACK/COMMIT messages using `src/common/crypto.KeyPair`.
- [ ] **Sync**: Finish header/block sync (`send_headers`, `send_block`).
- [ ] **Network**: Retry/backoff strategy for outbound connections.

---

## 🛠 DevOps & Tooling

- [ ] **Docker**: Optimize `Dockerfile.api` for smaller image size (multi-stage build).
- [ ] **CI/CD**: Add GitHub Actions workflow for running tests and linting.
- [ ] **Linting**: Enforce `flake8` or `ruff` for Python and `eslint` for JavaScript.
