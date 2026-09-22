/**
 * INFUSE Frontend ViewModel Contracts.
 * 
 * These JavaScript contract classes map 1:1 to Block 00 Python contracts (infuse.contracts.frontend).
 * Decouples the UI layer from database schemas and runtime internals.
 */

export const ExecutionState = Object.freeze({
  NORMAL: "NORMAL",
  COST_PRESSURE: "COST_PRESSURE",
  RUNAWAY: "RUNAWAY",
  QUALITY_DEGRADED: "QUALITY_DEGRADED",
  PROVIDER_CONSTRAINED: "PROVIDER_CONSTRAINED"
});

export const ExecutionActionState = Object.freeze({
  OPTIMIZED: "OPTIMIZED",
  THROTTLED: "THROTTLED",
  SWITCHED: "SWITCHED",
  STOPPED: "STOPPED"
});

export const GovernorAction = Object.freeze({
  CONTINUE: "CONTINUE",
  OPTIMIZE: "OPTIMIZE",
  ESCALATE: "ESCALATE",
  DOWNGRADE: "DOWNGRADE",
  SWITCH: "SWITCH",
  THROTTLE: "THROTTLE",
  STOP: "STOP"
});

export const EventType = Object.freeze({
  EXECUTION_STARTED: "ExecutionStarted",
  EXECUTION_COMPLETED: "ExecutionCompleted",
  EXECUTION_FAILED: "ExecutionFailed",
  TOKEN_OBSERVED: "TokenObserved",
  USAGE_UPDATED: "UsageUpdated",
  TOOL_CALLED: "ToolCalled",
  TOOL_COMPLETED: "ToolCompleted",
  WEB_REQUEST: "WebRequest",
  WEB_RESPONSE: "WebResponse",
  RETRY_STARTED: "RetryStarted",
  GOVERNOR_DECISION: "GovernorDecision",
  CONTROL_ACTION_ISSUED: "ControlActionIssued"
});

export const DataStatus = Object.freeze({
  IDLE: "IDLE",
  LOADING: "LOADING",
  LOADED: "LOADED",
  EMPTY: "EMPTY",
  ERROR: "ERROR"
});

/**
 * Normalized application error representation for frontend UI state.
 */
export class AppError {
  constructor(message, code = "UNKNOWN_ERROR", details = null) {
    this.message = message || "An unexpected error occurred.";
    this.code = code;
    this.details = details;
    this.timestamp = new Date().toISOString();
  }
}

/**
 * Top Execution context card ViewModel.
 */
export class ExecutionSummaryViewModel {
  constructor(data = {}) {
    this.execution_id = data.execution_id || "";
    this.agent_name = data.agent_name || "Unknown Agent";
    this.task_description = data.task_description || "";
    this.status = data.status || "RUNNING";
    this.is_live = data.is_live !== undefined ? data.is_live : true;
    this.provider = data.provider || "Unknown Provider";
    this.model = data.model || "Unknown Model";
    this.routing_mode = data.routing_mode || "Auto-Governor";
    this.isolation_pool = data.isolation_pool || "default-pool";
    this.started_at = data.started_at || new Date().toISOString();
    this.runtime_seconds = data.runtime_seconds || 0;
    this.formatted_runtime = data.formatted_runtime || "00m 00s";
  }
}

/**
 * 8-Card metrics grid & chart telemetry ViewModel.
 */
export class ExecutionMetricsViewModel {
  constructor(data = {}) {
    this.input_tokens = data.input_tokens || 0;
    this.cached_tokens = data.cached_tokens || 0;
    this.output_tokens = data.output_tokens || 0;
    this.total_tokens = data.total_tokens || 0;
    this.current_cost_usd = data.current_cost_usd || 0.0;
    this.budget_limit_usd = data.budget_limit_usd !== undefined ? data.budget_limit_usd : 1.0;
    this.budget_consumed_percent = data.budget_consumed_percent || 0.0;
    this.requests_count = data.requests_count || 0;
    this.requests_per_minute = data.requests_per_minute || 0.0;
    this.errors_count = data.errors_count || 0;
    this.retries_count = data.retries_count || 0;
    this.web_requests_count = data.web_requests_count || 0;
    this.tool_calls_count = data.tool_calls_count || 0;
    this.token_growth_series = data.token_growth_series || [];
    this.cost_series = data.cost_series || [];
  }
}

/**
 * Execution State section ViewModel.
 */
export class ExecutionStateViewModel {
  constructor(data = {}) {
    this.current_state = data.current_state || ExecutionState.NORMAL;
    this.state_display_name = data.state_display_name || this.current_state;
    this.description = data.description || "Execution progressing within standard policy bounds.";
    this.policy_boundary_threshold_percent = data.policy_boundary_threshold_percent || 80.0;
    this.reason_codes = data.reason_codes || [];
    this.available_states = data.available_states || Object.values(ExecutionState);
  }
}

/**
 * Governor decision & action panel ViewModel.
 */
export class GovernorDecisionViewModel {
  constructor(data = {}) {
    this.current_action = data.current_action || GovernorAction.CONTINUE;
    this.action_banner_title = data.action_banner_title || "Active Regulation: Standard";
    this.action_banner_description = data.action_banner_description || "Execution permitted to continue without intervention.";
    this.reason_codes = data.reason_codes || [];
    this.recent_decisions = data.recent_decisions || [];
  }
}

/**
 * Provider / Model health status ViewModel.
 */
export class ProviderModelHealthViewModel {
  constructor(data = {}) {
    this.provider = data.provider || "Anthropic";
    this.model = data.model || "Claude Sonnet";
    this.latency_ms = data.latency_ms || 0.0;
    this.availability_percent = data.availability_percent !== undefined ? data.availability_percent : 100.0;
    this.error_rate_percent = data.error_rate_percent || 0.0;
    this.status = data.status || "HEALTHY";
  }
}

/**
 * Single timeline event ViewModel.
 */
export class ExecutionTimelineEventViewModel {
  constructor(data = {}) {
    this.event_id = data.event_id || "";
    this.timestamp = data.timestamp || new Date().toISOString();
    this.time_offset = data.time_offset || "+00:00";
    this.event_type = data.event_type || EventType.TOKEN_OBSERVED;
    this.title = data.title || "";
    this.description = data.description || "";
    this.is_state_change = !!data.is_state_change;
    this.is_governor_decision = !!data.is_governor_decision;
    this.badge_label = data.badge_label || null;
    this.metadata = data.metadata || {};
  }
}

/**
 * Execution history row ViewModel.
 */
export class ExecutionHistoryItemViewModel {
  constructor(data = {}) {
    this.execution_id = data.execution_id || "";
    this.agent_name = data.agent_name || "";
    this.task_preview = data.task_preview || "";
    this.provider = data.provider || "";
    this.model = data.model || "";
    this.status = data.status || "COMPLETED";
    this.state = data.state || ExecutionState.NORMAL;
    this.total_tokens = data.total_tokens || 0;
    this.cost_usd = data.cost_usd || 0.0;
    this.runtime_formatted = data.runtime_formatted || "00m 00s";
    this.created_at = data.created_at || new Date().toISOString();
  }
}

/**
 * Normalized container ViewModel bundling complete execution telemetry for a single run.
 */
export class ExecutionBundleViewModel {
  constructor(data = {}) {
    this.summary = data.summary instanceof ExecutionSummaryViewModel ? data.summary : new ExecutionSummaryViewModel(data.summary || {});
    this.metrics = data.metrics instanceof ExecutionMetricsViewModel ? data.metrics : new ExecutionMetricsViewModel(data.metrics || {});
    this.state = data.state instanceof ExecutionStateViewModel ? data.state : new ExecutionStateViewModel(data.state || {});
    this.governor = data.governor instanceof GovernorDecisionViewModel ? data.governor : new GovernorDecisionViewModel(data.governor || {});
    this.health = data.health instanceof ProviderModelHealthViewModel ? data.health : new ProviderModelHealthViewModel(data.health || {});
    this.timeline = Array.isArray(data.timeline) 
      ? data.timeline.map(t => t instanceof ExecutionTimelineEventViewModel ? t : new ExecutionTimelineEventViewModel(t))
      : [];
    this.history = Array.isArray(data.history)
      ? data.history.map(h => h instanceof ExecutionHistoryItemViewModel ? h : new ExecutionHistoryItemViewModel(h))
      : [];
  }
}

/**
 * Governance Policy configuration ViewModel.
 */
export class GovernancePolicyViewModel {
  constructor(data = {}) {
    this.policy = data.policy || {
      policy_id: "pol_default",
      name: "Default Execution Policy",
      version: "1.0.4",
      is_active: true,
      last_saved_at: "2026-09-21T12:00:00Z",
      budget: {
        max_cost_per_task: 10.00,
        max_cost_per_day: 150.00,
        max_cost_per_month: 2500.00,
        currency: "USD"
      },
      tokens: {
        max_input_tokens: 128000,
        max_output_tokens: 8192,
        max_total_tokens: 136192
      },
      requests: {
        max_rpm: 60,
        max_requests_per_task: 25
      },
      runtime: {
        max_execution_time_seconds: 1800
      },
      providers: {
        allowed_providers: ["anthropic", "openai", "gemini", "deepseek"],
        allowed_models: ["claude-3-5-sonnet", "gpt-4o", "gemini-1.5-pro", "deepseek-chat"],
        blocked_providers: [],
        blocked_models: []
      },
      web: {
        enabled: true,
        allowed_domains: ["*"],
        blocked_domains: ["*.internal", "*.crypto-mining.pool"],
        max_web_requests_per_task: 20
      },
      tools: {
        enabled: true,
        allowed_tools: ["*"],
        blocked_tools: ["shell_root_exec", "eval_raw_code"],
        max_tool_calls_per_task: 50,
        max_consecutive_tool_failures: 3
      },
      retries: {
        max_retries: 3,
        backoff_factor: 1.5,
        retry_on_errors: ["rate_limit", "timeout", "503_service_unavailable"],
        fallback_provider_on_failure: true
      },
      anomaly: {
        token_velocity_surge_threshold: 500,
        repetitive_loop_threshold: 4,
        circuit_breaker_enabled: true
      },
      actions: {
        budget_action: GovernorAction.OPTIMIZE,
        token_action: GovernorAction.OPTIMIZE,
        request_action: GovernorAction.THROTTLE,
        runtime_action: GovernorAction.STOP,
        provider_failure_action: GovernorAction.SWITCH,
        anomaly_action: GovernorAction.STOP
      }
    };
    this.guardrail_strictness_index = data.guardrail_strictness_index || "99.98% Strict";
    this.is_editing = !!data.is_editing;
    this.has_unsaved_changes = !!data.has_unsaved_changes;
    this.last_saved_at = data.last_saved_at || this.policy.last_saved_at || new Date().toISOString();
    this.validation_errors = data.validation_errors || [];
    this.available_actions = data.available_actions || [
      GovernorAction.CONTINUE,
      GovernorAction.OPTIMIZE,
      GovernorAction.ESCALATE,
      GovernorAction.DOWNGRADE,
      GovernorAction.SWITCH,
      GovernorAction.THROTTLE,
      GovernorAction.STOP
    ];
  }
}

/**
 * Client-side UX validation helper for GovernancePolicy representation.
 * Prevents obvious malformed values before mock persistence / API dispatch.
 * 
 * @param {Object} policy 
 * @returns {{isValid: boolean, errors: string[]}}
 */
export function validateGovernancePolicy(policy) {
  const errors = [];
  if (!policy) {
    return { isValid: false, errors: ["Policy data is missing or empty."] };
  }

  // Budget validation
  if (policy.budget) {
    if (policy.budget.max_cost_per_task !== undefined && policy.budget.max_cost_per_task < 0) {
      errors.push("Budget max cost per task cannot be negative.");
    }
    if (policy.budget.max_cost_per_day !== undefined && policy.budget.max_cost_per_day < 0) {
      errors.push("Budget max cost per day cannot be negative.");
    }
    if (policy.budget.max_cost_per_month !== undefined && policy.budget.max_cost_per_month < 0) {
      errors.push("Budget max cost per month cannot be negative.");
    }
  }

  // Token validation
  if (policy.tokens) {
    if (policy.tokens.max_input_tokens !== undefined && policy.tokens.max_input_tokens < 0) {
      errors.push("Max input tokens cannot be negative.");
    }
    if (policy.tokens.max_output_tokens !== undefined && policy.tokens.max_output_tokens < 0) {
      errors.push("Max output tokens cannot be negative.");
    }
    if (policy.tokens.max_total_tokens !== undefined && policy.tokens.max_total_tokens < 0) {
      errors.push("Max total tokens cannot be negative.");
    }
    if (
      policy.tokens.max_total_tokens !== undefined &&
      policy.tokens.max_input_tokens !== undefined &&
      policy.tokens.max_total_tokens < policy.tokens.max_input_tokens
    ) {
      errors.push("Max total tokens should not be less than max input tokens.");
    }
  }

  // Request validation
  if (policy.requests) {
    if (policy.requests.max_rpm !== undefined && policy.requests.max_rpm < 1) {
      errors.push("Max requests per minute (RPM) must be at least 1.");
    }
    if (policy.requests.max_requests_per_task !== undefined && policy.requests.max_requests_per_task < 1) {
      errors.push("Max requests per task must be at least 1.");
    }
  }

  // Runtime validation
  if (policy.runtime) {
    if (policy.runtime.max_execution_time_seconds !== undefined && policy.runtime.max_execution_time_seconds < 1) {
      errors.push("Max execution time must be at least 1 second.");
    }
  }

  // Retries validation
  if (policy.retries) {
    if (policy.retries.max_retries !== undefined && policy.retries.max_retries < 0) {
      errors.push("Max retries cannot be negative.");
    }
    if (policy.retries.backoff_factor !== undefined && policy.retries.backoff_factor < 1.0) {
      errors.push("Backoff factor must be at least 1.0.");
    }
  }

  // Anomaly validation
  if (policy.anomaly) {
    if (policy.anomaly.token_velocity_surge_threshold !== undefined && policy.anomaly.token_velocity_surge_threshold < 0) {
      errors.push("Token velocity surge threshold cannot be negative.");
    }
    if (policy.anomaly.repetitive_loop_threshold !== undefined && policy.anomaly.repetitive_loop_threshold < 1) {
      errors.push("Repetitive loop threshold must be at least 1.");
    }
  }

  // Canonical Action Vocabulary validation
  const validActions = Object.values(GovernorAction);
  if (policy.actions) {
    for (const [key, actionVal] of Object.entries(policy.actions)) {
      if (actionVal && !validActions.includes(actionVal)) {
        errors.push(`Action '${actionVal}' for '${key}' is not a canonical GovernorAction.`);
      }
    }
  }

  return {
    isValid: errors.length === 0,
    errors
  };
}
