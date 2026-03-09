# Production environment template (AWS / Docker)

Use this as a checklist for variables required by `docker-compose.production.yml` and the CS Pulse platform. Set them via a `.env` file on the deploy host, or via AWS SSM Parameter Store / Secrets Manager (inject into the container at runtime).

## Required (must set before first deploy)

| Variable | Description | Example / notes |
|----------|-------------|------------------|
| `POSTGRES_PASSWORD` | PostgreSQL password for user `cspulse` | Strong password, min 32 chars. **Never use** the default `cspulse_dev` from the Postgres Dockerfile in production. |
| `SECRET_KEY` | Flask session signing key | Min 32 characters. Generate: `python -c "import secrets; print(secrets.token_hex(32))"` |
| `OPENAI_API_KEY` | OpenAI API key | From OpenAI dashboard. |
| `ANTHROPIC_API_KEY` | Anthropic API key | For Claude / agent features. |

## Optional (sensible defaults in compose)

| Variable | Description | Default in compose |
|----------|-------------|--------------------|
| `GUNICORN_WORKERS` | Number of Gunicorn workers | `4` |
| `GUNICORN_TIMEOUT` | Request timeout (seconds) | `180` |

## Do not set in production

| Variable | Reason |
|----------|--------|
| `FLASK_DEBUG=true` | Keeps debug mode off; do not enable in production. |
| `FLASK_ENV=development` | Use `production` (or unset so production config is used). |

## Load driver (when run locally or on EC2-B)

| Variable | Description |
|----------|-------------|
| `CS_PULSE_BASE_URL` | Base URL of the CS Pulse app (e.g. `https://www.auctusai.ai/CSPulseV6` or `http://localhost:80`). |
| `LOG_LEVEL` | Optional; e.g. `INFO`. |

## Example `.env` for production (do not commit)

```bash
# Copy this block to .env on the deploy host; fill in real values.
POSTGRES_PASSWORD=your-strong-postgres-password-min-32-chars
SECRET_KEY=your-flask-secret-key-min-32-chars
OPENAI_API_KEY=sk-your-openai-key
ANTHROPIC_API_KEY=your-anthropic-key

# Optional
GUNICORN_WORKERS=4
GUNICORN_TIMEOUT=180
```

## AWS: using SSM or Secrets Manager

- Store each secret in Parameter Store (SecureString) or Secrets Manager.
- In ECS task definitions (or EC2 user-data / startup script), inject them as environment variables into the `cs-pulse` and `postgres` services.
- Never bake these values into Docker images or commit them to git.
