from flask import Blueprint, request, jsonify
from extensions import db
from models import KPI, KPIUpload, Account
import pandas as pd
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import re
import json
from datetime import datetime, timedelta

rag_api = Blueprint('rag_api', __name__)

class AccountAnalyticsRAGSystem:
    def __init__(self):
        self.vectorizer = TfidfVectorizer(stop_words='english', max_features=1000)
        self.account_embeddings = None
        self.account_data = []
        
    def build_account_knowledge_base(self, customer_id):
        """Build knowledge base from account and KPI data"""
        # Get all accounts for customer
        accounts = Account.query.filter_by(customer_id=customer_id).all()
        
        self.account_data = []
        for account in accounts:
            # Get KPIs for this account
            account_kpis = KPI.query.filter_by(account_id=account.account_id).all()
            
            # Create comprehensive account profile
            account_text = f"""
            Account: {account.account_name}
            Revenue: ${account.revenue:,.2f}
            Industry: {account.industry or 'Not specified'}
            Region: {account.region or 'Not specified'}
            Status: {account.account_status}
            
            KPI Summary:
            """
            
            # Add KPI details
            for kpi in account_kpis:
                account_text += f"""
                - {kpi.category}: {kpi.kpi_parameter} = {kpi.data} (Weight: {kpi.weight}, Impact: {kpi.impact_level})
                """
            
            self.account_data.append({
                'account_id': account.account_id,
                'account_name': account.account_name,
                'revenue': float(account.revenue),
                'industry': account.industry,
                'region': account.region,
                'status': account.account_status,
                'text': account_text,
                'kpis': account_kpis
            })
        
        # Create TF-IDF embeddings
        texts = [item['text'] for item in self.account_data]
        if texts:
            self.account_embeddings = self.vectorizer.fit_transform(texts)
        
        return self.account_data
    
    def analyze_account_growth(self, customer_id):
        """Analyze which accounts have the best growth and what drives it"""
        accounts = self.build_account_knowledge_base(customer_id)
        
        if not accounts:
            return {"error": "No accounts found"}
        
        # Analyze growth patterns
        growth_analysis = []
        
        for account in accounts:
            # Calculate growth score based on KPI performance
            growth_score = self._calculate_growth_score(account)
            revenue_impact = self._analyze_revenue_drivers(account)
            
            growth_analysis.append({
                'account_name': account['account_name'],
                'revenue': account['revenue'],
                'growth_score': growth_score,
                'revenue_drivers': revenue_impact,
                'industry': account['industry'],
                'region': account['region']
            })
        
        # Sort by growth score
        growth_analysis.sort(key=lambda x: x['growth_score'], reverse=True)
        
        return {
            'top_growing_accounts': growth_analysis[:5],
            'total_accounts': len(accounts),
            'analysis_summary': self._generate_growth_summary(growth_analysis)
        }
    
    def _calculate_growth_score(self, account):
        """Calculate growth score based on KPI performance"""
        score = 0
        total_weight = 0
        
        for kpi in account['kpis']:
            try:
                # Convert KPI data to numeric
                kpi_value = self._parse_kpi_value(kpi.data)
                weight = self._parse_weight(kpi.weight)
                
                if kpi_value is not None and weight is not None:
                    # Normalize KPI value (assuming 0-100 scale)
                    normalized_value = min(max(kpi_value, 0), 100) / 100
                    score += normalized_value * weight
                    total_weight += weight
            except:
                continue
        
        return score / total_weight if total_weight > 0 else 0
    
    def _analyze_revenue_drivers(self, account):
        """Analyze what drives revenue for this account"""
        drivers = []
        
        for kpi in account['kpis']:
            if kpi.impact_level and 'high' in kpi.impact_level.lower():
                drivers.append({
                    'kpi': kpi.kpi_parameter,
                    'category': kpi.category,
                    'value': kpi.data,
                    'impact': kpi.impact_level
                })
        
        return drivers
    
    def _parse_kpi_value(self, data):
        """Parse KPI data to numeric value"""
        if not data:
            return None
        
        # Try to extract numeric value
        try:
            # Remove common non-numeric characters
            clean_data = re.sub(r'[^\d.]', '', str(data))
            if clean_data:
                return float(clean_data)
        except:
            pass
        
        # Try to parse percentage
        if '%' in str(data):
            try:
                return float(re.sub(r'[^\d.]', '', str(data)))
            except:
                pass
        
        return None
    
    def _parse_weight(self, weight):
        """Parse weight to numeric value"""
        if not weight:
            return None
        
        try:
            return float(weight)
        except:
            return None
    
    def _generate_growth_summary(self, growth_analysis):
        """Generate summary of growth patterns"""
        if not growth_analysis:
            return "No growth data available"
        
        top_account = growth_analysis[0]
        avg_revenue = sum(acc['revenue'] for acc in growth_analysis) / len(growth_analysis)
        
        summary = f"""
        Top performing account: {top_account['account_name']} (Revenue: ${top_account['revenue']:,.2f})
        Average revenue across accounts: ${avg_revenue:,.2f}
        
        Key revenue drivers for top account:
        """
        
        for driver in top_account['revenue_drivers'][:3]:
            summary += f"- {driver['kpi']} ({driver['category']}): {driver['value']}\n"
        
        return summary

class KPIRAGSystem:
    def __init__(self):
        self.vectorizer = TfidfVectorizer(stop_words='english', max_features=1000)
        self.kpi_embeddings = None
        self.kpi_data = []
        
    def build_knowledge_base(self, upload_id=None):
        """Build knowledge base from KPI data"""
        if upload_id:
            kpis = KPI.query.filter_by(upload_id=upload_id).all()
        else:
            # Get latest upload for customer_id=1 (fallback for backward compatibility)
            latest_upload = KPIUpload.query.filter_by(customer_id=1).order_by(KPIUpload.version.desc()).first()
            if not latest_upload:
                return []
            kpis = KPI.query.filter_by(upload_id=latest_upload.upload_id).all()
        
        self.kpi_data = []
        for kpi in kpis:
            # Create a comprehensive text representation of the KPI
            kpi_text = f"""
            Category: {kpi.category}
            Health Score Component: {kpi.health_score_component}
            Weight: {kpi.weight}
            Data: {kpi.data}
            Source Review: {kpi.source_review}
            KPI Parameter: {kpi.kpi_parameter}
            Impact Level: {kpi.impact_level}
            Measurement Frequency: {kpi.measurement_frequency}
            """
            self.kpi_data.append({
                'kpi_id': kpi.kpi_id,
                'text': kpi_text,
                'kpi': kpi
            })
        
        # Create TF-IDF embeddings
        texts = [item['text'] for item in self.kpi_data]
        if texts:
            self.kpi_embeddings = self.vectorizer.fit_transform(texts)
        
        return self.kpi_data

    def build_knowledge_base_from_customer(self, customer_id):
        """Build knowledge base from all customer data in Data Management"""
        self.kpi_data = []
        
        # Get all KPIs for the customer with account information
        kpis_with_accounts = db.session.query(KPI, Account).join(
            KPIUpload, KPI.upload_id == KPIUpload.upload_id
        ).join(
            Account, KPI.account_id == Account.account_id, isouter=True
        ).filter(KPIUpload.customer_id == customer_id).all()
        
        for kpi, account in kpis_with_accounts:
            # Create comprehensive KPI text with account context
            account_info = f"Account: {account.account_name if account else 'Unknown'}"
            if account:
                account_info += f" (Revenue: ${account.revenue:,.0f}, Industry: {account.industry}, Region: {account.region})"
            
            kpi_text = f"""
            {account_info}
            KPI: {kpi.kpi_parameter}
            Category: {kpi.category}
            Data: {kpi.data}
            Impact Level: {kpi.impact_level}
            Measurement Frequency: {kpi.measurement_frequency}
            Weight: {kpi.weight}
            Source Review: {kpi.source_review}
            Health Score Component: {kpi.health_score_component}
            """
            
            self.kpi_data.append({
                'kpi_id': kpi.kpi_id,
                'upload_id': kpi.upload_id,
                'account_id': kpi.account_id,
                'account_name': account.account_name if account else 'Unknown',
                'account_revenue': float(account.revenue) if account else 0,
                'account_industry': account.industry if account else 'Unknown',
                'account_region': account.region if account else 'Unknown',
                'kpi': kpi,
                'text': kpi_text
            })
        
        # Create TF-IDF embeddings
        texts = [item['text'] for item in self.kpi_data]
        if texts:
            self.kpi_embeddings = self.vectorizer.fit_transform(texts)
        
        return self.kpi_data
    
    def semantic_search(self, query, top_k=10):
        """Perform semantic search on KPI data"""
        if self.kpi_embeddings is None or len(self.kpi_data) == 0:
            self.build_knowledge_base()
        
        if len(self.kpi_data) == 0:
            return []
        
        # Analyze query type first
        query_type = self.analyze_query(query)
        
        # For specific query types, filter by actual data rather than just similarity
        if query_type == "impact_analysis":
            return self._filter_by_impact_level(query)
        elif query_type == "weight_analysis":
            return self._filter_by_weight(query)
        elif query_type == "frequency_analysis":
            return self._filter_by_frequency(query)
        elif query_type == "category_analysis":
            return self._filter_by_category(query)
        else:
            # Use semantic search for general queries
            return self._semantic_search_general(query, top_k)
    
    def _filter_by_impact_level(self, query):
        """Filter KPIs by impact level"""
        query_lower = query.lower()
        results = []
        
        # Define impact level keywords
        high_impact_keywords = ['high', 'critical', 'important', 'high-impact']
        medium_impact_keywords = ['medium', 'moderate']
        low_impact_keywords = ['low', 'minor']
        
        for item in self.kpi_data:
            kpi = item['kpi']
            impact_level = str(kpi.impact_level).lower() if kpi.impact_level else ""
            
            # Check if KPI matches the query
            matches = False
            if any(keyword in query_lower for keyword in high_impact_keywords):
                if any(keyword in impact_level for keyword in high_impact_keywords):
                    matches = True
            elif any(keyword in query_lower for keyword in medium_impact_keywords):
                if any(keyword in impact_level for keyword in medium_impact_keywords):
                    matches = True
            elif any(keyword in query_lower for keyword in low_impact_keywords):
                if any(keyword in impact_level for keyword in low_impact_keywords):
                    matches = True
            else:
                # General impact query - include all with impact levels
                if impact_level:
                    matches = True
            
            if matches and kpi.impact_level:
                results.append({
                    'kpi_id': item['kpi_id'],
                    'similarity': 1.0,  # Exact match
                    'kpi': {
                        'category': kpi.category,
                        'health_score_component': kpi.health_score_component,
                        'weight': kpi.weight,
                        'data': kpi.data,
                        'source_review': kpi.source_review,
                        'kpi_parameter': kpi.kpi_parameter,
                        'impact_level': kpi.impact_level,
                        'measurement_frequency': kpi.measurement_frequency,
                    }
                })
        
        return results
    
    def _filter_by_weight(self, query):
        """Filter KPIs by weight"""
        results = []
        query_lower = query.lower()
        
        for item in self.kpi_data:
            kpi = item['kpi']
            weight = str(kpi.weight).lower() if kpi.weight else ""
            
            if weight and ('high' in query_lower or 'weight' in query_lower):
                results.append({
                    'kpi_id': item['kpi_id'],
                    'similarity': 1.0,
                    'kpi': {
                        'category': kpi.category,
                        'health_score_component': kpi.health_score_component,
                        'weight': kpi.weight,
                        'data': kpi.data,
                        'source_review': kpi.source_review,
                        'kpi_parameter': kpi.kpi_parameter,
                        'impact_level': kpi.impact_level,
                        'measurement_frequency': kpi.measurement_frequency,
                    }
                })
        
        return results
    
    def _filter_by_frequency(self, query):
        """Filter KPIs by measurement frequency"""
        results = []
        query_lower = query.lower()
        # Define possible frequency keywords
        freq_keywords = ['quarterly', 'monthly', 'weekly', 'daily', 'annual', 'yearly', 'per customer']
        matched_freqs = [freq for freq in freq_keywords if freq in query_lower]
        for item in self.kpi_data:
            kpi = item['kpi']
            freq = (kpi.measurement_frequency or '').lower()
            # If the query specifies a frequency, filter for it
            if matched_freqs:
                if any(f in freq for f in matched_freqs):
                    results.append({
                        'kpi_id': item['kpi_id'],
                        'similarity': 1.0,
                        'kpi': {
                            'category': kpi.category,
                            'health_score_component': kpi.health_score_component,
                            'weight': kpi.weight,
                            'data': kpi.data,
                            'source_review': kpi.source_review,
                            'kpi_parameter': kpi.kpi_parameter,
                            'impact_level': kpi.impact_level,
                            'measurement_frequency': kpi.measurement_frequency,
                        }
                    })
            # If no specific frequency in query, return all with a frequency
            elif freq:
                results.append({
                    'kpi_id': item['kpi_id'],
                    'similarity': 1.0,
                    'kpi': {
                        'category': kpi.category,
                        'health_score_component': kpi.health_score_component,
                        'weight': kpi.weight,
                        'data': kpi.data,
                        'source_review': kpi.source_review,
                        'kpi_parameter': kpi.kpi_parameter,
                        'impact_level': kpi.impact_level,
                        'measurement_frequency': kpi.measurement_frequency,
                    }
                })
        return results
    
    def _filter_by_category(self, query):
        """Filter KPIs by category"""
        results = []
        query_lower = query.lower()
        
        for item in self.kpi_data:
            kpi = item['kpi']
            category = kpi.category.lower()
            
            if any(keyword in category for keyword in query_lower.split()):
                results.append({
                    'kpi_id': item['kpi_id'],
                    'similarity': 1.0,
                    'kpi': {
                        'category': kpi.category,
                        'health_score_component': kpi.health_score_component,
                        'weight': kpi.weight,
                        'data': kpi.data,
                        'source_review': kpi.source_review,
                        'kpi_parameter': kpi.kpi_parameter,
                        'impact_level': kpi.impact_level,
                        'measurement_frequency': kpi.measurement_frequency,
                    }
                })
        
        return results
    
    def _semantic_search_general(self, query, top_k=10):
        """General semantic search using TF-IDF"""
        # Vectorize the query
        query_vector = self.vectorizer.transform([query])
        
        # Calculate similarities
        similarities = cosine_similarity(query_vector, self.kpi_embeddings).flatten()
        
        # Get top matches
        top_indices = similarities.argsort()[-top_k:][::-1]
        
        results = []
        for idx in top_indices:
            if similarities[idx] > 0.05:  # Minimum similarity threshold
                results.append({
                    'kpi_id': self.kpi_data[idx]['kpi_id'],
                    'similarity': float(similarities[idx]),
                    'kpi': {
                        'category': self.kpi_data[idx]['kpi'].category,
                        'health_score_component': self.kpi_data[idx]['kpi'].health_score_component,
                        'weight': self.kpi_data[idx]['kpi'].weight,
                        'data': self.kpi_data[idx]['kpi'].data,
                        'source_review': self.kpi_data[idx]['kpi'].source_review,
                        'kpi_parameter': self.kpi_data[idx]['kpi'].kpi_parameter,
                        'impact_level': self.kpi_data[idx]['kpi'].impact_level,
                        'measurement_frequency': self.kpi_data[idx]['kpi'].measurement_frequency,
                    }
                })
        
        return results
    
    def analyze_query(self, query):
        """Analyze the type of query and provide insights"""
        query_lower = query.lower()
        
        # Pattern matching for different query types
        if any(word in query_lower for word in ['health', 'score', 'overall', 'performance', 'best', 'worst', 'top']):
            return "health_score_analysis"
        elif any(word in query_lower for word in ['weight', 'importance', 'priority']):
            return "weight_analysis"
        elif any(word in query_lower for word in ['impact', 'level', 'critical', 'high-impact', 'high impact']):
            return "impact_analysis"
        elif any(word in query_lower for word in ['frequency', 'measurement', 'tracking']):
            return "frequency_analysis"
        elif any(word in query_lower for word in ['category', 'type', 'group']):
            return "category_analysis"
        else:
            return "general_search"

def calculate_health_score(kpis, component_name):
    """Calculate health score for a specific component"""
    component_kpis = [kpi for kpi in kpis 
                     if component_name.lower() in kpi.health_score_component.lower()]
    
    if not component_kpis:
        return 0
    
    total_score = 0
    total_weight = 0
    
    for kpi in component_kpis:
        try:
            # Parse data value
            data_str = str(kpi.data).replace('%', '').replace('$', '').replace('K', '000').replace('M', '000000')
            value = float(data_str) if data_str.strip() else 0
            
            # Use weight if available
            weight = float(kpi.weight) if kpi.weight else 1
            
            total_score += value * weight
            total_weight += weight
        except (ValueError, TypeError):
            continue
    
    return total_score / total_weight if total_weight > 0 else 0

def calculate_overall_health_score(category_scores):
    """Calculate overall health score from category scores"""
    valid_scores = [score for score in category_scores.values() if score > 0]
    return sum(valid_scores) / len(valid_scores) if valid_scores else 0

def analyze_health_scores(customer_id):
    """Analyze health scores across all accounts"""
    accounts = Account.query.filter_by(customer_id=customer_id).all()
    
    health_analysis = []
    total_revenue = 0
    
    for account in accounts:
        account_kpis = KPI.query.filter_by(account_id=account.account_id).all()
        
        if account_kpis:
            # Calculate health scores
            product_usage = calculate_health_score(account_kpis, 'Product Usage')
            support = calculate_health_score(account_kpis, 'Support')
            customer_sentiment = calculate_health_score(account_kpis, 'Customer Sentiment')
            business_outcomes = calculate_health_score(account_kpis, 'Business Outcomes')
            relationship_strength = calculate_health_score(account_kpis, 'Relationship Strength')
            
            overall = calculate_overall_health_score({
                'product_usage': product_usage,
                'support': support,
                'customer_sentiment': customer_sentiment,
                'business_outcomes': business_outcomes,
                'relationship_strength': relationship_strength
            })
            
            health_analysis.append({
                'account_name': account.account_name,
                'account_id': account.account_id,
                'revenue': float(account.revenue),
                'industry': account.industry,
                'region': account.region,
                'health_scores': {
                    'product_usage': product_usage,
                    'support': support,
                    'customer_sentiment': customer_sentiment,
                    'business_outcomes': business_outcomes,
                    'relationship_strength': relationship_strength,
                    'overall': overall
                }
            })
            
            total_revenue += float(account.revenue)
    
    # Calculate corporate averages
    if health_analysis:
        corporate_scores = {
            'product_usage': sum(a['health_scores']['product_usage'] for a in health_analysis) / len(health_analysis),
            'support': sum(a['health_scores']['support'] for a in health_analysis) / len(health_analysis),
            'customer_sentiment': sum(a['health_scores']['customer_sentiment'] for a in health_analysis) / len(health_analysis),
            'business_outcomes': sum(a['health_scores']['business_outcomes'] for a in health_analysis) / len(health_analysis),
            'relationship_strength': sum(a['health_scores']['relationship_strength'] for a in health_analysis) / len(health_analysis),
            'overall': sum(a['health_scores']['overall'] for a in health_analysis) / len(health_analysis)
        }
    else:
        corporate_scores = {
            'product_usage': 0, 'support': 0, 'customer_sentiment': 0,
            'business_outcomes': 0, 'relationship_strength': 0, 'overall': 0
        }
    
    return {
        'accounts': health_analysis,
        'corporate_scores': corporate_scores,
        'total_accounts': len(health_analysis),
        'total_revenue': total_revenue,
        'best_performing_accounts': sorted(health_analysis, key=lambda x: x['health_scores']['overall'], reverse=True)[:5],
        'worst_performing_accounts': sorted(health_analysis, key=lambda x: x['health_scores']['overall'])[:5]
    }

# Initialize RAG system
rag_system = KPIRAGSystem()
account_rag_system = AccountAnalyticsRAGSystem()

@rag_api.route('/api/rag/account/growth', methods=['POST'])
def analyze_account_growth():
    """Analyze account growth patterns and revenue drivers"""
    try:
        customer_id = request.headers.get('X-Customer-ID')
        if not customer_id:
            return jsonify({'error': 'Missing X-Customer-ID header'}), 400
        
        analysis = account_rag_system.analyze_account_growth(int(customer_id))
        return jsonify(analysis)
    except Exception as e:
        print(f"Error in account growth analysis: {str(e)}")
        return jsonify({'error': str(e)}), 500

@rag_api.route('/api/rag/account/query', methods=['POST'])
def query_account_analytics():
    """Answer questions about account performance, growth, and revenue drivers"""
    try:
        customer_id = request.headers.get('X-Customer-ID')
        if not customer_id:
            return jsonify({'error': 'Missing X-Customer-ID header'}), 400
        
        data = request.json
        query = data.get('query', '').lower()
        
        # Build account knowledge base
        accounts = account_rag_system.build_account_knowledge_base(int(customer_id))
        
        if not accounts:
            return jsonify({'error': 'No accounts found'}), 404
        
        # Analyze query type and provide relevant insights
        if 'growth' in query or 'best' in query:
            analysis = account_rag_system.analyze_account_growth(int(customer_id))
            return jsonify({
                'query': query,
                'analysis': analysis,
                'insights': _generate_growth_insights(analysis)
            })
        
        elif 'revenue' in query and 'driver' in query:
            revenue_analysis = _analyze_revenue_drivers_across_accounts(accounts)
            return jsonify({
                'query': query,
                'revenue_drivers': revenue_analysis
            })
        
        elif 'industry' in query or 'region' in query:
            industry_analysis = _analyze_by_industry_region(accounts)
            return jsonify({
                'query': query,
                'industry_analysis': industry_analysis
            })
        
        else:
            # General account analysis
            general_analysis = _generate_general_account_insights(accounts)
            return jsonify({
                'query': query,
                'general_analysis': general_analysis
            })
            
    except Exception as e:
        print(f"Error in account analytics query: {str(e)}")
        return jsonify({'error': str(e)}), 500

def _generate_growth_insights(analysis):
    """Generate insights from growth analysis"""
    if 'top_growing_accounts' not in analysis:
        return "No growth data available"
    
    top_accounts = analysis['top_growing_accounts']
    if not top_accounts:
        return "No growing accounts found"
    
    insights = []
    for i, account in enumerate(top_accounts[:3]):
        insight = f"#{i+1} Growing Account: {account['account_name']} "
        insight += f"(Revenue: ${account['revenue']:,.2f}, Growth Score: {account['growth_score']:.2f})"
        
        if account['revenue_drivers']:
            insight += f"\nKey drivers: {', '.join([d['kpi'] for d in account['revenue_drivers'][:2]])}"
        
        insights.append(insight)
    
    return insights

def _analyze_revenue_drivers_across_accounts(accounts):
    """Analyze revenue drivers across all accounts"""
    all_drivers = {}
    
    for account in accounts:
        for kpi in account['kpis']:
            if kpi.impact_level and 'high' in kpi.impact_level.lower():
                driver_key = kpi.kpi_parameter
                if driver_key not in all_drivers:
                    all_drivers[driver_key] = {
                        'kpi': kpi.kpi_parameter,
                        'category': kpi.category,
                        'accounts_affected': 0,
                        'total_revenue_impact': 0
                    }
                
                all_drivers[driver_key]['accounts_affected'] += 1
                all_drivers[driver_key]['total_revenue_impact'] += account['revenue']
    
    # Sort by revenue impact
    sorted_drivers = sorted(all_drivers.values(), 
                           key=lambda x: x['total_revenue_impact'], reverse=True)
    
    return sorted_drivers[:5]  # Top 5 revenue drivers

def _analyze_by_industry_region(accounts):
    """Analyze performance by industry and region"""
    industry_stats = {}
    region_stats = {}
    
    for account in accounts:
        # Industry analysis
        industry = account['industry'] or 'Unknown'
        if industry not in industry_stats:
            industry_stats[industry] = {
                'count': 0,
                'total_revenue': 0,
                'avg_growth_score': 0
            }
        
        industry_stats[industry]['count'] += 1
        industry_stats[industry]['total_revenue'] += account['revenue']
        
        # Region analysis
        region = account['region'] or 'Unknown'
        if region not in region_stats:
            region_stats[region] = {
                'count': 0,
                'total_revenue': 0
            }
        
        region_stats[region]['count'] += 1
        region_stats[region]['total_revenue'] += account['revenue']
    
    return {
        'industry_analysis': industry_stats,
        'region_analysis': region_stats
    }

def _generate_general_account_insights(accounts):
    """Generate general insights about accounts"""
    if not accounts:
        return "No accounts found"
    
    total_revenue = sum(acc['revenue'] for acc in accounts)
    avg_revenue = total_revenue / len(accounts)
    top_revenue_account = max(accounts, key=lambda x: x['revenue'])
    
    insights = {
        'total_accounts': len(accounts),
        'total_revenue': total_revenue,
        'average_revenue': avg_revenue,
        'top_revenue_account': top_revenue_account['account_name'],
        'top_revenue_amount': top_revenue_account['revenue']
    }
    
    return insights

@rag_api.route('/api/rag/debug', methods=['GET'])
def debug_kpi_data():
    """Debug endpoint to show KPI data structure"""
    upload_id = request.args.get('upload_id', type=int)
    
    try:
        rag_system.build_knowledge_base(upload_id)
        
        # Count impact levels
        impact_counts = {}
        weight_counts = {}
        frequency_counts = {}
        
        for item in rag_system.kpi_data:
            kpi = item['kpi']
            
            # Count impact levels
            if kpi.impact_level:
                impact_counts[kpi.impact_level] = impact_counts.get(kpi.impact_level, 0) + 1
            
            # Count weights
            if kpi.weight:
                weight_counts[kpi.weight] = weight_counts.get(kpi.weight, 0) + 1
            
            # Count frequencies
            if kpi.measurement_frequency:
                frequency_counts[kpi.measurement_frequency] = frequency_counts.get(kpi.measurement_frequency, 0) + 1
        
        return jsonify({
            'total_kpis': len(rag_system.kpi_data),
            'impact_level_distribution': impact_counts,
            'weight_distribution': weight_counts,
            'frequency_distribution': frequency_counts,
            'sample_kpis': [
                {
                    'kpi_id': item['kpi'].kpi_id,
                    'category': item['kpi'].category,
                    'health_score_component': item['kpi'].health_score_component,
                    'impact_level': item['kpi'].impact_level,
                    'weight': item['kpi'].weight,
                    'measurement_frequency': item['kpi'].measurement_frequency
                }
                for item in rag_system.kpi_data[:5]  # First 5 KPIs as sample
            ]
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@rag_api.route('/api/rag/query', methods=['POST'])
def query_kpis():
    """Query KPI data using natural language"""
    data = request.get_json()
    query = data.get('query', '').strip()
    upload_id = data.get('upload_id')
    customer_id = request.headers.get('X-Customer-ID')
    
    if not query:
        return jsonify({'error': 'Query is required'}), 400
    
    try:
        # If customer_id is provided, use all customer data from Data Management
        if customer_id:
            # Build knowledge base from all customer data
            rag_system.build_knowledge_base_from_customer(customer_id)
        else:
            # Fallback to upload_id method
            rag_system.build_knowledge_base(upload_id)
        
        # Debug info
        print(f"Query: {query}")
        print(f"Total KPIs in knowledge base: {len(rag_system.kpi_data)}")
        
        # Perform semantic search
        search_results = rag_system.semantic_search(query, top_k=15)
        
        # Analyze query type
        query_type = rag_system.analyze_query(query)
        
        # Generate insights based on query type
        insights = generate_insights(query_type, search_results, rag_system.kpi_data)
        
        # Debug info
        print(f"Query type: {query_type}")
        print(f"Search results: {len(search_results)}")
        print(f"Insights: {insights}")
        
        return jsonify({
            'query': query,
            'query_type': query_type,
            'results': search_results,
            'insights': insights,
            'total_matches': len(search_results),
            'debug_info': {
                'total_kpis': len(rag_system.kpi_data),
                'query_type': query_type,
                'data_source': 'customer_data' if customer_id else 'upload_data'
            }
        })
        
    except Exception as e:
        print(f"Error in RAG query: {str(e)}")
        return jsonify({'error': str(e)}), 500

@rag_api.route('/api/rag/analyze', methods=['POST'])
def analyze_kpis():
    """Provide comprehensive analysis of KPI data"""
    data = request.get_json()
    upload_id = data.get('upload_id')
    
    try:
        # Build knowledge base
        rag_system.build_knowledge_base(upload_id)
        
        # Generate comprehensive analysis
        analysis = generate_comprehensive_analysis(rag_system.kpi_data)
        
        return jsonify(analysis)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def generate_insights(query_type, search_results, kpi_data):
    """Generate insights based on query type and results"""
    insights = {
        'summary': '',
        'recommendations': [],
        'statistics': {}
    }
    
    if query_type == "weight_analysis":
        weights = [r['kpi']['weight'] for r in search_results if r['kpi']['weight']]
        insights['summary'] = f"Found {len(weights)} KPIs with weight information"
        insights['recommendations'] = [
            "Focus on high-weight KPIs for maximum impact",
            "Consider rebalancing weights for better distribution"
        ]
        
    elif query_type == "impact_analysis":
        impact_levels = [r['kpi']['impact_level'] for r in search_results if r['kpi']['impact_level']]
        insights['summary'] = f"Found {len(impact_levels)} KPIs with impact level information"
        insights['recommendations'] = [
            "Prioritize high-impact KPIs",
            "Monitor critical impact areas closely"
        ]
        
    elif query_type == "health_score_analysis":
        # Get health scores analysis
        customer_id = request.headers.get('X-Customer-ID')
        if customer_id:
            try:
                health_analysis = analyze_health_scores(int(customer_id))
                insights['summary'] = f"Corporate overall health score: {health_analysis['corporate_scores']['overall']:.1f}%"
                insights['recommendations'] = [
                    f"Best performing account: {health_analysis['best_performing_accounts'][0]['account_name']} ({health_analysis['best_performing_accounts'][0]['health_scores']['overall']:.1f}%)",
                    f"Total accounts analyzed: {health_analysis['total_accounts']}",
                    f"Total revenue: ${health_analysis['total_revenue']:,.0f}"
                ]
                insights['statistics'] = {
                    'corporate_scores': health_analysis['corporate_scores'],
                    'best_accounts': health_analysis['best_performing_accounts'][:3],
                    'total_accounts': health_analysis['total_accounts']
                }
            except Exception as e:
                insights['summary'] = "Health score analysis not available"
                insights['recommendations'] = ["Ensure all accounts have KPI data loaded"]
        else:
            insights['summary'] = "Health score analysis requires customer context"
            insights['recommendations'] = ["Use Data Management tab to view health scores"]
            
    elif query_type == "frequency_analysis":
        frequencies = [r['kpi']['measurement_frequency'] for r in search_results if r['kpi']['measurement_frequency']]
        insights['summary'] = f"Found {len(frequencies)} KPIs with measurement frequency information"
        insights['recommendations'] = [
            "Ensure appropriate measurement frequency for each KPI",
            "Consider automation for high-frequency measurements"
        ]
        
    else:
        insights['summary'] = f"Found {len(search_results)} relevant KPIs"
        insights['recommendations'] = [
            "Review and update KPI definitions regularly",
            "Ensure data quality and accuracy"
        ]
    
    return insights

def generate_comprehensive_analysis(kpi_data):
    """Generate comprehensive analysis of all KPI data"""
    categories = {}
    impact_levels = {}
    frequencies = {}
    
    for item in kpi_data:
        kpi = item['kpi']
        
        # Category analysis
        cat = kpi.category
        categories[cat] = categories.get(cat, 0) + 1
        
        # Impact level analysis
        if kpi.impact_level:
            impact_levels[kpi.impact_level] = impact_levels.get(kpi.impact_level, 0) + 1
        
        # Frequency analysis
        if kpi.measurement_frequency:
            frequencies[kpi.measurement_frequency] = frequencies.get(kpi.measurement_frequency, 0) + 1
    
    return {
        'total_kpis': len(kpi_data),
        'category_distribution': categories,
        'impact_level_distribution': impact_levels,
        'frequency_distribution': frequencies,
        'recommendations': [
            f"Focus on {max(categories, key=categories.get) if categories else 'all'} categories",
            "Ensure balanced distribution across impact levels",
            "Optimize measurement frequencies for efficiency"
        ]
    } 

@rag_api.route('/api/rag/health-scores', methods=['POST'])
def get_health_scores():
    """Get health scores analysis for all accounts"""
    customer_id = request.headers.get('X-Customer-ID')
    
    if not customer_id:
        return jsonify({'error': 'Missing X-Customer-ID header'}), 400
    
    customer_id = int(customer_id)
    
    try:
        analysis = analyze_health_scores(customer_id)
        return jsonify(analysis)
    except Exception as e:
        return jsonify({'error': f'Failed to analyze health scores: {str(e)}'}), 500 