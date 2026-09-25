# INFUSE Remote MCP Production Endpoint Specification

## 1. Production Endpoint URL

The primary public-facing Remote MCP endpoint for OpenAI Directory submission is:

```
https://<your-infuse-domain>/mcp
```

- **Protocol**: MCP `2024-11-05` over Streamable HTTP (and Server-Sent Events).
- **Transport Security**: TLS 1.3 / HTTPS enforced. Host DNS-rebinding protection enabled.
- **Port**: Default HTTPS (443).

---

## 2. Handshake and Session Lifecycle

### 2.1 Initialization Request (`POST /mcp`)
ChatGPT sends a JSON-RPC 2.0 `initialize` request with client capabilities:

```http
POST /mcp HTTP/1.1
Host: api.infuse.adorbis.com
Content-Type: application/json
Accept: application/json, text/event-stream

{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "initialize",
  "params": {
    "protocolVersion": "2024-11-05",
    "capabilities": {
      "roots": { "listChanged": true },
      "sampling": {}
    },
    "clientInfo": {
      "name": "chatgpt-plugin-client",
      "version": "1.0.0"
    }
  }
}
```

### 2.2 Initialization Response
The INFUSE production gateway responds with server capabilities and assigns an `mcp-session-id`:

```http
HTTP/1.1 200 OK
Content-Type: text/event-stream
mcp-session-id: sess_94a8f3b20c91
cache-control: no-cache

event: message
data: {"jsonrpc":"2.0","id":1,"result":{"protocolVersion":"2024-11-05","capabilities":{"tools":{"listChanged":false},"resources":{"subscribe":false,"listChanged":false},"prompts":{"listChanged":false}},"serverInfo":{"name":"infuse","version":"0.1.0"}}}
```

### 2.3 Subsequent Requests
All subsequent tool invocations must pass the returned `mcp-session-id` header:

```http
POST /mcp HTTP/1.1
Host: api.infuse.adorbis.com
Content-Type: application/json
mcp-session-id: sess_94a8f3b20c91
Accept: application/json, text/event-stream

{
  "jsonrpc": "2.0",
  "id": 2,
  "method": "tools/call",
  "params": {
    "name": "infuse_get_execution_state",
    "arguments": {
      "execution_id": "exec_demo_01"
    }
  }
}
```

---

## 3. Tool Catalog and Annotations

The INFUSE MCP endpoint registers 12 authoritative tools with standardized OpenAI `ToolAnnotations`:

| Tool Name | Type | readOnlyHint | destructiveHint | openWorldHint |
| :--- | :--- | :---: | :---: | :---: |
| `infuse_execute` | Execution | `false` | `false` | `false` |
| `infuse_get_execution` | Read | `true` | `false` | `false` |
| `infuse_get_execution_state` | Read | `true` | `false` | `false` |
| `infuse_get_execution_result` | Read | `true` | `false` | `false` |
| `infuse_list_executions` | Read | `true` | `false` | `false` |
| `infuse_list_events` | Read | `true` | `false` | `false` |
| `infuse_publish_event` | Mutation | `false` | `false` | `false` |
| `infuse_get_policy` | Read | `true` | `false` | `false` |
| `infuse_list_policies` | Read | `true` | `false` | `false` |
| `infuse_update_policy` | Mutation | `false` | `false` | `false` |
| `infuse_get_governor_decision` | Read | `true` | `false` | `false` |
| `infuse_control` | Control | `false` | `true` | `false` |

---

## 4. Reverse Proxy and Deployment Configuration (Nginx / Caddy)

### 4.1 Nginx Streamable HTTP Configuration
When deploying behind Nginx, configure chunked transfer and SSE streaming:

```nginx
server {
    listen 443 ssl http2;
    server_name api.infuse.adorbis.com;

    ssl_certificate /etc/letsencrypt/live/api.infuse.adorbis.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/api.infuse.adorbis.com/privkey.pem;

    # OpenAI Apps Domain Challenge Verification
    location /.well-known/openai-apps-challenge {
        proxy_pass http://127.0.0.1:8000/.well-known/openai-apps-challenge;
        proxy_set_header Host $host;
    }

    # Remote MCP Streamable HTTP endpoint
    location /mcp {
        proxy_pass http://127.0.0.1:8000/mcp;
        proxy_http_version 1.1;
        proxy_set_header Connection "";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # Disable buffering for live streaming
        proxy_buffering off;
        proxy_cache off;
        proxy_read_timeout 86400s;
        proxy_send_timeout 86400s;
    }
}
```
