#!/usr/bin/env python3
"""
Scenario 1: Onboarding
Uses the /api/onboarding/complete endpoint which handles the full pipeline:
  1. Creates customer + CustomerConfig
  2. Creates sample accounts
  3. Generates synthetic data (KPI measurements, signals)
  4. Calculates scores (KPI → Pillar → Health)

After complete, registers a user via /api/register and verifies login + dashboard.
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
    1. /api/onboarding/complete (all-in-one: customer + accounts + data + scores)
    2. Verify customer was created
    3. Register a user for this customer via /api/register
    4. Login with new user and verify dashboard
    5. Verify accounts and scores exist

    Measures:
    - Complete endpoint response time
    - Customer + account creation
    - Data generation pipeline
    - Score calculation
    - Dashboard accessibility
    """

    def run(self) -> Dict[str, Any]:
        """Execute onboarding scenario"""
        self.start_timer()
        logger.info("=== Scenario 1: Onboarding ===")

        api_calls = 0
        errors = []
        results = {}
        customer_id = None

        # Generate test data
        company_name = f"LoadTest-{fake.company()}"
        admin_name = fake.name()
        email = fake.email()
        password = "TestPassword2026!"

        results['company_name'] = company_name
        results['email'] = email

        try:
            # ================================================================
            # Step 1: Complete Onboarding (all-in-one)
            # ================================================================
            logger.info("  Step 1: /api/onboarding/complete (all-in-one pipeline)")

            start_step1 = time.time()
            # Increase timeout — this endpoint runs data generation subprocess (up to 300s)
            original_timeout = self.client.timeout
            self.client.timeout = 180
            # Build onboarding payload
            onboarding_payload = {
                'customer_name': company_name,
                'industry': 'Technology'
            }
            # Allow --num-accounts to control account count (default: 3)
            if self.args and hasattr(self.args, 'num_accounts') and self.args.num_accounts:
                onboarding_payload['num_accounts'] = self.args.num_accounts
                logger.info(f"    Requesting {self.args.num_accounts} accounts")

            complete_response = self.client.post(
                '/api/onboarding/complete',
                onboarding_payload,
                skip_auth_check=True
            )
            self.client.timeout = original_timeout
            step1_duration = time.time() - start_step1
            api_calls += 1

            if complete_response and complete_response.get('success'):
                customer_id = complete_response.get('customer_id')
                accounts_count = complete_response.get('accounts', 0)
                logger.info(f"    OK: Customer {customer_id} created ({accounts_count} accounts) in {step1_duration:.1f}s")
                results['step1_complete'] = 'success'
                results['customer_id'] = customer_id
                results['accounts_created'] = accounts_count
                results['step1_duration_s'] = round(step1_duration, 2)
                results['complete_response'] = {
                    k: v for k, v in complete_response.items()
                    if k not in ('logs', 'trace')
                }
            elif complete_response and complete_response.get('customer_id'):
                # Partial success — customer created but maybe data gen failed
                customer_id = complete_response.get('customer_id')
                logger.warning(f"    WARN: Partial success — customer {customer_id} created but pipeline incomplete")
                results['step1_complete'] = 'partial'
                results['customer_id'] = customer_id
                results['complete_response_raw'] = str(complete_response)[:200]
                errors.append(f"Complete endpoint partial: {str(complete_response)[:100]}")
            else:
                logger.error(f"    FAIL: Complete onboarding failed: {str(complete_response)[:150]}")
                results['step1_complete'] = 'failed'
                results['complete_response_raw'] = str(complete_response)[:200]
                return self.failure(
                    "Complete onboarding failed — cannot proceed",
                    error=str(complete_response)[:200] if complete_response else "No response",
                    api_calls=api_calls,
                    details=results
                )

            # ================================================================
            # Step 2: Register a user for this customer
            # ================================================================
            logger.info("  Step 2: Register user via /api/register")

            register_response = self.client.register_customer(
                company_name=f"{company_name}-User",  # Different name to avoid duplicate
                admin_name=admin_name,
                email=email,
                password=password,
                vertical="dc"
            )
            api_calls += 1

            user_customer_id = None
            if register_response and register_response.get('status') == 'success':
                user_customer_id = register_response.get('customer_id')
                user_id = register_response.get('user_id')
                logger.info(f"    OK: User registered (user_id: {user_id}, customer: {user_customer_id})")
                results['step2_register'] = 'success'
                results['user_id'] = user_id
                results['user_customer_id'] = user_customer_id
            else:
                logger.warning(f"    WARN: User registration failed: {str(register_response)[:80]}")
                results['step2_register'] = f"failed: {str(register_response)[:80]}"
                errors.append("User registration failed (non-critical — customer exists)")

            # ================================================================
            # Step 3: Login and verify dashboard
            # ================================================================
            logger.info("  Step 3: Login and verify dashboard")

            if user_customer_id:
                from client import CSPulseClient
                new_client = CSPulseClient(
                    base_url=self.client.base_url,
                    email=email,
                    password=password,
                    customer_id=user_customer_id
                )
                login_ok = new_client.login()
                api_calls += 1

                if login_ok:
                    logger.info("    OK: Login successful")
                    results['step3_login'] = 'success'

                    # Get accounts
                    accounts = new_client.get_accounts()
                    api_calls += 1

                    if accounts is not None:
                        account_count = len(accounts) if isinstance(accounts, list) else 0
                        logger.info(f"    OK: Dashboard shows {account_count} accounts")
                        results['step3_dashboard'] = 'accessible'
                        results['accounts_visible'] = account_count
                    else:
                        logger.warning("    WARN: No accounts returned from dashboard")
                        results['step3_dashboard'] = 'no_accounts'
                else:
                    logger.warning("    WARN: Login failed")
                    results['step3_login'] = 'failed'
                    errors.append("Login with registered user failed")
            else:
                logger.info("    SKIP: No user registered, skipping login test")
                results['step3_login'] = 'skipped'

            # ================================================================
            # Step 4: Verify scores exist (use original customer_id from complete)
            # ================================================================
            logger.info("  Step 4: Verify scores exist")

            # Try to get scores for the customer created by /complete
            scores_response = self.client.get(
                f'/api/dc2s/scores/customer/{customer_id}/latest',
                skip_auth_check=True
            )
            api_calls += 1

            if scores_response and isinstance(scores_response, dict):
                has_scores = bool(
                    scores_response.get('health_scores') or
                    scores_response.get('pillar_scores') or
                    scores_response.get('kpi_scores') or
                    scores_response.get('scores')
                )
                if has_scores:
                    logger.info("    OK: Scores exist for customer")
                    results['step4_scores'] = 'verified'
                else:
                    logger.info(f"    INFO: Score response keys: {list(scores_response.keys())[:5]}")
                    results['step4_scores'] = f"response_ok_keys={list(scores_response.keys())[:5]}"
            else:
                logger.warning("    WARN: Could not fetch scores")
                results['step4_scores'] = 'not_available'

            # ================================================================
            # Summary
            # ================================================================
            if not errors:
                return self.success(
                    f"Onboarding complete: customer {customer_id}, pipeline OK",
                    details=results,
                    api_calls=api_calls
                )
            else:
                return self.success(
                    f"Onboarding partial: customer {customer_id} ({len(errors)} warnings)",
                    details=results,
                    api_calls=api_calls,
                    errors=errors
                )

        except Exception as e:
            logger.error(f"Onboarding failed with exception: {e}")
            return self.failure(
                "Onboarding scenario failed",
                error=str(e),
                api_calls=api_calls,
                details=results
            )
