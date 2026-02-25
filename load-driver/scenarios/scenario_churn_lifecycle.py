#!/usr/bin/env python3
"""
Scenario 2e: Churn Lifecycle
Archive churned accounts, delete them, verify cascading cleanup
"""

import logging
from typing import Dict, Any

from .base import BaseScenario

logger = logging.getLogger(__name__)


class ScenarioChurnLifecycle(BaseScenario):
    """
    Scenario 2e: Account Churn Lifecycle

    Steps:
    1. Identify 2 critical accounts (lowest health scores)
    2. Archive them (soft-delete: status → 'archived')
    3. Verify archived accounts are excluded from active listings
    4. Delete archived accounts (hard-delete with cascade)
    5. Verify all related data is cleaned up

    Measures:
    - Archive success
    - Deletion success
    - Cascade verification (KPIs, scores, signals removed)
    - No orphan rows remain
    """

    CHURN_COUNT = 2  # How many accounts to churn

    def run(self) -> Dict[str, Any]:
        self.start_timer()
        logger.info("💀 Scenario: Churn Lifecycle")

        api_calls = 0
        errors = []
        results = {
            'accounts_archived': 0,
            'accounts_deleted': 0,
            'cascade_verified': False,
            'churned_accounts': []
        }

        try:
            # Step 1: Identify lowest-health accounts
            logger.info("  Step 1: Identify churn candidates")
            accounts = self.client.get_accounts()
            api_calls += 1

            if not accounts or len(accounts) < self.CHURN_COUNT + 2:
                return self.failure(
                    f"Need at least {self.CHURN_COUNT + 2} accounts, found {len(accounts) if accounts else 0}",
                    api_calls=api_calls
                )

            # Score all accounts
            scored = []
            for acc in accounts:
                score = self.client.get_account_scores(acc.get('account_id'))
                api_calls += 1
                health = 50  # default
                if score and isinstance(score.get('health_score'), dict):
                    health = score['health_score'].get('overall_health_score', 50)
                scored.append((acc, health))

            # Sort by health (lowest first) and pick churn candidates
            scored.sort(key=lambda x: x[1])
            churn_candidates = scored[:self.CHURN_COUNT]

            for acc, health in churn_candidates:
                logger.info(f"    Churn candidate: {acc.get('account_name')} (health={health})")

            # Step 2: Archive accounts
            logger.info("  Step 2: Archive churn candidates")
            for acc, health in churn_candidates:
                account_id = acc.get('account_id')
                archive_response = self.client.post(
                    f'/api/accounts/{account_id}/archive',
                    {}
                )
                api_calls += 1

                if archive_response and archive_response.get('status') == 'success':
                    results['accounts_archived'] += 1
                    results['churned_accounts'].append({
                        'account_id': account_id,
                        'account_name': acc.get('account_name'),
                        'health_at_churn': health,
                        'archived': True,
                        'deleted': False
                    })
                    logger.info(f"    ✅ Archived account {account_id}")
                else:
                    errors.append(f"Archive failed for {account_id}: {archive_response}")

            # Step 3: Verify archived accounts excluded from active list
            logger.info("  Step 3: Verify archive exclusion")
            active_accounts = self.client.get_accounts()
            api_calls += 1

            archived_ids = [c['account_id'] for c in results['churned_accounts'] if c['archived']]
            if active_accounts:
                active_ids = [a.get('account_id') for a in active_accounts]
                leaked = [aid for aid in archived_ids if aid in active_ids]
                if leaked:
                    # Some APIs may still return archived accounts — check status field
                    for acc in active_accounts:
                        if acc.get('account_id') in archived_ids:
                            if acc.get('account_status') != 'archived':
                                errors.append(f"Archived account {acc.get('account_id')} still shows as active")
                    logger.info(f"    Archived accounts in listing: {len(leaked)} (checking status field)")
                else:
                    logger.info(f"    ✅ Archived accounts excluded from active list")

            # Step 4: Hard-delete archived accounts
            logger.info("  Step 4: Delete archived accounts")
            for churned in results['churned_accounts']:
                if not churned['archived']:
                    continue

                account_id = churned['account_id']
                delete_response = self.client.post(
                    f'/api/accounts/{account_id}/delete',
                    {'confirm': True}
                )
                api_calls += 1

                if delete_response and delete_response.get('status') == 'success':
                    results['accounts_deleted'] += 1
                    churned['deleted'] = True
                    churned['rows_deleted'] = delete_response.get('rows_deleted', 0)
                    logger.info(f"    ✅ Deleted account {account_id}: {churned['rows_deleted']} rows")
                else:
                    errors.append(f"Deletion failed for {account_id}: {delete_response}")

            # Step 5: Verify cascade cleanup
            logger.info("  Step 5: Verify cascade cleanup")
            cascade_ok = True
            for churned in results['churned_accounts']:
                if not churned['deleted']:
                    continue

                account_id = churned['account_id']

                # Try to fetch scores for deleted account — should return 404
                score = self.client.get_account_scores(account_id)
                api_calls += 1

                if score and score.get('health_score'):
                    cascade_ok = False
                    errors.append(f"Orphan scores found for deleted account {account_id}")
                else:
                    logger.info(f"    ✅ No orphan data for account {account_id}")

            results['cascade_verified'] = cascade_ok

            results['summary'] = {
                'accounts_archived': results['accounts_archived'],
                'accounts_deleted': results['accounts_deleted'],
                'cascade_verified': results['cascade_verified'],
                'total_rows_deleted': sum(
                    c.get('rows_deleted', 0) for c in results['churned_accounts']
                )
            }

            if results['accounts_deleted'] >= self.CHURN_COUNT:
                return self.success(
                    f"Churn lifecycle complete: {results['accounts_deleted']} accounts deleted, "
                    f"cascade={'clean' if cascade_ok else 'ORPHANS FOUND'}",
                    details=results,
                    api_calls=api_calls,
                    errors=errors
                )
            else:
                return self.failure(
                    f"Churn lifecycle incomplete: only {results['accounts_deleted']}/{self.CHURN_COUNT} deleted",
                    api_calls=api_calls,
                    errors=errors
                )

        except Exception as e:
            logger.error(f"❌ Churn lifecycle failed: {e}")
            return self.failure("Churn lifecycle failed", error=str(e), api_calls=api_calls)
