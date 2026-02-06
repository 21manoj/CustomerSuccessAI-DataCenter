# Qdrant Cloud Setup Guide

This guide explains how to configure the backend to use Qdrant Cloud.

## Configuration

### Environment Variables

Set the following environment variables to connect to Qdrant Cloud:

```bash
# Qdrant Cloud URL (required for cloud)
QDRANT_URL=https://7528cec3-24f4-4584-bee2-ca371726134a.us-east-1-1.aws.cloud.qdrant.io

# Qdrant Cloud API Key (required for cloud)
QDRANT_API_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJhY2Nlc3MiOiJtIn0.8t-hHzNql_9C-BEBs2Pye0l942C6HbBvz7Ro_DDKEH4
```

### Option 1: Set in .env file

Create or update `.env` file in the backend directory:

```bash
QDRANT_URL=https://7528cec3-24f4-4584-bee2-ca371726134a.us-east-1-1.aws.cloud.qdrant.io
QDRANT_API_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJhY2Nlc3MiOiJtIn0.8t-hHzNql_9C-BEBs2Pye0l942C6HbBvz7Ro_DDKEH4
```

### Option 2: Export in shell

```bash
export QDRANT_URL=https://7528cec3-24f4-4584-bee2-ca371726134a.us-east-1-1.aws.cloud.qdrant.io
export QDRANT_API_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJhY2Nlc3MiOiJtIn0.8t-hHzNql_9C-BEBs2Pye0l942C6HbBvz7Ro_DDKEH4
```

## Connection Priority

The system checks for Qdrant configuration in this order:

1. **QDRANT_URL** (Qdrant Cloud) - Takes highest priority
2. **QDRANT_HOST + QDRANT_PORT** (Self-hosted remote)
3. **localhost:6333** (Local Qdrant server)
4. **Local file storage** (Fallback if no server available)

## Verification

After setting the environment variables, restart the backend and check the logs:

```
✅ Connected to Qdrant Cloud: https://7528cec3-24f4-4584-bee2-ca371726134a.us-east-1-1.aws.cloud.qdrant.io
```

## Testing Connection

You can test the connection by:

1. Building the knowledge base:
   ```bash
   curl -X POST http://localhost:8005/api/rag-qdrant/build \
     -H "X-Customer-ID: 5" \
     -H "Content-Type: application/json"
   ```

2. Running a query:
   ```bash
   curl -X POST http://localhost:8005/api/rag-qdrant/query \
     -H "X-Customer-ID: 5" \
     -H "Content-Type: application/json" \
     -d '{"query": "Which accounts have the highest revenue?", "query_type": "general"}'
   ```

## Security Notes

- **API Key**: Keep your QDRANT_API_KEY secure and never commit it to version control
- **Collections**: The system automatically creates per-customer collections for tenant isolation
- **HTTPS**: Qdrant Cloud uses HTTPS for secure connections

## Troubleshooting

### Connection Failed

If you see "Qdrant connection failed", check:
- QDRANT_URL is set correctly (must be HTTPS for cloud)
- QDRANT_API_KEY is set and valid
- Network connectivity to Qdrant Cloud
- Firewall rules allow outbound HTTPS connections

### Fallback to FAISS

If Qdrant connection fails, the system automatically falls back to FAISS (in-memory). This is normal behavior and queries will still work.
