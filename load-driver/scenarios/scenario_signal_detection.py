#!/usr/bin/env python3
"""
Scenario 2c: Signal Detection
Detect churn/expansion signals, trigger playbooks
"""

import logging
import time
from typing import Dict, Any

from .base import BaseScenario

logger = logging.getLogger(__name__)


class ScenarioSignalDetection(BaseScenario):
    """
    Scenario 2c: Signal Detection + Playbook Triggering

    Steps:
    1. Fetch accounts and identify critical/at-risk accounts
    2. Run signal analyst on degraded accounts (churn signals)
    3. Run signal analyst on healthy accounts (expansion signals)
    4. Trigger appropriate playbooks for detected signals
    5. Verify execution status transitions

    Measures:
    - Signals detected per account
    - Playbooks triggered
    - Execution status transitions (IN_PROGRESS → HANDED_OFF → COMPLETED)
    """

    MAX_CHURN_ACCOUNTS = 3
    MAX_EXPANSION_ACCOUNTS = 2

    def run(self) -> Dict[str, Any]:
        self.start_timer()
        logger.info("🚨 Scenario: Signal Detection")

        api_calls = 0
        errors = []
        results = {
            'churn_signals': [],
            'expansion_signals': [],
            'playbooks_triggered': 0,
            'executions': []
        }

        try:
            # Step 1: Fetch accounts and classify
            logger.info("  Step 1: Fetch and classify accounts")
            accounts = self.client.get_accounts()
            api_calls += 1

            if not accounts:
                return self.failure("No accounts found", api_calls=api_calls)

            # Classify by health
            critical = []
            healthy = []
            for acc in accounts:
                score = self.client.get_account_scores(acc.get('account_id'))
                api_calls += 1
                if not score:
                    continue
                health = score.get('health_score', {})
                overall = health.get('overall_health_score', 50) if isinstance(health, dict) else 50
                acc['_health'] = overall
                if overall < 60:
                    critical.append(acc)
                elif overall >= 80:
                    healthy.append(acc)

            logger.info(f"    Critical: {len(critical)}, Healthy: {len(healthy)}")

            # Step 2: Churn signal detection
            logger.info("  Step 2: Detect churn signals")
            churn_targets = critical[:self.MAX_CHURN_ACCOUNTS]

            for acc in churn_targets:
                account_id = acc.get('account_id')
                account_name = acc.get('account_name', 'Unknown')
                logger.info(f"    Analyzing churn risk: {account_name} (health={acc['_health']})")

                signal_response = self.client.post(
                    '/api/signal-analyst/analyze',
                    {
                        'account_id': account_id,
                        'analysis_type': 'churn_risk',
                        'include_recommendations': True
                    }
                )
                api_calls += 1

                if signal_response and signal_response.get('status') != 'error':
                    signals = signal_response.get('signals', [])
                    results['churn_signals'].append({
                        'account_id': account_id,
                        'account_name': account_name,
                        'health_score': acc['_health'],
                        'signals_detected': len(signals) if isinstance(signals, list) else 1,
                        'risk_level': signal_response.get('risk_level', 'unknown')
                    })
                    logger.info(f"      ✅ Detected {len(signals) if isinstance(signals, list) else 1} churn signals")
                else:
                    errors.append(f"Signal analysis failed for {account_name}: {signal_response}")

            # Step 3: Expansion signal detection
            logger.info("  Step 3: Detect expansion signals")
            expansion_targets = healthy[:self.MAX_EXPANSION_ACCOUNTS]

            for acc in expansion_targets:
                account_id = acc.get('account_id')
                account_name = acc.get('account_name', 'Unknown')
                logger.info(f"    Analyzing expansion: {account_name} (health={acc['_health']})")

                signal_response = self.client.post(
                    '/api/signal-analyst/analyze',
                    {
                        'account_id': account_id,
                        'analysis_type': 'expansion_opportunity',
                        'include_recommendations': True
                    }
                )
                api_calls += 1

                if signal_response and signal_response.get('status') != 'error':
                    results['expansion_signals'].append({
                        'account_id': account_id,
                        'account_name': account_name,
                        'health_score': acc['_health'],
                        'opportunity_score': signal_response.get('opportunity_score', 0)
                    })
                    logger.info(f"      ✅ Expansion opportunity detected")
                else:
                    errors.append(f"Expansion analysis failed for {account_name}: {signal_response}")

            # Step 4: Trigger playbooks
            logger.info("  Step 4: Trigger playbooks")

            # Churn prevention playbook for critical accounts
            for signal in results['churn_signals']:
                exec_response = self.client.trigger_playbook(
                    playbook_id='churn_prevention',
                    account_id=signal['account_id'],
                    context={
                        'trigger': 'signal_detection',
                        'risk_level': signal.get('risk_level', 'high'),
                        'health_score': signal['health_score']
                    }
                )
                api_calls += 1

                if exec_response and exec_response.get('execution_id'):
                    results['playbooks_triggered'] += 1
                    results['executions'].append({
                        'execution_id': exec_response['execution_id'],
                        'playbook': 'churn_prevention',
                        'account_id': signal['account_id'],
                        'status': exec_response.get('status', 'unknown')
                    })
                    logger.info(f"      ✅ Triggered churn_prevention for account {signal['account_id']}")
                else:
                    errors.append(f"Playbook trigger failed for account {signal['account_id']}")

            # Expansion playbook for healthy accounts
            for signal in results['expansion_signals']:
                exec_response = self.client.trigger_playbook(
                    playbook_id='expansion',
                    account_id=signal['account_id'],
                    context={
                        'trigger': 'signal_detection',
                        'health_score': signal['health_score'],
                        'opportunity_score': signal.get('opportunity_score', 0)
                    }
                )
                api_calls += 1

                if exec_response and exec_response.get('execution_id'):
                    results['playbooks_triggered'] += 1
                    results['executions'].append({
                        'execution_id': exec_response['execution_id'],
                        'playbook': 'expansion',
                        'account_id': signal['account_id'],
                        'status': exec_response.get('status', 'unknown')
                    })

            # Step 5: Check execution statuses
            logger.info("  Step 5: Verify execution status")
            time.sleep(2)  # Brief pause for async processing

            for execution in results['executions']:
                status = self.client.get_execution_status(execution['execution_id'])
                api_calls += 1
                if status:
                    execution['final_status'] = status.get('status', 'unknown')

            results['summary'] = {
                'churn_signals_detected': len(results['churn_signals']),
                'expansion_signals_detected': len(results['expansion_signals']),
                'playbooks_triggered': results['playbooks_triggered'],
                'total_accounts_analyzed': len(churn_targets) + len(expansion_targets)
            }

            return self.success(
                f"Signal detection complete: {len(results['churn_signals'])} churn, "
                f"{len(results['expansion_signals'])} expansion, "
                f"{results['playbooks_triggered']} playbooks triggered",
                details=results,
                api_calls=api_calls,
                errors=errors
            )

        except Exception as e:
            logger.error(f"❌ Signal detection failed: {e}")
            return self.failure("Signal detection failed", error=str(e), api_calls=api_calls)
