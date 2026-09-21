/**
 * Mock Data Provider for INFUSE Frontend (Hardened Baseline).
 * 
 * Provides synthetic ViewModels across all 5 execution states, 7 Governor actions,
 * metric time-series, multi-agent historical runs, and governance policies.
 */

import { IDataProvider } from "./IDataProvider.js";
import {
  ExecutionSummaryViewModel,
  ExecutionMetricsViewModel,
  ExecutionStateViewModel,
  GovernorDecisionViewModel,
  ProviderModelHealthViewModel,
  ExecutionTimelineEventViewModel,
  ExecutionHistoryItemViewModel,
  GovernancePolicyViewModel,
  ExecutionState,
  GovernorAction,
  EventType
} from "../contracts/viewmodels.js";

export class MockDataProvider extends IDataProvider {
  constructor() {
    super();
    this.currentState = ExecutionState.COST_PRESSURE;
    this.activeExecutionId = "exec_01J8K7A2";
    this.policy = new GovernancePolicyViewModel();
    this.historyDatabase = this._initHistoryDatabase();
  }

  _initHistoryDatabase() {
    return [
      new ExecutionHistoryItemViewModel({
        execution_id: "exec_01J8K7A2",
        agent_name: "OpenCode",
        task_preview: "Refactor authentication middleware to use decoupled JWT validators",
        provider: "Anthropic",
        model: "Claude Sonnet",
        status: "RUNNING",
        state: ExecutionState.COST_PRESSURE,
        total_tokens: 69480,
        cost_usd: 0.184,
        runtime_formatted: "08m 42s",
        created_at: "2026-09-21T14:32:18Z"
      }),
      new ExecutionHistoryItemViewModel({
        execution_id: "exec_01J8J691",
        agent_name: "Claude Code",
        task_preview: "Generate OpenAPI 3.1 Swagger specification from FastAPI endpoints",
        provider: "Anthropic",
        model: "Claude Haiku",
        status: "COMPLETED",
        state: ExecutionState.NORMAL,
        total_tokens: 18450,
        cost_usd: 0.024,
        runtime_formatted: "02m 14s",
        created_at: "2026-09-21T13:10:04Z"
      }),
      new ExecutionHistoryItemViewModel({
        execution_id: "exec_01J8H432",
        agent_name: "Codex",
        task_preview: "Database migration for multi-tenant customer isolation schema",
        provider: "DeepSeek",
        model: "DeepSeek Chat",
        status: "COMPLETED",
        state: ExecutionState.NORMAL,
        total_tokens: 42100,
        cost_usd: 0.012,
        runtime_formatted: "04m 50s",
        created_at: "2026-09-21T11:45:30Z"
      }),
      new ExecutionHistoryItemViewModel({
        execution_id: "exec_01J8G219",
        agent_name: "OpenCode",
        task_preview: "Fix memory leak in websocket event loop during rapid disconnects",
        provider: "OpenAI",
        model: "GPT-4o",
        status: "STOPPED",
        state: ExecutionState.RUNAWAY,
        total_tokens: 145000,
        cost_usd: 0.950,
        runtime_formatted: "12m 08s",
        created_at: "2026-09-21T09:12:15Z"
      }),
      new ExecutionHistoryItemViewModel({
        execution_id: "exec_01J8F104",
        agent_name: "Hermes",
        task_preview: "Synthesize quarterly AI infrastructure spend report across 4 clouds",
        provider: "Google Gemini",
        model: "Gemini 1.5 Pro",
        status: "COMPLETED",
        state: ExecutionState.NORMAL,
        total_tokens: 88400,
        cost_usd: 0.115,
        runtime_formatted: "06m 30s",
        created_at: "2026-09-21T07:40:00Z"
      }),
      new ExecutionHistoryItemViewModel({
        execution_id: "exec_01J8E095",
        agent_name: "OpenClaw",
        task_preview: "Deep web verification of vendor security compliance certificates",
        provider: "DeepSeek",
        model: "DeepSeek Chat",
        status: "COMPLETED",
        state: ExecutionState.PROVIDER_CONSTRAINED,
        total_tokens: 54200,
        cost_usd: 0.038,
        runtime_formatted: "05m 12s",
        created_at: "2026-09-21T06:15:22Z"
      }),
      new ExecutionHistoryItemViewModel({
        execution_id: "exec_01J8D980",
        agent_name: "Lovable",
        task_preview: "Generate accessible design tokens for high-contrast dark theme",
        provider: "Anthropic",
        model: "Claude Sonnet",
        status: "COMPLETED",
        state: ExecutionState.NORMAL,
        total_tokens: 31200,
        cost_usd: 0.078,
        runtime_formatted: "03m 45s",
        created_at: "2026-09-21T04:20:10Z"
      })
    ];
  }

  async getExecutionData(executionId = this.activeExecutionId) {
    this.activeExecutionId = executionId;
    const historyItem = this.historyDatabase.find(h => h.execution_id === executionId) || this.historyDatabase[0];

    const summary = new ExecutionSummaryViewModel({
      execution_id: historyItem.execution_id,
      agent_name: historyItem.agent_name,
      task_description: historyItem.task_preview,
      status: historyItem.status,
      is_live: historyItem.status === "RUNNING",
      provider: historyItem.provider,
      model: historyItem.model,
      routing_mode: "Auto-Governor v2",
      isolation_pool: "eu-central-sandbox",
      started_at: historyItem.created_at,
      runtime_seconds: 522,
      formatted_runtime: historyItem.runtime_formatted
    });

    const stateProfiles = {
      [ExecutionState.NORMAL]: {
        display: "NORMAL",
        desc: "Execution progressing stably within standard token, request rate, and cost boundaries.",
        action: GovernorAction.CONTINUE,
        bannerTitle: "Active Regulation: Standard Flow",
        bannerDesc: "Execution permitted to continue without intervention.",
        reasonCodes: ["WITHIN_POLICY_BOUNDS", "HEALTH_OPTIMAL"],
        cost: 0.082,
        budgetPercent: 8.2,
        tokensIn: 18400,
        tokensOut: 3200,
        tokensCached: 12000,
        tokensTotal: 21600,
        rpm: 2.1,
        retries: 0,
        errors: 0
      },
      [ExecutionState.COST_PRESSURE]: {
        display: "COST PRESSURE",
        desc: "Execution cost is approaching the configured policy boundary. Automated throttling and cache compaction algorithms are currently engaged to prevent budget overrun.",
        action: GovernorAction.OPTIMIZE,
        bannerTitle: "Active Regulation: Prompt Compression",
        bannerDesc: "Context compression active to remain within task budget.",
        reasonCodes: ["BUDGET_THRESHOLD_74_PERCENT", "TOKEN_GROWTH_SURGE"],
        cost: 0.184,
        budgetPercent: 18.4,
        tokensIn: 42840,
        tokensOut: 8240,
        tokensCached: 18400,
        tokensTotal: 69480,
        rpm: 4.8,
        retries: 1,
        errors: 0
      },
      [ExecutionState.RUNAWAY]: {
        display: "RUNAWAY",
        desc: "Anomalous recursive tool call loop detected without convergence. Circuit breaker triggered.",
        action: GovernorAction.STOP,
        bannerTitle: "Active Regulation: Circuit-Breaker Halt",
        bannerDesc: "Execution forcibly halted due to infinite tool recursion limit breach.",
        reasonCodes: ["REPETITIVE_TOOL_LOOP_BREACH", "ZERO_CONVERGENCE_SIGNAL"],
        cost: 0.890,
        budgetPercent: 89.0,
        tokensIn: 112000,
        tokensOut: 24000,
        tokensCached: 4000,
        tokensTotal: 136000,
        rpm: 18.5,
        retries: 4,
        errors: 3
      },
      [ExecutionState.QUALITY_DEGRADED]: {
        display: "QUALITY DEGRADED",
        desc: "Syntactic collapse or schema validation errors observed in model completions.",
        action: GovernorAction.ESCALATE,
        bannerTitle: "Active Regulation: Model Tier Escalation",
        bannerDesc: "Escalating model tier to restore structured schema compliance.",
        reasonCodes: ["SCHEMA_VALIDATION_FAILURE", "OUTPUT_DRIFT_DETECTED"],
        cost: 0.220,
        budgetPercent: 22.0,
        tokensIn: 32000,
        tokensOut: 4500,
        tokensCached: 14000,
        tokensTotal: 36500,
        rpm: 3.2,
        retries: 2,
        errors: 1
      },
      [ExecutionState.PROVIDER_CONSTRAINED]: {
        display: "PROVIDER CONSTRAINED",
        desc: "Upstream provider rate limiting (429) and elevated latency observed. Dynamic failover engaged.",
        action: GovernorAction.SWITCH,
        bannerTitle: "Active Regulation: Dynamic Route Switching",
        bannerDesc: "Switching downstream execution to fallback provider due to upstream rate exhaustion.",
        reasonCodes: ["PROVIDER_HTTP_429_RATE_LIMIT", "LATENCY_P95_EXCEEDED"],
        cost: 0.140,
        budgetPercent: 14.0,
        tokensIn: 28000,
        tokensOut: 5200,
        tokensCached: 10000,
        tokensTotal: 33200,
        rpm: 1.2,
        retries: 3,
        errors: 2
      }
    };

    const currentProfile = stateProfiles[this.currentState] || stateProfiles[ExecutionState.NORMAL];

    const state = new ExecutionStateViewModel({
      current_state: this.currentState,
      state_display_name: currentProfile.display,
      description: currentProfile.desc,
      policy_boundary_threshold_percent: 80.0,
      reason_codes: currentProfile.reasonCodes
    });

    const metrics = new ExecutionMetricsViewModel({
      input_tokens: currentProfile.tokensIn,
      cached_tokens: currentProfile.tokensCached,
      output_tokens: currentProfile.tokensOut,
      total_tokens: currentProfile.tokensTotal,
      current_cost_usd: currentProfile.cost,
      budget_limit_usd: 1.00,
      budget_consumed_percent: currentProfile.budgetPercent,
      requests_count: 14,
      requests_per_minute: currentProfile.rpm,
      errors_count: currentProfile.errors,
      retries_count: currentProfile.retries,
      web_requests_count: 6,
      tool_calls_count: 11,
      token_growth_series: [
        { time: "14:32", tokens: 12000, output: 800 },
        { time: "14:34", tokens: 24000, output: 2100 },
        { time: "14:36", tokens: 38000, output: 4200 },
        { time: "14:38", tokens: 52000, output: 6100 },
        { time: "14:40", tokens: currentProfile.tokensTotal, output: currentProfile.tokensOut }
      ],
      cost_series: [
        { time: "14:32", cost: 0.02 },
        { time: "14:34", cost: 0.06 },
        { time: "14:36", cost: 0.11 },
        { time: "14:38", cost: 0.15 },
        { time: "14:40", cost: currentProfile.cost }
      ]
    });

    const governor = new GovernorDecisionViewModel({
      current_action: currentProfile.action,
      action_banner_title: currentProfile.bannerTitle,
      action_banner_description: currentProfile.bannerDesc,
      reason_codes: currentProfile.reasonCodes,
      recent_decisions: [
        { id: "dec_01", time: "14:39:10", action: "OPTIMIZE", reason: "Budget pacing threshold 70% reached" },
        { id: "dec_02", time: "14:36:44", action: "CONTINUE", reason: "Tool call completed within variance bounds" },
        { id: "dec_03", time: "14:32:18", action: "CONTINUE", reason: "Execution initialized via Auto-Governor" }
      ]
    });

    const health = new ProviderModelHealthViewModel({
      provider: summary.provider,
      model: summary.model,
      latency_ms: this.currentState === ExecutionState.PROVIDER_CONSTRAINED ? 2450.0 : 680.0,
      availability_percent: this.currentState === ExecutionState.PROVIDER_CONSTRAINED ? 92.4 : 99.95,
      error_rate_percent: this.currentState === ExecutionState.PROVIDER_CONSTRAINED ? 7.6 : 0.05,
      status: this.currentState === ExecutionState.PROVIDER_CONSTRAINED ? "DEGRADED" : "HEALTHY"
    });

    const timeline = [
      new ExecutionTimelineEventViewModel({
        event_id: "evt_08",
        time_offset: "+08:35",
        event_type: EventType.GOVERNOR_DECISION,
        title: `Governor Decision: ${currentProfile.action}`,
        description: currentProfile.bannerDesc,
        is_governor_decision: true,
        badge_label: currentProfile.action
      }),
      new ExecutionTimelineEventViewModel({
        event_id: "evt_07",
        time_offset: "+08:12",
        event_type: EventType.STATE_CHANGED,
        title: `State Transition: ${currentProfile.display}`,
        description: currentProfile.desc,
        is_state_change: true,
        badge_label: currentProfile.display
      }),
      new ExecutionTimelineEventViewModel({
        event_id: "evt_06",
        time_offset: "+06:40",
        event_type: EventType.TOOL_COMPLETED,
        title: "Tool: write_file",
        description: "Modified /src/middleware/auth.ts (38 lines written, 0 errors)"
      }),
      new ExecutionTimelineEventViewModel({
        event_id: "evt_05",
        time_offset: "+05:15",
        event_type: EventType.WEB_RESPONSE,
        title: "Web Request: GET /v1/jwks.json",
        description: "Status: 200 OK • 2.4KB • 112ms latency"
      }),
      new ExecutionTimelineEventViewModel({
        event_id: "evt_04",
        time_offset: "+03:45",
        event_type: EventType.TOKEN_OBSERVED,
        title: "Token Stream Checkpoint",
        description: "42,840 input tokens, 18,400 cached (hit rate 30.1%)"
      }),
      new ExecutionTimelineEventViewModel({
        event_id: "evt_03",
        time_offset: "+02:10",
        event_type: EventType.TOOL_COMPLETED,
        title: "Tool: grep_codebase",
        description: "Scanned 14 files for 'jwt.verify' references"
      }),
      new ExecutionTimelineEventViewModel({
        event_id: "evt_02",
        time_offset: "+00:45",
        event_type: EventType.TOKEN_OBSERVED,
        title: "Initial Context Ingestion",
        description: "12,400 tokens ingested • Anthropic Claude Sonnet"
      }),
      new ExecutionTimelineEventViewModel({
        event_id: "evt_01",
        time_offset: "+00:00",
        event_type: EventType.EXECUTION_STARTED,
        title: "Execution Started",
        description: `Agent ${summary.agent_name} initialized execution ${summary.execution_id}`
      })
    ];

    return {
      summary,
      metrics,
      state,
      governor,
      health,
      timeline,
      history: this.historyDatabase
    };
  }

  async getGovernancePolicy() {
    return this.policy;
  }

  async saveGovernancePolicy(updatedPolicyData) {
    this.policy = new GovernancePolicyViewModel({
      policy: updatedPolicyData,
      guardrail_strictness_index: "99.98% Strict",
      is_editing: false
    });
    return this.policy;
  }

  async triggerStateChange(executionId, targetState) {
    if (Object.values(ExecutionState).includes(targetState)) {
      this.currentState = targetState;
    }
    return this.getExecutionData(executionId);
  }
}
