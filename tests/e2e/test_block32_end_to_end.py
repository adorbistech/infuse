"""INFUSE Block 32 — 11 Mandatory End-to-End Scenarios.

Verifies:
- Scenario 1: Normal execution (Request -> policy -> routing -> agent -> events -> observers -> NORMAL -> CONTINUE)
- Scenario 2: Cost pressure (telemetry -> NORMAL -> COST_PRESSURE -> Governor -> Control Boundary -> audit)
- Scenario 3: Runaway execution (velocity -> RUNAWAY -> observer -> state engine -> governor -> STOP -> control boundary)
- Scenario 4: Provider failure (ProviderError -> event bus -> health/state -> Governor -> policy response)
- Scenario 5: Unsupported control (adapter capability check -> UNSUPPORTED -> audit/event)
- Scenario 6: Tool activity (ToolCalled, ToolCompleted -> observers -> state)
- Scenario 7: Web activity (WebRequest, WebResponse -> normalization, correlation, observer)
- Scenario 8: Retry/provider error sequence (RetryStarted, ProviderError, RetryStarted, ExecutionCompleted)
- Scenario 9: SDK execution (InfuseClient with in-process transport -> execution -> events -> governor -> state)
- Scenario 10: CLI execution (Infuse CLI -> SDK -> Core)
- Scenario 11: MCP execution (MCP server -> SDK/core boundary -> execution -> events -> state/governor)
"""

import asyncio
import io
import json
import unittest
import uuid
from unittest.mock import patch

from infuse.api.app import create_app
from infuse.cli.main import run_cli
from infuse.contracts.control import ControlCapability, ControlOperation, ControlStatus
from infuse.contracts.events import EventSource, EventType, ExecutionEvent
from infuse.contracts.execution import (
    ExecutionContext,
    ExecutionRequirements,
    ExecutionRequest,
    NormalizedResponse,
    OperationRequest,
    TaskContext,
)
from infuse.contracts.governor import GovernorAction
from infuse.contracts.policy import (
    AnomalyProtection,
    BudgetControls,
    GovernancePolicy,
    PolicyActionBindings,
    RequestControls,
    RuntimeControls,
    TokenControls,
    ToolAccessControls,
    WebAccessControls,
)
from infuse.contracts.state import ExecutionState
from infuse.e2e.environment import EndToEndIntegrationEnvironment
from infuse.e2e.transport import InProcessE2ETransport
from infuse.mcp.server import create_mcp_server
from infuse.sdk.client import InfuseClient


class TestBlock32EndToEndScenarios(unittest.TestCase):
    """End-to-End integration suite for all 11 mandatory system scenarios."""

    def setUp(self):
        self.env = EndToEndIntegrationEnvironment()

    # -------------------------------------------------------------------------
    # Scenario 1 — Normal execution
    # -------------------------------------------------------------------------
    def test_scenario_01_normal_execution(self):
        """Scenario 1: Full lifecycle of a normal, compliant request."""
        req = ExecutionRequest(
            request_id="req_scen_01",
            task=TaskContext(
                task_id="task_scen_01",
                description="Perform code review on module A",
            ),
            request=OperationRequest(
                messages=[{"role": "user", "content": "def hello(): pass"}],
            ),
            requirements=ExecutionRequirements(
                preferred_providers=["mock"],
                preferred_models=["mock-model"],
            ),
        )

        audit = self.env.execute_e2e(request=req)

        self.assertIsNotNone(audit.execution_id)
        self.assertEqual(audit.request_id, "req_scen_01")
        self.assertEqual(audit.final_state, ExecutionState.NORMAL)
        self.assertEqual(len(audit.governor_decisions), 1)
        self.assertEqual(audit.governor_decisions[0].action, GovernorAction.CONTINUE)
        self.assertEqual(len(audit.control_results), 0)  # No control needed on CONTINUE
        self.assertIsNotNone(audit.result)
        self.assertEqual(audit.result.execution_id, audit.execution_id)
        self.assertEqual(audit.result.execution.state, ExecutionState.NORMAL)

    # -------------------------------------------------------------------------
    # Scenario 2 — Cost pressure
    # -------------------------------------------------------------------------
    def test_scenario_02_cost_pressure(self):
        """Scenario 2: Telemetry causes COST_PRESSURE -> Governor -> Control Boundary."""
        b = BudgetControls(max_cost_per_task=0.0001)
        t = TokenControls(max_total_tokens=100_000)
        policy = GovernancePolicy(
            policy_id="pol_cost_tight",
            name="Tight Cost Policy",
            budget=b,
            budget_controls=b,
            tokens=t,
            token_controls=t,
            actions=PolicyActionBindings(
                budget_action=GovernorAction.OPTIMIZE,
            ),
        )

        exec_id = f"exec_cost_{uuid.uuid4().hex[:8]}"
        # Register adapter executor
        adapter = self.env.get_agent_adapter("universal")
        self.env.control_boundary.register_executor(exec_id, adapter)

        # Emit high token usage event
        tok_evt = ExecutionEvent(
            event_id=f"evt_tok_{uuid.uuid4().hex[:8]}",
            execution_id=exec_id,
            type=EventType.TOKEN_OBSERVED,
            source=EventSource.PROVIDER,
            sequence=1,
            payload={
                "input_tokens": 50_000,
                "output_tokens": 50_000,
                "total_tokens": 100_000,
                "provider": "mock",
                "model": "mock-model",
            },
        )
        self.env.emit_event(tok_evt)

        # Derive state & evaluate governor
        state_snap = self.env.derive_state(exec_id, policy=policy)
        self.assertEqual(state_snap.current_state, ExecutionState.COST_PRESSURE)

        gov_dec = self.env.evaluate_governor(exec_id, policy=policy)
        self.assertEqual(gov_dec.action, GovernorAction.OPTIMIZE)

        # Dispatch control
        ctrl_res = self.env.dispatch_control(exec_id, action=gov_dec.action)
        self.assertIn(ctrl_res.status, [ControlStatus.ACCEPTED, ControlStatus.COMPLETED, ControlStatus.SUPPORTED, ControlStatus.UNSUPPORTED])

    # -------------------------------------------------------------------------
    # Scenario 3 — Runaway execution
    # -------------------------------------------------------------------------
    def test_scenario_03_runaway_execution(self):
        """Scenario 3: Excessive tool loop causes RUNAWAY -> Governor STOP -> Control Boundary."""
        tc = ToolAccessControls(max_tool_calls_per_task=2)
        policy = GovernancePolicy(
            policy_id="pol_runaway_check",
            name="Runaway Protection Policy",
            tools=tc,
            tool_controls=tc,
            actions=PolicyActionBindings(
                anomaly_action=GovernorAction.STOP,
            ),
        )

        exec_id = f"exec_runaway_{uuid.uuid4().hex[:8]}"
        adapter = self.env.get_agent_adapter("universal")
        self.env.control_boundary.register_executor(exec_id, adapter)

        # Emit 3 tool calls exceeding max_tool_calls_per_task
        for i in range(1, 4):
            self.env.emit_event(ExecutionEvent(
                event_id=f"evt_run_tool_{i}_{uuid.uuid4().hex[:8]}",
                execution_id=exec_id,
                type=EventType.TOOL_CALLED,
                source=EventSource.AGENT,
                sequence=i,
                payload={"tool_call_id": f"call_{i}", "tool_name": "bash", "parameters": {}},
            ))

        state_snap = self.env.derive_state(exec_id, policy=policy)
        self.assertEqual(state_snap.current_state, ExecutionState.RUNAWAY)

        gov_dec = self.env.evaluate_governor(exec_id, policy=policy)
        self.assertEqual(gov_dec.action, GovernorAction.STOP)

        ctrl_res = self.env.dispatch_control(exec_id, action=gov_dec.action)
        self.assertIn(ctrl_res.status, [ControlStatus.ACCEPTED, ControlStatus.COMPLETED, ControlStatus.SUPPORTED])

    # -------------------------------------------------------------------------
    # Scenario 4 — Provider failure
    # -------------------------------------------------------------------------
    def test_scenario_04_provider_failure(self):
        """Scenario 4: Provider error events feed Health Engine -> Governor policy response."""
        policy = GovernancePolicy(
            policy_id="pol_failover",
            name="Failover Policy",
            actions=PolicyActionBindings(
                provider_failure_action=GovernorAction.SWITCH,
            ),
        )

        exec_id = f"exec_prov_fail_{uuid.uuid4().hex[:8]}"
        adapter = self.env.get_agent_adapter("universal")
        self.env.control_boundary.register_executor(exec_id, adapter)

        # Emit consecutive provider errors
        for i in range(1, 4):
            err_evt = ExecutionEvent(
                event_id=f"evt_err_{i}_{uuid.uuid4().hex[:8]}",
                execution_id=exec_id,
                type=EventType.PROVIDER_ERROR,
                source=EventSource.PROVIDER,
                sequence=i,
                payload={
                    "provider": "mock_unstable",
                    "model": "mock-model",
                    "error_type": "RateLimitError",
                    "message": "429 Too Many Requests",
                    "http_status": 429,
                    "is_retryable": True,
                },
            )
            self.env.emit_event(err_evt)

        health_sum = self.env.health_engine.get_execution_health(exec_id)
        self.assertEqual(len(health_sum.errors), 3)

        state_snap = self.env.derive_state(exec_id, policy=policy)
        self.assertEqual(state_snap.current_state, ExecutionState.PROVIDER_CONSTRAINED)

        gov_dec = self.env.evaluate_governor(exec_id, policy=policy)
        self.assertEqual(gov_dec.action, GovernorAction.SWITCH)

    # -------------------------------------------------------------------------
    # Scenario 5 — Unsupported control
    # -------------------------------------------------------------------------
    def test_scenario_05_unsupported_control(self):
        """Scenario 5: Adapter without throttle capability fails safely with UNSUPPORTED."""
        exec_id = f"exec_unsupported_{uuid.uuid4().hex[:8]}"

        # Mock adapter without throttle capability
        adapter = self.env.get_agent_adapter("claude")
        self.env.control_boundary.register_executor(exec_id, adapter)

        # Dispatch THOROTTLE or SWITCH
        ctrl_res = self.env.dispatch_control(exec_id, action=GovernorAction.THROTTLE)
        self.assertEqual(ctrl_res.status, ControlStatus.UNSUPPORTED)

    # -------------------------------------------------------------------------
    # Scenario 6 — Tool activity
    # -------------------------------------------------------------------------
    def test_scenario_06_tool_activity(self):
        """Scenario 6: ToolCalled and ToolCompleted events reach tool observer and state."""
        exec_id = f"exec_tool_{uuid.uuid4().hex[:8]}"

        call_evt = ExecutionEvent(
            event_id="evt_tool_call_1",
            execution_id=exec_id,
            type=EventType.TOOL_CALLED,
            source=EventSource.AGENT,
            sequence=1,
            payload={
                "tool_call_id": "call_123",
                "tool_name": "database_query",
                "parameters": {"sql": "SELECT 1;"},
            },
        )
        self.env.emit_event(call_evt)

        comp_evt = ExecutionEvent(
            event_id="evt_tool_comp_1",
            execution_id=exec_id,
            type=EventType.TOOL_COMPLETED,
            source=EventSource.AGENT,
            sequence=2,
            payload={
                "tool_call_id": "call_123",
                "tool_name": "database_query",
                "success": True,
                "result": {"rows": 1},
                "duration_ms": 45.0,
            },
        )
        self.env.emit_event(comp_evt)

        tool_sum = self.env.tool_observer.get_execution_summary(exec_id)
        self.assertIsNotNone(tool_sum)
        self.assertEqual(tool_sum.total_calls, 1)
        self.assertEqual(tool_sum.successful_calls, 1)
        self.assertEqual(tool_sum.unique_tools, ["database_query"])

    # -------------------------------------------------------------------------
    # Scenario 7 — Web activity
    # -------------------------------------------------------------------------
    def test_scenario_07_web_activity(self):
        """Scenario 7: WebRequest and WebResponse events reach web observer."""
        exec_id = f"exec_web_{uuid.uuid4().hex[:8]}"

        req_evt = ExecutionEvent(
            event_id="evt_web_req_1",
            execution_id=exec_id,
            type=EventType.WEB_REQUEST,
            source=EventSource.AGENT,
            sequence=1,
            payload={
                "request_id": "http_1",
                "url": "https://api.example.com/data",
                "method": "GET",
            },
        )
        self.env.emit_event(req_evt)

        res_evt = ExecutionEvent(
            event_id="evt_web_res_1",
            execution_id=exec_id,
            type=EventType.WEB_RESPONSE,
            source=EventSource.AGENT,
            sequence=2,
            payload={
                "request_id": "http_1",
                "url": "https://api.example.com/data",
                "status_code": 200,
                "duration_ms": 120.0,
                "success": True,
            },
        )
        self.env.emit_event(res_evt)

        web_sum = self.env.web_observer.get_execution_summary(exec_id)
        self.assertIsNotNone(web_sum)
        self.assertEqual(web_sum.total_requests, 1)
        self.assertEqual(web_sum.successful_requests, 1)

    # -------------------------------------------------------------------------
    # Scenario 8 — Retry / Provider Error Sequence
    # -------------------------------------------------------------------------
    def test_scenario_08_retry_provider_error_sequence(self):
        """Scenario 8: RetryStarted -> ProviderError -> RetryStarted -> Completed."""
        exec_id = f"exec_retry_{uuid.uuid4().hex[:8]}"

        events = [
            ExecutionEvent(
                event_id="evt_ret_1",
                execution_id=exec_id,
                type=EventType.RETRY_STARTED,
                source=EventSource.RUNTIME,
                sequence=1,
                payload={"attempt": 1, "reason": "Initial timeout"},
            ),
            ExecutionEvent(
                event_id="evt_perr_1",
                execution_id=exec_id,
                type=EventType.PROVIDER_ERROR,
                source=EventSource.PROVIDER,
                sequence=2,
                payload={"error_type": "TimeoutError", "provider": "mock", "is_retryable": True},
            ),
            ExecutionEvent(
                event_id="evt_ret_2",
                execution_id=exec_id,
                type=EventType.RETRY_STARTED,
                source=EventSource.RUNTIME,
                sequence=3,
                payload={"attempt": 2, "reason": "Second attempt"},
            ),
            ExecutionEvent(
                event_id="evt_comp_1",
                execution_id=exec_id,
                type=EventType.EXECUTION_COMPLETED,
                source=EventSource.RUNTIME,
                sequence=4,
                payload={"status": "completed"},
            ),
        ]

        for e in events:
            self.env.emit_event(e)

        health_sum = self.env.health_engine.get_execution_health(exec_id)
        self.assertEqual(len(health_sum.retries), 2)
        self.assertEqual(len(health_sum.errors), 1)

    # -------------------------------------------------------------------------
    # Scenario 9 — SDK Execution
    # -------------------------------------------------------------------------
    def test_scenario_09_sdk_execution(self):
        """Scenario 9: InfuseClient executes request over in-process transport."""
        transport = InProcessE2ETransport(environment=self.env)
        client = InfuseClient(transport=transport)

        req = ExecutionRequest(
            request_id="sdk_req_01",
            task=TaskContext(task_id="task_sdk_1", description="SDK test task"),
            request=OperationRequest(messages=[{"role": "user", "content": "Hello SDK"}]),
            requirements=ExecutionRequirements(preferred_providers=["mock"]),
        )

        res = client.execute(req)
        self.assertIsNotNone(res.execution_id)
        self.assertEqual(res.request_id, "sdk_req_01")
        self.assertEqual(res.execution.state, ExecutionState.NORMAL)

        # Policy round-trip via SDK
        active_pol = client.get_active_policy()
        self.assertIsNotNone(active_pol)

    # -------------------------------------------------------------------------
    # Scenario 10 — CLI Execution
    # -------------------------------------------------------------------------
    def test_scenario_10_cli_execution(self):
        """Scenario 10: Infuse CLI invokes SDK commands and parses outputs."""
        transport = InProcessE2ETransport(environment=self.env)
        client = InfuseClient(transport=transport)
        
        exit_code = run_cli(["policy", "get", "--json"], client=client)
        self.assertEqual(exit_code, 0)

    # -------------------------------------------------------------------------
    # Scenario 11 — MCP Execution
    # -------------------------------------------------------------------------
    def test_scenario_11_mcp_execution(self):
        """Scenario 11: Infuse MCP server executes tools against the SDK boundary."""
        transport = InProcessE2ETransport(environment=self.env)
        client = InfuseClient(transport=transport)
        mcp_server = create_mcp_server(client=client)

        tools = asyncio.run(mcp_server.list_tools())
        self.assertTrue(len(tools) >= 5)

        tool_names = [t.name for t in tools]
        self.assertIn("infuse_execute", tool_names)
        self.assertIn("infuse_get_policy", tool_names)

        # Call tool via MCP server
        result = asyncio.run(mcp_server.call_tool("infuse_get_policy", {}))
        self.assertIsNotNone(result)


if __name__ == "__main__":
    unittest.main()
