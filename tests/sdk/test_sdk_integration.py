"""Integration and Starlette ASGI compatibility tests for the INFUSE SDK (Block 28)."""

import json
import unittest
from typing import Any, Dict
from starlette.testclient import TestClient

from infuse.api.app import create_app
from infuse.contracts.control import ControlCapability, ControlStatus
from infuse.contracts.events import EventSource, EventType, ExecutionEvent
from infuse.contracts.execution import (
    ExecutionRequest,
    ExecutionResult,
    ExecutionStatus,
    OperationRequest,
    TaskContext,
)
from infuse.contracts.governor import GovernorAction
from infuse.contracts.policy import BudgetControls, GovernancePolicy
from infuse.control.boundary import ExecutionControlBoundary
from infuse.sdk import (
    ClientConfig,
    InfuseClient,
    ITransport,
    TransportResponse,
)


class StarletteTestClientTransport(ITransport):
    """Transport that bridges SDK directly to Starlette TestClient in-memory."""

    def __init__(self, test_client: TestClient) -> None:
        self.client = test_client

    def send_request(
        self,
        method: str,
        path: str,
        params: Any = None,
        json_data: Any = None,
        headers: Any = None,
    ) -> TransportResponse:
        resp = self.client.request(
            method=method,
            url=path,
            params=params,
            json=json_data,
            headers=headers,
        )
        try:
            data = resp.json()
        except Exception:
            data = resp.text
        return TransportResponse(
            status_code=resp.status_code,
            data=data,
            headers=dict(resp.headers.items()),
        )


class TestSdkIntegrationWithApi(unittest.TestCase):
    """E2E and ASGI Integration Tests for InfuseClient against Starlette Universal API."""

    def setUp(self) -> None:
        self.app = create_app()
        self.test_client = TestClient(self.app, raise_server_exceptions=False)
        self.transport = StarletteTestClientTransport(self.test_client)
        self.boundary = ExecutionControlBoundary()
        self.client = InfuseClient(
            transport=self.transport,
            control_boundary=self.boundary,
        )

    def test_41_api_health_endpoint_via_transport(self) -> None:
        resp = self.transport.send_request("GET", "/health")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data.get("status"), "OK")

    def test_42_e2e_execute_flow_via_api(self) -> None:
        req = ExecutionRequest(
            request_id="req_e2e_1",
            task=TaskContext(task_id="t_e2e_1", description="Test task"),
            request=OperationRequest(messages=[{"role": "user", "content": "Hello"}]),
        )
        res = self.client.execute(req)
        self.assertIsInstance(res, ExecutionResult)
        self.assertEqual(res.request_id, "req_e2e_1")
        self.assertTrue(len(res.execution_id) > 0)

    def test_43_e2e_list_executions_via_api(self) -> None:
        # First execute one item
        req = ExecutionRequest(
            request_id="req_e2e_2",
            task=TaskContext(task_id="t_e2e_2", description="List test"),
            request=OperationRequest(messages=[{"role": "user", "content": "Hello"}]),
        )
        self.client.execute(req)

        # List executions
        res = self.client.list_executions(limit=50)
        self.assertGreaterEqual(res.total, 1)
        self.assertGreaterEqual(len(res.items), 1)

    def test_44_e2e_event_ingestion_via_api(self) -> None:
        # Create execution first
        req = ExecutionRequest(
            request_id="req_e2e_3",
            task=TaskContext(task_id="t_e2e_3", description="Event test"),
            request=OperationRequest(messages=[{"role": "user", "content": "Hello"}]),
        )
        exec_res = self.client.execute(req)
        exec_id = exec_res.execution_id

        # Ingest event
        ev = ExecutionEvent(
            event_id="ev_e2e_1",
            execution_id=exec_id,
            type=EventType.EXECUTION_COMPLETED,
            source=EventSource.AGENT,
            sequence=1,
            payload={"step": 1},
        )
        ingest_res = self.client.publish_event(exec_id, ev)
        self.assertEqual(ingest_res.status, "INGESTED")
        self.assertEqual(ingest_res.event_id, "ev_e2e_1")

    def test_45_e2e_policy_list_and_update_via_api(self) -> None:
        # Get active policy
        active = self.client.get_active_policy()
        self.assertIsNotNone(active)

        # Update default active policy
        updated_policy = GovernancePolicy(
            policy_id=active.policy_id,
            name="SDK Updated Policy",
            budget=BudgetControls(max_cost_per_task=2.5),
        )
        saved = self.client.update_policy(active.policy_id, updated_policy)
        self.assertEqual(saved.policy_id, active.policy_id)
        self.assertEqual(saved.name, "SDK Updated Policy")

    def test_46_control_throttle_dispatch_preserves_parameters(self) -> None:
        self.boundary.register_capability(
            "exec_throttle_1",
            ControlCapability(supports_throttle=True, supported_actions=[GovernorAction.THROTTLE]),
        )
        res = self.client.control.throttle("exec_throttle_1", delay_ms=2500)
        self.assertEqual(res.status, ControlStatus.ACCEPTED)
        self.assertEqual(res.action, GovernorAction.THROTTLE)

    def test_47_control_switch_dispatch_preserves_target_model(self) -> None:
        self.boundary.register_capability(
            "exec_switch_1",
            ControlCapability(supports_next_step_switch=True, supported_actions=[GovernorAction.SWITCH]),
        )
        res = self.client.control.switch("exec_switch_1", target_model="gpt-4o-mini")
        self.assertEqual(res.status, ControlStatus.ACCEPTED)
        self.assertEqual(res.action, GovernorAction.SWITCH)

    def test_48_control_history_retrieval(self) -> None:
        self.boundary.register_capability(
            "exec_hist_1",
            ControlCapability(supports_cancel=True, supported_actions=[GovernorAction.STOP]),
        )
        self.client.cancel("exec_hist_1")
        history = self.client.control.get_history("exec_hist_1")
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0].execution_id, "exec_hist_1")
        self.assertEqual(history[0].operation.action, GovernorAction.STOP)

    def test_49_control_latest_result_retrieval(self) -> None:
        self.boundary.register_capability(
            "exec_latest_1",
            ControlCapability(supports_cancel=True, supported_actions=[GovernorAction.STOP]),
        )
        self.client.cancel("exec_latest_1")
        latest = self.client.control.get_latest("exec_latest_1")
        self.assertIsNotNone(latest)
        self.assertEqual(latest.action, GovernorAction.STOP)
        self.assertEqual(latest.status, ControlStatus.ACCEPTED)

    def test_50_custom_headers_in_client_config(self) -> None:
        cfg = ClientConfig(
            custom_headers={"X-Custom-Tenant": "tenant-abc", "X-Custom-Env": "staging"}
        )
        self.assertEqual(cfg.custom_headers["X-Custom-Tenant"], "tenant-abc")
        self.assertEqual(cfg.custom_headers["X-Custom-Env"], "staging")


if __name__ == "__main__":
    unittest.main()
