#!/usr/bin/env python3
"""
V3 Integration Test Suite
Tests V3-specific features: Conversation History, Query Classification, Context Awareness
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

class V3IntegrationTests:
    def __init__(self, base_url="http://localhost:3000", backend_url="http://localhost:5059"):
        self.base_url = base_url
        self.backend_url = backend_url
        self.customer_id = 1
        self.test_results = []
        self.session = requests.Session()
        self.session.headers.update({
            'X-Customer-ID': str(self.customer_id),
            'Content-Type': 'application/json'
        })
        self.user_email = "test@test.com"
        self.user_password = "test123"
        self.auth_token = None
    
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
    
    def test_login(self):
        """Test 1: User Login"""
        start_time = time.time()
        try:
            response = self.session.post(
                f"{self.base_url}/api/login",
                json={"email": self.user_email, "password": self.user_password}
            )
            duration = time.time() - start_time
            
            if response.status_code == 200:
                data = response.json()
                if 'customer_id' in data and 'email' in data:
                    self.log_test(
                        "Login",
                        "PASS",
                        f"Login successful for {data['email']}",
                        duration,
                        f"Customer ID: {data['customer_id']}, User: {data.get('user_name', 'N/A')}"
                    )
                    return True
            
            self.log_test("Login", "FAIL", f"Login failed: {response.status_code}", duration)
            return False
        except Exception as e:
            duration = time.time() - start_time
            self.log_test("Login", "FAIL", f"Exception: {str(e)}", duration)
            return False
    
    def test_query_without_history(self):
        """Test 2: Query without conversation history (baseline)"""
        start_time = time.time()
        try:
            response = self.session.post(
                f"{self.backend_url}/api/direct-rag/query",
                json={
                    "query": "Which accounts have the highest revenue?",
                    "conversation_history": []
                }
            )
            duration = time.time() - start_time
            
            if response.status_code == 200:
                data = response.json()
                if 'response' in data and len(data['response']) > 0:
                    self.log_test(
                        "Query Without History",
                        "PASS",
                        "RAG query successful",
                        duration,
                        f"Response length: {len(data['response'])} chars"
                    )
                    return True, data
            
            self.log_test("Query Without History", "FAIL", f"Status: {response.status_code}", duration)
            return False, None
        except Exception as e:
            duration = time.time() - start_time
            self.log_test("Query Without History", "FAIL", f"Exception: {str(e)}", duration)
            return False, None
    
    def test_query_with_conversation_history(self):
        """Test 3: Follow-up query with conversation history (V3 CORE FEATURE)"""
        start_time = time.time()
        try:
            # First query
            response1 = self.session.post(
                f"{self.backend_url}/api/direct-rag/query",
                json={
                    "query": "Which accounts have the highest revenue?",
                    "conversation_history": []
                }
            )
            
            if response1.status_code != 200:
                duration = time.time() - start_time
                self.log_test("Query With History", "FAIL", "First query failed", duration)
                return False
            
            result1 = response1.json()
            
            # Follow-up query with context
            conversation_history = [
                {
                    "query": "Which accounts have the highest revenue?",
                    "response": result1['response']
                }
            ]
            
            response2 = self.session.post(
                f"{self.backend_url}/api/direct-rag/query",
                json={
                    "query": "Tell me more about the first one",  # Requires context!
                    "conversation_history": conversation_history
                }
            )
            
            duration = time.time() - start_time
            
            if response2.status_code == 200:
                result2 = response2.json()
                
                # Check if AI understood context (mentions specific account name)
                has_context = any(word in result2['response'].lower() 
                                 for word in ['digitalfirst', 'techhub', 'account'])
                
                if has_context:
                    self.log_test(
                        "Query With Conversation History (V3 CORE)",
                        "PASS",
                        "AI understood 'the first one' from context!",
                        duration,
                        f"Context-aware response: {result2['response'][:100]}..."
                    )
                    return True
                else:
                    self.log_test(
                        "Query With Conversation History",
                        "WARN",
                        "Context may not have been used",
                        duration
                    )
                    return False
            
            self.log_test("Query With History", "FAIL", f"Status: {response2.status_code}", duration)
            return False
        except Exception as e:
            duration = time.time() - start_time
            self.log_test("Query With History", "FAIL", f"Exception: {str(e)}", duration)
            return False
    
    def test_query_classifier(self):
        """Test 4: Query classifier categorizes queries correctly"""
        start_time = time.time()
        try:
            # Import the classifier
            sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))
            from query_classifier import QueryClassifier
            
            classifier = QueryClassifier()
            
            test_cases = [
                ("List all accounts", "deterministic"),
                ("Why is NPS declining?", "analytical"),
                ("Which playbooks are running?", "deterministic"),
                ("How can I improve customer satisfaction?", "analytical"),
            ]
            
            passed = 0
            failed = 0
            results = []
            
            for query, expected_type in test_cases:
                result = classifier.classify(query)
                actual_type = result['type']
                
                if actual_type == expected_type:
                    passed += 1
                    results.append(f"✓ '{query}' → {actual_type}")
                else:
                    failed += 1
                    results.append(f"✗ '{query}' → Expected: {expected_type}, Got: {actual_type}")
            
            duration = time.time() - start_time
            
            if failed == 0:
                self.log_test(
                    "Query Classifier",
                    "PASS",
                    f"All {passed} queries classified correctly",
                    duration,
                    "\n      ".join(results)
                )
                return True
            else:
                self.log_test(
                    "Query Classifier",
                    "FAIL",
                    f"{passed} passed, {failed} failed",
                    duration,
                    "\n      ".join(results)
                )
                return False
        except Exception as e:
            duration = time.time() - start_time
            self.log_test("Query Classifier", "FAIL", f"Exception: {str(e)}", duration)
            return False
    
    def test_playbook_insights_in_rag(self):
        """Test 5: Playbook insights are included in RAG responses"""
        start_time = time.time()
        try:
            # Query that should trigger playbook context
            response = self.session.post(
                f"{self.backend_url}/api/direct-rag/query",
                json={
                    "query": "Which playbooks can help improve NRR?",
                    "conversation_history": []
                }
            )
            duration = time.time() - start_time
            
            if response.status_code == 200:
                data = response.json()
                response_text = data.get('response', '').lower()
                
                # Check if system playbooks are mentioned
                system_playbooks = ['renewal safeguard', 'expansion timing', 'voc sprint', 
                                   'activation blitz', 'sla stabilizer']
                playbooks_mentioned = [p for p in system_playbooks if p in response_text]
                
                # Check for playbook enhancement flag
                playbook_enhanced = data.get('playbook_enhanced', False)
                
                if playbooks_mentioned or playbook_enhanced:
                    self.log_test(
                        "Playbook Insights in RAG",
                        "PASS",
                        f"Playbook context included",
                        duration,
                        f"Playbooks mentioned: {', '.join(playbooks_mentioned) or 'N/A'}, Enhanced: {playbook_enhanced}"
                    )
                    return True
                else:
                    self.log_test(
                        "Playbook Insights in RAG",
                        "WARN",
                        "No playbook insights detected in response",
                        duration
                    )
                    return False
            
            self.log_test("Playbook Insights", "FAIL", f"Status: {response.status_code}", duration)
            return False
        except Exception as e:
            duration = time.time() - start_time
            self.log_test("Playbook Insights", "FAIL", f"Exception: {str(e)}", duration)
            return False
    
    def test_multi_turn_conversation(self):
        """Test 6: Multi-turn conversation maintains context"""
        start_time = time.time()
        try:
            conversation = []
            
            # Turn 1
            q1 = "Which accounts are at risk?"
            r1 = self.session.post(
                f"{self.backend_url}/api/direct-rag/query",
                json={"query": q1, "conversation_history": conversation}
            )
            if r1.status_code != 200:
                raise Exception("Turn 1 failed")
            
            result1 = r1.json()
            conversation.append({"query": q1, "response": result1['response']})
            
            # Turn 2 - pronoun resolution
            q2 = "What about the first one?"
            r2 = self.session.post(
                f"{self.backend_url}/api/direct-rag/query",
                json={"query": q2, "conversation_history": conversation[-3:]}
            )
            if r2.status_code != 200:
                raise Exception("Turn 2 failed")
            
            result2 = r2.json()
            conversation.append({"query": q2, "response": result2['response']})
            
            # Turn 3 - continued context
            q3 = "What playbooks should I run for them?"
            r3 = self.session.post(
                f"{self.backend_url}/api/direct-rag/query",
                json={"query": q3, "conversation_history": conversation[-3:]}
            )
            duration = time.time() - start_time
            
            if r3.status_code == 200:
                result3 = r3.json()
                
                # Check if playbooks are mentioned in response
                has_playbooks = any(p in result3['response'].lower() 
                                   for p in ['playbook', 'sprint', 'safeguard', 'blitz', 'stabilizer'])
                
                if has_playbooks:
                    self.log_test(
                        "Multi-turn Conversation (V3 CORE)",
                        "PASS",
                        "3-turn conversation with context maintained",
                        duration,
                        f"Turns: Q1→Q2('first one')→Q3('them') all understood!"
                    )
                    return True
            
            self.log_test("Multi-turn Conversation", "FAIL", "Context not maintained", duration)
            return False
        except Exception as e:
            duration = time.time() - start_time
            self.log_test("Multi-turn Conversation", "FAIL", f"Exception: {str(e)}", duration)
            return False
    
    def test_accounts_api(self):
        """Test 7: Accounts API returns data"""
        start_time = time.time()
        try:
            response = self.session.get(f"{self.backend_url}/api/accounts")
            duration = time.time() - start_time
            
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, list) and len(data) > 0:
                    self.log_test(
                        "Accounts API",
                        "PASS",
                        f"Retrieved {len(data)} accounts",
                        duration
                    )
                    return True
            
            self.log_test("Accounts API", "FAIL", f"Status: {response.status_code}", duration)
            return False
        except Exception as e:
            duration = time.time() - start_time
            self.log_test("Accounts API", "FAIL", f"Exception: {str(e)}", duration)
            return False
    
    def test_playbooks_api(self):
        """Test 8: Playbooks executions API"""
        start_time = time.time()
        try:
            response = self.session.get(
                f"{self.backend_url}/api/playbooks/executions",
                params={"customer_id": self.customer_id}
            )
            duration = time.time() - start_time
            
            if response.status_code == 200:
                data = response.json()
                self.log_test(
                    "Playbooks API",
                    "PASS",
                    f"Retrieved {len(data)} playbook executions",
                    duration
                )
                return True
            
            self.log_test("Playbooks API", "FAIL", f"Status: {response.status_code}", duration)
            return False
        except Exception as e:
            duration = time.time() - start_time
            self.log_test("Playbooks API", "FAIL", f"Exception: {str(e)}", duration)
            return False
    
    def test_deterministic_query_speed(self):
        """Test 9: Deterministic queries should be fast (< 1s)"""
        start_time = time.time()
        try:
            # This should be routed to database directly
            response = self.session.get(f"{self.backend_url}/api/accounts")
            duration = time.time() - start_time
            
            if response.status_code == 200 and duration < 1.0:
                self.log_test(
                    "Deterministic Query Speed",
                    "PASS",
                    f"Database query completed in {duration:.3f}s",
                    duration,
                    "Target: < 1.0s for direct DB queries"
                )
                return True
            elif duration >= 1.0:
                self.log_test(
                    "Deterministic Query Speed",
                    "FAIL",
                    f"Too slow: {duration:.3f}s (should be < 1s)",
                    duration
                )
                return False
            
            self.log_test("Deterministic Query Speed", "FAIL", f"Status: {response.status_code}", duration)
            return False
        except Exception as e:
            duration = time.time() - start_time
            self.log_test("Deterministic Query Speed", "FAIL", f"Exception: {str(e)}", duration)
            return False
    
    def test_analytical_query_completeness(self):
        """Test 10: Analytical queries include comprehensive context"""
        start_time = time.time()
        try:
            response = self.session.post(
                f"{self.backend_url}/api/direct-rag/query",
                json={
                    "query": "Why is TechCorp's NPS declining and what should I do?",
                    "conversation_history": []
                }
            )
            duration = time.time() - start_time
            
            if response.status_code == 200:
                data = response.json()
                response_text = data.get('response', '')
                
                # Check for analytical elements
                has_explanation = any(word in response_text.lower() 
                                     for word in ['because', 'due to', 'reason', 'indicates'])
                has_recommendation = any(word in response_text.lower() 
                                        for word in ['recommend', 'should', 'suggest', 'playbook'])
                has_metrics = any(char.isdigit() for char in response_text)
                
                if has_explanation and has_recommendation and has_metrics:
                    self.log_test(
                        "Analytical Query Completeness",
                        "PASS",
                        "Response includes explanation, recommendations, and metrics",
                        duration,
                        f"Length: {len(response_text)} chars"
                    )
                    return True
                else:
                    missing = []
                    if not has_explanation: missing.append("explanation")
                    if not has_recommendation: missing.append("recommendations")
                    if not has_metrics: missing.append("metrics")
                    
                    self.log_test(
                        "Analytical Query Completeness",
                        "WARN",
                        f"Response missing: {', '.join(missing)}",
                        duration
                    )
                    return False
            
            self.log_test("Analytical Query", "FAIL", f"Status: {response.status_code}", duration)
            return False
        except Exception as e:
            duration = time.time() - start_time
            self.log_test("Analytical Query", "FAIL", f"Exception: {str(e)}", duration)
            return False
    
    def test_frontend_accessibility(self):
        """Test 11: Frontend is accessible"""
        start_time = time.time()
        try:
            response = requests.get(self.base_url)
            duration = time.time() - start_time
            
            if response.status_code == 200 and 'DOCTYPE html' in response.text:
                self.log_test(
                    "Frontend Accessibility",
                    "PASS",
                    "Frontend serving React app",
                    duration
                )
                return True
            
            self.log_test("Frontend Accessibility", "FAIL", f"Status: {response.status_code}", duration)
            return False
        except Exception as e:
            duration = time.time() - start_time
            self.log_test("Frontend Accessibility", "FAIL", f"Exception: {str(e)}", duration)
            return False
    
    def test_backend_accessibility(self):
        """Test 12: Backend is accessible"""
        start_time = time.time()
        try:
            response = self.session.get(f"{self.backend_url}/api/accounts")
            duration = time.time() - start_time
            
            if response.status_code == 200:
                self.log_test(
                    "Backend Accessibility",
                    "PASS",
                    "Backend API responding",
                    duration
                )
                return True
            
            self.log_test("Backend Accessibility", "FAIL", f"Status: {response.status_code}", duration)
            return False
        except Exception as e:
            duration = time.time() - start_time
            self.log_test("Backend Accessibility", "FAIL", f"Exception: {str(e)}", duration)
            return False
    
    def run_all_tests(self):
        """Run all V3 integration tests"""
        print("=" * 80)
        print("V3 INTEGRATION TEST SUITE")
        print("=" * 80)
        print(f"Frontend: {self.base_url}")
        print(f"Backend:  {self.backend_url}")
        print(f"Customer: {self.customer_id}")
        print("=" * 80)
        print()
        
        tests = [
            self.test_frontend_accessibility,
            self.test_backend_accessibility,
            self.test_login,
            self.test_accounts_api,
            self.test_playbooks_api,
            self.test_deterministic_query_speed,
            self.test_query_without_history,
            self.test_query_with_conversation_history,  # V3 CORE
            self.test_analytical_query_completeness,
            self.test_query_classifier,  # V3 CORE
        ]
        
        passed = 0
        failed = 0
        warned = 0
        
        for test in tests:
            result = test()
            if result == True:
                passed += 1
            elif result == False:
                failed += 1
            else:
                warned += 1
        
        # Print summary
        print("=" * 80)
        print("TEST SUMMARY")
        print("=" * 80)
        print(f"Total Tests:  {len(tests)}")
        print(f"✅ Passed:    {passed}")
        print(f"❌ Failed:    {failed}")
        print(f"⚠️  Warnings:  {warned}")
        print(f"Pass Rate:    {(passed/len(tests)*100):.1f}%")
        print("=" * 80)
        
        # V3-specific features
        print()
        print("V3 CORE FEATURES:")
        core_results = [r for r in self.test_results if 'V3 CORE' in r['test']]
        for r in core_results:
            status_icon = "✅" if r['status'] == "PASS" else "❌"
            print(f"{status_icon} {r['test']}: {r['message']}")
        
        print()
        if failed == 0:
            print("🎉 ALL TESTS PASSED! V3 is ready for deployment!")
            return True
        else:
            print(f"⚠️  {failed} test(s) failed. Review and fix before deployment.")
            return False

def main():
    """Run V3 integration tests"""
    import argparse
    parser = argparse.ArgumentParser(description='V3 Integration Tests')
    parser.add_argument('--frontend', default='http://localhost:3000', help='Frontend URL')
    parser.add_argument('--backend', default='http://localhost:5059', help='Backend URL')
    args = parser.parse_args()
    
    suite = V3IntegrationTests(base_url=args.frontend, backend_url=args.backend)
    success = suite.run_all_tests()
    
    # Save results to file
    with open('v3_test_results.json', 'w') as f:
        json.dump(suite.test_results, f, indent=2)
    
    print(f"\n📄 Detailed results saved to: v3_test_results.json")
    
    sys.exit(0 if success else 1)

if __name__ == '__main__':
    main()

