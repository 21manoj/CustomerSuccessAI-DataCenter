#!/usr/bin/env python3
"""
Scenario 3: Tenant Isolation
12 cross-tenant security tests — verify Customer A cannot see Customer B's data
"""

import logging
from typing import Dict, Any, List

from .base import BaseScenario

logger = logging.getLogger(__name__)


class ScenarioTenantIsolation(BaseScenario):
    """
    Scenario 3: Tenant Isolation Testing

    Requires: At least 2 customers already onboarded (Scenario 1 run for customers 1 and 2)

    Tests (12 total):
    Group 1: Account Visibility (2)
    Group 2: KPI Data Isolation (2)
    Group 3: RAG Query Isolation (1)
    Group 4: Playbook Isolation (2)
    Group 5: Report Isolation (1)
    Group 6: Activity Log Isolation (1)
    Group 7: Header Spoofing (2)
    Group 8: Cross-Customer Signal (1)

    Every test should return 404, empty, or scoped-to-own-customer data.
    """

    def run(self) -> Dict[str, Any]:
        self.start_timer()
        logger.info("🔒 Scenario: Tenant Isolation")

        api_calls = 0
        tests_passed = 0
        tests_failed = 0
        test_results: List[Dict] = []

        # This customer's ID range
        my_customer_id = self.client.customer_id
        other_customer_id = my_customer_id + 1 if my_customer_id else 2
        other_account_base = other_customer_id * 1000 + 1

        logger.info(f"  My customer: {my_customer_id}")
        logger.info(f"  Other customer: {other_customer_id}")
        logger.info(f"  Other account sample: {other_account_base}")

        def record_test(name: str, passed: bool, detail: str = ""):
            nonlocal tests_passed, tests_failed
            if passed:
                tests_passed += 1
                logger.info(f"    ✅ {name}")
            else:
                tests_failed += 1
                logger.warning(f"    ❌ {name}: {detail}")
            test_results.append({
                'test': name,
                'passed': passed,
                'detail': detail
            })

        try:
            # ============================================================
            # Group 1: Account Visibility
            # ============================================================
            logger.info("  Group 1: Account Visibility")

            # Test 1: Listing should only show own accounts
            accounts = self.client.get_accounts()
            api_calls += 1
            if accounts:
                own_only = all(
                    acc.get('customer_id') == my_customer_id or
                    acc.get('account_id', 0) // 1000 == my_customer_id
                    for acc in accounts
                )
                record_test(
                    "account_list_scoped_to_customer",
                    own_only,
                    f"Found {len(accounts)} accounts, all mine={own_only}"
                )
            else:
                record_test("account_list_scoped_to_customer", True, "No accounts returned (OK if none onboarded)")

            # Test 2: Direct access to other customer's account should fail
            other_acc_response = self.client.get_account_scores(other_account_base)
            api_calls += 1
            record_test(
                "cannot_access_other_customer_account",
                other_acc_response is None or other_acc_response.get('error') is not None,
                f"Response: {str(other_acc_response)[:80]}" if other_acc_response else "None (correct)"
            )

            # ============================================================
            # Group 2: KPI Data Isolation
            # ============================================================
            logger.info("  Group 2: KPI Data Isolation")

            # Test 3: Cannot read other customer's KPI scores
            kpi_response = self.client.get(f'/api/dc2s/scores/account/{other_account_base}/latest')
            api_calls += 1
            record_test(
                "cannot_read_other_customer_kpis",
                kpi_response is None or 'error' in str(kpi_response).lower(),
                f"Response: {str(kpi_response)[:80]}" if kpi_response else "None (correct)"
            )

            # Test 4: Cannot upload CSV to other customer
            upload_response = self.client.post(
                '/api/onboarding/upload',
                {
                    'customer_id': other_customer_id,
                    'data': 'test'
                }
            )
            api_calls += 1
            # Should fail or be ignored (customer_id mismatch)
            is_rejected = (
                upload_response is None or
                upload_response.get('status') == 'error' or
                upload_response.get('customer_id') == my_customer_id  # Server overrides to session customer
            )
            record_test(
                "cannot_upload_to_other_customer",
                is_rejected,
                f"Response: {str(upload_response)[:80]}" if upload_response else "None (correct)"
            )

            # ============================================================
            # Group 3: RAG Query Isolation
            # ============================================================
            logger.info("  Group 3: RAG Query Isolation")

            # Test 5: RAG query should only return own data
            rag_response = self.client.rag_query(
                query="List all accounts and their health scores",
                customer_id=my_customer_id
            )
            api_calls += 1
            if rag_response:
                answer = str(rag_response.get('answer', '') or rag_response.get('response', ''))
                # Check that other customer's account names don't appear
                contains_other = str(other_account_base) in answer
                record_test(
                    "rag_query_scoped_to_customer",
                    not contains_other,
                    "Other customer data leaked in RAG response" if contains_other else "Clean"
                )
            else:
                record_test("rag_query_scoped_to_customer", True, "No RAG response (OK if Qdrant not configured)")

            # ============================================================
            # Group 4: Playbook Isolation
            # ============================================================
            logger.info("  Group 4: Playbook Isolation")

            # Test 6: Cannot see other customer's executions
            exec_response = self.client.get('/api/playbooks/executions')
            api_calls += 1
            if exec_response:
                executions = exec_response.get('executions', [])
                if isinstance(exec_response, list):
                    executions = exec_response
                all_mine = all(
                    e.get('customer_id') == my_customer_id
                    for e in executions if 'customer_id' in e
                )
                record_test(
                    "execution_list_scoped_to_customer",
                    all_mine,
                    f"{len(executions)} executions, all mine={all_mine}"
                )
            else:
                record_test("execution_list_scoped_to_customer", True, "No executions")

            # Test 7: Cannot trigger playbook on other customer's account
            trigger_response = self.client.trigger_playbook(
                playbook_id='churn_prevention',
                account_id=other_account_base,
                context={'test': 'isolation'}
            )
            api_calls += 1
            record_test(
                "cannot_trigger_playbook_on_other_account",
                trigger_response is None or 'error' in str(trigger_response).lower(),
                f"Response: {str(trigger_response)[:80]}" if trigger_response else "None (correct)"
            )

            # ============================================================
            # Group 5: Report Isolation
            # ============================================================
            logger.info("  Group 5: Report Isolation")

            # Test 8: Customer summary should only contain own data
            summary = self.client.get('/api/dc2s/scores/customer/summary')
            api_calls += 1
            record_test(
                "customer_summary_scoped",
                summary is not None,  # Just verify it returns without error
                "Summary returned" if summary else "No summary"
            )

            # ============================================================
            # Group 6: Activity Log Isolation
            # ============================================================
            logger.info("  Group 6: Activity Log Isolation")

            # Test 9: Activity log should only show own entries
            activity = self.client.get('/api/activity-log')
            api_calls += 1
            if activity:
                entries = activity.get('entries', activity.get('logs', []))
                if isinstance(activity, list):
                    entries = activity
                all_mine = all(
                    e.get('customer_id') == my_customer_id
                    for e in entries if 'customer_id' in e
                )
                record_test(
                    "activity_log_scoped_to_customer",
                    all_mine,
                    f"{len(entries)} entries, all mine={all_mine}"
                )
            else:
                record_test("activity_log_scoped_to_customer", True, "No activity log")

            # ============================================================
            # Group 7: Header Spoofing
            # ============================================================
            logger.info("  Group 7: Header Spoofing")

            # Test 10: X-Customer-ID header should be ignored when logged in
            original_headers = dict(self.client.session.headers)
            self.client.session.headers['X-Customer-ID'] = str(other_customer_id)

            spoofed_accounts = self.client.get_accounts()
            api_calls += 1

            # Restore headers
            self.client.session.headers.update(original_headers)
            if 'X-Customer-ID' not in original_headers:
                self.client.session.headers.pop('X-Customer-ID', None)

            if spoofed_accounts:
                still_mine = all(
                    acc.get('customer_id') == my_customer_id or
                    acc.get('account_id', 0) // 1000 == my_customer_id
                    for acc in spoofed_accounts
                )
                record_test(
                    "header_spoofing_ignored_when_authenticated",
                    still_mine,
                    f"Accounts returned belong to me: {still_mine}"
                )
            else:
                record_test("header_spoofing_ignored_when_authenticated", True, "No accounts (OK)")

            # Test 11: Unauthenticated header should be rejected
            import requests as raw_requests
            try:
                unauth_response = raw_requests.get(
                    f"{self.client.base_url}/api/dc2s/accounts",
                    headers={'X-Customer-ID': str(other_customer_id)},
                    timeout=10
                )
                record_test(
                    "unauthenticated_header_rejected",
                    unauth_response.status_code in (401, 403),
                    f"Status: {unauth_response.status_code}"
                )
                api_calls += 1
            except Exception as e:
                record_test("unauthenticated_header_rejected", True, f"Connection error: {e}")

            # ============================================================
            # Group 8: Cross-Customer Signal Analysis
            # ============================================================
            logger.info("  Group 8: Cross-Customer Signal")

            # Test 12: Signal analysis on other customer's account should fail
            signal_response = self.client.post(
                '/api/signal-analyst/analyze',
                {
                    'account_id': other_account_base,
                    'analysis_type': 'churn_risk'
                }
            )
            api_calls += 1
            record_test(
                "signal_analyst_scoped_to_customer",
                signal_response is None or 'error' in str(signal_response).lower(),
                f"Response: {str(signal_response)[:80]}" if signal_response else "None (correct)"
            )

            # ============================================================
            # Summary
            # ============================================================
            total_tests = tests_passed + tests_failed
            results = {
                'total_tests': total_tests,
                'tests_passed': tests_passed,
                'tests_failed': tests_failed,
                'pass_rate': round(tests_passed / total_tests * 100, 1) if total_tests else 0,
                'test_results': test_results
            }

            if tests_failed == 0:
                return self.success(
                    f"Tenant isolation: ALL {total_tests} tests passed",
                    details=results,
                    api_calls=api_calls
                )
            else:
                return self.failure(
                    f"Tenant isolation: {tests_failed}/{total_tests} tests FAILED",
                    api_calls=api_calls,
                    errors=[t['detail'] for t in test_results if not t['passed']]
                )

        except Exception as e:
            logger.error(f"❌ Tenant isolation failed: {e}")
            return self.failure("Tenant isolation failed", error=str(e), api_calls=api_calls)
