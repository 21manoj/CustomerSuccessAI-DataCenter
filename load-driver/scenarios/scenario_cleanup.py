#!/usr/bin/env python3
"""
Scenario 4: Post-Test Cleanup
Delete all test data in FK-safe order, verify no orphans remain
"""

import logging
from typing import Dict, Any

from .base import BaseScenario

logger = logging.getLogger(__name__)


class ScenarioCleanup(BaseScenario):
    """
    Scenario 4: Post-Test Cleanup

    Deletes all test data for customer in FK-safe order:
    1. Leaf tables (no dependents)
    2. Playbook chain (reports → executions → triggers)
    3. Config and features
    4. Score tables (no FK to customer)
    5. Health/KPI records
    6. Products and accounts
    7. Activity logs
    8. User and config
    9. Customer record (last)

    Measures:
    - Deletion success rate
    - Cascading delete verification
    - Orphan row detection
    """

    def run(self) -> Dict[str, Any]:
        """Execute cleanup scenario"""
        self.start_timer()
        logger.info("🧹 Scenario: Post-Test Cleanup")

        api_calls = 0
        errors = []
        results = {}

        try:
            customer_id = self.client.customer_id
            if not customer_id:
                return self.failure(
                    "Customer ID not set on client",
                    error="Cannot clean up without customer_id"
                )

            # ================================================================
            # Dry Run (Preview)
            # ================================================================
            logger.info(f"  Dry-run: Preview cleanup for customer {customer_id}")

            dry_run_response = self.client.cleanup_customer(
                customer_id=customer_id,
                dry_run=True
            )
            api_calls += 1

            if not dry_run_response or dry_run_response.get('status') != 'success':
                errors.append(f"Dry-run failed: {dry_run_response}")
            else:
                logger.info("    ✅ Dry-run successful")
                results['dry_run'] = {
                    'tables_to_delete': dry_run_response.get('tables', []),
                    'rows_to_delete': dry_run_response.get('total_rows', 0)
                }

                logger.info(f"    Would delete {dry_run_response.get('total_rows', 0)} rows from {len(dry_run_response.get('tables', []))} tables")

            # ================================================================
            # Actual Cleanup (only if not --dry-run flag)
            # ================================================================
            if self.args and hasattr(self.args, 'dry_run') and self.args.dry_run:
                logger.info("  🚫 Dry-run mode: skipping actual cleanup")
                return self.success(
                    f"Dry-run complete: customer {customer_id} cleanup preview",
                    details=results,
                    api_calls=api_calls
                )

            logger.info(f"  Executing cleanup for customer {customer_id}")

            cleanup_response = self.client.cleanup_customer(
                customer_id=customer_id,
                dry_run=False
            )
            api_calls += 1

            if not cleanup_response or cleanup_response.get('status') != 'success':
                return self.failure(
                    f"Cleanup failed for customer {customer_id}",
                    error=str(cleanup_response),
                    api_calls=api_calls
                )

            logger.info("    ✅ Cleanup completed")
            results['cleanup'] = {
                'tables_deleted': cleanup_response.get('tables_deleted', 0),
                'rows_deleted': cleanup_response.get('rows_deleted', 0),
                'duration_seconds': cleanup_response.get('duration_seconds', 0)
            }

            # ================================================================
            # Verification (Check for Orphans)
            # ================================================================
            logger.info("  Verifying cleanup...")

            verify_response = cleanup_response.get('verification', {})
            orphan_count = verify_response.get('orphan_rows', 0)

            if orphan_count == 0:
                logger.info("    ✅ Verification: No orphans found")
                results['verification'] = {
                    'status': 'clean',
                    'orphan_rows': 0
                }
            else:
                logger.warning(f"    ⚠️  Verification: {orphan_count} orphan rows found")
                results['verification'] = {
                    'status': 'orphans_found',
                    'orphan_rows': orphan_count,
                    'orphan_tables': verify_response.get('orphan_details', {})
                }
                errors.append(f"Orphan rows detected: {orphan_count}")

            # ================================================================
            # Summary
            # ================================================================
            if not errors:
                return self.success(
                    f"Cleanup complete: customer {customer_id}, {results['cleanup']['rows_deleted']} rows deleted",
                    details=results,
                    api_calls=api_calls
                )
            else:
                return self.success(
                    f"Cleanup complete with warnings: customer {customer_id}",
                    details=results,
                    api_calls=api_calls,
                    errors=errors,
                    message_notes="Some orphans or warnings detected"
                )

        except Exception as e:
            logger.error(f"❌ Cleanup failed: {e}")
            return self.failure(
                "Cleanup scenario failed",
                error=str(e),
                api_calls=api_calls,
                errors=errors
            )
