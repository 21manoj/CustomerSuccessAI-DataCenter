"""
Query Classifier for V3 - Deterministic Query Detection

This module classifies user queries into two categories:
1. Deterministic Queries - Can be answered directly from database (fast, accurate)
2. Analytical Queries - Require RAG + AI for reasoning and recommendations

The classifier helps route queries to the appropriate backend:
- Deterministic → Direct database queries (0.1s response time)
- Analytical → RAG + OpenAI (2-5s response time, deeper insights)
"""

import re
from typing import Dict, List, Optional

class QueryClassifier:
    """Classifies user queries to determine the best execution strategy."""
    
    def __init__(self):
        # Deterministic query patterns (database queries)
        self.deterministic_patterns = {
            'account_list': [
                r'\b(list|show|display|get)\s+(all\s+)?accounts?\b',
                r'\bhow many accounts?\b',
                r'\baccounts?\s+in\s+\w+\s+(industry|region)\b',
                r'\baccounts?\s+with\s+(health|revenue|nps)',
            ],
            'kpi_lookup': [
                r'\bwhat\s+is\s+the\s+(current\s+)?(nps|csat|grr|nrr|churn|health|adoption)',
                r'\b(nps|csat|grr|nrr|churn|health|adoption)\s+(for|of|at)\s+\w+',
                r'\b(show|get|display)\s+(nps|csat|grr|nrr|churn|health|adoption)',
                r'\bcurrent\s+value\s+of\b',
                r'\blatest\s+(nps|csat|grr|nrr|churn|health|adoption)',
            ],
            'playbook_status': [
                r'\b(list|show|display|get)\s+(all\s+)?(running|active|completed)?\s*playbooks?\b',
                r'\bhow many playbooks?\b',
                r'\bplaybooks?\s+(for|on|at)\s+\w+',
                r'\bwhich\s+playbooks?\s+(are|were)\s+(running|executed|completed)',
                r'\bplaybook\s+(status|results|outcomes|reports)\b',
            ],
            'health_status': [
                r'\bhealth\s+(score|status)\s+(for|of)\s+\w+',
                r'\b(show|get|display)\s+health\s+(score|status)',
                r'\baccounts?\s+with\s+health\s+(below|above|over|under)',
                r'\bat-risk\s+accounts?\b',
            ],
            'revenue_lookup': [
                r'\btotal\s+revenue\b',
                r'\brevenue\s+(for|of|from)\s+\w+',
                r'\b(arr|mrr|revenue)\s+for\s+\w+',
                r'\bhighest\s+revenue\s+accounts?\b',
            ],
        }
        
        # Analytical query patterns (RAG + AI)
        self.analytical_patterns = {
            'why_how': [
                r'\bwhy\s+(is|are|do|does)',
                r'\bhow\s+(can|should|do|does)',
                r'\bwhat\s+(should|can|would)\s+(i|we)',
            ],
            'recommendation': [
                r'\brecommend',
                r'\bsuggest',
                r'\badvise',
                r'\bwhat\s+to\s+do',
                r'\bnext\s+steps?\b',
            ],
            'improvement': [
                r'\bimprove',
                r'\bincrease',
                r'\breduce',
                r'\bdecrease',
                r'\boptimize',
                r'\bboost',
            ],
            'analysis': [
                r'\banalyze',
                r'\bcompare',
                r'\bexplain',
                r'\binsights?\b',
                r'\btrends?',
                r'\bpatterns?',
            ],
            'prediction': [
                r'\bpredict',
                r'\bforecast',
                r'\bexpect',
                r'\blikely',
                r'\brisk\s+of\b',
            ],
        }
        
        # Playbook-related keywords that trigger playbook context
        self.playbook_keywords = [
            'playbook', 'voc sprint', 'activation blitz', 'sla stabilizer',
            'renewal safeguard', 'expansion timing', 'improve', 'leverage',
            'execute', 'start', 'run'
        ]
    
    def classify(self, query: str) -> Dict[str, any]:
        """
        Classify a query and return routing information.
        
        Returns:
            {
                'type': 'deterministic' | 'analytical',
                'subtype': specific category,
                'needs_playbook_context': boolean,
                'confidence': 0.0 to 1.0,
                'suggested_endpoint': API endpoint to use
            }
        """
        query_lower = query.lower().strip()
        
        # Check for deterministic patterns first (highest priority)
        for subtype, patterns in self.deterministic_patterns.items():
            for pattern in patterns:
                if re.search(pattern, query_lower, re.IGNORECASE):
                    return {
                        'type': 'deterministic',
                        'subtype': subtype,
                        'needs_playbook_context': self._needs_playbook_context(query_lower),
                        'confidence': 0.9,
                        'suggested_endpoint': self._get_deterministic_endpoint(subtype),
                        'reason': f'Matched pattern: {subtype}'
                    }
        
        # Check for analytical patterns
        for subtype, patterns in self.analytical_patterns.items():
            for pattern in patterns:
                if re.search(pattern, query_lower, re.IGNORECASE):
                    return {
                        'type': 'analytical',
                        'subtype': subtype,
                        'needs_playbook_context': self._needs_playbook_context(query_lower),
                        'confidence': 0.8,
                        'suggested_endpoint': '/api/direct-rag/query',
                        'reason': f'Matched pattern: {subtype}'
                    }
        
        # Default to analytical (RAG)
        return {
            'type': 'analytical',
            'subtype': 'general',
            'needs_playbook_context': self._needs_playbook_context(query_lower),
            'confidence': 0.5,
            'suggested_endpoint': '/api/direct-rag/query',
            'reason': 'Default to RAG for safety'
        }
    
    def _needs_playbook_context(self, query_lower: str) -> bool:
        """Check if query mentions playbooks or improvement."""
        return any(keyword in query_lower for keyword in self.playbook_keywords)
    
    def _get_deterministic_endpoint(self, subtype: str) -> str:
        """Map deterministic query subtypes to API endpoints."""
        endpoint_map = {
            'account_list': '/api/accounts',
            'kpi_lookup': '/api/kpis/customer/all',
            'playbook_status': '/api/playbooks/executions',
            'health_status': '/api/health-trends',
            'revenue_lookup': '/api/accounts',  # Includes revenue data
        }
        return endpoint_map.get(subtype, '/api/direct-rag/query')
    
    def is_deterministic(self, query: str) -> bool:
        """Quick check if query can be answered deterministically."""
        classification = self.classify(query)
        return classification['type'] == 'deterministic'
    
    def needs_playbook_insights(self, query: str) -> bool:
        """Check if query should include playbook insights."""
        classification = self.classify(query)
        return classification['needs_playbook_context']


def classify_query(query: str) -> Dict[str, any]:
    """Convenience function for quick classification."""
    classifier = QueryClassifier()
    return classifier.classify(query)


# Example usage and testing
if __name__ == '__main__':
    classifier = QueryClassifier()
    
    test_queries = [
        # Deterministic (should use database)
        "List all accounts",
        "Show me accounts in Technology industry",
        "What is the current NPS for TechCorp?",
        "Which playbooks are running?",
        "Show me health score for all accounts",
        "How many accounts do we have?",
        
        # Analytical (should use RAG + AI)
        "Why is TechCorp's NPS declining?",
        "How can I improve customer satisfaction?",
        "What should I do about low adoption?",
        "Which playbooks should I run for TechCorp?",
        "Analyze trends for Financial Services accounts",
        "What's the risk of churn for DataCo?",
    ]
    
    print("=" * 80)
    print("QUERY CLASSIFICATION TESTS")
    print("=" * 80)
    
    for query in test_queries:
        result = classifier.classify(query)
        print(f"\nQuery: {query}")
        print(f"Type: {result['type'].upper()}")
        print(f"Subtype: {result['subtype']}")
        print(f"Endpoint: {result['suggested_endpoint']}")
        print(f"Playbook Context: {result['needs_playbook_context']}")
        print(f"Confidence: {result['confidence']:.1%}")
        print(f"Reason: {result['reason']}")
        print("-" * 80)

