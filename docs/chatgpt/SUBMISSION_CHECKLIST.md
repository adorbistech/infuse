# OpenAI App / GPT Store Submission Checklist

Use this verification checklist prior to submitting the **INFUSE ChatGPT App** to the OpenAI GPT Store or OpenAI App Directory.

---

## 1. OpenAPI Specification & Schema Validation

- [x] Schema is served with `Content-Type: application/json` at `/chatgpt/openapi.json`.
- [x] Schema version adheres to OpenAPI 3.1.0 specifications.
- [x] Every action defines a distinct, descriptive `operationId`.
- [x] All parameters have explicit `description` and `schema` constraints.
- [x] All response types are documented under `200 OK`, `401 Unauthorized`, and `422 Unprocessable Entity`.
- [x] Zero unresolved `$ref` pointers.

---

## 2. Authentication & Security Gate

- [x] Custom GPT action authentication is configured with **API Key / Bearer Token**.
- [x] Key rotation supported via comma-delimited secret configuration.
- [x] Authentication requests lacking a valid token return `401 Unauthorized`.
- [x] Constant-time comparison (`hmac.compare_digest`) protects against timing attacks.
- [x] Rate limiting, prompt injection resistance, and SSRF defenses are verified.

---

## 3. Privacy & Compliance

- [x] Privacy Policy is publicly hosted at `https://adorbistech.com/privacy`.
- [x] Terms of Service is publicly hosted at `https://adorbistech.com/terms`.
- [x] Actions do not leak internal infrastructure secrets, local system file paths, or credentials.
- [x] User telemetry and execution payloads respect tenant isolation boundaries.

---

## 4. Operational & Performance Verification

- [x] Server responds to health checks within < 50ms.
- [x] Automated test suite passes 100% (1,222 Python + 49 Frontend = 1,271 tests).
- [x] Cross-interface vocabulary parity (`NORMAL`, `COST_PRESSURE`, `RUNAWAY`, `QUALITY_DEGRADED`, `PROVIDER_CONSTRAINED` & `CONTINUE`, `OPTIMIZE`, `ESCALATE`, `DOWNGRADE`, `SWITCH`, `THROTTLE`, `STOP`) verified across all interfaces.
