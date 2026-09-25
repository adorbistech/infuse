# Deployment & Operations Runbook

Operational runbook for hosting the INFUSE ChatGPT App in staging and production environments.

---

## Environment Variables Configuration

| Variable | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `INFUSE_CHATGPT_AUTH_MODE` | `string` | `bearer` | Auth mode: `bearer`, `oauth2`, or `none`. |
| `INFUSE_CHATGPT_API_KEY` | `string` | `""` | Valid API key(s) for Custom GPT. Comma-separated for key rotation. |
| `INFUSE_PUBLIC_URL` | `string` | `""` | Publicly accessible HTTPS base URL (e.g. `https://infuse.yourdomain.com`). |
| `INFUSE_API_URL` | `string` | `http://localhost:8000` | URL of upstream INFUSE core API if running as standalone proxy. |
| `INFUSE_CHATGPT_OAUTH_AUDIENCE`| `string` | `""` | Expected JWT audience if using OAuth2 mode. |
| `INFUSE_CHATGPT_OAUTH_ISSUER` | `string` | `""` | Expected JWT issuer if using OAuth2 mode. |

---

## Production Deployment Options

### Option 1: Integrated Deployment (Unified Server)

In the default configuration, `/chatgpt` endpoints are mounted directly onto the main INFUSE Starlette server (`infuse.deployment.server`).

```bash
export INFUSE_HOST="0.0.0.0"
export INFUSE_PORT="8000"
export INFUSE_CHATGPT_AUTH_MODE="bearer"
export INFUSE_CHATGPT_API_KEY="sk_live_prod_secret_key"
export INFUSE_PUBLIC_URL="https://infuse.yourdomain.com"

# Launch unified server
python3 -m infuse.deployment.server
```

### Option 2: Docker / Container Deployment

```dockerfile
# Run the official INFUSE container with ChatGPT environment variables
docker run -d \
  -p 8000:8000 \
  -e INFUSE_CHATGPT_AUTH_MODE=bearer \
  -e INFUSE_CHATGPT_API_KEY=sk_live_prod_secret_key \
  -e INFUSE_PUBLIC_URL=https://infuse.yourdomain.com \
  --name infuse-server \
  infuse:latest
```

---

## Reverse Proxy / Cloudflare / Nginx Setup

Ensure that your reverse proxy forwards the `Authorization` header and terminates TLS cleanly:

```nginx
server {
    listen 443 ssl http2;
    server_name infuse.yourdomain.com;

    ssl_certificate /etc/letsencrypt/live/infuse.yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/infuse.yourdomain.com/privkey.pem;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto https;
        proxy_set_header Authorization $http_authorization;
        proxy_pass_header Authorization;
    }
}
```

---

## Health Check & Verification

Verify the live deployment by running:

```bash
curl -i https://infuse.yourdomain.com/health
curl -i https://infuse.yourdomain.com/chatgpt/openapi.json
curl -i -H "Authorization: Bearer sk_live_prod_secret_key" https://infuse.yourdomain.com/chatgpt/v1/system
```
