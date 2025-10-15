#!/usr/bin/env python3
"""
Query Router: Routes queries to deterministic analytics or RAG based on intent
"""

import re
from typing import Dict, Tuple, List


class QueryRouter:
    """Routes queries to deterministic analytics or RAG based on intent"""
    
    DETERMINISTIC_KEYWORDS = [
        'total', 'sum', 'average', 'mean', 'median', 'count',
        'how many', 'number of', 'min', 'max', 'list all',
        'show all', 'get all', 'standard deviation', 'std dev',
        'what is the', 'calculate', 'give me the'
    ]
    
    RAG_KEYWORDS = [
        'why', 'how can', 'what factors', 'recommend', 'suggest',
        'analyze', 'insights', 'explain', 'patterns', 'trends',
        'compare', 'difference', 'better', 'improve', 'strategy',
        'should focus', 'opportunities', 'understand'
    ]
    
    @staticmethod
    def classify_query(query: str) -> Dict:
        """
        Classify query as 'deterministic' or 'rag'
        
        Args:
            query: User's natural language query
            
        Returns:
            {
                'routing': 'deterministic' | 'rag',
                'confidence': float (0-1),
                'query_type': str,
                'extracted_params': dict,
                'original_query': str
            }
        """
        query_lower = query.lower().strip()
        
        # Calculate scores
        deterministic_score = QueryRouter._calculate_deterministic_score(query_lower)
        rag_score = QueryRouter._calculate_rag_score(query_lower)
        
        # Extract query parameters
        params = QueryRouter._extract_parameters(query_lower)
        
        # Determine routing (handle edge case where both scores are 0)
        total_score = deterministic_score + rag_score
        if total_score == 0:
            # Default to RAG for ambiguous queries
            routing = 'rag'
            confidence = 0.5
            query_type = 'general'
        elif deterministic_score > rag_score:
            routing = 'deterministic'
            confidence = deterministic_score / total_score
            query_type = QueryRouter._get_deterministic_type(query_lower, params)
        else:
            routing = 'rag'
            confidence = rag_score / total_score
            query_type = QueryRouter._get_rag_type(query_lower)
        
        return {
            'routing': routing,
            'confidence': confidence,
            'query_type': query_type,
            'extracted_params': params,
            'original_query': query,
            'scores': {
                'deterministic': deterministic_score,
                'rag': rag_score
            }
        }
    
    @staticmethod
    def _calculate_deterministic_score(query: str) -> float:
        """Calculate deterministic query score based on patterns"""
        score = 0.0
        
        # High confidence patterns for exact numeric questions
        if re.search(r'\b(what is|show me|get|calculate|give me)\b.*\b(total|sum|average|count|number)\b', query):
            score += 5.0
        
        # List/retrieval patterns
        if re.search(r'\b(list|show|get|display)\b.*\b(all|accounts|kpis)\b', query):
            score += 4.0
        
        # Statistical operations
        if re.search(r'\b(average|mean|median|min|max|minimum|maximum|std|deviation)\b', query):
            score += 4.0
        
        # Count operations (very strong indicator)
        if re.search(r'\b(how many|count|number of)\b', query):
            score += 5.0
        
        # Specific IDs (always deterministic)
        if re.search(r'\b(account|kpi).*\bid\b.*\d+', query):
            score += 6.0
        
        # Comparison operators
        if re.search(r'\b(greater than|less than|more than|at least|exactly|equal to)\b|[><=]', query):
            score += 3.0
        
        # Direct value questions
        if re.search(r'\b(what is the|show the|get the)\b.*\b(value|revenue|score|number)\b', query):
            score += 3.0
        
        # Keyword matching
        for keyword in QueryRouter.DETERMINISTIC_KEYWORDS:
            if keyword in query:
                score += 1.5
        
        return score
    
    @staticmethod
    def _calculate_rag_score(query: str) -> float:
        """Calculate RAG query score based on patterns"""
        score = 0.0
        
        # Why/How questions (strong indicator for RAG)
        if re.search(r'\b(why|how can|what factors|what causes|what drives)\b', query):
            score += 6.0
        
        # Recommendation requests
        if re.search(r'\b(recommend|suggest|should|advise|what can|how to improve)\b', query):
            score += 5.0
        
        # Analysis requests
        if re.search(r'\b(analyze|insights|explain|understand|interpret)\b', query):
            score += 5.0
        
        # Comparison with context (not just simple comparison)
        if re.search(r'\bcompare\b.*\b(performance|trends|patterns|behaviors)\b', query):
            score += 4.0
        
        # Pattern/trend questions
        if re.search(r'\b(patterns|trends|common traits|similarities|characteristics)\b', query):
            score += 4.0
        
        # Strategic questions
        if re.search(r'\b(strategy|focus on|prioritize|opportunities|risks)\b', query):
            score += 4.0
        
        # Best/worst with reasoning
        if re.search(r'\b(best|worst|highest|lowest)\b.*\b(why|because|factors|traits)\b', query):
            score += 4.0
        
        # Keyword matching
        for keyword in QueryRouter.RAG_KEYWORDS:
            if keyword in query:
                score += 1.5
        
        return score
    
    @staticmethod
    def _extract_parameters(query: str) -> Dict:
        """Extract parameters from query for use in API calls"""
        params = {}
        
        # Extract numbers
        numbers = re.findall(r'\d+(?:,\d{3})*(?:\.\d+)?', query)
        if numbers:
            params['numbers'] = [float(n.replace(',', '')) for n in numbers]
        
        # Extract account ID
        account_match = re.search(r'account\s*(?:id)?\s*(\d+)', query)
        if account_match:
            params['account_id'] = int(account_match.group(1))
        
        # Extract industries (common ones)
        industries = [
            'healthcare', 'financial services', 'technology', 
            'manufacturing', 'retail', 'education', 'finance',
            'insurance', 'telecommunications', 'media'
        ]
        for industry in industries:
            if industry in query:
                params['industry'] = industry.title()
                break
        
        # Extract regions
        regions = ['north america', 'europe', 'asia', 'south america', 'africa']
        for region in regions:
            if region in query:
                params['region'] = region.title()
                break
        
        # Extract operations
        operations = {
            'sum': ['total', 'sum', 'add up'],
            'avg': ['average', 'mean'],
            'count': ['count', 'how many', 'number of'],
            'min': ['minimum', 'min', 'lowest', 'smallest'],
            'max': ['maximum', 'max', 'highest', 'largest', 'biggest'],
            'median': ['median'],
            'std': ['standard deviation', 'std dev', 'variance']
        }
        for op, keywords in operations.items():
            if any(kw in query for kw in keywords):
                params['operation'] = op
                break
        
        # Extract metric (what to measure)
        metrics = {
            'revenue': ['revenue', 'sales', 'income'],
            'satisfaction': ['satisfaction', 'csat', 'nps', 'sentiment'],
            'engagement': ['engagement', 'usage', 'activity'],
            'health': ['health', 'score']
        }
        for metric, keywords in metrics.items():
            if any(kw in query for kw in keywords):
                params['metric'] = metric
                break
        
        # Extract filters
        if 'active' in query:
            params['status'] = 'active'
        elif 'inactive' in query:
            params['status'] = 'inactive'
        
        # Extract limit/top-k
        limit_match = re.search(r'top\s+(\d+)|first\s+(\d+)|limit\s+(\d+)', query)
        if limit_match:
            params['limit'] = int(limit_match.group(1) or limit_match.group(2) or limit_match.group(3))
        
        return params
    
    @staticmethod
    def _get_deterministic_type(query: str, params: Dict) -> str:
        """Determine specific deterministic query type"""
        if 'count' in params.get('operation', '') or re.search(r'\bhow many\b', query):
            return 'count'
        elif re.search(r'\btotal\b|\bsum\b', query):
            return 'sum'
        elif re.search(r'\baverage\b|\bmean\b', query):
            return 'average'
        elif re.search(r'\bmedian\b', query):
            return 'median'
        elif re.search(r'\bmin\b|\blowest\b|\bsmallest\b', query):
            return 'min'
        elif re.search(r'\bmax\b|\bhighest\b|\blargest\b', query):
            return 'max'
        elif re.search(r'\blist\b|\bshow\b|\bget\b|\bdisplay\b', query):
            return 'list'
        elif 'account_id' in params:
            return 'single_record'
        else:
            return 'aggregation'
    
    @staticmethod
    def _get_rag_type(query: str) -> str:
        """Determine specific RAG query type"""
        if re.search(r'\bwhy\b|\bhow can\b|\bwhat factors\b|\bwhat causes\b', query):
            return 'why_how'
        elif re.search(r'\brecommend\b|\bsuggest\b|\bshould\b|\badvise\b', query):
            return 'recommendation'
        elif re.search(r'\banalyze\b|\binsights\b|\bexplain\b', query):
            return 'analysis'
        elif re.search(r'\bcompare\b', query):
            return 'comparison'
        elif re.search(r'\bpatterns\b|\btrends\b|\btraits\b', query):
            return 'pattern_recognition'
        elif re.search(r'\bstrategy\b|\bfocus\b|\bprioritize\b', query):
            return 'strategic'
        else:
            return 'general'


def test_query_router():
    """Test the query router with sample queries"""
    router = QueryRouter()
    
    test_queries = [
        # Deterministic queries
        "What is the total revenue?",
        "How many accounts do we have?",
        "Show me the average revenue per account",
        "List all accounts in Healthcare",
        "Get the top 5 accounts by revenue",
        "What is the revenue for account ID 4?",
        "Count the number of active accounts",
        "Show me the minimum and maximum revenue",
        
        # RAG queries
        "Why is revenue declining for Healthcare accounts?",
        "What are the common traits of high-performing accounts?",
        "How can we improve customer satisfaction?",
        "Which accounts should we focus on and why?",
        "Analyze the trends in customer engagement",
        "What factors contribute to account health?",
        "Compare performance between Healthcare and Technology industries",
        "Recommend strategies for at-risk accounts",
    ]
    
    print("=" * 80)
    print("QUERY ROUTER TEST RESULTS")
    print("=" * 80)
    
    for query in test_queries:
        result = router.classify_query(query)
        print(f"\n📝 Query: {query}")
        print(f"   🎯 Routing: {result['routing'].upper()}")
        print(f"   📊 Confidence: {result['confidence']:.2%}")
        print(f"   🏷️  Type: {result['query_type']}")
        print(f"   📦 Params: {result['extracted_params']}")
        print(f"   ⚖️  Scores: Det={result['scores']['deterministic']:.1f}, RAG={result['scores']['rag']:.1f}")
    
    print("\n" + "=" * 80)


if __name__ == '__main__':
    test_query_router()

