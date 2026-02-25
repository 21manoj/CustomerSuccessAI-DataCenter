#!/usr/bin/env python3
"""
Scenario 2b: RAG Queries
Execute natural language queries against Qdrant for multiple accounts
"""

import logging
import random
import time
from typing import Dict, Any

from .base import BaseScenario

logger = logging.getLogger(__name__)


class ScenarioRagQueries(BaseScenario):
    """
    Scenario 2b: RAG Query Testing

    Steps:
    1. Fetch 5 random accounts
    2. For each account, run 3-5 queries from template library
    3. Track query latency, response quality, and cost
    4. Validate responses contain account-specific data

    Measures:
    - Query success rate
    - Average response latency
    - Response relevance (does response mention the account name?)
    - Total LLM cost (estimated from tokens)
    """

    QUERIES_PER_ACCOUNT = 4
    MAX_ACCOUNTS = 5

    def run(self) -> Dict[str, Any]:
        self.start_timer()
        logger.info("🔍 Scenario: RAG Queries")

        api_calls = 0
        errors = []
        results = {
            'queries_executed': 0,
            'queries_successful': 0,
            'queries_relevant': 0,
            'latencies_ms': [],
            'per_account': {}
        }

        try:
            from query_templates import get_queries_for_account, KPI_NAMES, PILLAR_NAMES

            # Step 1: Fetch accounts
            logger.info("  Step 1: Fetch accounts")
            all_accounts = self.client.get_accounts()
            api_calls += 1

            if not all_accounts:
                return self.failure("No accounts found", api_calls=api_calls)

            # Pick random subset
            accounts = random.sample(all_accounts, min(self.MAX_ACCOUNTS, len(all_accounts)))
            logger.info(f"    Selected {len(accounts)} accounts for RAG testing")

            # Step 2: Run queries per account
            for acc in accounts:
                account_name = acc.get('account_name', 'Unknown')
                account_id = acc.get('account_id')
                logger.info(f"  Account: {account_name} ({account_id})")

                kpi_name = random.choice(KPI_NAMES)
                pillar_name = random.choice(PILLAR_NAMES)

                queries = get_queries_for_account(
                    account_name=account_name,
                    kpi_name=kpi_name,
                    pillar_name=pillar_name,
                    num_queries=self.QUERIES_PER_ACCOUNT
                )

                account_results = {
                    'queries': [],
                    'success_count': 0,
                    'relevant_count': 0,
                    'avg_latency_ms': 0
                }
                latencies = []

                for query in queries:
                    results['queries_executed'] += 1
                    logger.info(f"    Query: {query[:60]}...")

                    start_time = time.time()
                    response = self.client.rag_query(
                        query=query,
                        customer_id=self.client.customer_id
                    )
                    latency_ms = int((time.time() - start_time) * 1000)
                    api_calls += 1
                    latencies.append(latency_ms)
                    results['latencies_ms'].append(latency_ms)

                    query_result = {
                        'query': query,
                        'latency_ms': latency_ms,
                        'success': False,
                        'relevant': False,
                        'response_length': 0
                    }

                    if response:
                        answer = response.get('answer', '') or response.get('response', '') or ''
                        query_result['success'] = True
                        query_result['response_length'] = len(answer)
                        results['queries_successful'] += 1
                        account_results['success_count'] += 1

                        # Check relevance: does response mention the account?
                        if account_name.lower() in answer.lower() or str(account_id) in answer:
                            query_result['relevant'] = True
                            results['queries_relevant'] += 1
                            account_results['relevant_count'] += 1

                        logger.info(f"      ✅ {latency_ms}ms, {len(answer)} chars, relevant={query_result['relevant']}")
                    else:
                        errors.append(f"Query failed for {account_name}: {query[:40]}...")
                        logger.warning(f"      ❌ Query failed ({latency_ms}ms)")

                    account_results['queries'].append(query_result)

                if latencies:
                    account_results['avg_latency_ms'] = round(sum(latencies) / len(latencies))

                results['per_account'][account_name] = account_results

            # Step 3: Summary
            total = results['queries_executed']
            successful = results['queries_successful']
            relevant = results['queries_relevant']
            all_latencies = results['latencies_ms']

            results['summary'] = {
                'total_queries': total,
                'success_rate': round(successful / total * 100, 1) if total else 0,
                'relevance_rate': round(relevant / total * 100, 1) if total else 0,
                'avg_latency_ms': round(sum(all_latencies) / len(all_latencies)) if all_latencies else 0,
                'p95_latency_ms': sorted(all_latencies)[int(len(all_latencies) * 0.95)] if all_latencies else 0,
                'accounts_tested': len(accounts)
            }

            logger.info(f"  Summary: {successful}/{total} queries OK, "
                        f"{relevant}/{total} relevant, "
                        f"avg latency {results['summary']['avg_latency_ms']}ms")

            if successful >= total * 0.8:
                return self.success(
                    f"RAG queries complete: {successful}/{total} successful, "
                    f"{results['summary']['relevance_rate']}% relevant",
                    details=results,
                    api_calls=api_calls,
                    errors=errors
                )
            else:
                return self.failure(
                    f"Too many RAG query failures: {successful}/{total}",
                    api_calls=api_calls,
                    errors=errors
                )

        except Exception as e:
            logger.error(f"❌ RAG queries failed: {e}")
            return self.failure("RAG query scenario failed", error=str(e), api_calls=api_calls)
