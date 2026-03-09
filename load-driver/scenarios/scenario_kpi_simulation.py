#!/usr/bin/env python3
"""
Scenario 2a: KPI Simulation
Mutate KPIs over 12 months, upload each month, trigger score recalculation
"""

import logging
import random
from typing import Dict, Any

from .base import BaseScenario

logger = logging.getLogger(__name__)


class ScenarioKpiSimulation(BaseScenario):
    """
    Scenario 2a: 12-Month KPI Drift Simulation

    Steps:
    1. Fetch all accounts for the customer
    2. Assign drift profiles (60% healthy, 20% declining, 10% critical, 5% recovering, 5% seasonal)
    3. For each month (1-12):
       a. Mutate KPI values using drift profile
       b. Upload mutated CSV via /api/onboarding/upload
       c. Trigger score recalculation via /api/dc2s/scores/calculate
    4. Verify final health distribution

    Measures:
    - Upload success per month
    - Score recalculation success
    - Health score distribution shift over 12 months
    """

    def run(self) -> Dict[str, Any]:
        self.start_timer()
        logger.info("📊 Scenario: KPI Simulation (12-month drift)")

        api_calls = 0
        errors = []
        results = {'months_processed': 0, 'profile_assignments': {}}

        try:
            from kpi_mutator import KPIMutator, ALL_KPI_CODES, DEFAULT_TARGETS

            # Step 1: Fetch accounts
            logger.info("  Step 1: Fetch accounts")
            accounts = self.client.get_accounts()
            api_calls += 1

            if not accounts:
                return self.failure("No accounts found", api_calls=api_calls)

            logger.info(f"    Found {len(accounts)} accounts")

            # Step 2: Assign drift profiles
            mutator = KPIMutator(seed=42)
            profiles = mutator.assign_profiles(len(accounts))
            results['profile_assignments'] = {
                acc.get('account_name', f'account_{i}'): profiles[i]
                for i, acc in enumerate(accounts)
            }

            profile_summary = {}
            for profile in profiles.values():
                profile_summary[profile] = profile_summary.get(profile, 0) + 1
            logger.info(f"    Profiles: {profile_summary}")

            # Step 3: Generate baselines
            baseline_values = {}
            for i, acc in enumerate(accounts):
                account_id = acc.get('account_id')
                baselines = {}
                for kpi_code in ALL_KPI_CODES:
                    target = DEFAULT_TARGETS[kpi_code]
                    baselines[kpi_code] = round(random.uniform(target * 0.85, target * 1.05), 2)
                baseline_values[account_id] = baselines

            # Step 4: Simulate 12 months
            months_ok = 0
            for month in range(12):
                month_str = f"2024-{month+1:02d}-01"
                logger.info(f"  Month {month+1}/12: {month_str}")

                # Generate mutated data for all accounts
                all_rows = []
                for i, acc in enumerate(accounts):
                    account_id = acc.get('account_id')
                    profile = profiles[i]
                    month_data = mutator.generate_12_months(
                        account_id=account_id,
                        baseline_values=baseline_values[account_id],
                        profile=profile,
                        start_month=month_str
                    )
                    # Only take the first month's data
                    month_rows = [r for r in month_data if r['measured_at'] == month_str]
                    all_rows.extend(month_rows)

                # Upload via data-ingestion endpoint
                upload_response = self.client.post(
                    '/api/data-ingestion/kpis',
                    {'records': all_rows, 'source': 'kpi_simulation'}
                )
                api_calls += 1

                if upload_response and upload_response.get('status') != 'error':
                    months_ok += 1
                else:
                    errors.append(f"Month {month+1} upload failed: {upload_response}")

                # Trigger score recalculation
                score_response = self.client.calculate_scores(
                    customer_id=self.client.customer_id,
                    measurement_month=month_str
                )
                api_calls += 1

                if not score_response or score_response.get('status') == 'error':
                    errors.append(f"Month {month+1} score calc failed: {score_response}")

            results['months_processed'] = months_ok

            # Step 5: Verify final health distribution
            logger.info("  Step 5: Verify final health distribution")
            final_scores = []
            for acc in accounts:
                score = self.client.get_account_scores(acc.get('account_id'))
                api_calls += 1
                if score and 'health_score' in score:
                    health = score['health_score']
                    if isinstance(health, dict):
                        final_scores.append(health.get('overall_health_score', 0))
                    else:
                        final_scores.append(health)

            if final_scores:
                results['final_health'] = {
                    'avg': round(sum(final_scores) / len(final_scores), 1),
                    'min': round(min(final_scores), 1),
                    'max': round(max(final_scores), 1),
                    'healthy': sum(1 for s in final_scores if s >= 80),
                    'at_risk': sum(1 for s in final_scores if 60 <= s < 80),
                    'critical': sum(1 for s in final_scores if s < 60),
                }

            if months_ok >= 10:
                return self.success(
                    f"KPI simulation complete: {months_ok}/12 months, {len(accounts)} accounts",
                    details=results,
                    api_calls=api_calls,
                    errors=errors
                )
            else:
                return self.failure(
                    f"KPI simulation incomplete: only {months_ok}/12 months succeeded",
                    api_calls=api_calls,
                    errors=errors
                )

        except Exception as e:
            logger.error(f"❌ KPI simulation failed: {e}")
            return self.failure("KPI simulation failed", error=str(e), api_calls=api_calls)
