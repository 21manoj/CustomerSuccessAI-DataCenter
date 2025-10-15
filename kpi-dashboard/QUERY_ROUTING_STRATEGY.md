# 🎯 Query Routing Strategy: Deterministic Analytics vs RAG

## Executive Summary

Route **numeric/quantitative queries** to **deterministic analytics APIs** for accuracy and speed, while routing **qualitative/analytical queries** to **RAG systems** for insights and recommendations.

---

## 🔀 Query Classification

### **Deterministic Queries** → Analytics APIs
These queries have exact, verifiable answers from database calculations:

**Financial Queries:**
- ❓ "What is the total revenue?"
- ❓ "How many accounts have revenue > $5M?"
- ❓ "What is the average revenue per account?"
- ❓ "Show me the sum of all revenue"
- ❓ "What is the revenue for account ID 4?"

**Count Queries:**
- ❓ "How many accounts do we have?"
- ❓ "How many KPIs are in the database?"
- ❓ "Count accounts by industry"
- ❓ "How many active accounts are there?"

**Statistical Queries:**
- ❓ "What is the average customer satisfaction score?"
- ❓ "What is the median revenue?"
- ❓ "Show me the min/max revenue"
- ❓ "Calculate the standard deviation of NPS scores"

**List/Retrieval Queries:**
- ❓ "List all accounts in Healthcare"
- ❓ "Show all KPIs for account ID 5"
- ❓ "Get all accounts in North America"
- ❓ "List accounts by revenue (sorted)"

### **RAG Queries** → AI Analysis
These queries require reasoning, context, and qualitative analysis:

**Why/How Queries:**
- ❓ "Why is revenue declining for Financial Services Group?"
- ❓ "How can we improve customer satisfaction?"
- ❓ "What factors contribute to account health?"
- ❓ "How do top performers differ from others?"

**Pattern Recognition:**
- ❓ "What are common traits of high-performing accounts?"
- ❓ "Find patterns in churn risk indicators"
- ❓ "Identify trends across industries"

**Recommendations:**
- ❓ "Which accounts should we focus on?"
- ❓ "What strategies would improve engagement?"
- ❓ "How should we prioritize at-risk accounts?"

**Comparative Analysis:**
- ❓ "Compare Healthcare vs Financial Services performance"
- ❓ "Which industry has better customer satisfaction and why?"
- ❓ "Analyze differences between high and low performers"

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         User Query                               │
└──────────────────────┬──────────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Query Router Service                          │
│  - NLP-based classification                                      │
│  - Keyword pattern matching                                      │
│  - Intent detection (numeric vs analytical)                      │
└──────────────────────┬─────────────────────┬────────────────────┘
                       │                     │
         ┌─────────────┴──────┐    ┌────────┴──────────┐
         │ DETERMINISTIC      │    │   RAG SYSTEM      │
         │   (Analytics)      │    │   (AI Analysis)    │
         └─────────┬──────────┘    └────────┬───────────┘
                   │                        │
    ┌──────────────┴──────────────┐        │
    │                             │        │
    ▼                             ▼        ▼
┌─────────────┐          ┌─────────────┐  ┌──────────────┐
│  Analytics  │          │  Aggregation│  │ GPT-4/Claude │
│  Endpoints  │          │  Functions  │  │   Analysis   │
└──────┬──────┘          └──────┬──────┘  └──────┬───────┘
       │                        │                 │
       └────────────┬───────────┘                 │
                    │                             │
                    ▼                             ▼
          ┌─────────────────────┐       ┌────────────────┐
          │   PostgreSQL DB     │       │  FAISS/Qdrant  │
          │  (Direct Queries)   │       │  (Semantic)    │
          └─────────────────────┘       └────────────────┘
```

---

## 🔍 Query Classifier Implementation

### Detection Patterns

```python
DETERMINISTIC_PATTERNS = {
    'financial_aggregation': [
        r'total revenue',
        r'sum of revenue',
        r'average revenue',
        r'mean revenue',
        r'median revenue',
        r'revenue for account',
    ],
    'count': [
        r'how many accounts',
        r'count.*accounts',
        r'number of.*accounts',
        r'how many kpis',
        r'count.*kpis',
    ],
    'list': [
        r'list all accounts',
        r'show.*accounts',
        r'get.*accounts',
        r'list.*kpis',
        r'accounts in.*industry',
        r'accounts in.*region',
    ],
    'statistical': [
        r'average.*score',
        r'mean.*score',
        r'min.*revenue',
        r'max.*revenue',
        r'standard deviation',
        r'median',
    ],
    'single_record': [
        r'account.*id.*\d+',
        r'kpi.*id.*\d+',
        r'show account \d+',
    ]
}

RAG_PATTERNS = {
    'why_how': [
        r'why.*',
        r'how can.*',
        r'what factors.*',
        r'what causes.*',
    ],
    'recommendations': [
        r'should.*focus',
        r'recommend',
        r'suggest',
        r'what strategies',
        r'how to improve',
    ],
    'patterns': [
        r'common traits',
        r'patterns',
        r'trends',
        r'identify.*similarities',
    ],
    'comparison': [
        r'compare.*',
        r'difference between',
        r'vs\.',
        r'versus',
        r'better than',
    ],
    'analysis': [
        r'analyze.*',
        r'insights',
        r'explain.*',
        r'understand.*',
    ]
}
```

---

## 📡 New Deterministic Analytics API

### Endpoint Design

#### 1. **Revenue Analytics**
```http
GET /api/analytics/revenue/total
GET /api/analytics/revenue/average
GET /api/analytics/revenue/by-industry
GET /api/analytics/revenue/by-region
GET /api/analytics/revenue/top-accounts?limit=10
```

#### 2. **Account Analytics**
```http
GET /api/analytics/accounts/count
GET /api/analytics/accounts/by-industry
GET /api/analytics/accounts/by-region
GET /api/analytics/accounts/by-status
GET /api/analytics/accounts/{account_id}
POST /api/analytics/accounts/filter
  Body: {"industry": "Healthcare", "min_revenue": 1000000}
```

#### 3. **KPI Analytics**
```http
GET /api/analytics/kpis/count
GET /api/analytics/kpis/average-by-category
GET /api/analytics/kpis/summary
GET /api/analytics/kpis/account/{account_id}
```

#### 4. **Aggregation Endpoint**
```http
POST /api/analytics/aggregate
Body: {
  "metric": "revenue",
  "operation": "sum|avg|count|min|max",
  "filters": {
    "industry": "Healthcare",
    "region": "North America",
    "min_revenue": 1000000
  },
  "group_by": ["industry", "region"]
}
```

---

## 🚀 Implementation Plan

### Phase 1: Query Router (Week 1)
**Priority: HIGH**

1. **Create `query_router.py`**
   - Classify queries as deterministic vs RAG
   - Pattern matching with regex
   - Intent detection scoring
   - Return routing decision with confidence

2. **Create `query_classifier.py`**
   - NLP-based classification (optional: use sentence-transformers)
   - Keyword extraction
   - Query type identification

### Phase 2: Analytics API (Week 1-2)
**Priority: HIGH**

1. **Create `analytics_api.py`**
   - Revenue aggregation endpoints
   - Account statistics endpoints
   - KPI aggregation endpoints
   - Generic aggregation endpoint

2. **Create `analytics_service.py`**
   - Centralized business logic
   - SQL query builders
   - Caching layer
   - Response formatting

### Phase 3: Integration (Week 2)
**Priority: HIGH**

1. **Modify RAG entry point**
   - Add router before RAG query
   - Route to analytics if deterministic
   - Route to RAG if analytical
   - Return unified response format

2. **Create unified query endpoint**
   - Single entry point: `/api/query`
   - Automatic routing
   - Response standardization

### Phase 4: Testing & Optimization (Week 3)
**Priority: MEDIUM**

1. **Unit tests** for query router
2. **Integration tests** for both paths
3. **Performance benchmarks**
4. **A/B testing** with sample queries

---

## 📝 Sample Implementation

### Query Router Service

```python
# backend/query_router.py

import re
from typing import Dict, Tuple, List

class QueryRouter:
    """Routes queries to deterministic analytics or RAG based on intent"""
    
    DETERMINISTIC_KEYWORDS = [
        'total', 'sum', 'average', 'mean', 'median', 'count',
        'how many', 'number of', 'min', 'max', 'list all',
        'show all', 'get all', 'standard deviation', 'std dev'
    ]
    
    RAG_KEYWORDS = [
        'why', 'how can', 'what factors', 'recommend', 'suggest',
        'analyze', 'insights', 'explain', 'patterns', 'trends',
        'compare', 'difference', 'better', 'improve', 'strategy'
    ]
    
    @staticmethod
    def classify_query(query: str) -> Dict:
        """
        Classify query as 'deterministic' or 'rag'
        
        Returns:
            {
                'routing': 'deterministic' | 'rag',
                'confidence': float,
                'query_type': str,
                'extracted_params': dict
            }
        """
        query_lower = query.lower().strip()
        
        # Calculate scores
        deterministic_score = QueryRouter._calculate_deterministic_score(query_lower)
        rag_score = QueryRouter._calculate_rag_score(query_lower)
        
        # Extract query parameters
        params = QueryRouter._extract_parameters(query_lower)
        
        # Determine routing
        if deterministic_score > rag_score:
            routing = 'deterministic'
            confidence = deterministic_score / (deterministic_score + rag_score)
            query_type = QueryRouter._get_deterministic_type(query_lower, params)
        else:
            routing = 'rag'
            confidence = rag_score / (deterministic_score + rag_score)
            query_type = QueryRouter._get_rag_type(query_lower)
        
        return {
            'routing': routing,
            'confidence': confidence,
            'query_type': query_type,
            'extracted_params': params,
            'original_query': query
        }
    
    @staticmethod
    def _calculate_deterministic_score(query: str) -> float:
        """Calculate deterministic query score"""
        score = 0.0
        
        # Check for exact numeric questions
        if re.search(r'\b(what is|show|get|calculate)\b.*\b(total|sum|average|count|number)\b', query):
            score += 3.0
        
        # Check for list/retrieval patterns
        if re.search(r'\b(list|show|get|display)\b.*\b(all|accounts|kpis)\b', query):
            score += 2.5
        
        # Check for statistical operations
        if re.search(r'\b(average|mean|median|min|max|std|deviation)\b', query):
            score += 2.0
        
        # Check for count operations
        if re.search(r'\b(how many|count|number of)\b', query):
            score += 2.5
        
        # Check for specific IDs
        if re.search(r'\b(account|kpi).*\bid\b.*\d+', query):
            score += 3.0
        
        # Check for comparison operators
        if re.search(r'\b(greater than|less than|>|<|=)\b', query):
            score += 2.0
        
        # Keyword matching
        for keyword in QueryRouter.DETERMINISTIC_KEYWORDS:
            if keyword in query:
                score += 1.0
        
        return score
    
    @staticmethod
    def _calculate_rag_score(query: str) -> float:
        """Calculate RAG query score"""
        score = 0.0
        
        # Check for why/how questions
        if re.search(r'\b(why|how can|what factors|what causes)\b', query):
            score += 3.0
        
        # Check for recommendation requests
        if re.search(r'\b(recommend|suggest|should|advise)\b', query):
            score += 3.0
        
        # Check for analysis requests
        if re.search(r'\b(analyze|insights|explain|understand)\b', query):
            score += 2.5
        
        # Check for comparison with context
        if re.search(r'\bcompare\b.*\b(performance|trends|patterns)\b', query):
            score += 2.5
        
        # Check for pattern/trend questions
        if re.search(r'\b(patterns|trends|common traits|similarities)\b', query):
            score += 2.5
        
        # Keyword matching
        for keyword in QueryRouter.RAG_KEYWORDS:
            if keyword in query:
                score += 1.0
        
        return score
    
    @staticmethod
    def _extract_parameters(query: str) -> Dict:
        """Extract parameters from query"""
        params = {}
        
        # Extract numbers
        numbers = re.findall(r'\d+(?:,\d{3})*(?:\.\d+)?', query)
        if numbers:
            params['numbers'] = numbers
        
        # Extract account ID
        account_match = re.search(r'account\s*(?:id)?\s*(\d+)', query)
        if account_match:
            params['account_id'] = int(account_match.group(1))
        
        # Extract industries
        industries = ['healthcare', 'financial services', 'technology', 
                     'manufacturing', 'retail', 'education']
        for industry in industries:
            if industry in query:
                params['industry'] = industry.title()
        
        # Extract regions
        regions = ['north america', 'europe', 'asia', 'south america']
        for region in regions:
            if region in query:
                params['region'] = region.title()
        
        # Extract operations
        operations = {
            'sum': ['total', 'sum'],
            'avg': ['average', 'mean'],
            'count': ['count', 'how many', 'number of'],
            'min': ['minimum', 'min', 'lowest'],
            'max': ['maximum', 'max', 'highest'],
        }
        for op, keywords in operations.items():
            if any(kw in query for kw in keywords):
                params['operation'] = op
                break
        
        return params
    
    @staticmethod
    def _get_deterministic_type(query: str, params: Dict) -> str:
        """Determine specific deterministic query type"""
        if 'count' in params.get('operation', ''):
            return 'count'
        elif re.search(r'\btotal\b|\bsum\b', query):
            return 'sum'
        elif re.search(r'\baverage\b|\bmean\b', query):
            return 'average'
        elif re.search(r'\blist\b|\bshow\b|\bget\b', query):
            return 'list'
        elif 'account_id' in params:
            return 'single_record'
        else:
            return 'aggregation'
    
    @staticmethod
    def _get_rag_type(query: str) -> str:
        """Determine specific RAG query type"""
        if re.search(r'\bwhy\b|\bhow can\b', query):
            return 'why_how'
        elif re.search(r'\brecommend\b|\bsuggest\b', query):
            return 'recommendation'
        elif re.search(r'\banalyze\b|\binsights\b', query):
            return 'analysis'
        elif re.search(r'\bcompare\b', query):
            return 'comparison'
        elif re.search(r'\bpatterns\b|\btrends\b', query):
            return 'pattern_recognition'
        else:
            return 'general'


# Example usage
if __name__ == '__main__':
    router = QueryRouter()
    
    # Test queries
    test_queries = [
        "What is the total revenue?",
        "How many accounts do we have?",
        "Why is revenue declining for Healthcare accounts?",
        "List all accounts in North America",
        "What are the common traits of high-performing accounts?",
        "Show me account ID 5",
        "What is the average customer satisfaction score?",
        "How can we improve engagement?",
    ]
    
    for query in test_queries:
        result = router.classify_query(query)
        print(f"\nQuery: {query}")
        print(f"Routing: {result['routing']} (confidence: {result['confidence']:.2f})")
        print(f"Type: {result['query_type']}")
        print(f"Params: {result['extracted_params']}")
```

### Analytics API

```python
# backend/analytics_api.py

from flask import Blueprint, request, jsonify, abort
from extensions import db
from models import Account, KPI, KPIUpload
from sqlalchemy import func, and_, or_
from typing import Dict, List, Any

analytics_api = Blueprint('analytics_api', __name__)

def get_customer_id():
    """Extract and validate customer ID"""
    cid = request.headers.get('X-Customer-ID')
    if not cid:
        abort(400, 'Missing X-Customer-ID header')
    try:
        return int(cid)
    except:
        abort(400, 'Invalid X-Customer-ID header')


# ==================== REVENUE ANALYTICS ====================

@analytics_api.route('/api/analytics/revenue/total', methods=['GET'])
def get_total_revenue():
    """Get total revenue across all accounts"""
    customer_id = get_customer_id()
    
    total = db.session.query(
        func.sum(Account.revenue)
    ).filter(
        Account.customer_id == customer_id
    ).scalar() or 0
    
    return jsonify({
        'query_type': 'revenue_total',
        'customer_id': customer_id,
        'result': {
            'total_revenue': float(total),
            'formatted': f"${total:,.2f}"
        },
        'metadata': {
            'source': 'deterministic_analytics',
            'calculation': 'SUM(revenue)',
            'precision': 'exact'
        }
    })


@analytics_api.route('/api/analytics/revenue/average', methods=['GET'])
def get_average_revenue():
    """Get average revenue per account"""
    customer_id = get_customer_id()
    
    result = db.session.query(
        func.avg(Account.revenue).label('average'),
        func.count(Account.account_id).label('count')
    ).filter(
        Account.customer_id == customer_id
    ).first()
    
    return jsonify({
        'query_type': 'revenue_average',
        'customer_id': customer_id,
        'result': {
            'average_revenue': float(result.average or 0),
            'account_count': result.count,
            'formatted': f"${result.average or 0:,.2f}"
        },
        'metadata': {
            'source': 'deterministic_analytics',
            'calculation': 'AVG(revenue)',
            'precision': 'exact'
        }
    })


@analytics_api.route('/api/analytics/revenue/by-industry', methods=['GET'])
def get_revenue_by_industry():
    """Get revenue breakdown by industry"""
    customer_id = get_customer_id()
    
    results = db.session.query(
        Account.industry,
        func.sum(Account.revenue).label('total_revenue'),
        func.count(Account.account_id).label('account_count'),
        func.avg(Account.revenue).label('avg_revenue')
    ).filter(
        Account.customer_id == customer_id
    ).group_by(
        Account.industry
    ).order_by(
        func.sum(Account.revenue).desc()
    ).all()
    
    return jsonify({
        'query_type': 'revenue_by_industry',
        'customer_id': customer_id,
        'result': [{
            'industry': r.industry,
            'total_revenue': float(r.total_revenue or 0),
            'account_count': r.account_count,
            'average_revenue': float(r.avg_revenue or 0),
            'formatted_total': f"${r.total_revenue or 0:,.2f}"
        } for r in results],
        'metadata': {
            'source': 'deterministic_analytics',
            'calculation': 'SUM(revenue) GROUP BY industry',
            'precision': 'exact'
        }
    })


@analytics_api.route('/api/analytics/revenue/top-accounts', methods=['GET'])
def get_top_revenue_accounts():
    """Get top accounts by revenue"""
    customer_id = get_customer_id()
    limit = request.args.get('limit', 10, type=int)
    
    accounts = Account.query.filter_by(
        customer_id=customer_id
    ).order_by(
        Account.revenue.desc()
    ).limit(limit).all()
    
    return jsonify({
        'query_type': 'top_revenue_accounts',
        'customer_id': customer_id,
        'result': [{
            'account_id': a.account_id,
            'account_name': a.account_name,
            'revenue': float(a.revenue or 0),
            'industry': a.industry,
            'region': a.region,
            'formatted_revenue': f"${a.revenue or 0:,.2f}"
        } for a in accounts],
        'metadata': {
            'source': 'deterministic_analytics',
            'limit': limit,
            'precision': 'exact'
        }
    })


# ==================== ACCOUNT ANALYTICS ====================

@analytics_api.route('/api/analytics/accounts/count', methods=['GET'])
def get_account_count():
    """Get total account count"""
    customer_id = get_customer_id()
    
    # Get optional filters
    industry = request.args.get('industry')
    region = request.args.get('region')
    status = request.args.get('status')
    
    query = Account.query.filter_by(customer_id=customer_id)
    
    if industry:
        query = query.filter(Account.industry == industry)
    if region:
        query = query.filter(Account.region == region)
    if status:
        query = query.filter(Account.account_status == status)
    
    count = query.count()
    
    return jsonify({
        'query_type': 'account_count',
        'customer_id': customer_id,
        'result': {
            'count': count
        },
        'filters': {
            'industry': industry,
            'region': region,
            'status': status
        },
        'metadata': {
            'source': 'deterministic_analytics',
            'calculation': 'COUNT(*)',
            'precision': 'exact'
        }
    })


@analytics_api.route('/api/analytics/accounts/by-industry', methods=['GET'])
def get_accounts_by_industry():
    """Get account distribution by industry"""
    customer_id = get_customer_id()
    
    results = db.session.query(
        Account.industry,
        func.count(Account.account_id).label('count'),
        func.sum(Account.revenue).label('total_revenue')
    ).filter(
        Account.customer_id == customer_id
    ).group_by(
        Account.industry
    ).order_by(
        func.count(Account.account_id).desc()
    ).all()
    
    return jsonify({
        'query_type': 'accounts_by_industry',
        'customer_id': customer_id,
        'result': [{
            'industry': r.industry,
            'account_count': r.count,
            'total_revenue': float(r.total_revenue or 0)
        } for r in results],
        'metadata': {
            'source': 'deterministic_analytics',
            'precision': 'exact'
        }
    })


# ==================== GENERIC AGGREGATION ====================

@analytics_api.route('/api/analytics/aggregate', methods=['POST'])
def aggregate_data():
    """Generic aggregation endpoint"""
    customer_id = get_customer_id()
    data = request.json
    
    metric = data.get('metric', 'revenue')  # revenue, account_count, etc.
    operation = data.get('operation', 'sum')  # sum, avg, count, min, max
    filters = data.get('filters', {})
    group_by = data.get('group_by', [])  # ['industry', 'region']
    
    # Build base query
    query = db.session.query(Account).filter(Account.customer_id == customer_id)
    
    # Apply filters
    if filters.get('industry'):
        query = query.filter(Account.industry == filters['industry'])
    if filters.get('region'):
        query = query.filter(Account.region == filters['region'])
    if filters.get('status'):
        query = query.filter(Account.account_status == filters['status'])
    if filters.get('min_revenue'):
        query = query.filter(Account.revenue >= filters['min_revenue'])
    if filters.get('max_revenue'):
        query = query.filter(Account.revenue <= filters['max_revenue'])
    
    # Apply aggregation
    if operation == 'sum':
        agg_func = func.sum(getattr(Account, metric))
    elif operation == 'avg':
        agg_func = func.avg(getattr(Account, metric))
    elif operation == 'count':
        agg_func = func.count(Account.account_id)
    elif operation == 'min':
        agg_func = func.min(getattr(Account, metric))
    elif operation == 'max':
        agg_func = func.max(getattr(Account, metric))
    else:
        return jsonify({'error': f'Invalid operation: {operation}'}), 400
    
    # Build final query with grouping
    if group_by:
        group_cols = [getattr(Account, col) for col in group_by]
        query = db.session.query(*group_cols, agg_func.label('value')).filter(
            Account.customer_id == customer_id
        )
        
        # Reapply filters
        if filters.get('industry'):
            query = query.filter(Account.industry == filters['industry'])
        if filters.get('region'):
            query = query.filter(Account.region == filters['region'])
            
        query = query.group_by(*group_cols)
        results = query.all()
        
        return jsonify({
            'query_type': 'aggregate_grouped',
            'customer_id': customer_id,
            'result': [{
                **{col: getattr(r, col) for col in group_by},
                'value': float(r.value or 0)
            } for r in results],
            'metadata': {
                'metric': metric,
                'operation': operation,
                'group_by': group_by,
                'filters': filters,
                'source': 'deterministic_analytics'
            }
        })
    else:
        # Single aggregation
        result = db.session.query(agg_func).filter(
            Account.customer_id == customer_id
        ).scalar() or 0
        
        return jsonify({
            'query_type': 'aggregate_single',
            'customer_id': customer_id,
            'result': {
                'value': float(result),
                'operation': operation,
                'metric': metric
            },
            'metadata': {
                'filters': filters,
                'source': 'deterministic_analytics',
                'precision': 'exact'
            }
        })


# ==================== KPI ANALYTICS ====================

@analytics_api.route('/api/analytics/kpis/count', methods=['GET'])
def get_kpi_count():
    """Get total KPI count"""
    customer_id = get_customer_id()
    
    count = db.session.query(func.count(KPI.kpi_id)).join(
        Account, KPI.account_id == Account.account_id
    ).filter(
        Account.customer_id == customer_id
    ).scalar()
    
    return jsonify({
        'query_type': 'kpi_count',
        'customer_id': customer_id,
        'result': {
            'count': count
        },
        'metadata': {
            'source': 'deterministic_analytics',
            'precision': 'exact'
        }
    })


@analytics_api.route('/api/analytics/kpis/average-by-category', methods=['GET'])
def get_kpi_average_by_category():
    """Get average KPI values by category"""
    customer_id = get_customer_id()
    
    results = db.session.query(
        KPI.category,
        func.avg(func.cast(KPI.data, db.Float)).label('avg_value'),
        func.count(KPI.kpi_id).label('count')
    ).join(
        Account, KPI.account_id == Account.account_id
    ).filter(
        Account.customer_id == customer_id,
        KPI.data.isnot(None)
    ).group_by(
        KPI.category
    ).all()
    
    return jsonify({
        'query_type': 'kpi_average_by_category',
        'customer_id': customer_id,
        'result': [{
            'category': r.category,
            'average_value': float(r.avg_value or 0),
            'kpi_count': r.count
        } for r in results],
        'metadata': {
            'source': 'deterministic_analytics',
            'precision': 'exact'
        }
    })
```

### Unified Query Endpoint

```python
# backend/unified_query_api.py

from flask import Blueprint, request, jsonify
from query_router import QueryRouter
import requests

unified_query_api = Blueprint('unified_query_api', __name__)

@unified_query_api.route('/api/query', methods=['POST'])
def unified_query():
    """
    Unified query endpoint that routes to analytics or RAG
    """
    data = request.json
    query = data.get('query', '').strip()
    customer_id = request.headers.get('X-Customer-ID')
    
    if not query:
        return jsonify({'error': 'Query is required'}), 400
    
    if not customer_id:
        return jsonify({'error': 'X-Customer-ID header is required'}), 400
    
    # Classify the query
    router = QueryRouter()
    classification = router.classify_query(query)
    
    # Route based on classification
    if classification['routing'] == 'deterministic':
        # Route to analytics API
        response = _execute_deterministic_query(
            query,
            classification,
            customer_id
        )
    else:
        # Route to RAG system
        response = _execute_rag_query(
            query,
            classification,
            customer_id
        )
    
    # Add routing metadata
    response['routing_decision'] = {
        'routed_to': classification['routing'],
        'confidence': classification['confidence'],
        'query_type': classification['query_type']
    }
    
    return jsonify(response)


def _execute_deterministic_query(query: str, classification: Dict, customer_id: str) -> Dict:
    """Execute deterministic query via analytics API"""
    query_type = classification['query_type']
    params = classification['extracted_params']
    
    # Map to specific endpoint
    if query_type == 'sum' and 'revenue' in query.lower():
        endpoint = '/api/analytics/revenue/total'
        method = 'GET'
        body = None
    
    elif query_type == 'average' and 'revenue' in query.lower():
        endpoint = '/api/analytics/revenue/average'
        method = 'GET'
        body = None
    
    elif query_type == 'count':
        endpoint = '/api/analytics/accounts/count'
        method = 'GET'
        body = None
    
    elif query_type == 'list':
        if params.get('industry'):
            endpoint = f'/api/analytics/accounts/by-industry'
            method = 'GET'
            body = None
        else:
            endpoint = '/api/analytics/revenue/top-accounts'
            method = 'GET'
            body = None
    
    else:
        # Use generic aggregation endpoint
        endpoint = '/api/analytics/aggregate'
        method = 'POST'
        body = {
            'metric': 'revenue',
            'operation': params.get('operation', 'sum'),
            'filters': {
                k: v for k, v in params.items() 
                if k in ['industry', 'region', 'status']
            }
        }
    
    # Execute the query (in production, call internal function instead of HTTP)
    # For now, return structured response
    return {
        'query': query,
        'answer': f"Deterministic result for: {query}",
        'endpoint_used': endpoint,
        'method': method,
        'extracted_params': params
    }


def _execute_rag_query(query: str, classification: Dict, customer_id: str) -> Dict:
    """Execute RAG query via RAG API"""
    # Call existing RAG endpoint
    from enhanced_rag_openai import get_rag_system
    
    rag_system = get_rag_system(int(customer_id))
    
    # Ensure knowledge base is built
    if not rag_system.faiss_index:
        rag_system.build_knowledge_base(int(customer_id))
    
    # Query the RAG system
    result = rag_system.query(query, classification['query_type'])
    
    return result
```

---

## 📊 Performance Comparison

| Metric | Deterministic Analytics | RAG System |
|--------|------------------------|------------|
| **Accuracy** | 100% (exact) | ~95% (AI-generated) |
| **Speed** | 50-200ms | 1-3 seconds |
| **Cost per query** | $0.00 | $0.01-0.05 |
| **Consistency** | Perfect | Variable |
| **Best for** | Numbers, counts, lists | Insights, why/how, patterns |

---

## ✅ Benefits

### **For Users:**
1. ⚡ **Faster responses** for numeric queries (10x faster)
2. 🎯 **Exact answers** for factual questions
3. 💰 **Lower costs** (no AI API calls for simple queries)
4. 🔄 **Consistent results** every time

### **For System:**
1. 📉 **Reduced AI API costs** (70-80% reduction)
2. ⚡ **Lower latency** for deterministic queries
3. 🎯 **Better AI utilization** (use for complex queries only)
4. 📊 **Better tracking** of query types

---

## 🚦 Decision Tree

```
Is the query asking for:
├─ Exact number/count? → Analytics
├─ Sum/Total/Average? → Analytics
├─ List of items? → Analytics
├─ Specific record by ID? → Analytics
├─ Why/How question? → RAG
├─ Recommendation? → RAG
├─ Pattern analysis? → RAG
└─ Comparison with context? → RAG
```

---

## 📈 Success Metrics

1. **Routing Accuracy**: >95% of queries routed correctly
2. **Response Time**: <200ms for deterministic, <3s for RAG
3. **Cost Reduction**: 70%+ reduction in AI API costs
4. **User Satisfaction**: >90% correct answers
5. **System Load**: Balanced distribution of queries

---

## 🔄 Migration Path

### Week 1:
- ✅ Create query router
- ✅ Create analytics API
- ✅ Unit tests

### Week 2:
- ✅ Integrate with RAG endpoint
- ✅ Create unified query endpoint
- ✅ Integration tests

### Week 3:
- ✅ Deploy to staging
- ✅ A/B testing
- ✅ Performance optimization

### Week 4:
- ✅ Deploy to production
- ✅ Monitor and tune
- ✅ Documentation

---

## 📝 Example Query Flow

```
User Query: "What is the total revenue?"
    ↓
Query Router: classify_query()
    → Deterministic (confidence: 0.95)
    → Type: sum
    → Params: {metric: "revenue", operation: "sum"}
    ↓
Analytics API: /api/analytics/revenue/total
    → SQL: SELECT SUM(revenue) FROM accounts WHERE customer_id = 6
    → Result: $43,700,000
    ↓
Response (150ms):
{
  "answer": "The total revenue is $43,700,000",
  "result": {"total_revenue": 43700000},
  "routing": "deterministic",
  "confidence": 0.95,
  "source": "exact_calculation"
}
```

```
User Query: "Why is revenue declining for Healthcare accounts?"
    ↓
Query Router: classify_query()
    → RAG (confidence: 0.92)
    → Type: why_how
    → Params: {industry: "Healthcare"}
    ↓
RAG System: GPT-4 Analysis
    → Semantic search for relevant KPIs
    → AI analysis of patterns
    ↓
Response (2.5s):
{
  "answer": "Revenue is declining in Healthcare accounts due to...",
  "insights": [...],
  "recommendations": [...],
  "routing": "rag",
  "confidence": 0.92,
  "source": "ai_analysis"
}
```

---

This approach gives you **the best of both worlds**: exact answers when needed, AI insights when valuable! 🎯

