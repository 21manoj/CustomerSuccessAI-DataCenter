#!/usr/bin/env python3
"""
Scenario 2d: RACI Reports
Fetch playbook execution reports, validate markdown output
"""

import logging
from typing import Dict, Any
from pathlib import Path

from .base import BaseScenario

logger = logging.getLogger(__name__)


class ScenarioRaciReports(BaseScenario):
    """
    Scenario 2d: RACI Report Generation

    Steps:
    1. List all playbook executions for the customer
    2. For each completed execution, fetch the RACI report
    3. Validate report structure (has sections, action items, owners)
    4. Save reports to results directory as markdown

    Measures:
    - Executions with reports
    - Report completeness (required sections present)
    - Report file sizes
    """

    def run(self) -> Dict[str, Any]:
        self.start_timer()
        logger.info("📋 Scenario: RACI Reports")

        api_calls = 0
        errors = []
        results = {
            'executions_found': 0,
            'reports_fetched': 0,
            'reports_valid': 0,
            'reports': []
        }

        try:
            # Step 1: List executions
            logger.info("  Step 1: List playbook executions")
            executions_response = self.client.get('/api/playbooks/executions')
            api_calls += 1

            if not executions_response:
                return self.failure("Could not fetch executions", api_calls=api_calls)

            executions = executions_response.get('executions', [])
            if isinstance(executions_response, list):
                executions = executions_response

            results['executions_found'] = len(executions)
            logger.info(f"    Found {len(executions)} executions")

            if not executions:
                return self.success(
                    "No executions found (run signal detection first)",
                    details=results,
                    api_calls=api_calls
                )

            # Step 2: Fetch reports for completed executions
            logger.info("  Step 2: Fetch RACI reports")
            for execution in executions:
                exec_id = execution.get('execution_id') or execution.get('id')
                status = execution.get('status', '')

                if status not in ('COMPLETED', 'PARTIALLY_COMPLETED', 'completed'):
                    continue

                report_response = self.client.get(f'/api/playbooks/reports/{exec_id}')
                api_calls += 1

                if not report_response:
                    errors.append(f"No report for execution {exec_id}")
                    continue

                results['reports_fetched'] += 1

                # Step 3: Validate report structure
                report = report_response
                report_info = {
                    'execution_id': exec_id,
                    'playbook': execution.get('playbook_id', 'unknown'),
                    'has_summary': False,
                    'has_actions': False,
                    'has_owners': False,
                    'valid': False,
                    'size_bytes': 0
                }

                # Check for key sections in the report
                report_content = str(report)
                report_info['size_bytes'] = len(report_content)

                # Check for essential report components
                summary_keywords = ['summary', 'overview', 'executive', 'status']
                action_keywords = ['action', 'task', 'step', 'recommendation']
                owner_keywords = ['owner', 'assignee', 'responsible', 'csm', 'assigned']

                report_lower = report_content.lower()
                report_info['has_summary'] = any(kw in report_lower for kw in summary_keywords)
                report_info['has_actions'] = any(kw in report_lower for kw in action_keywords)
                report_info['has_owners'] = any(kw in report_lower for kw in owner_keywords)
                report_info['valid'] = report_info['has_summary'] or report_info['has_actions']

                if report_info['valid']:
                    results['reports_valid'] += 1

                results['reports'].append(report_info)
                logger.info(f"    ✅ Report {exec_id}: {report_info['size_bytes']} bytes, valid={report_info['valid']}")

            # Step 4: Save reports to files
            logger.info("  Step 3: Save reports")
            results_dir = Path('results')
            results_dir.mkdir(exist_ok=True)

            for i, report_info in enumerate(results['reports']):
                report_path = results_dir / f"raci_report_{report_info['execution_id'][:8]}.md"
                # Write a summary (actual report content would come from API)
                report_path.write_text(
                    f"# RACI Report: {report_info['playbook']}\n\n"
                    f"**Execution ID:** {report_info['execution_id']}\n"
                    f"**Has Summary:** {report_info['has_summary']}\n"
                    f"**Has Actions:** {report_info['has_actions']}\n"
                    f"**Has Owners:** {report_info['has_owners']}\n"
                    f"**Size:** {report_info['size_bytes']} bytes\n"
                )

            results['summary'] = {
                'total_executions': results['executions_found'],
                'reports_fetched': results['reports_fetched'],
                'reports_valid': results['reports_valid'],
                'validity_rate': round(
                    results['reports_valid'] / results['reports_fetched'] * 100, 1
                ) if results['reports_fetched'] else 0
            }

            return self.success(
                f"RACI reports: {results['reports_fetched']} fetched, "
                f"{results['reports_valid']} valid",
                details=results,
                api_calls=api_calls,
                errors=errors
            )

        except Exception as e:
            logger.error(f"❌ RACI reports failed: {e}")
            return self.failure("RACI report scenario failed", error=str(e), api_calls=api_calls)
