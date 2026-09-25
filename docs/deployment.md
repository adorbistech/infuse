# INFUSE — Deployment & Packaging Guide

This guide describes how to build, package, configure, containerize, and deploy **INFUSE (Execution Intelligence)** in self-hosted and production container environments.

---

## 1. Architecture Overview

INFUSE is distributed as a Python package (`infuse-ai`) and an accompanying web dashboard UI (`infuse-frontend`).

```
                              ┌────────────────────────┐
                              │   Reverse Proxy / LB   │
                              │      (TLS, 443)        │
                              └───────────┬────────────┘
                                          │
                     ┌────────────────────┴────────────────────┐
                     │                                         │
                     ▼                                         ▼
         ┌───────────────────────┐                 ┌───────────────────────┐
         │    infuse-frontend    │                 │    infuse-backend     │
         │   (Nginx SPA, :3000)  │ ──/v1 Proxy───► │  (Starlette API, :8000)│
         └───────────────────────┘                 └───────────┬───────────┘
                                                               │
                                                   ┌───────────┴───────────┐
                                                   │   Execution Engine    │
                                                   │  Governor / Control   │
                                                   └───────────────────────┘
```

The system provides three standard deployment models:
1. **Docker Compose (Recommended for Self-Hosting):** Full stack deployment with orchestrated backend API and frontend reverse proxy.
2. **Direct Container Deployment (Kubernetes / ECS):** Independent scaling of `infuse-backend` and `infuse-frontend` container images.
3. **Bare Metal / Virtual Environment Python Process:** Running `infuse-server` or CLI directly in a managed Python virtual environment.

---

## 2. Environment Variables & Configuration

All deployment configurations are managed via environment variables. Create a `.env` file based on `.env.example`.

| Variable | Type | Default | Description |
|---|---|---|---|
| `INFUSE_HOST` | `string` | `0.0.0.0` | Host IP address to bind HTTP API server. |
| `INFUSE_PORT` | `integer` | `8000` | Port number for the HTTP API server (1–65535). |
| `INFUSE_ENVIRONMENT` | `string` | `production` | Deployment environment (`production`, `staging`, `development`, `test`). |
| `INFUSE_LOG_LEVEL` | `string` | `INFO` | Logging level (`DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`). |
| `INFUSE_WORKERS` | `integer` | `1` | Number of worker processes (1–128). |
| `INFUSE_SHUTDOWN_TIMEOUT_SEC` | `float` | `15.0` | Graceful shutdown deadline before forcing termination. |
| `INFUSE_MAX_REQUEST_SIZE_BYTES`| `integer` | `10485760` | Maximum incoming request body size in bytes (default: 10MB). |
| `INFUSE_CORS_ORIGINS` | `string` | `*` | Comma-separated list of allowed CORS origin URLs or `*`. |
| `INFUSE_ENABLE_METRICS` | `boolean` | `true` | Enables system metrics and telemetry collection. |
| `INFUSE_ENABLE_READINESS_PROBE`| `boolean` | `true` | Enables `/ready` endpoint with deep subsystem probes. |
| `INFUSE_MCP_SERVER_ENABLED` | `boolean` | `false` | Enables MCP server sidecar integration. |
| `INFUSE_MCP_SERVER_PORT` | `integer` | `8001` | Port for optional MCP server sidecar. |
| `INFUSE_STORAGE_BACKEND` | `string` | `inmemory` | Persistence backend type (`inmemory`, `filesystem`). |
| `INFUSE_STORAGE_PATH` | `string` | `None` | Directory path for filesystem persistence. |

---

## 3. Quickstart: Docker Compose

To deploy INFUSE with Docker Compose:

```bash
# 1. Clone repository and navigate to root
cd infuse

# 2. Copy environment template
cp .env.example .env

# 3. Build and launch services
docker compose up -d --build

# 4. Verify running services
docker compose ps
```

Services will be available at:
- **Web Dashboard UI:** `http://localhost:3000`
- **HTTP API:** `http://localhost:8000`
- **API Health Endpoint:** `http://localhost:8000/health`
- **System Readiness Probe:** `http://localhost:8000/ready`

---

## 4. Container Build & Packaging

### Backend Container Image
The backend uses a multi-stage Dockerfile creating a minimal, non-root runtime image:

```bash
# Build backend image
docker build -t infuse-backend:latest -f Dockerfile .

# Run backend container
docker run -d \
  --name infuse-backend \
  -p 8000:8000 \
  --read-only \
  --tmpfs /tmp \
  infuse-backend:latest
```

### Frontend Container Image
```bash
# Build frontend image
docker build -t infuse-frontend:latest -f Dockerfile.frontend .

# Run frontend container
docker run -d \
  --name infuse-frontend \
  -p 3000:3000 \
  infuse-frontend:latest
```

### Python Wheel Packaging
```bash
# Build distribution wheel and sdist
python -m build

# Install built wheel
pip install dist/infuse_ai-0.1.0-py3-none-any.whl
```

---

## 5. Health, Readiness, and Lifecycle

INFUSE distinguishes between process liveness, deep system readiness, and graceful shutdown:

### Liveness Probe (`GET /health`)
- **Status Code:** `200 OK`
- **Response:**
  ```json
  {
    "status": "OK",
    "version": "0.1.0",
    "schema_version": "1.0.0"
  }
  ```

### Readiness Probe (`GET /ready` or `GET /v1/ready`)
- **Status Code:** `200 OK` (when ready) or `503 Service Unavailable` (when unready/shutting down)
- **Response:**
  ```json
  {
    "status": "READY",
    "version": "0.1.0",
    "schema_version": "1.0.0",
    "uptime_seconds": 124.5,
    "checks": {
      "execution_service": "OK",
      "event_service": "OK",
      "policy_service": "OK"
    },
    "timestamp": "2026-09-26T01:50:00Z"
  }
  ```

### Graceful Shutdown
Upon receiving `SIGTERM` or `SIGINT`:
1. Readiness probe immediately flips to `UNREADY` (`503 Service Unavailable`), instructing load balancers to cease sending new traffic.
2. In-flight execution tasks finish within `INFUSE_SHUTDOWN_TIMEOUT_SEC` (default: 15s).
3. Subprocesses and event buses are safely flushed.

---

## 6. Kubernetes Deployment Guidelines

### Recommended Pod Specification
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: infuse-backend
  labels:
    app: infuse-backend
spec:
  replicas: 2
  selector:
    matchLabels:
      app: infuse-backend
  template:
    metadata:
      labels:
        app: infuse-backend
    spec:
      securityContext:
        runAsNonRoot: true
        runAsUser: 10001
        runAsGroup: 10001
        fsGroup: 10001
      containers:
      - name: infuse-backend
        image: infuse-backend:0.1.0
        ports:
        - containerPort: 8000
          name: http
        envFrom:
        - configMapRef:
            name: infuse-config
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 15
        readinessProbe:
          httpGet:
            path: /ready
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 10
        resources:
          requests:
            cpu: "250m"
            memory: "256Mi"
          limits:
            cpu: "1000m"
            memory: "1024Mi"
```

---

## 7. Production Security Checklist

- [x] **Non-Root Execution:** Container runs as unprivileged user (`UID 10001`).
- [x] **Zero Hardcoded Secrets:** Configuration purely externalized via environment variables.
- [x] **Secret Redaction:** Bearer tokens and API keys are automatically scrubbed from logs and errors.
- [x] **Subprocess Security:** Agent adapters invoke child processes strictly via `shell=False` argv lists.
- [x] **API Boundary Isolation:** Error middleware catches unhandled exceptions without leaking stack traces.
- [x] **Read-Only Root Filesystem:** Container supports `--read-only` mode with `/tmp` tmpfs mount.
- [x] **Minimal Attack Surface:** Multi-stage build eliminates build tools and dev dependencies from runtime image.
