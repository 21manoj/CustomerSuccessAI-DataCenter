#!/usr/bin/env python3
"""
Load Driver Orchestrator
Manages scenario execution, timing, and result collection
"""

import argparse
import logging
import os
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from dotenv import load_dotenv

from client import CSPulseClient, create_authenticated_client

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.FileHandler('load_driver.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class LoadDriver:
    """
    Test load orchestrator
    Executes scenarios in order, collects results, generates report
    """

    # Scenario order matters: run cleanup (4) last so customer/user are not deleted
    # before ROI (5) and data_ingestion (7). Recommended: 1,2a,2b,2c,2d,2e,3,5,7,8,4
    SCENARIOS = {
        '1': 'onboarding',
        '2a': 'kpi_simulation',
        '2b': 'rag_queries',
        '2c': 'signal_detection',
        '2d': 'raci_reports',
        '2e': 'churn_lifecycle',
        '3': 'tenant_isolation',
        '4': 'cleanup',
        '5': 'roi_power_of_1',
        '6': 'n8n_workflow',
        '7': 'data_ingestion',
        '8': 'context_graph',
        '9': 'roi_simulation'
    }

    def __init__(
        self,
        base_url: str = None,
        admin_email: str = None,
        admin_password: str = None,
        results_dir: str = None
    ):
        """Initialize load driver"""
        self.base_url = base_url or os.getenv('CS_PULSE_BASE_URL', 'http://localhost:5059')
        self.admin_email = admin_email or os.getenv('CS_PULSE_ADMIN_EMAIL', 'admin@sacme.com')
        self.admin_password = admin_password or os.getenv('CS_PULSE_ADMIN_PASSWORD', 'test123')
        self.results_dir = Path(results_dir or 'results')
        self.results_dir.mkdir(exist_ok=True)

        self.clients: Dict[int, CSPulseClient] = {}
        self.results = {
            'timestamp': datetime.now().isoformat(),
            'base_url': self.base_url,
            'scenarios': {},
            'summary': {}
        }

        logger.info(f"🚀 Load Driver initialized: {self.base_url}")

    def get_or_create_client(self, customer_id: int) -> Optional[CSPulseClient]:
        """Get cached client or create + authenticate new one"""
        if customer_id in self.clients:
            return self.clients[customer_id]

        logger.info(f"📝 Creating authenticated client for customer {customer_id}")

        # Register + login OR login to existing customer
        client = create_authenticated_client(
            self.base_url,
            self.admin_email,
            self.admin_password,
            customer_id=customer_id
        )

        if not client:
            logger.error(f"❌ Failed to create client for customer {customer_id}")
            return None

        self.clients[customer_id] = client
        return client

    def run_scenario(
        self,
        scenario_name: str,
        customer_ids: List[int],
        args: argparse.Namespace
    ) -> Dict[str, any]:
        """
        Execute a single scenario

        Returns:
            Scenario results dict
        """
        logger.info(f"\n{'='*60}")
        logger.info(f"📋 Scenario: {scenario_name.upper()}")
        logger.info(f"{'='*60}")

        scenario_result = {
            'name': scenario_name,
            'status': 'pending',
            'start_time': datetime.now().isoformat(),
            'customers': customer_ids,
            'details': {}
        }

        try:
            # Import scenario module dynamically
            scenario_module = __import__(
                f'scenarios.scenario_{scenario_name}',
                fromlist=[f'Scenario{scenario_name.title().replace("_", "")}']
            )

            # Get scenario class
            class_name = ''.join(word.title() for word in scenario_name.split('_'))
            scenario_class = getattr(scenario_module, f'Scenario{class_name}')

            # Run scenario for each customer
            for customer_id in customer_ids:
                client = self.get_or_create_client(customer_id)
                if not client:
                    logger.error(f"⚠️  Skipping customer {customer_id}: client creation failed")
                    continue

                logger.info(f"  Customer {customer_id}: {scenario_name.upper()}")

                scenario = scenario_class(client=client, args=args)
                result = scenario.run()

                scenario_result['details'][customer_id] = result

            scenario_result['status'] = 'completed'
            scenario_result['end_time'] = datetime.now().isoformat()

            logger.info(f"✅ Scenario {scenario_name} completed")

        except ModuleNotFoundError:
            logger.error(f"❌ Scenario module not found: scenario_{scenario_name}")
            scenario_result['status'] = 'failed'
            scenario_result['error'] = 'Module not found'
        except Exception as e:
            logger.error(f"❌ Scenario {scenario_name} failed: {e}")
            scenario_result['status'] = 'failed'
            scenario_result['error'] = str(e)

        return scenario_result

    def run_all(self, scenario_ids: List[str], customer_ids: List[int], args: argparse.Namespace):
        """Execute all requested scenarios in order"""
        logger.info(f"🎯 Running scenarios: {', '.join(scenario_ids)}")
        logger.info(f"👥 For customers: {', '.join(map(str, customer_ids))}")

        for scenario_id in scenario_ids:
            scenario_name = self.SCENARIOS.get(scenario_id)
            if not scenario_name:
                logger.warning(f"⚠️  Unknown scenario: {scenario_id}")
                continue

            result = self.run_scenario(scenario_name, customer_ids, args)
            self.results['scenarios'][scenario_name] = result

        self.generate_report()

    def generate_report(self):
        """Generate test results markdown report"""
        report_path = self.results_dir / 'LOAD_TEST_RESULTS.md'

        logger.info(f"📄 Generating report: {report_path}")

        # Build markdown
        md_lines = [
            "# Load Test Results",
            f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"**Base URL:** {self.results['base_url']}",
            "",
            "## Executive Summary",
            "",
        ]

        # Count scenarios
        total_scenarios = len(self.results['scenarios'])
        completed = sum(1 for s in self.results['scenarios'].values() if s['status'] == 'completed')
        failed = sum(1 for s in self.results['scenarios'].values() if s['status'] == 'failed')

        md_lines.extend([
            f"- **Total Scenarios:** {total_scenarios}",
            f"- **Completed:** {completed}",
            f"- **Failed:** {failed}",
            f"- **Success Rate:** {completed/total_scenarios*100:.1f}%" if total_scenarios > 0 else "- **Success Rate:** N/A",
            "",
            "## Scenario Results",
            "",
        ])

        # Details per scenario
        for scenario_name, result in self.results['scenarios'].items():
            status_emoji = "✅" if result['status'] == 'completed' else "❌"
            md_lines.append(f"### {status_emoji} {scenario_name.replace('_', ' ').title()}")
            md_lines.append("")
            md_lines.append(f"- **Status:** {result['status'].upper()}")
            md_lines.append(f"- **Start:** {result.get('start_time', 'N/A')}")
            md_lines.append(f"- **End:** {result.get('end_time', 'N/A')}")
            if 'error' in result:
                md_lines.append(f"- **Error:** {result['error']}")
            md_lines.append("")

            # Customer details
            if result['details']:
                for customer_id, customer_result in result['details'].items():
                    md_lines.append(f"#### Customer {customer_id}")
                    if isinstance(customer_result, dict):
                        for key, value in customer_result.items():
                            if key not in ['detailed_results', 'logs']:
                                md_lines.append(f"- {key}: {value}")
                    md_lines.append("")

        md_lines.extend([
            "---",
            "",
            "## Raw Results (JSON)",
            "",
            "```json",
            json.dumps(self.results, indent=2),
            "```"
        ])

        # Write report
        report_path.write_text('\n'.join(md_lines))
        logger.info(f"📝 Report written to {report_path}")

        # Also save raw JSON
        json_path = self.results_dir / 'LOAD_TEST_RESULTS.json'
        json_path.write_text(json.dumps(self.results, indent=2))
        logger.info(f"📊 Raw results written to {json_path}")


def main():
    """Entry point for load driver"""
    parser = argparse.ArgumentParser(
        description='CS Pulse Load Driver - Non-intrusive E2E testing'
    )
    parser.add_argument(
        '--scenarios',
        default='1,2a,2b,2c,2d,2e,3,4,5,6,7',
        help='Comma-separated scenario IDs (1,2a,2b,2c,2d,2e,3,4,5,6,7)'
    )
    parser.add_argument(
        '--customers',
        default='1,2,3',
        help='Comma-separated customer IDs (e.g., 1,2,3)'
    )
    parser.add_argument(
        '--base-url',
        default=os.getenv('CS_PULSE_BASE_URL', 'http://localhost:5059'),
        help='CS Pulse backend URL'
    )
    parser.add_argument(
        '--results-dir',
        default='results',
        help='Directory for test results'
    )
    parser.add_argument(
        '--num-accounts',
        type=int,
        default=None,
        help='Number of accounts per customer (scenario 1, default: 3)'
    )
    parser.add_argument(
        '--arc-id',
        default='arc_expansion_champion',
        help='Story arc ID for scenario 8 (default: arc_expansion_champion)'
    )
    parser.add_argument(
        '--months',
        type=int,
        default=6,
        help='Months to simulate (scenario 9, default: 6)'
    )
    parser.add_argument(
        '--improvement',
        type=float,
        default=2.5,
        help='Total improvement %% (scenario 9, default: 2.5)'
    )
    parser.add_argument(
        '--seed',
        type=int,
        default=None,
        help='Random seed for reproducible data generation'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Run without making changes (preview only)'
    )
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable debug logging'
    )

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Parse scenarios and customers
    scenario_ids = [s.strip() for s in args.scenarios.split(',')]
    customer_ids = [int(c.strip()) for c in args.customers.split(',')]

    # Run driver
    driver = LoadDriver(base_url=args.base_url, results_dir=args.results_dir)
    driver.run_all(scenario_ids, customer_ids, args)

    logger.info("\n🎉 Load test complete!")
    logger.info(f"Results: {driver.results_dir}/LOAD_TEST_RESULTS.md")


if __name__ == '__main__':
    main()
