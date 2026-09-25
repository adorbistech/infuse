"""OpenAPI 3.1.0 Schema Generator and ChatGPT Action Manifest for INFUSE."""

from typing import Any, Dict
from infuse.version import SCHEMA_VERSION, __version__


def generate_openapi_schema(server_url: str = "https://api.infuse.adorbistech.com") -> Dict[str, Any]:
    """Generate OpenAPI 3.1.0 specification tailored for ChatGPT Apps and Custom GPT Actions."""
    return {
        "openapi": "3.1.0",
        "info": {
            "title": "INFUSE — Execution Intelligence for Autonomous AI Agents",
            "description": (
                "Official ChatGPT App integration for INFUSE. Enables autonomous agent monitoring, "
                "cost/token telemetry analysis, real-time Governor inspection, and governed task execution."
            ),
            "version": __version__,
        },
        "servers": [
            {
                "url": server_url,
                "description": "Production INFUSE ChatGPT Action Gateway",
            }
        ],
        "paths": {
            "/chatgpt/v1/system": {
                "get": {
                    "operationId": "get_system_info",
                    "summary": "Get INFUSE system status and capabilities",
                    "description": "Retrieves version info, health status, registered agents, and active governance policy.",
                    "responses": {
                        "200": {
                            "description": "System status response",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/ToolResponseEnvelope"}
                                }
                            },
                        }
                    },
                    "security": [{"BearerAuth": []}],
                }
            },
            "/chatgpt/v1/executions": {
                "get": {
                    "operationId": "list_executions",
                    "summary": "List executions with filtering and pagination",
                    "description": "Returns execution telemetry records filtered by state (NORMAL, COST_PRESSURE, RUNAWAY, QUALITY_DEGRADED, PROVIDER_CONSTRAINED) or agent.",
                    "parameters": [
                        {"name": "query", "in": "query", "required": False, "schema": {"type": "string"}, "description": "Search keyword"},
                        {"name": "state", "in": "query", "required": False, "schema": {"type": "string"}, "description": "Canonical execution state"},
                        {"name": "agent", "in": "query", "required": False, "schema": {"type": "string"}, "description": "Agent adapter name"},
                        {"name": "limit", "in": "query", "required": False, "schema": {"type": "integer", "default": 20}, "description": "Max records"},
                        {"name": "offset", "in": "query", "required": False, "schema": {"type": "integer", "default": 0}, "description": "Offset"},
                    ],
                    "responses": {
                        "200": {
                            "description": "List of executions",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/ToolResponseEnvelope"}
                                }
                            },
                        }
                    },
                    "security": [{"BearerAuth": []}],
                }
            },
            "/chatgpt/v1/executions/{execution_id}/state": {
                "get": {
                    "operationId": "get_execution_state",
                    "summary": "Inspect real-time execution state",
                    "description": "Returns the active execution state (e.g. NORMAL, COST_PRESSURE, RUNAWAY) and reason code for an execution.",
                    "parameters": [
                        {"name": "execution_id", "in": "path", "required": True, "schema": {"type": "string"}, "description": "Execution ID"}
                    ],
                    "responses": {
                        "200": {
                            "description": "Execution state snapshot",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/ToolResponseEnvelope"}
                                }
                            },
                        }
                    },
                    "security": [{"BearerAuth": []}],
                }
            },
            "/chatgpt/v1/executions/{execution_id}/result": {
                "get": {
                    "operationId": "get_execution_result",
                    "summary": "Get execution result and telemetry",
                    "description": "Retrieves token counts, cost breakdown, latency metrics, and final assistant response.",
                    "parameters": [
                        {"name": "execution_id", "in": "path", "required": True, "schema": {"type": "string"}, "description": "Execution ID"}
                    ],
                    "responses": {
                        "200": {
                            "description": "Execution result telemetry",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/ToolResponseEnvelope"}
                                }
                            },
                        }
                    },
                    "security": [{"BearerAuth": []}],
                }
            },
            "/chatgpt/v1/executions/{execution_id}/inspect": {
                "get": {
                    "operationId": "inspect_execution",
                    "summary": "Detailed execution inspection & anomaly breakdown",
                    "description": "Comprehensive analysis of execution metrics, anomaly flags, state transitions, and Governor regulation history.",
                    "parameters": [
                        {"name": "execution_id", "in": "path", "required": True, "schema": {"type": "string"}, "description": "Execution ID"}
                    ],
                    "responses": {
                        "200": {
                            "description": "Comprehensive execution inspection report",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/ToolResponseEnvelope"}
                                }
                            },
                        }
                    },
                    "security": [{"BearerAuth": []}],
                }
            },
            "/chatgpt/v1/executions/{execution_id}/governor": {
                "get": {
                    "operationId": "inspect_governor_decision",
                    "summary": "Inspect Governor regulation decision",
                    "description": "Retrieves the authoritative Governor decision (CONTINUE, OPTIMIZE, ESCALATE, DOWNGRADE, SWITCH, THROTTLE, STOP) and rule evaluation reason.",
                    "parameters": [
                        {"name": "execution_id", "in": "path", "required": True, "schema": {"type": "string"}, "description": "Execution ID"}
                    ],
                    "responses": {
                        "200": {
                            "description": "Governor decision detail",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/ToolResponseEnvelope"}
                                }
                            },
                        }
                    },
                    "security": [{"BearerAuth": []}],
                }
            },
            "/chatgpt/v1/providers/health": {
                "get": {
                    "operationId": "get_provider_health",
                    "summary": "Check provider health & latency status",
                    "description": "Reports operational status and latency for all registered AI providers.",
                    "responses": {
                        "200": {
                            "description": "Provider health overview",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/ToolResponseEnvelope"}
                                }
                            },
                        }
                    },
                    "security": [{"BearerAuth": []}],
                }
            },
            "/chatgpt/v1/policies": {
                "get": {
                    "operationId": "list_policies",
                    "summary": "List governance policies",
                    "description": "Lists all available policies and indicates the active governance policy.",
                    "responses": {
                        "200": {
                            "description": "Policy listing",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/ToolResponseEnvelope"}
                                }
                            },
                        }
                    },
                    "security": [{"BearerAuth": []}],
                }
            },
            "/chatgpt/v1/policies/{policy_id}": {
                "get": {
                    "operationId": "get_policy",
                    "summary": "Get governance policy details",
                    "description": "Retrieves budget limits, token caps, and action thresholds for a specific policy.",
                    "parameters": [
                        {"name": "policy_id", "in": "path", "required": True, "schema": {"type": "string"}, "description": "Policy ID"}
                    ],
                    "responses": {
                        "200": {
                            "description": "Policy detail response",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/ToolResponseEnvelope"}
                                }
                            },
                        }
                    },
                    "security": [{"BearerAuth": []}],
                }
            },
            "/chatgpt/v1/execute": {
                "post": {
                    "operationId": "execute_task",
                    "summary": "Execute governed task",
                    "description": "Submits a task to be processed under active INFUSE governance and execution intelligence.",
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/ExecuteTaskInput"}
                            }
                        },
                    },
                    "responses": {
                        "200": {
                            "description": "Governed execution result",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/ToolResponseEnvelope"}
                                }
                            },
                        }
                    },
                    "security": [{"BearerAuth": []}],
                }
            },
            "/chatgpt/v1/control": {
                "post": {
                    "operationId": "control_execution",
                    "summary": "Dispatch governed control action",
                    "description": "Dispatches a control command (STOP, THROTTLE, SWITCH, CONTINUE) strictly through the Execution Control Boundary.",
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/ControlExecutionInput"}
                            }
                        },
                    },
                    "responses": {
                        "200": {
                            "description": "Control result response",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/ToolResponseEnvelope"}
                                }
                            },
                        }
                    },
                    "security": [{"BearerAuth": []}],
                }
            },
        },
        "components": {
            "schemas": {
                "ToolResponseEnvelope": {
                    "type": "object",
                    "required": ["success", "tool_name", "category"],
                    "properties": {
                        "success": {"type": "boolean"},
                        "tool_name": {"type": "string"},
                        "category": {"type": "string", "enum": ["READ", "ANALYZE", "EXECUTE", "CONTROL"]},
                        "data": {"type": "object"},
                        "error": {"type": "string", "nullable": True},
                        "error_code": {"type": "string", "nullable": True},
                        "ui_card": {"type": "object", "nullable": True},
                    },
                },
                "ExecuteTaskInput": {
                    "type": "object",
                    "required": ["task_description"],
                    "properties": {
                        "task_description": {"type": "string"},
                        "prompt": {"type": "string"},
                        "workload_hint": {"type": "string", "default": "general"},
                        "preferred_provider": {"type": "string"},
                        "preferred_model": {"type": "string"},
                        "temperature": {"type": "number", "default": 0.2},
                    },
                },
                "ControlExecutionInput": {
                    "type": "object",
                    "required": ["execution_id", "action"],
                    "properties": {
                        "execution_id": {"type": "string"},
                        "action": {"type": "string", "enum": ["STOP", "THROTTLE", "SWITCH", "CONTINUE"]},
                        "reason": {"type": "string"},
                        "delay_ms": {"type": "integer"},
                        "target_model": {"type": "string"},
                    },
                },
            },
            "securitySchemes": {
                "BearerAuth": {
                    "type": "http",
                    "scheme": "bearer",
                    "bearerFormat": "JWT",
                    "description": "Enter your INFUSE API Token (or OAuth2 Access Token).",
                }
            },
        },
    }
