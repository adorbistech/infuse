# Authentication and Multi-Tenant Isolation

Comprehensive specification for securing and isolating the INFUSE ChatGPT App.

---

## Supported Authentication Modes

The INFUSE ChatGPT App supports three authentication modes configured via `INFUSE_CHATGPT_AUTH_MODE`:

1. `BEARER` (Default for OpenAI Custom GPTs): Static API Key or Comma-Separated Key Rotation Ring.
2. `OAUTH2`: Bearer JWT token with standard claim decoding (`sub`, `aud`, `iss`, `tenant_id`, `scope`).
3. `NONE`: Development and unauthenticated testing mode.

---

## 1. Bearer Token Authentication (API Key)

In standard Custom GPT Actions, the API key is passed in the `Authorization` header:

```http
Authorization: Bearer <INFUSE_API_KEY>
```

### Key Rotation & Multiple Keys
To support zero-downtime key rotation or multi-client access, `INFUSE_CHATGPT_API_KEY` accepts a comma-separated list of valid keys:

```bash
export INFUSE_CHATGPT_API_KEY="key_prod_active_v2,key_prod_retiring_v1"
```

The gateway checks incoming keys using constant-time comparisons (`hmac.compare_digest`) to prevent timing attacks.

---

## 2. OAuth2 / JWT Authentication

When deployed in enterprise environments with an OAuth2 Identity Provider (e.g. Auth0, Okta, Azure AD):

- Tokens are validated against configured `audience` and `issuer`.
- Claims extracted automatically:
  - `tenant_id`: Maps to execution isolation pools.
  - `user_id`: Attributed in execution contexts.
  - `scope` / `scp`: Enforced against endpoint RBAC requirements.

---

## 3. RBAC Scopes Matrix

| Scope | Endpoints Authorized |
| :--- | :--- |
| `read:executions` | `GET /chatgpt/v1/system`<br>`GET /chatgpt/v1/executions`<br>`GET /chatgpt/v1/executions/{id}/state`<br>`GET /chatgpt/v1/executions/{id}/result`<br>`GET /chatgpt/v1/executions/{id}/inspect`<br>`GET /chatgpt/v1/executions/{id}/governor`<br>`GET /chatgpt/v1/providers/health` |
| `read:policies` | `GET /chatgpt/v1/policies`<br>`GET /chatgpt/v1/policies/{id}` |
| `execute:tasks` | `POST /chatgpt/v1/execute` |
| `control:write` | `POST /chatgpt/v1/control` |

If a client attempts to invoke an endpoint without the required scope, INFUSE immediately returns:

```http
HTTP/1.1 403 Forbidden
Content-Type: application/json

{
  "success": false,
  "tool_name": "execute_task",
  "category": "EXECUTE",
  "error": "Forbidden: Token lacks required scope 'execute:tasks'",
  "error_code": "FORBIDDEN"
}
```

---

## 4. Multi-Tenant Isolation Guarantees

1. **Isolation at Query Boundary**: When a user queries `list_executions`, results are filtered strictly by `isolation_pool == context.tenant_id`. Executions belonging to Tenant Alpha are invisible to Tenant Beta.
2. **Isolation at Execution Boundary**: New tasks submitted via `execute_task` automatically stamp `isolation_pool=context.tenant_id` onto the `ExecutionContext`.
3. **Admin Exemption**: Tokens bearing `tenant_id == "admin"` can view cluster-wide executions for operational diagnostics.
