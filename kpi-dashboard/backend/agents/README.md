# Signal Analyst Agent

AI-powered agent for customer success churn prediction and expansion opportunity identification.

## Overview

The Signal Analyst Agent analyzes customer signals (usage patterns, support interactions, financial trends, external market events) to:
- Predict churn probability
- Identify expansion opportunities
- Calculate health scores
- Provide actionable recommendations

## Features

✅ **Multi-signal analysis** - Quantitative (usage, financial) + Qualitative (support, sentiment, external events)  
✅ **Type-safe** - Pydantic models for inputs and outputs  
✅ **Explainable** - Detailed reasoning for predictions  
✅ **Actionable** - Specific recommendations with owners and deadlines  
✅ **Vertical-aware** - Optimized prompts for different industries (SaaS, Data Center)  
✅ **Confidence scoring** - Honest about prediction uncertainty  

## Installation

Dependencies are included in `requirements.txt`:
- `pydantic>=2.0.0`
- `openai>=1.0.0`

## Quick Start

### API Usage

```bash
# Test endpoint with mock data
curl -X POST http://localhost:8001/api/signal-analyst/test \
  -H "Content-Type: application/json" \
  -H "X-Customer-ID: 1" \
  -d '{
    "account_id": "test-account-001",
    "analysis_type": "comprehensive"
  }'

# Real analysis with account data
curl -X POST http://localhost:8001/api/signal-analyst/analyze \
  -H "Content-Type: application/json" \
  -H "X-Customer-ID: 1" \
  -d '{
    "account_id": "123",
    "analysis_type": "comprehensive",
    "time_horizon_days": 60,
    "use_qdrant": true,
    "use_database": true
  }'
```

### Python Usage

```python
from agents import SignalAnalystAgent, SignalAnalystInput, SignalData

# Initialize agent
agent = SignalAnalystAgent(
    openai_api_key=os.getenv('OPENAI_API_KEY'),
    model="gpt-4o"
)

# Prepare input
agent_input = SignalAnalystInput(
    account_id="ACME-001",
    customer_id=1,
    vertical_type="saas_customer_success",
    account_name="ACME Corp",
    account_arr=120000,
    quantitative_signals=[...],  # List of SignalData
    qualitative_signals=[...],   # List of SignalData
    historical_patterns=[...],   # List of SignalData
    analysis_type="comprehensive",
    time_horizon_days=60
)

# Run analysis
analysis = agent.analyze(agent_input)

# Access results
print(f"Churn Probability: {analysis.churn_probability}%")
print(f"Health Score: {analysis.health_score}/100")
print(f"Top Risk: {analysis.risk_drivers[0].driver}")
```

## Integration with Existing System

The agent integrates with:

1. **Qdrant Vector Database** - Retrieves signals from existing RAG collections
2. **PostgreSQL Database** - Converts Account, KPI, AccountNote models to signals
3. **Authentication** - Uses existing `get_current_customer_id()` middleware
4. **OpenAI API Keys** - Uses existing `get_openai_api_key()` utility

## Vertical Support

The system automatically maps verticals:
- `'saas'` → `'saas_customer_success'`
- `'datacenter'` → `'data_center_infrastructure'`

## API Endpoints

### POST `/api/signal-analyst/analyze`

Analyze account signals and get predictions.

**Request:**
```json
{
  "account_id": "123",
  "analysis_type": "comprehensive",
  "time_horizon_days": 60,
  "use_qdrant": true,
  "use_database": true
}
```

**Response:**
```json
{
  "account_id": "123",
  "predicted_outcome": "churn",
  "churn_probability": 78.0,
  "health_score": 62.0,
  "risk_drivers": [...],
  "recommended_actions": [...],
  "confidence": {...},
  "reasoning": "...",
  "key_insights": [...]
}
```

### POST `/api/signal-analyst/test`

Test endpoint using mock data (for verification).

## Architecture

```
agents/
├── __init__.py                  # Package exports
├── models.py                    # Pydantic models (type-safe)
├── prompts.py                   # Prompt templates
├── signal_analyst_agent.py      # Core agent logic
├── vertical_mapper.py           # Vertical type mapping
├── signal_converter.py          # Database model → SignalData converter
├── qdrant_integration.py        # Qdrant → SignalData integration
└── signal_analyst_api.py        # Flask API endpoints
```

## Testing

Run unit tests:
```bash
python -m pytest backend/tests/test_signal_analyst_agent.py
```

## Cost Estimates

**Per analysis:**
- GPT-4o: ~$0.02-$0.05 per account

**Monthly (1,000 accounts, weekly analysis):**
- GPT-4o: ~$80-$200/month

## License

MIT

