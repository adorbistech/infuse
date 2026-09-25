# ==============================================================================
# INFUSE — Execution Intelligence: Production Backend Container Image
# Multi-stage, minimal runtime, non-root user execution
# ==============================================================================

# --- Stage 1: Build & Package Wheels ---
FROM python:3.11-slim AS builder

WORKDIR /build

# Install build dependencies
RUN pip install --no-cache-dir --upgrade pip build wheel setuptools

# Copy project manifest and source code
COPY pyproject.toml README.md LICENSE ./
COPY infuse/ ./infuse/

# Build wheel package
RUN python -m build --wheel --no-isolation

# --- Stage 2: Final Minimal Production Runtime ---
FROM python:3.11-slim AS runtime

# Security: Create non-root user and group (UID 10001)
RUN groupadd -g 10001 infuse && \
    useradd -u 10001 -g infuse -d /app -s /sbin/nologin -M infuse

WORKDIR /app

# Copy built wheel from builder stage
COPY --from=builder /build/dist/*.whl /tmp/

# Install application and production runtime dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir /tmp/*.whl uvicorn "mcp>=1.0.0,<2.0.0" && \
    rm -rf /tmp/*.whl

# Switch to unprivileged non-root user
USER infuse

# Expose HTTP API port
EXPOSE 8000

# Container environment defaults
ENV INFUSE_HOST="0.0.0.0" \
    INFUSE_PORT="8000" \
    INFUSE_ENVIRONMENT="production" \
    INFUSE_LOG_LEVEL="INFO" \
    PYTHONUNBUFFERED="1" \
    PYTHONDONTWRITEBYTECODE="1"

# Healthcheck configuration using standard library urllib
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD python3 -c "import urllib.request, sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/health').getcode() == 200 else 1)"

# Signal handling for graceful termination
STOPSIGNAL SIGTERM

# Default command entrypoint
ENTRYPOINT ["infuse-server"]
