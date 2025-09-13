#!/usr/bin/env python3
"""
Test suite for RAG system time series functionality
Ensures revenue time series data is properly included in RAG responses
"""

import pytest
import requests
import json
from datetime import datetime

class TestRAGTimeSeries:
    """Test RAG system time series functionality"""
    
    BASE_URL = "http://3.84.178.121:3000"
    CUSTOMER_ID = 6
    
    def test_rag_time_series_revenue_query(self):
        """Test that RAG system includes time series revenue data in responses"""
        query = "Show me the revenue trends for our accounts over the last 6 months"
        
        response = requests.post(
            f"{self.BASE_URL}/api/direct-rag/query",
            headers={
                "Content-Type": "application/json",
                "X-Customer-ID": str(self.CUSTOMER_ID)
            },
            json={"query": query}
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "response" in data, "Response should contain 'response' field"
        assert "relevant_results" in data, "Response should contain 'relevant_results' field"
        
        # Check that response mentions time series data
        response_text = data["response"].lower()
        time_series_indicators = [
            "march", "april", "may", "june", "july", "august", "september",
            "2025", "growth", "trend", "monthly", "revenue"
        ]
        
        found_indicators = [indicator for indicator in time_series_indicators if indicator in response_text]
        assert len(found_indicators) >= 3, f"Response should mention time series data. Found: {found_indicators}"
        
        print(f"✅ Revenue time series query test passed")
        print(f"   Response mentions: {found_indicators}")
    
    def test_rag_specific_monthly_revenue(self):
        """Test RAG system with specific monthly revenue queries"""
        query = "What was the revenue for June, July and August for our accounts?"
        
        response = requests.post(
            f"{self.BASE_URL}/api/direct-rag/query",
            headers={
                "Content-Type": "application/json",
                "X-Customer-ID": str(self.CUSTOMER_ID)
            },
            json={"query": query}
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        response_text = data["response"]
        
        # Check that response provides specific monthly data
        monthly_indicators = ["june", "july", "august", "$", "revenue", "growth"]
        found_monthly = [indicator for indicator in monthly_indicators if indicator.lower() in response_text.lower()]
        
        assert len(found_monthly) >= 4, f"Response should provide specific monthly revenue data. Found: {found_monthly}"
        
        # Check that response doesn't say "no data available"
        assert "no data available" not in response_text.lower(), "Response should not claim no data available"
        assert "unable to provide" not in response_text.lower(), "Response should provide data"
        
        print(f"✅ Specific monthly revenue query test passed")
        print(f"   Found monthly indicators: {found_monthly}")
    
    def test_rag_revenue_growth_analysis(self):
        """Test RAG system with revenue growth analysis queries"""
        query = "Which accounts had the highest revenue growth in August 2025?"
        
        response = requests.post(
            f"{self.BASE_URL}/api/direct-rag/query",
            headers={
                "Content-Type": "application/json",
                "X-Customer-ID": str(self.CUSTOMER_ID)
            },
            json={"query": query}
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        response_text = data["response"]
        
        # Check that response identifies specific accounts with growth data
        growth_indicators = ["august", "2025", "growth", "%", "account", "highest"]
        found_growth = [indicator for indicator in growth_indicators if indicator.lower() in response_text.lower()]
        
        assert len(found_growth) >= 4, f"Response should identify accounts with growth data. Found: {found_growth}"
        
        # Check that response provides specific percentages
        assert "%" in response_text, "Response should include percentage growth data"
        
        print(f"✅ Revenue growth analysis test passed")
        print(f"   Found growth indicators: {found_growth}")
    
    def test_rag_account_count_accuracy(self):
        """Test that RAG system reports accurate account count"""
        query = "How many accounts do we have?"
        
        response = requests.post(
            f"{self.BASE_URL}/api/direct-rag/query",
            headers={
                "Content-Type": "application/json",
                "X-Customer-ID": str(self.CUSTOMER_ID)
            },
            json={"query": query}
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        response_text = data["response"]
        
        # Check that response mentions 25 accounts
        assert "25" in response_text, f"Response should mention 25 accounts, got: {response_text[:200]}..."
        
        # Check that response doesn't mention limited data
        assert "limited" not in response_text.lower(), "Response should not mention limited data"
        assert "only" not in response_text.lower() or "25" in response_text, "Response should not suggest limited account count"
        
        print(f"✅ Account count accuracy test passed")
        print(f"   Response correctly mentions 25 accounts")
    
    def test_rag_time_series_data_inclusion(self):
        """Test that RAG system includes comprehensive time series data"""
        query = "Show me comprehensive revenue analysis with time series data"
        
        response = requests.post(
            f"{self.BASE_URL}/api/direct-rag/query",
            headers={
                "Content-Type": "application/json",
                "X-Customer-ID": str(self.CUSTOMER_ID)
            },
            json={"query": query}
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        response_text = data["response"]
        
        # Check for comprehensive time series indicators
        comprehensive_indicators = [
            "march", "april", "may", "june", "july", "august", "september",
            "revenue growth", "net revenue retention", "gross revenue retention",
            "expansion revenue", "upsell", "cross-sell"
        ]
        
        found_comprehensive = [indicator for indicator in comprehensive_indicators 
                             if indicator.lower() in response_text.lower()]
        
        assert len(found_comprehensive) >= 6, f"Response should include comprehensive time series data. Found: {found_comprehensive}"
        
        print(f"✅ Comprehensive time series data test passed")
        print(f"   Found comprehensive indicators: {found_comprehensive}")
    
    def test_rag_endpoint_availability(self):
        """Test that RAG endpoint is available and responding"""
        response = requests.post(
            f"{self.BASE_URL}/api/direct-rag/query",
            headers={
                "Content-Type": "application/json",
                "X-Customer-ID": str(self.CUSTOMER_ID)
            },
            json={"query": "test"}
        )
        
        assert response.status_code == 200, f"RAG endpoint should be available. Got {response.status_code}"
        
        data = response.json()
        assert "customer_id" in data, "Response should contain customer_id"
        assert "query" in data, "Response should contain query"
        assert "response" in data, "Response should contain response"
        
        print(f"✅ RAG endpoint availability test passed")
    
    def run_all_tests(self):
        """Run all RAG time series tests"""
        print("🧪 Running RAG Time Series Test Suite...")
        print("=" * 50)
        
        tests = [
            self.test_rag_endpoint_availability,
            self.test_rag_time_series_revenue_query,
            self.test_rag_specific_monthly_revenue,
            self.test_rag_revenue_growth_analysis,
            self.test_rag_account_count_accuracy,
            self.test_rag_time_series_data_inclusion
        ]
        
        passed = 0
        failed = 0
        
        for test in tests:
            try:
                test()
                passed += 1
            except Exception as e:
                print(f"❌ {test.__name__} FAILED: {str(e)}")
                failed += 1
        
        print("=" * 50)
        print(f"📊 Test Results: {passed} passed, {failed} failed")
        
        if failed == 0:
            print("🎉 All RAG time series tests passed! System is working correctly.")
        else:
            print("⚠️  Some tests failed. Please check the RAG system.")
        
        return failed == 0

def main():
    """Main test runner"""
    test_suite = TestRAGTimeSeries()
    success = test_suite.run_all_tests()
    exit(0 if success else 1)

if __name__ == "__main__":
    main()
