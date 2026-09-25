# INFUSE — Getting Started Guide

Welcome to **INFUSE (Execution Intelligence)**. This guide will take you from zero to a fully running INFUSE server, governed execution tasks, and CLI/SDK interaction in under 5 minutes.

---

## 1. Prerequisites

- **Python:** Version `>= 3.10` (tested on 3.10, 3.11, 3.12, 3.13, 3.14)
- **Node.js (Optional):** Version `>= 18` (only needed if building or developing the frontend SPA)
- **Git:** For cloning the repository

---

## 2. Installation

Clone the repository and install the package in editable mode:

```bash
git clone https://github.com/adorbistech/infuse.git
cd infuse

# Install core package
pip install -e .
```

Verify the CLI is installed and check the version:

```bash
infuse version
```

You should see output similar to:
```text
INFUSE Execution Intelligence CLI
Version: 0.1.0
Schema Version: 1.0.0
```

---

## 3. Starting the Local Server

Launch the production-grade Starlette ASGI server using the registered console script:

```bash
infuse-server
```

Or run via Python module:

```bash
python3 -m infuse.deployment.server
```

The server binds to `http://0.0.0.0:8000` by default.

---

## 4. Operational Health Checks

Check server liveness:

```bash
curl http://localhost:8000/health
```

Check deep subsystem readiness (Event Bus, Governor, Registry, Repositories):

```bash
curl http://localhost:8000/ready
```

---

## 5. Submitting Your First Governed Task

Send an execution request via the REST API:

```bash
curl -X POST http://localhost:8000/v1/execute \
  -H "Content-Type: application/json" \
  -d '{
    "request_id": "req_getting_started_01",
    "task": {
      "task_id": "task_demo_01",
      "description": "Demonstrate execution governance",
      "workload_hint": "coding"
    },
    "request": {
      "messages": [{"role": "user", "content": "Write a Python hello world script."}],
      "parameters": {"temperature": 0.1}
    },
    "requirements": {
      "preferred_providers": ["MockProvider"]
    },
    "execution_context": {
      "agent_id": "OpenCode",
      "session_id": "sess_getting_started"
    }
  }'
```

The response includes the execution telemetry, normalized response, and the Governor's decision:

```json
{
  "execution_id": "exec_a1b2c3d4",
  "request_id": "req_getting_started_01",
  "status": "COMPLETED",
  "execution": {
    "provider": "MockProvider",
    "model": "mock-general-v1",
    "total_tokens": 45,
    "cost_usd": 0.000225,
    "state": "NORMAL"
  },
  "decision": {
    "action": "CONTINUE",
    "reason": "Execution within defined budget and latency thresholds."
  }
}
```

---

## 6. Using the Python SDK

Create a file `quickstart.py`:

```python
from infuse.sdk import InfuseClient, ExecutionRequest, TaskContext, OperationRequest

# Initialize client
client = InfuseClient(base_url="http://localhost:8000")

# Submit task
req = ExecutionRequest(
    request_id="req_sdk_01",
    task=TaskContext(task_id="task_sdk_demo", workload_hint="coding"),
    request=OperationRequest(messages=[{"role": "user", "content": "Calculate fibonacci(10)"}]),
)

result = client.execute(req)
print(f"Status: {result.status}")
print(f"Execution State: {result.execution.state}")
print(f"Governor Action: {result.decision.action}")
print(f"Cost USD: ${result.execution.cost_usd:.6f}")
```

Run it:
```bash
python3 quickstart.py
```

---

## 7. Next Steps

- Explore [Real-Time Agent Workflows](REALTIME_INTEGRATION.md) to place INFUSE around an agent loop.
- Review [Agent & Provider Integration Guide](INTEGRATION.md) for custom agent adapters.
- Inspect [Deployment Guide](deployment.md) for Docker Compose and containerization.
- Learn about [Policy Management](governor_engine.md) and declarative budgets.
