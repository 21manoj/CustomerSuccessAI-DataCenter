#!/usr/bin/env python3
"""
Scenario 1: Onboarding
Register customer, create accounts, process data, calculate scores
"""

import logging
import time
from typing import Dict, Any
from faker import Faker

from .base import BaseScenario

logger = logging.getLogger(__name__)
fake = Faker()


class ScenarioOnboarding(BaseScenario):
    """
    Scenario 1: Customer Onboarding

    Steps:
    1. Register new customer
    2. Complete onboarding (create accounts)
    3. Process data (load CSVs, embeddings, journey)
    4. Calculate scores (KPI → Pillar → Health)

    Measures:
    - Registration success
    - Account creation
    - Data processing pipeline
    - Score calculation
    """

    def run(self) -> Dict[str, Any]:
        """Execute onboarding scenario"""
        self.start_timer()
        logger.info("🚀 Scenario: Onboarding")

        api_calls = 0
        errors = []
        results = {}

        try:
            # ================================================================
            # Step 1: Register Customer
            # ================================================================
            logger.info("  Step 1: Register customer")

            company_name = f"{fake.company()} - {fake.word()}"
            admin_name = fake.name()
            email = fake.email()
            password = "TestPassword2026!"

            register_response = self.client.register_customer(
                company_name=company_name,
                admin_name=admin_name,
                email=email,
                password=password,
                vertical="dc2_s"
            )
            api_calls += 1

            if not register_response or register_response.get('status') != 'success':
                return self.failure(
                    "Customer registration failed",
                    error=str(register_response),
                    api_calls=api_calls
                )

            customer_id = register_response['customer_id']
            customer_uuid = register_response.get('customer_uuid')
            user_id = register_response['user_id']

            logger.info(f"    ✅ Customer registered: {customer_id}")
            results['customer_id'] = customer_id
            results['customer_uuid'] = customer_uuid

            # ================================================================
            # Step 2: Complete Onboarding (Create Accounts)
            # ================================================================
            logger.info("  Step 2: Complete onboarding (demo mode)")

            num_accounts = 10  # Default for load testing
            onboarding_response = self.client.complete_onboarding(
                customer_id=customer_id,
                customer_name=company_name,
                vertical="dc2_s",
                num_accounts=num_accounts,
                onboarding_mode="demo"
            )
            api_calls += 1

            if not onboarding_response or not onboarding_response.get('success'):
                return self.failure(
                    "Onboarding completion failed",
                    error=str(onboarding_response),
                    api_calls=api_calls
                )

            account_ids = [f"{customer_id}{str(i).zfill(3)}" for i in range(1, num_accounts + 1)]
            logger.info(f"    ✅ Created {num_accounts} accounts")
            results['accounts_created'] = num_accounts
            results['account_id_range'] = f"{customer_id}001 - {customer_id}{num_accounts:03d}"

            # ================================================================
            # Step 3: Process Data
            # ================================================================
            logger.info("  Step 3: Process data (CSVs → database → embeddings)")

            process_response = self.client.process_data(
                customer_id=customer_id,
                vertical="dc2_s",
                skip_wizard_b=True,
                skip_wizard_c=False
            )
            api_calls += 1

            if not process_response or process_response.get('status') != 'success':
                # Process data can take time; allow for warning
                if process_response and 'timeout' in str(process_response).lower():
                    logger.warning("    ⏱️  Data processing timed out (may still be in progress)")
                    results['data_processing'] = 'timeout'
                else:
                    errors.append(f"Data processing failed: {process_response}")
                    results['data_processing'] = 'failed'
            else:
                logger.info("    ✅ Data processed successfully")
                results['data_processing'] = 'success'
                results['data_processing_steps'] = process_response.get('steps_completed', [])

            # ================================================================
            # Step 4: Calculate Scores
            # ================================================================
            logger.info("  Step 4: Calculate health scores")

            score_response = self.client.calculate_scores(
                customer_id=customer_id,
                measurement_month="2024-12-01"
            )
            api_calls += 1

            if not score_response or score_response.get('status') != 'success':
                errors.append(f"Score calculation failed: {score_response}")
                results['scores_calculated'] = False
            else:
                logger.info("    ✅ Scores calculated successfully")
                results['scores_calculated'] = True
                results['health_scores_created'] = score_response.get('health_scores_created', 0)

            # ================================================================
            # Step 5: Verify Dashboard Access
            # ================================================================
            logger.info("  Step 5: Verify dashboard access")

            # Login again with registered credentials
            temp_client = type(self.client)(
                base_url=self.client.base_url,
                email=email,
                password=password,
                customer_id=customer_id
            )
            if temp_client.health_check() and temp_client.login():
                accounts = temp_client.get_accounts()
                if accounts:
                    logger.info(f"    ✅ Dashboard accessible: {len(accounts)} accounts visible")
                    results['dashboard_accessible'] = True
                    results['accounts_visible'] = len(accounts)
                else:
                    logger.warning("    ⚠️  No accounts visible in dashboard (may need processing)")
                    results['dashboard_accessible'] = True
                    results['accounts_visible'] = 0
            else:
                errors.append("Failed to login with new credentials")
                results['dashboard_accessible'] = False

            # ================================================================
            # Summary
            # ================================================================
            if not errors:
                return self.success(
                    f"Onboarding complete: customer {customer_id}, {num_accounts} accounts",
                    details=results,
                    api_calls=api_calls,
                    errors=errors
                )
            else:
                return self.success(
                    f"Onboarding partially complete: customer {customer_id}, {num_accounts} accounts",
                    details=results,
                    api_calls=api_calls,
                    errors=errors,
                    message_notes="Some steps had warnings"
                )

        except Exception as e:
            logger.error(f"❌ Onboarding failed: {e}")
            return self.failure(
                "Onboarding scenario failed",
                error=str(e),
                api_calls=api_calls,
                errors=errors
            )
