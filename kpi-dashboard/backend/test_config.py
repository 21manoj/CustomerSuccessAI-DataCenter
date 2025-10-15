#!/usr/bin/env python3
"""
Test Configuration for E2E Test Suite
Centralized configuration for all test scenarios
"""

import os
from dataclasses import dataclass
from typing import List, Dict, Any

@dataclass
class TestConfig:
    """Test configuration class"""
    
    # Service URLs
    backend_url: str = "http://localhost:5059"
    frontend_url: str = "http://localhost:3000"
    
    # Test data
    customer_id: int = 6
    test_timeout: int = 30
    
    # Test scenarios
    rag_queries: List[Dict[str, str]] = None
    api_endpoints: List[str] = None
    performance_thresholds: Dict[str, float] = None
    
    def __post_init__(self):
        """Initialize default values after object creation"""
        if self.rag_queries is None:
            self.rag_queries = [
                {
                    "query": "Which accounts have the highest revenue?",
                    "query_type": "general",
                    "expected_results": 5
                },
                {
                    "query": "Show me customer satisfaction scores",
                    "query_type": "kpi_analysis",
                    "expected_results": 3
                },
                {
                    "query": "What are the top performing accounts?",
                    "query_type": "account_analysis",
                    "expected_results": 5
                },
                {
                    "query": "Show me revenue trends for the last 4 months",
                    "query_type": "temporal_analysis",
                    "expected_results": 3
                },
                {
                    "query": "Which accounts might be at risk?",
                    "query_type": "risk_analysis",
                    "expected_results": 2
                }
            ]
        
        if self.api_endpoints is None:
            self.api_endpoints = [
                "/api/health",
                "/api/accounts",
                "/api/kpi-uploads",
                "/api/health-scores",
                "/api/rag-qdrant/status",
                "/api/corporate/health-summary"
            ]
        
        if self.performance_thresholds is None:
            self.performance_thresholds = {
                "rag_query_response_time": 5.0,  # seconds
                "api_response_time": 2.0,        # seconds
                "knowledge_base_build_time": 30.0,  # seconds
                "health_score_calculation_time": 10.0  # seconds
            }

# Test data validation rules
VALIDATION_RULES = {
    "account": {
        "required_fields": ["account_id", "account_name", "revenue", "industry", "region"],
        "revenue_range": (0, 100000000),  # $0 to $100M
        "min_accounts": 1
    },
    "kpi_upload": {
        "required_fields": ["upload_id", "customer_id", "uploaded_at", "file_name"],
        "min_uploads": 1
    },
    "health_score": {
        "required_fields": ["account_id", "health_score", "category_scores"],
        "score_range": (0, 100),
        "min_accounts": 1
    },
    "rag_response": {
        "required_fields": ["query", "results_count", "relevant_results"],
        "min_results": 1,
        "max_response_time": 5.0
    }
}

# Test categories and their descriptions
TEST_CATEGORIES = {
    "infrastructure": {
        "name": "Infrastructure Tests",
        "description": "Tests Docker containers, service health, and basic connectivity",
        "tests": ["docker_containers", "backend_health", "frontend_health"]
    },
    "data_integrity": {
        "name": "Data Integrity Tests", 
        "description": "Tests database connectivity, data consistency, and validation",
        "tests": ["database_connectivity", "data_consistency", "kpi_data_integrity"]
    },
    "api_functionality": {
        "name": "API Functionality Tests",
        "description": "Tests all API endpoints and their responses",
        "tests": ["api_endpoints", "health_score_calculation", "data_export"]
    },
    "rag_system": {
        "name": "RAG System Tests",
        "description": "Tests the RAG system, knowledge base, and AI responses",
        "tests": ["rag_knowledge_base_build", "rag_query_execution", "temporal_analysis"]
    },
    "performance": {
        "name": "Performance Tests",
        "description": "Tests system performance and response times",
        "tests": ["performance_benchmarks", "load_testing", "memory_usage"]
    },
    "end_to_end": {
        "name": "End-to-End Tests",
        "description": "Tests complete user workflows and system integration",
        "tests": ["complete_workflow", "user_scenarios", "error_handling"]
    }
}

# Error codes and their meanings
ERROR_CODES = {
    "SERVICE_UNAVAILABLE": "Required service is not running or not accessible",
    "DATA_MISSING": "Expected data is missing or incomplete",
    "VALIDATION_FAILED": "Data validation failed against expected schema",
    "PERFORMANCE_DEGRADED": "System performance is below acceptable thresholds",
    "API_ERROR": "API endpoint returned an error status",
    "RAG_ERROR": "RAG system failed to process query or build knowledge base",
    "DATABASE_ERROR": "Database operation failed or returned unexpected results",
    "TIMEOUT_ERROR": "Operation timed out after maximum wait time",
    "CONFIGURATION_ERROR": "Test configuration is invalid or missing",
    "UNEXPECTED_ERROR": "An unexpected error occurred during test execution"
}

# Test result statuses
TEST_STATUS = {
    "PASS": "Test completed successfully",
    "FAIL": "Test failed due to assertion or validation error", 
    "ERROR": "Test failed due to unexpected exception",
    "SKIP": "Test was skipped due to missing prerequisites",
    "TIMEOUT": "Test timed out before completion"
}

def get_test_config() -> TestConfig:
    """Get test configuration with environment variable overrides"""
    config = TestConfig()
    
    # Override with environment variables if present
    config.backend_url = os.getenv("TEST_BACKEND_URL", config.backend_url)
    config.frontend_url = os.getenv("TEST_FRONTEND_URL", config.frontend_url)
    config.customer_id = int(os.getenv("TEST_CUSTOMER_ID", config.customer_id))
    config.test_timeout = int(os.getenv("TEST_TIMEOUT", config.test_timeout))
    
    return config

def validate_test_environment(config: TestConfig) -> List[str]:
    """Validate that the test environment is properly configured"""
    errors = []
    
    # Check if required environment variables are set
    required_env_vars = ["OPENAI_API_KEY"]
    for var in required_env_vars:
        if not os.getenv(var):
            errors.append(f"Missing required environment variable: {var}")
    
    # Check if URLs are valid
    if not config.backend_url.startswith("http"):
        errors.append(f"Invalid backend URL: {config.backend_url}")
    
    if not config.frontend_url.startswith("http"):
        errors.append(f"Invalid frontend URL: {config.frontend_url}")
    
    # Check if customer ID is valid
    if config.customer_id <= 0:
        errors.append(f"Invalid customer ID: {config.customer_id}")
    
    return errors

if __name__ == "__main__":
    """Test the configuration"""
    config = get_test_config()
    print("Test Configuration:")
    print(f"  Backend URL: {config.backend_url}")
    print(f"  Frontend URL: {config.frontend_url}")
    print(f"  Customer ID: {config.customer_id}")
    print(f"  Test Timeout: {config.test_timeout}")
    print(f"  RAG Queries: {len(config.rag_queries)}")
    print(f"  API Endpoints: {len(config.api_endpoints)}")
    
    errors = validate_test_environment(config)
    if errors:
        print("\nConfiguration Errors:")
        for error in errors:
            print(f"  ❌ {error}")
    else:
        print("\n✅ Configuration is valid")
