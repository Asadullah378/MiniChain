# MiniChain Docker Deployment Guide

This guide explains how to run MiniChain API and frontend using Docker and Docker Compose, locally and on a public server.

## Prerequisites

- Docker 24+ and Docker Compose (`docker compose` CLI)
- Cloned repository with these files:
  - `Dockerfile.api`
  - `frontend/Dockerfile`
  - `frontend/nginx.conf`
  - `docker-compose.yml`
  - `peers.txt`, `config.yaml`, `data/` (created by you)

## Services Overview

- `api` (Python): Runs MiniChain node and FastAPI, listens on `8080`.
- `frontend` (Nginx): Serves built React app on port `5173` (host), container `80`.
- `VITE_API_URL`: Frontend uses this to call the API.

## Quick Start (Local Machine)

```bash
# From repo root
VITE_API_URL="http://localhost:8080" \
  docker compose up --build
```

- Open frontend: `http://localhost:5173`
- API health: `http://localhost:8080/status`

## Configuration

- `peers.txt`: List peers as `hostname:port` (mounted read-only into `api`).
- `config.yaml`: Node configuration (mounted read-only into `api`).
- `data/`: Blockchain data volume (persisted on host).
- Environment variables (override in shell or `.env`):
  - `NODE_HOSTNAME` (default `svm-11.cs.helsinki.fi`)
  - `API_PORT` (default `8080`)
  - `CLEAN` (default `false`)
  - `VITE_API_URL` (default `http://localhost:8080` in compose build args)

## Common Commands

```bash
# Rebuild only frontend
VITE_API_URL="http://localhost:8080" docker compose build frontend

# Recreate containers
docker compose up -d --force-recreate

# Tail logs
docker compose logs -f api
docker compose logs -f frontend

# Stop and remove containers
docker compose down
```

## Using Relative /api Routing (Optional)

If you prefer the frontend to call relative paths instead of `VITE_API_URL`, uncomment the `/api/` block in `frontend/nginx.conf` and update the frontend to use `/api/...`. Then build and run:

```bash
docker compose up --build
```

This proxies `frontend` → `api` internally without exposing API origin to the browser.

## Public Server Deployment (Single VM)

1. Provision a VM (AWS/GCP/Azure) and point DNS to it.
2. Open firewall: allow `80` (and `443` if using TLS).
3. Set environment and run in detached mode:

```bash
# Example using absolute API URL
VITE_API_URL="https://your-domain.com/api" \
  docker compose up -d --build
```

4. Add a reverse proxy for TLS (recommended):
   - Option A: Run an external Nginx/Caddy on the VM to terminate TLS and route `/` to `frontend`, `/api/` to `api`.
   - Option B: Add a `proxy` service in compose (see commented section in `docker-compose.yml`) and mount your gateway config + certs.

## University VMs (svm-11\*)

- These hosts are restricted to UH network; public exposure is typically blocked.
- Use VPN + SSH jump host and local port forwarding:

```bash
ssh -L 5173:localhost:5173 -L 8080:localhost:8080 \
  -J vienha@melkki.cs.helsinki.fi vienha@svm-11.cs.helsinki.fi
```

- Start compose on `svm-11`, then access from your laptop at `http://localhost:5173` and `http://localhost:8080/status`.

## Troubleshooting

- Frontend cannot reach API:
  - Ensure `VITE_API_URL` points to reachable origin.
  - Check CORS (FastAPI allows `*` by default here; tighten in production).
- Ports busy:
  - Change host ports in `docker-compose.yml` (e.g., `5174:80`, `8081:8080`).
- Data not persisting:
  - Verify `./data` exists and is mounted to `/app/data` in `api`.

## Clean Deploy

```bash
# Remove containers
docker compose down
# Rebuild images and start fresh
VITE_API_URL="http://localhost:8080" docker compose up --build
```

## Notes

- For production, restrict CORS and validate inputs.
- Consider `.env` files for environment variables instead of inline shell exports.
- Use TLS everywhere when exposed to the Internet.
