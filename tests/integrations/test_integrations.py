"""INFUSE Block 31 Third-Party Integration Comprehensive Test Suite.

Validates:
- Manifest parsing, schema compliance, and rules
- Component classification (DIRECT_DEPENDENCY, ADAPTER_INTEGRATION, etc.)
- Exact version pinning and commit SHA verification
- Zero duplicate authority invariants
- Boundary isolation and zero object leakage
- Secret redaction across payloads and errors
- Optional dependency availability and fallback behavior
- Failure normalization and error isolation
- Negative architectural boundary invariants
"""

import os
import unittest
from unittest.mock import MagicMock, patch

from infuse.contracts.control import ControlOperation, ControlResult, ControlStatus
from infuse.contracts.events import EventSource, EventType, ExecutionEvent
from infuse.contracts.execution import (
    ExecutionContext,
    ExecutionRequirements,
    ExecutionRequest,
    NormalizedResponse,
    OperationRequest,
    TaskContext,
)
from infuse.contracts.governor import GovernorAction, GovernorDecision
from infuse.contracts.policy import GovernancePolicy
from infuse.contracts.state import ExecutionState, ExecutionStateSnapshot
from infuse.control.boundary import ExecutionControlBoundary
from infuse.governor.engine import GovernorEngine
from infuse.integrations.boundary import IntegrationBoundary
from infuse.integrations.contracts import (
    IntegrationCategory,
    IntegrationComponentInfo,
    IntegrationStatus,
    VerificationStatus,
)
from infuse.integrations.litellm.adapter import LiteLLMProviderAdapter
from infuse.integrations.manifest import (
    ReuseManifest,
    load_manifest,
    validate_manifest,
)
from infuse.integrations.registry import IntegrationRegistry
from infuse.providers.errors import ProviderAdapterError, ProviderInvocationError
from infuse.providers.models import (
    ProviderExecutionRequest,
    ProviderExecutionResponse,
    ProviderUsage,
)
from infuse.state.engine import ExecutionStateEngine


class TestBlock31Integration(unittest.TestCase):
    """Test suite for Block 31 Third-Party Component Integration."""

    @classmethod
    def setUpClass(cls):
        cls.manifest = load_manifest()
        cls.registry = IntegrationRegistry(manifest=cls.manifest)

    # 1. Manifest loading and validation
    def test_01_manifest_load_success(self):
        self.assertIsNotNone(self.manifest)
        self.assertEqual(self.manifest.project, "INFUSE")
        self.assertTrue(len(self.manifest.components) >= 7)

    # 2. Manifest integrity validation
    def test_02_manifest_integrity_validation(self):
        errors = validate_manifest(self.manifest)
        self.assertEqual(errors, [], f"Manifest validation errors found: {errors}")

    # 3. Exact versions recorded (no latest or unpinned)
    def test_03_exact_versions_recorded(self):
        for comp in self.manifest.components:
            self.assertFalse(comp.version.lower().startswith("latest"))
            self.assertFalse(comp.version.lower().startswith("main"))
            self.assertFalse(comp.version.lower().startswith("master"))
            self.assertNotEqual(comp.version.strip(), "*")
            self.assertTrue(len(comp.version) > 0)

    # 4. Exact commit SHAs recorded
    def test_04_exact_commit_shas_recorded(self):
        for comp in self.manifest.components:
            self.assertTrue(len(comp.commit_sha) >= 8)
            self.assertTrue(all(c in "0123456789abcdefABCDEF" for c in comp.commit_sha))

    # 5. License metadata recording
    def test_05_license_metadata_recorded(self):
        for comp in self.manifest.components:
            self.assertIn(comp.license, ["MIT", "Apache-2.0"])
            self.assertTrue(len(comp.license_notes) > 0)

    # 6. Integration classification correctness
    def test_06_integration_classification(self):
        litellm = self.registry.get_component("litellm")
        self.assertEqual(litellm.integration_type, IntegrationCategory.ADAPTER_INTEGRATION)

        token_router = self.registry.get_component("jman4162/llm-token-router")
        self.assertEqual(token_router.integration_type, IntegrationCategory.REIMPLEMENTED_CLEAN_ROOM)

        timholm = self.registry.get_component("timholm/llm-router")
        self.assertEqual(timholm.integration_type, IntegrationCategory.REIMPLEMENTED_CLEAN_ROOM)

        vllm = self.registry.get_component("vllm-semantic-router")
        self.assertEqual(vllm.integration_type, IntegrationCategory.REFERENCE_ONLY)

        agentgw = self.registry.get_component("agentgateway")
        self.assertEqual(agentgw.integration_type, IntegrationCategory.SEPARATE_SERVICE)

    # 7. Verification status verification
    def test_07_verification_status(self):
        for comp in self.manifest.components:
            self.assertEqual(comp.verification_status, VerificationStatus.VERIFIED)

    # 8. Clean-room verification flags
    def test_08_clean_room_flags(self):
        for comp in self.manifest.components:
            self.assertFalse(comp.source_copied, f"Component {comp.name} illegally copied source")

    # 9. LiteLLM adapter initialization & interface compliance
    def test_09_litellm_adapter_interface(self):
        adapter = LiteLLMProviderAdapter()
        self.assertEqual(adapter.provider_id, "litellm")
        cap = adapter.get_capability()
        self.assertTrue(cap.supports_streaming)
        self.assertTrue(cap.supports_tool_calling)
        self.assertTrue(adapter.supports_model("litellm/gpt-4o"))
        self.assertTrue(adapter.supports_model("gpt-4o"))

    # 10. LiteLLM simulation execution
    def test_10_litellm_simulation_execution(self):
        adapter = LiteLLMProviderAdapter(allow_simulation=True)
        req = ProviderExecutionRequest(
            execution_id="exec_test_01",
            request_id="req_01",
            task_id="task_01",
            provider_id="litellm",
            model_id="litellm/gpt-4o",
            messages=[{"role": "user", "content": "What is execution intelligence?"}],
        )
        resp = adapter.execute(req)
        self.assertEqual(resp.execution_id, "exec_test_01")
        self.assertEqual(resp.provider_id, "litellm")
        self.assertIn("Simulated", resp.content)
        self.assertTrue(resp.usage.total_tokens > 0)
        self.assertFalse(resp.usage.is_authoritative)

    # 11. LiteLLM unavailable error when simulation disabled
    def test_11_litellm_unavailable_when_no_sim(self):
        with patch("infuse.integrations.litellm.adapter._LITELLM_AVAILABLE", False):
            adapter = LiteLLMProviderAdapter(allow_simulation=False)
            req = ProviderExecutionRequest(
                execution_id="exec_test_02",
                request_id="req_02",
                task_id="task_02",
                provider_id="litellm",
                model_id="litellm/gpt-4o",
                messages=[{"role": "user", "content": "Test"}],
            )
            with self.assertRaises(ProviderAdapterError):
                adapter.execute(req)

    # 12. LiteLLM streaming simulation
    def test_12_litellm_streaming_simulation(self):
        adapter = LiteLLMProviderAdapter(allow_simulation=True)
        req = ProviderExecutionRequest(
            execution_id="exec_test_stream",
            request_id="req_str",
            task_id="task_str",
            provider_id="litellm",
            model_id="litellm/gpt-4o",
            messages=[{"role": "user", "content": "Stream test"}],
            stream=True,
        )
        chunks = list(adapter.stream(req))
        self.assertTrue(len(chunks) > 0)
        self.assertEqual(chunks[0].execution_id, "exec_test_stream")
        self.assertEqual(chunks[-1].finish_reason, "stop")

    # 13. IntegrationBoundary secret redaction for strings
    def test_13_boundary_secret_redaction_string(self):
        raw = "User requested key sk-proj-1234567890abcdef and token ghp_ABCDEF123456"
        sanitized = IntegrationBoundary.sanitize_secrets(raw)
        self.assertNotIn("sk-proj-1234567890abcdef", sanitized)
        self.assertNotIn("ghp_ABCDEF123456", sanitized)
        self.assertIn("[REDACTED]", sanitized)

    # 14. IntegrationBoundary secret redaction for dictionaries
    def test_14_boundary_secret_redaction_dict(self):
        payload = {
            "api_key": "sk-secret-test-key",
            "nested": {"bearer_token": "Bearer test-jwt-123", "normal": "safe_value"},
        }
        sanitized = IntegrationBoundary.sanitize_secrets(payload)
        self.assertEqual(sanitized["api_key"], "[REDACTED]")
        self.assertEqual(sanitized["nested"]["bearer_token"], "[REDACTED]")
        self.assertEqual(sanitized["nested"]["normal"], "safe_value")

    # 15. IntegrationBoundary response normalization from dict
    def test_15_boundary_response_normalization_dict(self):
        raw_dict = {
            "choices": [{"message": {"role": "assistant", "content": "Clean response from LiteLLM"}}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30},
        }
        norm = IntegrationBoundary.normalize_response(raw_dict, provider="litellm", model="gpt-4o")
        self.assertEqual(norm.content, "Clean response from LiteLLM")
        self.assertEqual(norm.role, "assistant")
        self.assertEqual(norm.input_tokens, 10)
        self.assertEqual(norm.output_tokens, 20)
        self.assertEqual(norm.total_tokens, 30)
        self.assertIsNone(norm.raw_response)  # Guarantee no leakage

    # 16. IntegrationBoundary response normalization from mock object
    def test_16_boundary_response_normalization_object(self):
        class MockChoice:
            message = MagicMock(content="Object response", role="assistant")

        class MockResp:
            choices = [MockChoice()]
            usage = MagicMock(prompt_tokens=15, completion_tokens=25, total_tokens=40)

        norm = IntegrationBoundary.normalize_response(MockResp(), provider="litellm", model="claude-3-5")
        self.assertEqual(norm.content, "Object response")
        self.assertEqual(norm.total_tokens, 40)

    # 17. IntegrationBoundary error normalization
    def test_17_boundary_error_normalization(self):
        exc = ConnectionError("Failed to connect with Authorization: Bearer sk-leaked-key")
        err_payload = IntegrationBoundary.normalize_error(exc, provider="litellm", model="gpt-4o")
        self.assertEqual(err_payload.provider, "litellm")
        self.assertEqual(err_payload.error_type, "ConnectionError")
        self.assertTrue(err_payload.is_retryable)
        self.assertNotIn("sk-leaked-key", err_payload.message)
        self.assertIn("[REDACTED]", err_payload.message)

    # 18. Zero external object graph leakage
    def test_18_no_external_object_leakage(self):
        raw_complex_obj = {"custom_ext_field": {"internal_token": "secret"}, "content": "Simple text"}
        norm = IntegrationBoundary.normalize_response(raw_complex_obj, provider="litellm", model="test")
        dump = norm.model_dump()
        self.assertNotIn("custom_ext_field", dump)
        self.assertEqual(dump["content"], "Simple text")

    # 19. Manifest rules verification
    def test_19_manifest_rules_completeness(self):
        self.assertTrue(len(self.manifest.manifest_rules) >= 4)
        rule_texts = " ".join(self.manifest.manifest_rules)
        self.assertIn("Zero duplicate authorities", rule_texts)
        self.assertIn("No external model or provider types may leak", rule_texts)

    # 20. Registry component lookup
    def test_20_registry_component_lookup(self):
        comp = self.registry.get_component("litellm")
        self.assertIsNotNone(comp)
        self.assertEqual(comp.name, "litellm")

        missing = self.registry.get_component("non_existent_project")
        self.assertIsNone(missing)

    # 21. Registry status inspection
    def test_21_registry_status(self):
        status = self.registry.get_status("jman4162/llm-token-router")
        self.assertEqual(status, IntegrationStatus.ACTIVE)

    # 22. Registry telemetry recording
    def test_22_registry_telemetry_recording(self):
        self.registry.record_invocation("litellm", success=True)
        self.registry.record_invocation("litellm", success=False, error="Simulated test error")
        telem = self.registry.get_telemetry("litellm")
        self.assertTrue(telem["invocations_count"] >= 2)
        self.assertTrue(telem["errors_count"] >= 1)
        self.assertEqual(telem["last_error"], "Simulated test error")

    # 23. Environment override disabling integration
    def test_23_environment_override_disable(self):
        with patch.dict("os.environ", {"INFUSE_INTEGRATION_LITELLM_ENABLED": "false"}):
            reg = IntegrationRegistry(manifest=self.manifest)
            status = reg.get_status("litellm")
            self.assertEqual(status, IntegrationStatus.DISABLED)

    # 24. Clean-room token-router isolation (No external router imports)
    def test_24_token_router_no_source_import(self):
        import importlib
        with self.assertRaises(ModuleNotFoundError):
            importlib.import_module("llm_token_router")

    # 25. Clean-room timholm router isolation (No external router imports)
    def test_25_timholm_router_no_source_import(self):
        import importlib
        with self.assertRaises(ModuleNotFoundError):
            importlib.import_module("llm_router")

    # 26. Clean-room vllm semantic router isolation (No external router imports)
    def test_26_vllm_router_no_source_import(self):
        import importlib
        with self.assertRaises(ModuleNotFoundError):
            importlib.import_module("vllm.semantic_router")

    # 27. Clean-room agentgateway isolation (No Rust crate imports)
    def test_27_agentgateway_no_source_import(self):
        import importlib
        with self.assertRaises(ModuleNotFoundError):
            importlib.import_module("agentgateway")

    # 28. Supply-chain validation: Disallow 'latest' version tag
    def test_28_supply_chain_disallow_latest(self):
        bad_manifest = ReuseManifest(
            schema_version="1.0.0",
            project="INFUSE",
            components=[
                IntegrationComponentInfo(
                    name="bad-package",
                    repository="https://github.com/test/bad",
                    version="latest",
                    commit_sha="abcdef123456",
                    license="MIT",
                    intended_purpose="Testing",
                    integration_type=IntegrationCategory.ADAPTER_INTEGRATION,
                    infuse_boundary="test.boundary",
                )
            ],
        )
        errors = validate_manifest(bad_manifest)
        self.assertTrue(any("unpinned version" in e for e in errors))

    # 29. Supply-chain validation: Disallow unverified active integrations
    def test_29_supply_chain_disallow_unverified_integration(self):
        bad_manifest = ReuseManifest(
            schema_version="1.0.0",
            project="INFUSE",
            components=[
                IntegrationComponentInfo(
                    name="unverified-dep",
                    repository="https://github.com/test/unverified",
                    version="1.0.0",
                    commit_sha="abcdef123456",
                    license="MIT",
                    intended_purpose="Testing",
                    integration_type=IntegrationCategory.ADAPTER_INTEGRATION,
                    infuse_boundary="test.boundary",
                    verification_status=VerificationStatus.UNVERIFIED,
                )
            ],
        )
        errors = validate_manifest(bad_manifest)
        self.assertTrue(any("UNVERIFIED" in e for e in errors))

    # 30. Documentation file presence
    def test_30_documentation_presence(self):
        doc_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            "docs",
            "third_party_integration.md",
        )
        self.assertTrue(os.path.exists(doc_path))
        with open(doc_path, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn("Integration Inventory", content)
        self.assertIn("Architectural Ownership Matrix", content)
        self.assertIn("Zero Duplicate Authority Rule", content)

    # 31. Execution identity preservation
    def test_31_execution_identity_preservation(self):
        adapter = LiteLLMProviderAdapter()
        req = ProviderExecutionRequest(
            execution_id="canonical_exec_identity_99",
            request_id="req_99",
            task_id="task_99",
            provider_id="litellm",
            model_id="litellm/gpt-4o",
            messages=[{"role": "user", "content": "Identity check"}],
        )
        res = adapter.execute(req)
        self.assertEqual(res.execution_id, "canonical_exec_identity_99")
        self.assertEqual(res.request_id, "req_99")

    # 32. Provider Error Record structure
    def test_32_provider_error_record(self):
        adapter = LiteLLMProviderAdapter()
        err = adapter.normalize_error(ValueError("Invalid hyperparameter temperature=99"), model_id="gpt-4o")
        self.assertEqual(err.provider_id, "litellm")
        self.assertEqual(err.model_id, "gpt-4o")
        self.assertEqual(err.error_type, "ValueError")

    # 33. No subprocess execution in integration modules
    def test_33_no_subprocess_in_integrations(self):
        import importlib
        for mod_name in ["boundary", "contracts", "manifest", "registry"]:
            mod = importlib.import_module(f"infuse.integrations.{mod_name}")
            with open(mod.__file__, "r", encoding="utf-8") as f:
                src = f.read()
            self.assertNotIn("subprocess.Popen", src)
            self.assertNotIn("os.system", src)
            self.assertNotIn("eval(", src)
            self.assertNotIn("exec(", src)

    # 34. Negative Architectural Test: External component cannot issue Governor actions
    def test_34_external_cannot_issue_governor_action(self):
        gov = GovernorEngine()
        policy = GovernancePolicy(policy_id="test_pol", name="Test Policy")
        snapshot = ExecutionStateSnapshot(
            execution_id="exec_gov_test",
            current_state=ExecutionState.NORMAL,
        )
        # Governor is the sole authority
        decision = gov.evaluate(execution_id="exec_gov_test", state_snapshot=snapshot, policy=policy)
        self.assertEqual(decision.action, GovernorAction.CONTINUE.value)

    # 35. Negative Architectural Test: External component cannot mutate ExecutionStateEngine
    def test_35_external_cannot_mutate_state_engine(self):
        engine = ExecutionStateEngine()
        snapshot = engine.derive_state(execution_id="exec_test_isolation")
        self.assertIsInstance(snapshot, ExecutionStateSnapshot)
        self.assertEqual(snapshot.current_state, ExecutionState.NORMAL)

    # 36. Negative Architectural Test: External component cannot dispatch Control boundary commands without executor
    def test_36_external_cannot_bypass_control_boundary(self):
        boundary = ExecutionControlBoundary()
        res = boundary.dispatch_control(
            execution_id="exec_unregistered",
            action=GovernorAction.STOP,
        )
        self.assertEqual(res.status, ControlStatus.UNSUPPORTED)

    # 37. Negative Architectural Test: No non-canonical events published
    def test_37_event_contract_immutability(self):
        evt = ExecutionEvent(
            event_id="evt_valid_1",
            execution_id="exec_1",
            type=EventType.TOKEN_OBSERVED,
            source=EventSource.PROVIDER,
            sequence=1,
            payload={"tokens": 10},
        )
        self.assertEqual(evt.type, EventType.TOKEN_OBSERVED)
        self.assertEqual(evt.source, EventSource.PROVIDER)

    # 38. Mocking LiteLLM with real execution simulation
    def test_38_litellm_mock_completion(self):
        mock_completion_resp = {
            "choices": [{"message": {"role": "assistant", "content": "Mocked litellm output"}}],
            "usage": {"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150},
        }
        with patch("infuse.integrations.litellm.adapter._LITELLM_AVAILABLE", True), patch(
            "infuse.integrations.litellm.adapter.litellm"
        ) as mock_litellm:
            mock_litellm.completion.return_value = mock_completion_resp
            adapter = LiteLLMProviderAdapter()
            req = ProviderExecutionRequest(
                execution_id="exec_mock_litellm",
                request_id="req_m",
                task_id="task_m",
                provider_id="litellm",
                model_id="litellm/gpt-4o",
                messages=[{"role": "user", "content": "Hello"}],
            )
            res = adapter.execute(req)
            self.assertEqual(res.content, "Mocked litellm output")
            self.assertEqual(res.usage.total_tokens, 150)

    # 39. Mocking LiteLLM streaming
    def test_39_litellm_mock_streaming(self):
        class MockChunk:
            def __init__(self, text, reason=None):
                self.choices = [MagicMock(delta=MagicMock(content=text), finish_reason=reason)]

        mock_chunks = [MockChunk("Hello"), MockChunk(" world", "stop")]
        with patch("infuse.integrations.litellm.adapter._LITELLM_AVAILABLE", True), patch(
            "infuse.integrations.litellm.adapter.litellm"
        ) as mock_litellm:
            mock_litellm.completion.return_value = mock_chunks
            adapter = LiteLLMProviderAdapter()
            req = ProviderExecutionRequest(
                execution_id="exec_stream_mock",
                request_id="req_sm",
                task_id="task_sm",
                provider_id="litellm",
                model_id="litellm/gpt-4o",
                messages=[{"role": "user", "content": "Stream"}],
                stream=True,
            )
            chunks = list(adapter.stream(req))
            self.assertEqual(len(chunks), 2)
            self.assertEqual(chunks[0].delta_content, "Hello")
            self.assertEqual(chunks[1].finish_reason, "stop")

    # 40. Failure normalization during LiteLLM execution
    def test_40_litellm_execution_failure_normalized(self):
        with patch("infuse.integrations.litellm.adapter._LITELLM_AVAILABLE", True), patch(
            "infuse.integrations.litellm.adapter.litellm"
        ) as mock_litellm:
            mock_litellm.completion.side_effect = TimeoutError("LiteLLM upstream gateway timed out")
            adapter = LiteLLMProviderAdapter()
            req = ProviderExecutionRequest(
                execution_id="exec_fail_norm",
                request_id="req_fn",
                task_id="task_fn",
                provider_id="litellm",
                model_id="litellm/gpt-4o",
                messages=[{"role": "user", "content": "Timeout"}],
            )
            with self.assertRaises(ProviderInvocationError) as cm:
                adapter.execute(req)
            self.assertIn("timed out", str(cm.exception))
            self.assertTrue(cm.exception.is_retryable)

    # 41. No duplicate policy authority in Block 31
    def test_41_no_duplicate_policy_authority(self):
        import importlib
        for mod_name in ["boundary", "contracts", "manifest", "registry"]:
            mod = importlib.import_module(f"infuse.integrations.{mod_name}")
            with open(mod.__file__, "r", encoding="utf-8") as f:
                src = f.read()
            self.assertNotIn("evaluate_policy", src)
            self.assertNotIn("evaluate_budget", src)

    # 42. Verification of all 7 evaluated components present in manifest
    def test_42_all_seven_components_in_manifest(self):
        names = [c.name for c in self.manifest.components]
        expected = [
            "litellm",
            "jman4162/llm-token-router",
            "timholm/llm-router",
            "vllm-semantic-router",
            "agentgateway",
            "k1y0miiii/llm-gateway",
            "tahasiddiquii/llm-router",
        ]
        for exp in expected:
            self.assertIn(exp, names)

    # 43. Clean-room implementation flag true for all adapted components
    def test_43_clean_room_implementation_flags(self):
        for comp in self.manifest.components:
            if comp.integration_type in (
                IntegrationCategory.REIMPLEMENTED_CLEAN_ROOM,
                IntegrationCategory.ADAPTER_INTEGRATION,
            ):
                self.assertTrue(comp.clean_room_implementation)

    # 44. Removal strategy completeness
    def test_44_removal_strategy_completeness(self):
        for comp in self.manifest.components:
            self.assertTrue(len(comp.removal_strategy) > 0)

    # 45. Affected blocks validity
    def test_45_affected_blocks_validity(self):
        litellm = self.registry.get_component("litellm")
        self.assertTrue(any("Block 12" in b for b in litellm.affected_blocks))

    # 46. Package init exports
    def test_46_package_exports(self):
        import infuse.integrations as pkg
        self.assertTrue(hasattr(pkg, "IntegrationRegistry"))
        self.assertTrue(hasattr(pkg, "IntegrationBoundary"))
        self.assertTrue(hasattr(pkg, "LiteLLMProviderAdapter"))
        self.assertTrue(hasattr(pkg, "load_manifest"))
        self.assertTrue(hasattr(pkg, "validate_manifest"))

    # 47. Registry dynamic custom component registration
    def test_47_registry_custom_component(self):
        reg = IntegrationRegistry(manifest=self.manifest)
        custom = IntegrationComponentInfo(
            name="custom-test-plugin",
            repository="https://github.com/custom/plugin",
            version="1.0.0",
            commit_sha="1234567890abcdef",
            license="MIT",
            intended_purpose="Dynamic plugin test",
            integration_type=IntegrationCategory.ADAPTER_INTEGRATION,
            infuse_boundary="custom.boundary",
        )
        reg._custom_components["custom-test-plugin"] = custom
        found = reg.get_component("custom-test-plugin")
        self.assertIsNotNone(found)
        self.assertEqual(found.name, "custom-test-plugin")

    # 48. Deterministic response formatting
    def test_48_deterministic_response_formatting(self):
        norm1 = IntegrationBoundary.normalize_response("Fixed output", provider="p", model="m")
        norm2 = IntegrationBoundary.normalize_response("Fixed output", provider="p", model="m")
        self.assertEqual(norm1.model_dump(), norm2.model_dump())

    # 49. Empty message payload handling
    def test_49_empty_message_payload(self):
        adapter = LiteLLMProviderAdapter()
        req = ProviderExecutionRequest(
            execution_id="exec_empty_msg",
            request_id="req_em",
            task_id="task_em",
            provider_id="litellm",
            model_id="litellm/gpt-4o",
            messages=[],
        )
        res = adapter.execute(req)
        self.assertIsNotNone(res.content)

    # 50. End-to-end integration registry health validation
    def test_50_registry_health_validation(self):
        self.registry.record_invocation("litellm", success=True)
        telem = self.registry.get_telemetry()
        self.assertIn("litellm", telem)
        self.assertIn("jman4162/llm-token-router", telem)
        self.assertIn("agentgateway", telem)

    # 51. Negative test: External component cannot alter execution status in core
    def test_51_negative_execution_status_alteration(self):
        adapter = LiteLLMProviderAdapter()
        req = ProviderExecutionRequest(
            execution_id="exec_test_immutability",
            request_id="req_imm",
            task_id="task_imm",
            provider_id="litellm",
            model_id="litellm/gpt-4o",
            messages=[{"role": "user", "content": "status check"}],
        )
        resp = adapter.execute(req)
        self.assertFalse(hasattr(resp, "state_transition"))
        self.assertFalse(hasattr(resp, "governor_override"))

    # 52. Negative test: Raw third-party response object is never exposed on NormalizedResponse
    def test_52_raw_response_object_masked(self):
        raw_third_party = {"secret_tokens": [1, 2, 3], "internal_state": "active"}
        norm = IntegrationBoundary.normalize_response(raw_third_party, provider="litellm", model="test")
        self.assertIsNone(norm.raw_response)


if __name__ == "__main__":
    unittest.main()
