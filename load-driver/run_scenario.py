#!/usr/bin/env python3
"""
Run a single load driver scenario and output results to {customer_id}-test_results.md

Usage:
    python3 run_scenario.py --scenario 1 --customer-id 100
    python3 run_scenario.py --scenario 2a --customer-id 100
"""

import argparse
import json
import logging
import os
import sys
import time
from datetime import datetime
from pathlib import Path

# Add load-driver to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from client import CSPulseClient

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

SCENARIO_MAP = {
    '1': ('onboarding', 'ScenarioOnboarding', 'Customer Onboarding'),
    '2a': ('kpi_simulation', 'ScenarioKpiSimulation', 'KPI Simulation (12-month drift)'),
    '2b': ('rag_queries', 'ScenarioRagQueries', 'RAG Queries'),
    '2c': ('signal_detection', 'ScenarioSignalDetection', 'Signal Detection'),
    '2d': ('raci_reports', 'ScenarioRaciReports', 'RACI Reports'),
    '2e': ('churn_lifecycle', 'ScenarioChurnLifecycle', 'Churn Lifecycle'),
    '3': ('tenant_isolation', 'ScenarioTenantIsolation', 'Tenant Isolation'),
    '4': ('cleanup', 'ScenarioCleanup', 'Customer Cleanup'),
    '5': ('roi_power_of_1', 'ScenarioRoiPowerOf1', 'ROI Power-of-1'),
    '6': ('n8n_workflow', 'ScenarioN8nWorkflow', 'N8N Workflow Integration'),
}


def load_scenario_class(scenario_id):
    """Dynamically import and return the scenario class"""
    if scenario_id not in SCENARIO_MAP:
        raise ValueError(f"Unknown scenario: {scenario_id}. Valid: {list(SCENARIO_MAP.keys())}")

    module_name, class_name, _ = SCENARIO_MAP[scenario_id]
    module = __import__(f'scenarios.scenario_{module_name}', fromlist=[class_name])
    return getattr(module, class_name)


def generate_results_md(customer_id, scenario_id, scenario_title, result, base_url):
    """Generate markdown test results file"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    status_emoji = "PASS" if result.get('status') == 'success' else "FAIL"
    status_icon = "✅" if result.get('status') == 'success' else "❌"

    md = []
    md.append(f"# Test Results — Customer {customer_id}")
    md.append(f"")
    md.append(f"**Generated:** {timestamp}")
    md.append(f"**Backend:** {base_url}")
    md.append(f"**Customer ID:** {customer_id}")
    md.append(f"")
    md.append(f"---")
    md.append(f"")
    md.append(f"## Scenario {scenario_id}: {scenario_title}")
    md.append(f"")
    md.append(f"| Field | Value |")
    md.append(f"|-------|-------|")
    md.append(f"| **Result** | {status_icon} **{status_emoji}** |")
    md.append(f"| **Message** | {result.get('message', 'N/A')} |")
    md.append(f"| **Duration** | {result.get('duration_seconds', 0):.2f}s |")
    md.append(f"| **API Calls** | {result.get('api_calls', 'N/A')} |")

    if result.get('errors'):
        md.append(f"| **Errors** | {len(result['errors'])} |")
    md.append(f"")

    # Details section
    details = result.get('details', {})
    if details:
        md.append(f"### Details")
        md.append(f"")
        md.append(f"| Key | Value |")
        md.append(f"|-----|-------|")
        for key, value in details.items():
            if isinstance(value, (list, dict)):
                md.append(f"| {key} | `{json.dumps(value)[:100]}` |")
            else:
                md.append(f"| {key} | {value} |")
        md.append(f"")

    # Errors section
    errors = result.get('errors', [])
    if errors:
        md.append(f"### Errors")
        md.append(f"")
        for i, err in enumerate(errors, 1):
            md.append(f"{i}. {err}")
        md.append(f"")

    # Test results (for scenarios with individual tests)
    test_results = details.get('test_results', [])
    if test_results:
        md.append(f"### Individual Tests")
        md.append(f"")
        md.append(f"| # | Test | Result | Detail |")
        md.append(f"|---|------|--------|--------|")
        for i, t in enumerate(test_results, 1):
            icon = "✅" if t.get('passed') else "❌"
            detail = str(t.get('detail', ''))[:60]
            md.append(f"| {i} | {t.get('test', '?')} | {icon} | {detail} |")
        md.append(f"")

    # Raw JSON
    md.append(f"### Raw Result (JSON)")
    md.append(f"")
    md.append(f"```json")
    md.append(json.dumps(result, indent=2, default=str))
    md.append(f"```")
    md.append(f"")

    return '\n'.join(md)


def main():
    parser = argparse.ArgumentParser(description='Run a single load driver scenario')
    parser.add_argument('--scenario', '-s', required=True, help='Scenario ID (1, 2a, 2b, ...)')
    parser.add_argument('--customer-id', '-c', type=int, default=100, help='Customer ID')
    parser.add_argument('--base-url', default='http://localhost:5059', help='Backend URL')
    parser.add_argument('--email', default='admin@test.com', help='Admin email for auth')
    parser.add_argument('--password', default='password', help='Admin password for auth')
    parser.add_argument('--output-dir', default='.', help='Output directory for results')
    parser.add_argument('--dry-run', action='store_true', help='Preview-only mode (scenario 4: show what would be deleted)')
    parser.add_argument('--num-accounts', type=int, default=None, help='Number of accounts to create (scenario 1, default: 3)')
    parser.add_argument('--verbose', '-v', action='store_true', help='Debug logging')

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    scenario_id = args.scenario
    customer_id = args.customer_id
    _, _, scenario_title = SCENARIO_MAP.get(scenario_id, (None, None, 'Unknown'))

    logger.info(f"=" * 60)
    logger.info(f"Running Scenario {scenario_id}: {scenario_title}")
    logger.info(f"Customer ID: {customer_id}")
    logger.info(f"Backend: {args.base_url}")
    logger.info(f"=" * 60)

    # Step 1: Create client and check health
    client = CSPulseClient(
        base_url=args.base_url,
        email=args.email,
        password=args.password,
        customer_id=customer_id
    )

    if not client.health_check():
        logger.error("Backend health check failed. Is the server running?")
        sys.exit(1)

    # Step 2: Login (some scenarios need auth, onboarding may not)
    login_ok = client.login()
    if not login_ok:
        logger.warning("Login failed — proceeding anyway (onboarding registers a new user)")
        # For onboarding, the scenario itself handles registration
        # Mark client as "authenticated" so it can make calls
        client._authenticated = True

    # Step 3: Load and run scenario
    logger.info(f"Loading scenario class...")
    scenario_class = load_scenario_class(scenario_id)
    scenario = scenario_class(client=client, args=args)

    logger.info(f"Executing scenario...")
    result = scenario.run()

    # Step 4: Generate results markdown
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / f"{customer_id}-test_results.md"

    md_content = generate_results_md(customer_id, scenario_id, scenario_title, result, args.base_url)
    output_file.write_text(md_content)

    logger.info(f"")
    logger.info(f"{'=' * 60}")
    status = result.get('status', 'unknown')
    icon = "✅" if status == 'success' else "❌"
    logger.info(f"{icon} Scenario {scenario_id}: {status.upper()}")
    logger.info(f"   Message: {result.get('message', 'N/A')}")
    logger.info(f"   Duration: {result.get('duration_seconds', 0):.2f}s")
    logger.info(f"   Results: {output_file}")
    logger.info(f"{'=' * 60}")

    return 0 if status == 'success' else 1


if __name__ == '__main__':
    sys.exit(main())
