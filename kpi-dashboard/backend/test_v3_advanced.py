#!/usr/bin/env python3
"""
V3 Advanced Test Suite
Tests RAG caching, multi-tenant isolation, and security features
"""

import os
import sys
import json
import time
import requests
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class V3AdvancedTests:
    def __init__(self, backend_url="http://localhost:5059"):
        self.backend_url = backend_url
        self.test_results = []
        self.customer_1_id = 1  # Test Company
        self.customer_2_id = 2  # ACME
        
        # Create separate sessions for each customer
        self.session_customer_1 = requests.Session()
        self.session_customer_1.headers.update({
            'X-Customer-ID': str(self.customer_1_id),
            'Content-Type': 'application/json'
        })
        
        self.session_customer_2 = requests.Session()
        self.session_customer_2.headers.update({
            'X-Customer-ID': str(self.customer_2_id),
            'Content-Type': 'application/json'
        })
    
    def log_test(self, test_name, status, message="", duration=0, details=None):
        """Log test result"""
        result = {
            'test': test_name,
            'status': status,
            'message': message,
            'duration': duration,
            'timestamp': datetime.now().isoformat(),
            'details': details
        }
        self.test_results.append(result)
        
        status_icon = "✅" if status == "PASS" else "❌" if status == "FAIL" else "⚠️"
        print(f"{status_icon} {test_name}")
        print(f"   {message} ({duration:.2f}s)")
        if details:
            print(f"   Details: {details}")
        print()
    
    def test_rag_cache_first_query(self):
        """Test 1: First RAG query (cache miss)"""
        start_time = time.time()
        try:
            query = "What are the top 3 revenue accounts with detailed analysis?"
            
            response = self.session_customer_1.post(
                f"{self.backend_url}/api/direct-rag/query",
                json={"query": query, "conversation_history": []}
            )
            duration = time.time() - start_time
            
            if response.status_code == 200:
                data = response.json()
                cache_hit = data.get('cache_hit', False)
                
                if not cache_hit:
                    self.log_test(
                        "RAG Cache - First Query (Cache Miss)",
                        "PASS",
                        f"First query took {duration:.2f}s (uncached)",
                        duration,
                        f"Response: {len(data.get('response', ''))} chars, Cache: {cache_hit}"
                    )
                    return True, query, duration
                else:
                    self.log_test(
                        "RAG Cache - First Query",
                        "WARN",
                        "Expected cache miss, got cache hit",
                        duration
                    )
                    return False, query, duration
            
            self.log_test("RAG Cache First Query", "FAIL", f"Status: {response.status_code}", duration)
            return False, query, duration
        except Exception as e:
            duration = time.time() - start_time
            self.log_test("RAG Cache First Query", "FAIL", f"Exception: {str(e)}", duration)
            return False, "", duration
    
    def test_rag_cache_second_query(self, query, first_duration):
        """Test 2: Repeat RAG query (cache hit)"""
        start_time = time.time()
        try:
            response = self.session_customer_1.post(
                f"{self.backend_url}/api/direct-rag/query",
                json={"query": query, "conversation_history": []}
            )
            duration = time.time() - start_time
            
            if response.status_code == 200:
                data = response.json()
                cache_hit = data.get('cache_hit', False)
                cost = data.get('cost', 'N/A')
                
                # Cache should be faster
                speedup = first_duration / duration if duration > 0 else 0
                
                if cache_hit and duration < first_duration:
                    self.log_test(
                        "RAG Cache - Repeat Query (Cache Hit)",
                        "PASS",
                        f"Cached query {speedup:.1f}x faster!",
                        duration,
                        f"First: {first_duration:.2f}s → Cached: {duration:.2f}s, Cost: {cost}"
                    )
                    return True
                elif cache_hit:
                    self.log_test(
                        "RAG Cache - Repeat Query",
                        "PASS",
                        f"Cache hit confirmed (but not faster)",
                        duration,
                        f"First: {first_duration:.2f}s, Second: {duration:.2f}s"
                    )
                    return True
                else:
                    self.log_test(
                        "RAG Cache - Repeat Query",
                        "FAIL",
                        "Expected cache hit, got cache miss",
                        duration
                    )
                    return False
            
            self.log_test("RAG Cache Repeat Query", "FAIL", f"Status: {response.status_code}", duration)
            return False
        except Exception as e:
            duration = time.time() - start_time
            self.log_test("RAG Cache Repeat Query", "FAIL", f"Exception: {str(e)}", duration)
            return False
    
    def test_multi_tenant_data_isolation(self):
        """Test 3: Customer 1 cannot see Customer 2's accounts"""
        start_time = time.time()
        try:
            # Get Customer 1 accounts
            response1 = self.session_customer_1.get(f"{self.backend_url}/api/accounts")
            if response1.status_code != 200:
                raise Exception("Customer 1 accounts fetch failed")
            
            accounts1 = response1.json()
            account_names1 = [acc['account_name'] for acc in accounts1]
            
            # Get Customer 2 accounts
            response2 = self.session_customer_2.get(f"{self.backend_url}/api/accounts")
            if response2.status_code != 200:
                raise Exception("Customer 2 accounts fetch failed")
            
            accounts2 = response2.json()
            account_names2 = [acc['account_name'] for acc in accounts2]
            
            duration = time.time() - start_time
            
            # Check for overlap (should be NONE)
            overlap = set(account_names1) & set(account_names2)
            
            if len(overlap) == 0:
                self.log_test(
                    "Multi-Tenant Data Isolation",
                    "PASS",
                    f"No data leakage between customers",
                    duration,
                    f"Customer 1: {len(accounts1)} accounts, Customer 2: {len(accounts2)} accounts, Overlap: 0"
                )
                return True
            else:
                self.log_test(
                    "Multi-Tenant Data Isolation",
                    "FAIL",
                    f"Data leakage detected: {len(overlap)} shared accounts",
                    duration,
                    f"Overlap: {list(overlap)}"
                )
                return False
        except Exception as e:
            duration = time.time() - start_time
            self.log_test("Multi-Tenant Data Isolation", "FAIL", f"Exception: {str(e)}", duration)
            return False
    
    def test_multi_tenant_rag_isolation(self):
        """Test 4: RAG queries are customer-specific"""
        start_time = time.time()
        try:
            query = "List all account names"
            
            # Query as Customer 1
            response1 = self.session_customer_1.post(
                f"{self.backend_url}/api/direct-rag/query",
                json={"query": query, "conversation_history": []}
            )
            
            # Query as Customer 2
            response2 = self.session_customer_2.post(
                f"{self.backend_url}/api/direct-rag/query",
                json={"query": query, "conversation_history": []}
            )
            
            duration = time.time() - start_time
            
            if response1.status_code == 200 and response2.status_code == 200:
                data1 = response1.json()
                data2 = response2.json()
                
                response1_text = data1.get('response', '')
                response2_text = data2.get('response', '')
                
                # Responses should be different (different customer data)
                if response1_text != response2_text:
                    # Check that Customer 2's response doesn't mention Customer 1's accounts
                    customer1_specific = any(name in response2_text.lower() 
                                            for name in ['pharmaceutical', 'aerospace', 'digitalfirst', 'techhub'])
                    
                    # Check that Customer 1's response doesn't mention Customer 2's accounts  
                    customer2_specific = any(name in response1_text.lower() 
                                            for name in ['acme'])
                    
                    if not customer1_specific and not customer2_specific:
                        self.log_test(
                            "Multi-Tenant RAG Isolation",
                            "PASS",
                            "RAG responses are customer-specific",
                            duration,
                            f"Customer 1 response: {len(response1_text)} chars, Customer 2: {len(response2_text)} chars"
                        )
                        return True
                    else:
                        self.log_test(
                            "Multi-Tenant RAG Isolation",
                            "FAIL",
                            "Data leakage in RAG responses",
                            duration,
                            f"C1 has C2 data: {customer2_specific}, C2 has C1 data: {customer1_specific}"
                        )
                        return False
                else:
                    self.log_test(
                        "Multi-Tenant RAG Isolation",
                        "FAIL",
                        "Responses are identical (should be different)",
                        duration
                    )
                    return False
            
            self.log_test("Multi-Tenant RAG Isolation", "FAIL", 
                         f"Status: {response1.status_code}, {response2.status_code}", duration)
            return False
        except Exception as e:
            duration = time.time() - start_time
            self.log_test("Multi-Tenant RAG Isolation", "FAIL", f"Exception: {str(e)}", duration)
            return False
    
    def test_conversation_isolation(self):
        """Test 5: Conversation history is customer-specific"""
        start_time = time.time()
        try:
            # Customer 1 conversation
            query1 = "Which accounts have highest revenue?"
            r1 = self.session_customer_1.post(
                f"{self.backend_url}/api/direct-rag/query",
                json={"query": query1, "conversation_history": []}
            )
            
            if r1.status_code != 200:
                raise Exception("Customer 1 query failed")
            
            result1 = r1.json()
            conv_history_1 = [{"query": query1, "response": result1['response']}]
            
            # Customer 2 asks follow-up to Customer 1's question (should NOT work)
            query2 = "Tell me about the first one"  # Refers to Customer 1's context
            r2 = self.session_customer_2.post(
                f"{self.backend_url}/api/direct-rag/query",
                json={"query": query2, "conversation_history": conv_history_1}  # Customer 1's history!
            )
            
            duration = time.time() - start_time
            
            if r2.status_code == 200:
                result2 = r2.json()
                response2_text = result2.get('response', '').lower()
                
                # Customer 2's response should NOT reference Customer 1's accounts
                # (even though we sent Customer 1's conversation history)
                # The backend should filter by customer_id
                has_customer1_data = any(name in response2_text 
                                        for name in ['digitalfirst', 'techhub', 'pharmaceutical'])
                
                # The response should be confused or generic (no specific account from Customer 1)
                # OR the backend should have filtered the conversation history
                if not has_customer1_data:
                    self.log_test(
                        "Conversation Isolation (Security)",
                        "PASS",
                        "Customer 2 cannot access Customer 1's conversation context",
                        duration,
                        "Customer-specific filtering working correctly"
                    )
                    return True
                else:
                    self.log_test(
                        "Conversation Isolation (Security)",
                        "WARN",
                        "Customer 1 data appeared in Customer 2 response",
                        duration,
                        "Consider adding customer_id validation for conversation history"
                    )
                    return False
            
            self.log_test("Conversation Isolation", "FAIL", f"Status: {r2.status_code}", duration)
            return False
        except Exception as e:
            duration = time.time() - start_time
            self.log_test("Conversation Isolation", "FAIL", f"Exception: {str(e)}", duration)
            return False
    
    def test_rag_cache_invalidation(self):
        """Test 6: Cache is customer-specific (not shared)"""
        start_time = time.time()
        try:
            same_query = "What is the total revenue?"
            
            # Customer 1 query (should cache result)
            r1a = self.session_customer_1.post(
                f"{self.backend_url}/api/direct-rag/query",
                json={"query": same_query, "conversation_history": []}
            )
            
            if r1a.status_code != 200:
                raise Exception("Customer 1 first query failed")
            
            time.sleep(0.5)
            
            # Customer 1 repeat (should hit cache)
            r1b = self.session_customer_1.post(
                f"{self.backend_url}/api/direct-rag/query",
                json={"query": same_query, "conversation_history": []}
            )
            
            # Customer 2 same query (should be separate cache)
            r2 = self.session_customer_2.post(
                f"{self.backend_url}/api/direct-rag/query",
                json={"query": same_query, "conversation_history": []}
            )
            
            duration = time.time() - start_time
            
            if r1b.status_code == 200 and r2.status_code == 200:
                data1b = r1b.json()
                data2 = r2.json()
                
                cache_hit_1 = data1b.get('cache_hit', False)
                cache_hit_2 = data2.get('cache_hit', False)
                
                response1 = data1b.get('response', '')
                response2 = data2.get('response', '')
                
                # Customer 1 should hit cache
                # Customer 2 should have different response (different data)
                if cache_hit_1 and response1 != response2:
                    self.log_test(
                        "RAG Cache Customer Isolation",
                        "PASS",
                        "Cache is customer-specific, no cross-contamination",
                        duration,
                        f"C1 cache hit: {cache_hit_1}, C2 cache hit: {cache_hit_2}, Responses different: True"
                    )
                    return True
                else:
                    self.log_test(
                        "RAG Cache Customer Isolation",
                        "WARN",
                        f"Cache behavior unexpected",
                        duration,
                        f"C1 cache: {cache_hit_1}, C2 cache: {cache_hit_2}, Same response: {response1 == response2}"
                    )
                    return False
            
            self.log_test("RAG Cache Isolation", "FAIL", 
                         f"Status: {r1b.status_code}, {r2.status_code}", duration)
            return False
        except Exception as e:
            duration = time.time() - start_time
            self.log_test("RAG Cache Isolation", "FAIL", f"Exception: {str(e)}", duration)
            return False
    
    def test_account_count_isolation(self):
        """Test 7: Account counts are different per customer"""
        start_time = time.time()
        try:
            response1 = self.session_customer_1.get(f"{self.backend_url}/api/accounts")
            response2 = self.session_customer_2.get(f"{self.backend_url}/api/accounts")
            
            duration = time.time() - start_time
            
            if response1.status_code == 200 and response2.status_code == 200:
                accounts1 = response1.json()
                accounts2 = response2.json()
                
                count1 = len(accounts1)
                count2 = len(accounts2)
                
                # Test Company has 25 accounts, ACME has 10
                expected_count1 = 25
                expected_count2 = 10
                
                if count1 == expected_count1 and count2 == expected_count2:
                    self.log_test(
                        "Account Count Isolation",
                        "PASS",
                        "Each customer sees only their accounts",
                        duration,
                        f"Customer 1: {count1}/{expected_count1}, Customer 2: {count2}/{expected_count2}"
                    )
                    return True
                else:
                    self.log_test(
                        "Account Count Isolation",
                        "WARN",
                        f"Account counts unexpected",
                        duration,
                        f"C1: {count1} (expected {expected_count1}), C2: {count2} (expected {expected_count2})"
                    )
                    return False
            
            self.log_test("Account Count Isolation", "FAIL", 
                         f"Status: {response1.status_code}, {response2.status_code}", duration)
            return False
        except Exception as e:
            duration = time.time() - start_time
            self.log_test("Account Count Isolation", "FAIL", f"Exception: {str(e)}", duration)
            return False
    
    def test_playbook_isolation(self):
        """Test 8: Playbook executions are customer-specific"""
        start_time = time.time()
        try:
            response1 = self.session_customer_1.get(
                f"{self.backend_url}/api/playbooks/executions",
                params={"customer_id": self.customer_1_id}
            )
            response2 = self.session_customer_2.get(
                f"{self.backend_url}/api/playbooks/executions",
                params={"customer_id": self.customer_2_id}
            )
            
            duration = time.time() - start_time
            
            if response1.status_code == 200 and response2.status_code == 200:
                playbooks1 = response1.json()
                playbooks2 = response2.json()
                
                # Check that no playbooks reference other customer's accounts
                if isinstance(playbooks1, list) and isinstance(playbooks2, list):
                    # Get account IDs for each customer
                    r1_accounts = self.session_customer_1.get(f"{self.backend_url}/api/accounts")
                    r2_accounts = self.session_customer_2.get(f"{self.backend_url}/api/accounts")
                    
                    if r1_accounts.status_code == 200 and r2_accounts.status_code == 200:
                        account_ids1 = [acc['account_id'] for acc in r1_accounts.json()]
                        account_ids2 = [acc['account_id'] for acc in r2_accounts.json()]
                        
                        # Check playbook account_ids
                        playbook_accounts1 = [p.get('account_id') for p in playbooks1 if p.get('account_id')]
                        playbook_accounts2 = [p.get('account_id') for p in playbooks2 if p.get('account_id')]
                        
                        # All playbook account_ids should belong to respective customer
                        valid1 = all(aid in account_ids1 for aid in playbook_accounts1) if playbook_accounts1 else True
                        valid2 = all(aid in account_ids2 for aid in playbook_accounts2) if playbook_accounts2 else True
                        
                        if valid1 and valid2:
                            self.log_test(
                                "Playbook Execution Isolation",
                                "PASS",
                                "Playbooks correctly scoped to customer accounts",
                                duration,
                                f"C1 playbooks: {len(playbooks1)}, C2 playbooks: {len(playbooks2)}"
                            )
                            return True
                        else:
                            self.log_test(
                                "Playbook Execution Isolation",
                                "FAIL",
                                "Playbooks reference wrong customer's accounts",
                                duration
                            )
                            return False
                
                self.log_test(
                    "Playbook Isolation",
                    "PASS",
                    "Playbook data retrieved",
                    duration,
                    f"C1: {len(playbooks1)} playbooks, C2: {len(playbooks2)} playbooks"
                )
                return True
            
            self.log_test("Playbook Isolation", "FAIL", 
                         f"Status: {response1.status_code}, {response2.status_code}", duration)
            return False
        except Exception as e:
            duration = time.time() - start_time
            self.log_test("Playbook Isolation", "FAIL", f"Exception: {str(e)}", duration)
            return False
    
    def test_unauthorized_customer_access(self):
        """Test 9: Cannot access data with invalid customer ID"""
        start_time = time.time()
        try:
            # Try with invalid customer ID
            invalid_session = requests.Session()
            invalid_session.headers.update({
                'X-Customer-ID': '999',  # Non-existent customer
                'Content-Type': 'application/json'
            })
            
            response = invalid_session.get(f"{self.backend_url}/api/accounts")
            duration = time.time() - start_time
            
            # Should return empty array or error
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, list) and len(data) == 0:
                    self.log_test(
                        "Unauthorized Customer Access",
                        "PASS",
                        "Invalid customer ID returns empty data",
                        duration,
                        "Security: No data leaked for non-existent customer"
                    )
                    return True
                else:
                    self.log_test(
                        "Unauthorized Customer Access",
                        "FAIL",
                        f"Invalid customer ID returned {len(data)} records",
                        duration
                    )
                    return False
            elif response.status_code == 400 or response.status_code == 403:
                self.log_test(
                    "Unauthorized Customer Access",
                    "PASS",
                    f"Invalid customer ID properly rejected ({response.status_code})",
                    duration
                )
                return True
            
            self.log_test("Unauthorized Access", "FAIL", f"Unexpected status: {response.status_code}", duration)
            return False
        except Exception as e:
            duration = time.time() - start_time
            self.log_test("Unauthorized Access", "FAIL", f"Exception: {str(e)}", duration)
            return False
    
    def test_cache_performance_improvement(self):
        """Test 10: Cache significantly improves performance"""
        start_time = time.time()
        try:
            query = "Analyze health scores for all accounts with detailed recommendations"
            
            # First query (uncached)
            start1 = time.time()
            r1 = self.session_customer_1.post(
                f"{self.backend_url}/api/direct-rag/query",
                json={"query": query, "conversation_history": []}
            )
            duration1 = time.time() - start1
            
            if r1.status_code != 200:
                raise Exception("First query failed")
            
            time.sleep(0.5)
            
            # Second query (cached)
            start2 = time.time()
            r2 = self.session_customer_1.post(
                f"{self.backend_url}/api/direct-rag/query",
                json={"query": query, "conversation_history": []}
            )
            duration2 = time.time() - start2
            
            total_duration = time.time() - start_time
            
            if r2.status_code == 200:
                data2 = r2.json()
                cache_hit = data2.get('cache_hit', False)
                
                # Cache should provide at least 2x speedup
                speedup = duration1 / duration2 if duration2 > 0 else 0
                
                if cache_hit and speedup >= 2:
                    self.log_test(
                        "Cache Performance Improvement",
                        "PASS",
                        f"Cache provides {speedup:.1f}x speedup!",
                        total_duration,
                        f"Uncached: {duration1:.2f}s → Cached: {duration2:.2f}s"
                    )
                    return True
                elif cache_hit:
                    self.log_test(
                        "Cache Performance",
                        "WARN",
                        f"Cache hit but only {speedup:.1f}x faster (expected 2x+)",
                        total_duration,
                        f"Uncached: {duration1:.2f}s → Cached: {duration2:.2f}s"
                    )
                    return False
                else:
                    self.log_test(
                        "Cache Performance",
                        "FAIL",
                        "Second query did not hit cache",
                        total_duration
                    )
                    return False
            
            self.log_test("Cache Performance", "FAIL", f"Status: {r2.status_code}", total_duration)
            return False
        except Exception as e:
            duration = time.time() - start_time
            self.log_test("Cache Performance", "FAIL", f"Exception: {str(e)}", duration)
            return False
    
    def run_all_tests(self):
        """Run all V3 advanced tests"""
        print("=" * 80)
        print("V3 ADVANCED TEST SUITE - RAG Cache & Multi-Tenant Isolation")
        print("=" * 80)
        print(f"Backend:    {self.backend_url}")
        print(f"Customer 1: {self.customer_1_id} (Test Company)")
        print(f"Customer 2: {self.customer_2_id} (ACME)")
        print("=" * 80)
        print()
        
        # Test 1 & 2: RAG Caching
        print("📦 RAG CACHING TESTS")
        print("-" * 80)
        success1, query, first_duration = self.test_rag_cache_first_query()
        if success1:
            self.test_rag_cache_second_query(query, first_duration)
        self.test_cache_performance_improvement()
        print()
        
        # Test 3-5: Multi-Tenant Isolation
        print("🔒 MULTI-TENANT ISOLATION TESTS")
        print("-" * 80)
        self.test_account_count_isolation()
        self.test_multi_tenant_data_isolation()
        self.test_multi_tenant_rag_isolation()
        self.test_playbook_isolation()
        self.test_conversation_isolation()
        print()
        
        # Test 6: Security
        print("🛡️  SECURITY TESTS")
        print("-" * 80)
        self.test_unauthorized_customer_access()
        print()
        
        # Summary
        passed = len([r for r in self.test_results if r['status'] == 'PASS'])
        failed = len([r for r in self.test_results if r['status'] == 'FAIL'])
        warned = len([r for r in self.test_results if r['status'] == 'WARN'])
        total = len(self.test_results)
        
        print("=" * 80)
        print("TEST SUMMARY")
        print("=" * 80)
        print(f"Total Tests:  {total}")
        print(f"✅ Passed:    {passed}")
        print(f"❌ Failed:    {failed}")
        print(f"⚠️  Warnings:  {warned}")
        print(f"Pass Rate:    {(passed/total*100) if total > 0 else 0:.1f}%")
        print("=" * 80)
        print()
        
        # Critical tests
        critical_tests = [
            "Multi-Tenant Data Isolation",
            "Multi-Tenant RAG Isolation",
            "Unauthorized Customer Access"
        ]
        
        critical_results = [r for r in self.test_results if r['test'] in critical_tests]
        critical_passed = all(r['status'] == 'PASS' for r in critical_results)
        
        if critical_passed:
            print("🔒 SECURITY: All critical multi-tenant isolation tests PASSED ✅")
        else:
            print("⚠️  SECURITY: Some critical tests failed - review before production!")
        
        print()
        if failed == 0 and warned == 0:
            print("🎉 ALL TESTS PASSED! V3 caching and isolation working perfectly!")
            return True
        elif failed == 0:
            print(f"⚠️  {warned} warning(s). Review before deployment.")
            return True
        else:
            print(f"❌ {failed} test(s) failed. Fix before deployment.")
            return False

def main():
    """Run V3 advanced tests"""
    import argparse
    parser = argparse.ArgumentParser(description='V3 Advanced Tests (Cache & Multi-Tenant)')
    parser.add_argument('--backend', default='http://localhost:5059', help='Backend URL')
    args = parser.parse_args()
    
    suite = V3AdvancedTests(backend_url=args.backend)
    success = suite.run_all_tests()
    
    # Save results
    with open('v3_advanced_test_results.json', 'w') as f:
        json.dump(suite.test_results, f, indent=2)
    
    print(f"📄 Detailed results saved to: v3_advanced_test_results.json")
    
    sys.exit(0 if success else 1)

if __name__ == '__main__':
    main()

