# INFUSE Public ChatGPT Plugin Directory Submission Checklist

This checklist tracks automated engineering deliverables and operator actions required to submit INFUSE to the OpenAI Public Directory.

---

## 1. Automated Architecture & Code Verification

| Status | Verification Item | Subsystem / Location |
| :---: | :--- | :--- |
| ✅ **IMPLEMENTED** | Remote MCP Streamable HTTP transport on `/mcp` | `infuse/deployment/server.py` |
| ✅ **IMPLEMENTED** | Protocol version `2024-11-05` compliance | `infuse/mcp/server.py` |
| ✅ **IMPLEMENTED** | All 12 tools annotated (`readOnlyHint`, `destructiveHint`, `openWorldHint`) | `infuse/mcp/tools.py` |
| ✅ **IMPLEMENTED** | Execution Control Boundary mediation for all control operations | `infuse/control/boundary.py` |
| ✅ **IMPLEMENTED** | Domain challenge endpoint `/.well-known/openai-apps-challenge` | `infuse/deployment/server.py` |
| ✅ **IMPLEMENTED** | Multi-tenant isolation through MCP tool handling | `tests/chatgpt/test_chatgpt_mcp_plugin.py` |
| ✅ **IMPLEMENTED** | Zero regressions against frozen v0.1.0 baseline (1,277 passing tests) | Full test suite |
| ✅ **IMPLEMENTED** | OpenAPI 3.1 & Custom GPT Action compatibility router `/chatgpt` | `infuse/chatgpt/router.py` |

---

## 2. Directory Submission Test Cases

### Positive Test Cases (5/5 Certified)
1. **MCP Handshake (`initialize`)**:
   - Sends JSON-RPC 2.0 initialize request.
   - Verifies HTTP 200, `mcp-session-id` header returned, and `protocolVersion: 2024-11-05` acknowledged.
2. **Tool Discovery (`tools/list`)**:
   - Enumerates tool catalog.
   - Verifies exact 12 tools present with typed `ToolAnnotations`.
3. **Execution State Inspection (`infuse_get_execution_state`)**:
   - Queries state of execution run.
   - Verifies canonical state (`NORMAL`, `RUNAWAY`, `COST_PRESSURE`, `BUDGET_EXCEEDED`, `TERMINATED`) and reason codes.
4. **Execution List Filtering (`infuse_list_executions`)**:
   - Filters executions across query and state parameters.
   - Returns paginated execution view models with total count.
5. **Governed Task Execution (`infuse_execute`)**:
   - Dispatches execution request through SDK.
   - Returns token count, latency, cost metrics, and Governor regulation result.

### Negative Test Cases (3/3 Certified)
1. **Invalid / Unknown Tool Call**:
   - Invocations of non-existent tool names return clean error responses without server crash.
2. **Malformed JSON-RPC & Parameter Validation**:
   - Invalid payload parameters trigger structured validation errors with error codes.
3. **Unauthenticated / Domain Challenge Miss**:
   - Unconfigured domain verification returns 404; unauthorized host headers are rejected by transport security.

---

## 3. Operator / Human Action Checklist (OpenAI Developer Portal)

These tasks must be performed by the release administrator on the OpenAI Developer Portal:

- [ ] **DNS & TLS Setup**: Ensure production domain (e.g. `api.infuse.adorbis.com`) is pointing to the live server with a valid TLS certificate.
- [ ] **Set Challenge Token**: Populate `OPENAI_APPS_CHALLENGE_TOKEN` environment variable on the server from the OpenAI developer dashboard.
- [ ] **Domain Verification**: Trigger domain verification check in OpenAI portal against `https://<domain>/.well-known/openai-apps-challenge`.
- [ ] **Register Remote MCP Endpoint**: Enter `https://<domain>/mcp` into the OpenAI Plugin / App registration screen.
- [ ] **Upload Assets**: Upload `infuse-logo.svg`, descriptions, privacy policy link, and terms link.
- [ ] **Submit for Directory Review**: Click "Submit for Public Directory Review".
