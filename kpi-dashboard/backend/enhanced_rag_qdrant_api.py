#!/usr/bin/env python3
"""
Enhanced RAG API endpoints using Qdrant Vector Database and OpenAI GPT-4
Provides advanced KPI and account analysis capabilities with production-grade vector search
"""

from flask import Blueprint, request, jsonify, abort
from auth_middleware import get_current_customer_id, get_current_user_id
from extensions import db
from models import KPI, KPIUpload, Account, CustomerConfig
from enhanced_rag_qdrant import get_qdrant_rag_system
import re
import os

enhanced_rag_qdrant_api = Blueprint('enhanced_rag_qdrant_api', __name__)

# Use get_current_customer_id from auth_middleware (imported at top)
# No need to redefine it here

@enhanced_rag_qdrant_api.route('/api/rag-qdrant/build', methods=['POST'])
def build_qdrant_knowledge_base():
    """Build Qdrant knowledge base for specific customer"""
    customer_id = get_current_customer_id()
    
    try:
        rag_system = get_qdrant_rag_system(customer_id)
        rag_system.build_knowledge_base(customer_id)
        
        # Get collection info
        collection_info = rag_system.get_collection_info()
        
        return jsonify({
            'status': 'success',
            'message': f'Qdrant knowledge base built successfully for customer {customer_id}',
            'customer_id': customer_id,
            'collection_info': collection_info
        })
    except Exception as e:
        return jsonify({'error': f'Failed to build Qdrant knowledge base: {str(e)}'}), 500

@enhanced_rag_qdrant_api.route('/api/rag-qdrant/query', methods=['POST'])
def qdrant_query():
    """Query the RAG system - falls back to OpenAI RAG if Qdrant is not available"""
    customer_id = get_current_customer_id()
    data = request.json
    
    if not data or 'query' not in data:
        return jsonify({'error': 'Query is required'}), 400
    
    query_text = data['query']
    query_type = data.get('query_type', 'general')
    collection = data.get('collection')  # Optional collection parameter
    
    # Auto-detect query type based on keywords
    if not query_type or query_type == 'auto':
        query_type = _detect_query_type(query_text)
    
    # Try Qdrant first, but fall back to OpenAI RAG if Qdrant is not available
    try:
        rag_system = get_qdrant_rag_system(customer_id)
        
        # Check if we're using local storage (which means Qdrant server is not available)
        if hasattr(rag_system, 'using_local_storage') and rag_system.using_local_storage:
            # Qdrant server not available, use OpenAI RAG instead
            log_info("Qdrant server not available, using OpenAI RAG fallback")
            return _use_openai_rag_fallback(customer_id, query_text, query_type)
        
        # Try to query Qdrant
        result = rag_system.query(query_text, query_type, collection=collection)
        
        # Check if result contains an error
        if isinstance(result, dict) and 'error' in result:
            error_msg = result['error']
            # If it's a connection or collection error, fall back to OpenAI RAG
            if any(phrase in error_msg.lower() for phrase in ['not found', 'connection', 'refused', 'not available']):
                print(f"⚠️ Qdrant error detected, falling back to OpenAI RAG: {error_msg[:100]}")
                return _use_openai_rag_fallback(customer_id, query_text, query_type)
        
        return jsonify(result)
    except Exception as e:
        error_msg = str(e)
        # If it's a Qdrant-related error, fall back to FAISS
        if any(phrase in error_msg.lower() for phrase in ['qdrant', 'connection', 'refused', 'collection', 'not found', 'bypassed']):
            log_warning(f"Qdrant error, using FAISS fallback: {error_msg[:100]}")
            return _use_openai_rag_fallback(customer_id, query_text, query_type)
        return jsonify({'error': f'Query failed: {error_msg}'}), 500

def _use_openai_rag_fallback(customer_id: int, query_text: str, query_type: str):
    """Fallback to FAISS (in-memory, no Docker) when Qdrant is not available"""
    try:
        # Use FAISS-based RAG system (in-memory, no Docker required)
        from enhanced_rag_openai import get_rag_system
        rag_system = get_rag_system(customer_id)
        
        # Ensure knowledge base is built
        if not hasattr(rag_system, 'faiss_index') or rag_system.faiss_index is None:
            print(f"🔧 Building knowledge base with FAISS (in-memory, no Docker)...")
            rag_system.build_knowledge_base(customer_id)
        
        # Query using FAISS-based RAG
        result = rag_system.query(query_text, query_type)
        result['rag_system'] = 'faiss_in_memory'  # Indicate we used FAISS (in-memory)
        return jsonify(result)
    except Exception as e:
        # If FAISS fails, try Working RAG as last resort (simple numpy)
        print(f"⚠️ FAISS RAG failed, trying simple Working RAG fallback: {str(e)[:100]}")
        try:
            from working_rag_system import WorkingRAGSystem
            rag_system = WorkingRAGSystem()
            
            # Ensure knowledge base is built
            if not rag_system.vectors or not rag_system.data:
                print(f"🔧 Building knowledge base using Working RAG system (simple numpy)...")
                rag_system.build_knowledge_base(customer_id)
            
            # Query using Working RAG (simple in-memory cosine similarity)
            result = rag_system.query(query_text, query_type)
            result['rag_system'] = 'working_rag_simple_numpy'  # Indicate we used simple numpy fallback
            return jsonify(result)
        except Exception as e2:
            return jsonify({
                'error': f'RAG query failed: {str(e2)}',
                'suggestion': 'Please ensure OpenAI API key is configured and knowledge base is built'
            }), 500

@enhanced_rag_qdrant_api.route('/api/rag-qdrant/revenue-analysis', methods=['GET'])
def analyze_revenue_drivers_qdrant():
    """Analyze revenue drivers across accounts using Qdrant"""
    customer_id = get_current_customer_id()
    
    try:
        rag_system = get_qdrant_rag_system(customer_id)
        analysis = rag_system.analyze_revenue_drivers(customer_id)
        return jsonify(analysis)
    except Exception as e:
        return jsonify({'error': f'Revenue analysis failed: {str(e)}'}), 500

@enhanced_rag_qdrant_api.route('/api/rag-qdrant/risk-analysis', methods=['GET'])
def analyze_at_risk_accounts_qdrant():
    """Find accounts at risk of churn using Qdrant"""
    customer_id = get_current_customer_id()
    
    try:
        rag_system = get_qdrant_rag_system(customer_id)
        analysis = rag_system.find_at_risk_accounts(customer_id)
        return jsonify(analysis)
    except Exception as e:
        return jsonify({'error': f'Risk analysis failed: {str(e)}'}), 500

@enhanced_rag_qdrant_api.route('/api/rag-qdrant/status', methods=['GET'])
def get_knowledge_base_status():
    """Check if knowledge base is built for the customer"""
    customer_id = get_current_customer_id()
    
    try:
        rag_system = get_qdrant_rag_system(customer_id)
        
        # Check if Qdrant is bypassed
        if hasattr(rag_system, 'qdrant_bypassed') and rag_system.qdrant_bypassed:
            return jsonify({
                'customer_id': customer_id,
                'is_built': False,
                'status': 'qdrant_bypassed',
                'message': 'Qdrant is bypassed - will use FAISS fallback'
            })
        
        # Check if Qdrant client exists
        if not hasattr(rag_system, 'qdrant_client') or rag_system.qdrant_client is None:
            return jsonify({
                'customer_id': customer_id,
                'is_built': False,
                'status': 'no_client',
                'message': 'Qdrant client not available'
            })
        
        # Set collection name if not set
        if not hasattr(rag_system, 'collection_name') or not rag_system.collection_name:
            collection_name_base = os.getenv('QDRANT_COLLECTION', 'kpi_dashboard_vectors')
            rag_system.collection_name = f"{collection_name_base}_customer_{customer_id}"
        
        # Check if collection exists and has data
        try:
            collection_info = rag_system.qdrant_client.get_collection(rag_system.collection_name)
            points_count = collection_info.points_count if hasattr(collection_info, 'points_count') else 0
            
            # Check if collection has product data by sampling points
            has_products = False
            if points_count > 0:
                try:
                    # Sample points to check for product type
                    sample_results = rag_system.qdrant_client.scroll(
                        collection_name=rag_system.collection_name,
                        limit=min(100, points_count),
                        with_payload=True
                    )
                    if sample_results and len(sample_results[0]) > 0:
                        for point in sample_results[0]:
                            if hasattr(point, 'payload') and point.payload:
                                if point.payload.get('type') == 'product':
                                    has_products = True
                                    break
                except Exception as e:
                    print(f"⚠️ Could not check for products: {str(e)[:100]}")
                    # If we can't check, assume products might be missing
            
            is_built = points_count > 0
            # If built but no products found, suggest rebuild
            # Also check if there are any products in the database for this customer
            needs_rebuild = False
            if is_built and not has_products:
                # Check if products exist in database for this customer
                try:
                    from models import Product
                    product_count = Product.query.filter_by(customer_id=customer_id).count()
                    if product_count > 0:
                        # Products exist in DB but not in knowledge base - needs rebuild
                        needs_rebuild = True
                except:
                    pass  # If we can't check DB, assume rebuild might be needed
            
            return jsonify({
                'customer_id': customer_id,
                'is_built': is_built,
                'status': 'ready' if is_built else 'not_built',
                'points_count': points_count,
                'has_products': has_products,
                'needs_rebuild': needs_rebuild,
                'collection_name': rag_system.collection_name
            })
        except Exception as e:
            # Collection doesn't exist or error accessing it
            error_msg = str(e).lower()
            if 'not found' in error_msg or 'does not exist' in error_msg or '404' in error_msg:
                return jsonify({
                    'customer_id': customer_id,
                    'is_built': False,
                    'status': 'not_built',
                    'message': 'Collection does not exist - knowledge base needs to be built'
                })
            else:
                # Other error
                return jsonify({
                    'customer_id': customer_id,
                    'is_built': False,
                    'status': 'error',
                    'error': str(e)[:200]
                }), 500
                
    except Exception as e:
        return jsonify({
            'customer_id': customer_id,
            'is_built': False,
            'status': 'error',
            'error': str(e)[:200]
        }), 500

@enhanced_rag_qdrant_api.route('/api/rag-qdrant/collection-info', methods=['GET'])
def get_collection_info():
    """Get Qdrant collection information"""
    customer_id = get_current_customer_id()
    
    try:
        rag_system = get_qdrant_rag_system(customer_id)
        collection_info = rag_system.get_collection_info()
        return jsonify(collection_info)
    except Exception as e:
        return jsonify({'error': f'Failed to get collection info: {str(e)}'}), 500

@enhanced_rag_qdrant_api.route('/api/rag-qdrant/account/<int:account_id>', methods=['GET'])
def analyze_specific_account_qdrant(account_id):
    """Analyze a specific account's performance using Qdrant"""
    customer_id = get_current_customer_id()
    
    try:
        rag_system = get_qdrant_rag_system(customer_id)
        
        # Query for specific account data
        query_text = f"Analyze account {account_id} performance and health"
        result = rag_system.query(query_text, 'account_analysis')
        
        return jsonify({
            'account_id': account_id,
            'customer_id': customer_id,
            'analysis': result
        })
    except Exception as e:
        return jsonify({'error': f'Account analysis failed: {str(e)}'}), 500

@enhanced_rag_qdrant_api.route('/api/rag-qdrant/industry/<industry>', methods=['GET'])
def analyze_industry_performance_qdrant(industry):
    """Analyze performance by industry using Qdrant"""
    customer_id = get_current_customer_id()
    
    try:
        rag_system = get_qdrant_rag_system(customer_id)
        
        # Query for industry-specific data
        query_text = f"Analyze {industry} industry performance and trends"
        result = rag_system.query(query_text, 'revenue_analysis')
        
        return jsonify({
            'industry': industry,
            'customer_id': customer_id,
            'analysis': result
        })
    except Exception as e:
        return jsonify({'error': f'Industry analysis failed: {str(e)}'}), 500

@enhanced_rag_qdrant_api.route('/api/rag-qdrant/top-accounts', methods=['GET'])
def get_top_accounts_qdrant():
    """Get top accounts by revenue using Qdrant"""
    customer_id = get_current_customer_id()
    
    try:
        rag_system = get_qdrant_rag_system(customer_id)
        
        # Query for top accounts
        query_text = "Show me the top performing accounts by revenue"
        result = rag_system.query(query_text, 'revenue_analysis')
        
        return jsonify({
            'customer_id': customer_id,
            'analysis': result
        })
    except Exception as e:
        return jsonify({'error': f'Failed to get top accounts: {str(e)}'}), 500

@enhanced_rag_qdrant_api.route('/api/rag-qdrant/kpi-performance', methods=['GET'])
def analyze_kpi_performance_qdrant():
    """Analyze KPI performance across all accounts using Qdrant"""
    customer_id = get_current_customer_id()
    
    try:
        rag_system = get_qdrant_rag_system(customer_id)
        
        # Query for KPI performance
        query_text = "Analyze KPI performance across all categories and provide insights"
        result = rag_system.query(query_text, 'kpi_analysis')
        
        return jsonify({
            'customer_id': customer_id,
            'analysis': result
        })
    except Exception as e:
        return jsonify({'error': f'KPI analysis failed: {str(e)}'}), 500

@enhanced_rag_qdrant_api.route('/api/rag-qdrant/query-simple', methods=['POST'])
def simple_query_qdrant():
    """Simple natural language query handler using Qdrant"""
    customer_id = get_current_customer_id()
    data = request.json
    if not data or 'query' not in data:
        return jsonify({'error': 'Query is required'}), 400
    
    query_text = data['query'].lower()
    
    try:
        rag_system = get_qdrant_rag_system(customer_id)
        
        # Parse revenue questions
        if 'revenue' in query_text:
            import re
            amount_match = re.search(r'(\$?)(\d+(?:,\d+)*(?:\.\d+)?)([km]?)', query_text)
            
            if amount_match:
                amount_str = amount_match.group(2).replace(',', '')
                multiplier = 1000 if amount_match.group(3) == 'k' else 1000000 if amount_match.group(3) == 'm' else 1
                revenue_threshold = float(amount_str) * multiplier
                
                # Get all accounts
                accounts = Account.query.filter_by(customer_id=customer_id).all()
                
                # Determine filter type based on keywords
                if any(keyword in query_text for keyword in ['more than', 'greater than', 'above', 'over']):
                    filtered_accounts = [acc for acc in accounts if float(acc.revenue) >= revenue_threshold]
                    interpretation = f'Accounts with revenue >= ${revenue_threshold:,.0f}'
                elif any(keyword in query_text for keyword in ['less than', 'below', 'under', 'less']):
                    filtered_accounts = [acc for acc in accounts if float(acc.revenue) < revenue_threshold]
                    interpretation = f'Accounts with revenue < ${revenue_threshold:,.0f}'
                else:
                    filtered_accounts = [acc for acc in accounts if float(acc.revenue) >= revenue_threshold]
                    interpretation = f'Accounts with revenue >= ${revenue_threshold:,.0f}'
                
                # Sort by revenue descending
                filtered_accounts.sort(key=lambda x: float(x.revenue), reverse=True)
                
                result = {
                    'query': data['query'],
                    'interpretation': interpretation,
                    'accounts': [{
                        'account_id': acc.account_id,
                        'account_name': acc.account_name,
                        'revenue': float(acc.revenue),
                        'industry': acc.industry,
                        'region': acc.region
                    } for acc in filtered_accounts],
                    'total_accounts': len(filtered_accounts),
                    'total_revenue': sum(float(acc.revenue) for acc in filtered_accounts),
                    'average_revenue': sum(float(acc.revenue) for acc in filtered_accounts) / len(filtered_accounts) if filtered_accounts else 0
                }
                
                return jsonify(result)
        
        # Handle other query types with Qdrant
        result = rag_system.query(data['query'], 'general')
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'error': f'Query failed: {str(e)}'}), 500

def _detect_query_type(query_text: str) -> str:
    """Auto-detect query type based on keywords - ✅ RECOMMENDATION 3: Enhanced product query detection"""
    query_lower = query_text.lower()
    
    # ✅ RECOMMENDATION 3: Enhanced product health score queries
    product_health_keywords = [
        'product health', 'product health score', 'health score for product', 'product score',
        'product performance', 'product underperforming', 'products that need attention',
        'product health scores', 'compare product health', 'average health score per product',
        'product-level health', 'product health trend', 'product health analytics'
    ]
    if any(keyword in query_lower for keyword in product_health_keywords):
        return 'product_analysis'
    
    # ✅ RECOMMENDATION 3: Enhanced product adoption queries
    product_adoption_keywords = [
        'product adoption', 'adoption rate', 'product activation', 'product activation rate',
        'low adoption', 'product adoption across', 'adoption rates', 'product usage rate'
    ]
    if any(keyword in query_lower for keyword in product_adoption_keywords):
        return 'product_analysis'
    
    # ✅ RECOMMENDATION 3: Product-level KPI queries
    product_kpi_keywords = [
        'product-level kpi', 'product kpi', 'product-level kpis', 'product kpis',
        'kpi for product', 'kpis for product', 'product metrics', 'product-level metrics'
    ]
    if any(keyword in query_lower for keyword in product_kpi_keywords):
        return 'product_analysis'
    
    # Product-related keywords (check first for product queries)
    product_keywords = [
        'product', 'products', 'which product', 'what product', 'product name', 'product used',
        'product across', 'widely used', 'most used', 'popular product',
        'products used', 'products across', 'products widely', 'product deployed', 'product utilized',
        'product names', 'list products', 'show products', 'what products', 'which products',
        'product usage', 'product utilization', 'most popular product',
        'commonly used product', 'frequently used product', 'product list', 'all products',
        'revenue by product', 'revenue trends by product', 'products generate revenue',
        'accounts use multiple products', 'multi-product', 'multiple products'
    ]
    if any(keyword in query_lower for keyword in product_keywords):
        return 'product_analysis'
    
    # Revenue-related keywords
    revenue_keywords = ['revenue', 'growth', 'money', 'dollar', 'profit', 'income', 'sales', 'earnings']
    if any(keyword in query_lower for keyword in revenue_keywords):
        return 'revenue_analysis'
    
    # Account-related keywords
    account_keywords = ['account', 'customer', 'client', 'relationship', 'engagement', 'satisfaction', 'churn']
    if any(keyword in query_lower for keyword in account_keywords):
        return 'account_analysis'
    
    # KPI-related keywords
    kpi_keywords = ['kpi', 'metric', 'performance', 'score', 'measurement', 'indicator']
    if any(keyword in query_lower for keyword in kpi_keywords):
        return 'kpi_analysis'
    
    return 'general'
