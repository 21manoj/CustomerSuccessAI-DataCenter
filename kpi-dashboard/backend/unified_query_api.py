#!/usr/bin/env python3
"""
Unified Query API: Routes queries intelligently to analytics or RAG
Entry point for all user queries - automatically routes to the best system
"""

from flask import Blueprint, request, jsonify, abort
from auth_middleware import get_current_customer_id, get_current_user_id
from query_router import QueryRouter
from extensions import db
from models import Account, KPI
from sqlalchemy import func
from typing import Dict
from datetime import datetime

unified_query_api = Blueprint('unified_query_api', __name__)


def get_current_customer_id():
    """Extract and validate customer ID"""
    cid = get_current_customer_id()
    if not cid:
        abort(400, 'Authentication required (handled by middleware)')
    try:
        return int(cid)
    except:
        abort(400, 'Invalid authentication (handled by middleware)')


@unified_query_api.route('/api/query', methods=['POST'])
def unified_query():
    """
    Unified query endpoint that intelligently routes to analytics or RAG
    
    Request body:
    {
        "query": "What is the total revenue?",
        "force_routing": "deterministic" | "rag" (optional)
    }
    
    Response:
    {
        "query": "...",
        "answer": "...",
        "result": {...},
        "routing_decision": {
            "routed_to": "deterministic" | "rag",
            "confidence": 0.95,
            "query_type": "sum",
            "reason": "..."
        },
        "metadata": {...}
    }
    """
    data = request.json
    query = data.get('query', '').strip()
    force_routing = data.get('force_routing')  # Optional override
    customer_id = get_current_customer_id()
    
    if not query:
        return jsonify({'error': 'Query is required'}), 400
    
    # Classify the query
    router = QueryRouter()
    classification = router.classify_query(query)
    
    # Allow forced routing for testing/debugging
    if force_routing in ['deterministic', 'rag']:
        classification['routing'] = force_routing
        classification['forced'] = True
    
    # Route based on classification
    if classification['routing'] == 'deterministic':
        response = _execute_deterministic_query(query, classification, customer_id)
    else:
        response = _execute_rag_query(query, classification, customer_id)
    
    # Add routing metadata
    response['routing_decision'] = {
        'routed_to': classification['routing'],
        'confidence': classification['confidence'],
        'query_type': classification['query_type'],
        'extracted_params': classification['extracted_params'],
        'reason': _get_routing_reason(classification),
        'scores': classification['scores'],
        'forced': classification.get('forced', False)
    }
    
    response['original_query'] = query
    response['customer_id'] = customer_id
    response['timestamp'] = datetime.utcnow().isoformat()
    
    return jsonify(response)


def _execute_deterministic_query(query: str, classification: Dict, customer_id: int) -> Dict:
    """
    Execute deterministic query via direct database queries
    Fast, exact, and cost-effective
    """
    query_type = classification['query_type']
    params = classification['extracted_params']
    
    try:
        # Route to specific analytics based on query type
        if query_type in ['sum', 'total'] and 'revenue' in query.lower():
            result = _get_total_revenue(customer_id, params)
            answer = f"The total revenue is {result['formatted']}."
        
        elif query_type in ['average', 'mean'] and 'revenue' in query.lower():
            result = _get_average_revenue(customer_id, params)
            answer = f"The average revenue per account is {result['formatted_average']} across {result['account_count']} accounts."
        
        elif query_type == 'count':
            result = _get_account_count(customer_id, params)
            count = result['count']
            filter_desc = _describe_filters(params)
            answer = f"There are {count} accounts{filter_desc}."
        
        elif query_type in ['list', 'max'] and 'revenue' in query.lower():
            limit = params.get('limit', 10)
            result = _get_top_accounts(customer_id, limit)
            answer = _format_top_accounts_answer(result, limit)
        
        elif query_type == 'single_record' and 'account_id' in params:
            account_id = params['account_id']
            result = _get_account_details(customer_id, account_id)
            if result:
                answer = _format_account_details(result)
            else:
                answer = f"Account ID {account_id} not found."
                result = {}
        
        else:
            # Generic aggregation
            result = _execute_generic_aggregation(customer_id, params)
            answer = _format_generic_answer(result, params)
        
        return {
            'answer': answer,
            'result': result,
            'metadata': {
                'source': 'deterministic_analytics',
                'precision': 'exact',
                'execution_time_ms': '<200',
                'cost': '$0.00'
            }
        }
    
    except Exception as e:
        return {
            'answer': f"Error executing deterministic query: {str(e)}",
            'error': str(e),
            'result': {},
            'metadata': {
                'source': 'deterministic_analytics',
                'execution_failed': True
            }
        }


def _execute_rag_query(query: str, classification: Dict, customer_id: int) -> Dict:
    """
    Execute RAG query via AI analysis
    Provides insights, reasoning, and recommendations
    """
    try:
        # Import RAG system (lazy import to avoid circular dependencies)
        from enhanced_rag_openai import get_rag_system
        
        rag_system = get_rag_system(customer_id)
        
        # Ensure knowledge base is built
        if not rag_system.faiss_index:
            rag_system.build_knowledge_base(customer_id)
        
        # Execute RAG query
        rag_result = rag_system.query(query, classification['query_type'])
        
        return {
            'answer': rag_result.get('response', 'No response generated'),
            'result': {
                'relevant_results': rag_result.get('relevant_results', []),
                'results_count': rag_result.get('results_count', 0),
                'query_type': rag_result.get('query_type')
            },
            'metadata': {
                'source': 'rag_system',
                'precision': 'ai_generated',
                'execution_time_ms': '1000-3000',
                'cost': '$0.01-0.05',
                'ai_model': 'GPT-4'
            }
        }
    
    except Exception as e:
        return {
            'answer': f"Error executing RAG query: {str(e)}",
            'error': str(e),
            'result': {},
            'metadata': {
                'source': 'rag_system',
                'execution_failed': True
            }
        }


# ==================== DETERMINISTIC QUERY HELPERS ====================

def _get_total_revenue(customer_id: int, params: Dict) -> Dict:
    """Get total revenue with optional filters"""
    query = db.session.query(func.sum(Account.revenue)).filter(
        Account.customer_id == customer_id
    )
    
    if params.get('industry'):
        query = query.filter(Account.industry == params['industry'])
    if params.get('region'):
        query = query.filter(Account.region == params['region'])
    
    total = query.scalar() or 0
    return {
        'total_revenue': float(total),
        'formatted': f"${total:,.2f}",
        'filters': {k: v for k, v in params.items() if k in ['industry', 'region']}
    }


def _get_average_revenue(customer_id: int, params: Dict) -> Dict:
    """Get average revenue with optional filters"""
    query = db.session.query(
        func.avg(Account.revenue).label('avg'),
        func.count(Account.account_id).label('count')
    ).filter(Account.customer_id == customer_id)
    
    if params.get('industry'):
        query = query.filter(Account.industry == params['industry'])
    if params.get('region'):
        query = query.filter(Account.region == params['region'])
    
    result = query.first()
    return {
        'average_revenue': float(result.avg or 0),
        'account_count': result.count,
        'formatted_average': f"${result.avg or 0:,.2f}"
    }


def _get_account_count(customer_id: int, params: Dict) -> Dict:
    """Get account count with optional filters"""
    query = Account.query.filter_by(customer_id=customer_id)
    
    if params.get('industry'):
        query = query.filter(Account.industry == params['industry'])
    if params.get('region'):
        query = query.filter(Account.region == params['region'])
    if params.get('status'):
        query = query.filter(Account.account_status == params['status'])
    
    count = query.count()
    return {'count': count, 'filters': params}


def _get_top_accounts(customer_id: int, limit: int) -> Dict:
    """Get top accounts by revenue"""
    accounts = Account.query.filter_by(
        customer_id=customer_id
    ).order_by(
        Account.revenue.desc()
    ).limit(limit).all()
    
    return {
        'accounts': [{
            'rank': idx + 1,
            'account_name': a.account_name,
            'revenue': float(a.revenue or 0),
            'industry': a.industry,
            'formatted_revenue': f"${a.revenue or 0:,.2f}"
        } for idx, a in enumerate(accounts)],
        'count': len(accounts)
    }


def _get_account_details(customer_id: int, account_id: int) -> Dict:
    """Get details for a specific account"""
    account = Account.query.filter_by(
        account_id=account_id,
        customer_id=customer_id
    ).first()
    
    if not account:
        return None
    
    kpi_count = KPI.query.filter_by(account_id=account_id).count()
    
    return {
        'account_id': account.account_id,
        'account_name': account.account_name,
        'revenue': float(account.revenue or 0),
        'industry': account.industry,
        'region': account.region,
        'status': account.account_status,
        'kpi_count': kpi_count,
        'formatted_revenue': f"${account.revenue or 0:,.2f}"
    }


def _execute_generic_aggregation(customer_id: int, params: Dict) -> Dict:
    """Execute generic aggregation based on params"""
    operation = params.get('operation', 'sum')
    
    if operation == 'count':
        return _get_account_count(customer_id, params)
    elif operation == 'sum':
        return _get_total_revenue(customer_id, params)
    elif operation == 'avg':
        return _get_average_revenue(customer_id, params)
    else:
        return {'message': 'Aggregation completed', 'operation': operation}


# ==================== FORMATTING HELPERS ====================

def _describe_filters(params: Dict) -> str:
    """Create human-readable filter description"""
    filters = []
    if params.get('industry'):
        filters.append(f"in the {params['industry']} industry")
    if params.get('region'):
        filters.append(f"in {params['region']}")
    if params.get('status'):
        filters.append(f"with {params['status']} status")
    
    return f" {' '.join(filters)}" if filters else ""


def _format_top_accounts_answer(result: Dict, limit: int) -> str:
    """Format top accounts into readable answer"""
    accounts = result.get('accounts', [])
    if not accounts:
        return "No accounts found."
    
    answer = f"Here are the top {len(accounts)} accounts by revenue:\n\n"
    for acc in accounts:
        answer += f"{acc['rank']}. {acc['account_name']} - {acc['formatted_revenue']} ({acc['industry']})\n"
    
    return answer.strip()


def _format_account_details(result: Dict) -> str:
    """Format account details into readable answer"""
    return f"""Account Details:
- Name: {result['account_name']}
- Revenue: {result['formatted_revenue']}
- Industry: {result['industry']}
- Region: {result['region']}
- Status: {result['status']}
- KPI Count: {result['kpi_count']}"""


def _format_generic_answer(result: Dict, params: Dict) -> str:
    """Format generic aggregation answer"""
    if 'total_revenue' in result:
        return f"The total is {result['formatted']}."
    elif 'average_revenue' in result:
        return f"The average is {result['formatted_average']}."
    elif 'count' in result:
        return f"The count is {result['count']}."
    else:
        return f"Result: {result}"


def _get_routing_reason(classification: Dict) -> str:
    """Get human-readable reason for routing decision"""
    routing = classification['routing']
    query_type = classification['query_type']
    confidence = classification['confidence']
    
    if routing == 'deterministic':
        return (
            f"Routed to deterministic analytics because the query asks for exact "
            f"{query_type} calculation (confidence: {confidence:.1%}). "
            f"This provides precise answers instantly with zero cost."
        )
    else:
        return (
            f"Routed to RAG system because the query requires {query_type} analysis "
            f"(confidence: {confidence:.1%}). This provides AI-powered insights and reasoning."
        )


# ==================== TESTING ENDPOINT ====================

@unified_query_api.route('/api/query/test', methods=['POST'])
def test_routing():
    """
    Test endpoint to see routing decision without executing query
    """
    data = request.json
    query = data.get('query', '').strip()
    
    if not query:
        return jsonify({'error': 'Query is required'}), 400
    
    router = QueryRouter()
    classification = router.classify_query(query)
    
    return jsonify({
        'query': query,
        'routing_decision': {
            'routed_to': classification['routing'],
            'confidence': classification['confidence'],
            'query_type': classification['query_type'],
            'extracted_params': classification['extracted_params'],
            'scores': classification['scores'],
            'reason': _get_routing_reason(classification)
        },
        'metadata': {
            'test_mode': True,
            'execution_skipped': True
        }
    })


@unified_query_api.route('/api/query/batch-test', methods=['POST'])
def batch_test_routing():
    """
    Test multiple queries at once to evaluate routing decisions
    """
    data = request.json
    queries = data.get('queries', [])
    
    if not queries:
        return jsonify({'error': 'Queries array is required'}), 400
    
    router = QueryRouter()
    results = []
    
    for query in queries:
        classification = router.classify_query(query)
        results.append({
            'query': query,
            'routing': classification['routing'],
            'confidence': classification['confidence'],
            'query_type': classification['query_type'],
            'scores': classification['scores']
        })
    
    # Calculate statistics
    deterministic_count = sum(1 for r in results if r['routing'] == 'deterministic')
    rag_count = sum(1 for r in results if r['routing'] == 'rag')
    avg_confidence = sum(r['confidence'] for r in results) / len(results) if results else 0
    
    return jsonify({
        'results': results,
        'statistics': {
            'total_queries': len(results),
            'deterministic': deterministic_count,
            'rag': rag_count,
            'average_confidence': avg_confidence,
            'deterministic_percentage': (deterministic_count / len(results) * 100) if results else 0
        }
    })

