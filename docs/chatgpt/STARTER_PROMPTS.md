# ChatGPT Starter Prompts & Few-Shot Templates

Recommended starter prompts and few-shot conversation flows for the INFUSE ChatGPT App.

---

## Starter Conversation Buttons (Quick Prompts)

1. **Check INFUSE System Health**
   > *"Show me the current INFUSE system status, active policy, and registered AI providers."*

2. **List Recent Executions**
   > *"List the last 5 AI executions and tell me if any are experiencing cost pressure or anomalies."*

3. **Inspect Active Governor Policies**
   > *"What budget and anomaly protection rules are configured in our active governance policy?"*

4. **Run a Governed Task**
   > *"Execute a task to analyze Python performance optimization with a preferred model of claude-3-7-sonnet."*

---

## Few-Shot Conversation Flows

### Example 1: Diagnosing an Anomaly & Governor Intervention

**User**:
> *"Execution `exec_8548d99b` seems to be taking longer than expected. Can you inspect it?"*

**ChatGPT Tool Call**:
`inspect_execution(execution_id="exec_8548d99b")`

**ChatGPT Response**:
> **Execution Inspection: `exec_8548d99b`**
>
> - **Status**: `RUNNING` (Runtime: 01m 45s)
> - **Canonical State**: `COST_PRESSURE` ⚠️
> - **Current Tokens**: 24,500 / 30,000 threshold (81.6% consumed)
> - **Estimated Cost**: $0.185 USD
> - **Governor Verdict**: `THROTTLE` (Reason: `POLICY_BUDGET_THRESHOLD_REACHED`)
>
> 💡 *Recommendation*: The Governor has already flagged this execution with `THROTTLE` to pace token generation. Would you like to issue a `THROTTLE` with a 500ms pacing delay, or `SWITCH` to a more cost-effective model?

---

### Example 2: Multi-Provider Health Check

**User**:
> *"Check the health and latency across all connected LLM providers."*

**ChatGPT Tool Call**:
`get_provider_health()`

**ChatGPT Response**:
> **INFUSE Provider Health Matrix**
>
> | Provider | Status | Latency | Error Rate |
> | :--- | :--- | :--- | :--- |
> | **Google Gemini** | 🟢 HEALTHY | 140ms | 0.0% |
> | **LiteLLM Router** | 🟢 HEALTHY | 155ms | 0.0% |
> | **OpenAI** | 🟢 HEALTHY | 165ms | 0.0% |
> | **Anthropic** | 🟢 HEALTHY | 180ms | 0.0% |
> | **DeepSeek** | 🟢 HEALTHY | 210ms | 0.0% |
>
> All 5 providers are operating within normal latency SLAs with 0% error rates.
