#!/usr/bin/env python3
"""
CS Pulse Driver V3 — CLI for manifest-driven and scenario-based data loading.

V3 merges V2 extensions (phase windowing, validation, NarrativeTimelinePlanner)
into the canonical driver. This is the single entry point for all load operations.

Manifest mode (primary):
    python3 cs_pulse_driver.py --manifest manifests/novastar_dc2s.json

    Reads a curated manifest JSON, generates deterministic CSVs, uploads
    them via the onboarding API, and triggers process-data. Produces
    gold-reference demo data with named accounts, stakeholders, and
    realistic health trajectories.

Scenario mode (legacy):
    python3 cs_pulse_driver.py --scenarios 1,7,8 --customers 407

    Runs numbered load-test scenarios via the LoadDriver orchestrator.

Generate-only mode (offline):
    python3 cs_pulse_driver.py --manifest manifests/novastar_dc2s.json --generate-only /tmp/novastar/

    Generates CSVs to disk without uploading. Useful for inspection.

Phase mode (ROI testing):
    python3 cs_pulse_driver.py --manifest manifests/denali_dc2s.json --register --phase baseline
    python3 cs_pulse_driver.py --manifest manifests/denali_dc2s.json -c 420 --phase intervention
"""

__version__ = '3.0'

import argparse
import json
import logging
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

# Ensure load-driver root is in path
_root = str(Path(__file__).resolve().parent)
if _root not in sys.path:
    sys.path.insert(0, _root)

from client import CSPulseClient, create_authenticated_client

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.FileHandler('cs_pulse_driver.log'),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger('cs_pulse_driver')


# ═══════════════════════════════════════════════════════════════════════
# Manifest mode
# ═══════════════════════════════════════════════════════════════════════

def run_manifest(args):
    """
    Execute manifest-driven data load.

    Steps:
    1. Parse manifest JSON
    2. Optionally register a new customer (--register) then POST /api/onboarding/complete
    3. Generate CSVs from manifest
    4. Upload CSVs to onboarding API
    5. Trigger process-data
    6. Post-process validation (V3: merged from V2)
    """
    from scenarios.scenario_manifest import ManifestCSVGenerator

    manifest_path = Path(args.manifest)
    if not manifest_path.exists():
        logger.error(f"Manifest not found: {manifest_path}")
        sys.exit(1)

    with open(manifest_path) as f:
        manifest = json.load(f)

    customer_info = manifest['customer']
    logger.info(f"{'='*60}")
    logger.info(f"CS Pulse Driver V3 — Manifest Mode")
    logger.info(f"{'='*60}")
    logger.info(f"  Manifest:  {manifest_path.name}")
    logger.info(f"  Customer:  {customer_info['name']}")
    logger.info(f"  Vertical:  {customer_info.get('vertical', 'dc2_s')}")
    logger.info(f"  Accounts:  {len(manifest['accounts'])}")
    logger.info(f"  KPIs:      {manifest['kpis'].get('count', len(manifest['kpis'].get('codes', [])))}")
    logger.info(f"  Time:      {manifest['time_range']['start']} -> {manifest['time_range']['end']}")
    if args.phase:
        logger.info(f"  Phase:     {args.phase}")

    # ── Generate-only mode ──
    if args.generate_only:
        output_dir = args.generate_only
        logger.info(f"\n  Generate-only mode -> {output_dir}")
        gen = ManifestCSVGenerator(
            manifest_path=str(manifest_path),
            customer_id=args.customer_id or 0,
            seed=args.seed,
            phase=args.phase,
        )
        files = gen.generate_all(output_dir)
        logger.info(f"\n  Generated {len(files)} files:")
        for name in files:
            logger.info(f"    {name}")
        return

    # ── Online mode: need a server ──
    base_url = args.base_url
    password = args.password or os.getenv('CS_PULSE_ADMIN_PASSWORD', 'test123')
    cli_or_env_email = args.email or os.getenv('CS_PULSE_ADMIN_EMAIL', 'admin@sacme.com')

    # Registration creates the user for this email; login must use the same address.
    manifest_admin = (customer_info.get('admin_email') or '').strip()
    if args.email:
        email = args.email
    else:
        email = manifest_admin or cli_or_env_email
        if manifest_admin:
            logger.info(f"  Login/register user: {email} (manifest admin_email)")

    logger.info(f"  Server:    {base_url}")

    # Create or use existing customer
    customer_id = args.customer_id

    if args.register:
        logger.info("\n  Registering new customer...")
        reg_client = CSPulseClient(base_url=base_url, timeout=30)
        resp = reg_client.register_customer(
            company_name=customer_info['name'],
            admin_name=customer_info.get('admin_name', 'Admin'),
            email=email,
            password=password,
            vertical=customer_info.get('vertical', 'dc2_s'),
        )
        if not (resp and resp.get('customer_id')):
            logger.error(f"  Registration failed: {resp}")
            sys.exit(1)
        customer_id = int(resp['customer_id'])
        api_key = resp.get('api_key', '')
        logger.info(f"  Registered: customer_id={customer_id}")
        if api_key:
            logger.info(f"  API Key: {api_key}")
            logger.info(f"  ⚠️  Save this key — it is returned ONCE and required for MCP access.")

        # Login the reg_client so it has a session cookie for onboarding
        reg_client.email = email
        reg_client.password = password
        reg_client.customer_id = customer_id
        if not reg_client.login():
            logger.warning("  Post-registration login failed — trying onboarding without session")

        # Provision onboarding directory
        # num_accounts=0 in manifest mode: the accounts.csv will create
        # the real accounts. Passing num_accounts>0 creates placeholder
        # accounts (447001, 447002...) that diverge from manifest accounts.
        num_accounts = 0
        logger.info(
            f"  Provisioning onboarding (POST /api/onboarding/complete, "
            f"num_accounts={num_accounts})..."
        )
        complete = reg_client.complete_onboarding(
            customer_id=customer_id,
            customer_name=customer_info['name'],
            vertical=customer_info.get('vertical', 'dc2_s'),
            num_accounts=num_accounts,
            onboarding_mode='custom',
        )
        if not complete or not complete.get('success'):
            logger.error(
                f"  Onboarding complete failed (needed before CSV upload): {complete}"
            )
            sys.exit(1)
        logger.info(f"  Onboarding provisioned: {complete.get('message', 'ok')!r}")

    if args.extend and args.register:
        logger.error("  --extend and --register are mutually exclusive")
        sys.exit(1)

    if not customer_id:
        logger.error("  --customer-id required (or use --register to create new)")
        sys.exit(1)

    if args.extend:
        logger.info(f"  Mode:      EXTEND (adding {args.months} months to customer {customer_id})")

    # Authenticate — API key takes precedence over email/password
    api_key = getattr(args, 'api_key', None)
    client = CSPulseClient(
        base_url=base_url,
        email=email,
        password=password,
        api_key=api_key,
        customer_id=int(customer_id),
        timeout=60,
    )

    if not client.health_check():
        logger.error(f"  Server not reachable: {base_url}")
        sys.exit(1)

    # Pre-flight: check server uptime to catch stale processes
    try:
        import subprocess, re
        pids = subprocess.run(
            ["pgrep", "-f", "app_v3_minimal"],
            capture_output=True, text=True
        ).stdout.strip().split('\n')
        pids = [p for p in pids if p.strip()]
        if len(pids) > 1:
            logger.warning(f"  ⚠️  Multiple server processes detected (PIDs: {', '.join(pids)})")
            logger.warning(f"     Run: kill -9 {' '.join(pids)} && restart server")
            logger.warning(f"     Stale processes cause fixes to be invisible!")
        if pids:
            # Check how long the server has been running
            ps_out = subprocess.run(
                ["ps", "-o", "etime=", "-p", pids[0]],
                capture_output=True, text=True
            ).stdout.strip()
            if ps_out:
                logger.info(f"  Server PID {pids[0]}, uptime: {ps_out.strip()}")
                # Warn if server has been running for more than 2 hours
                parts = ps_out.strip().replace('-', ':').split(':')
                if len(parts) >= 3:  # HH:MM:SS or D-HH:MM:SS
                    hours = int(parts[-3]) if len(parts) == 3 else int(parts[-4]) * 24 + int(parts[-3])
                    if hours >= 2:
                        logger.warning(f"  ⚠️  Server has been running for {ps_out.strip()} — consider restarting to pick up code changes")
    except Exception:
        pass  # Non-fatal — pgrep may not exist on all platforms

    if not client.login():
        logger.error("  Login failed")
        sys.exit(1)

    # Auto-enable context graph for all driver-created customers
    try:
        client.enable_context_graph(int(customer_id))
        logger.info(f"  Context graph enabled for customer {customer_id}")
    except Exception as e:
        logger.warning(f"  Context graph toggle failed (non-fatal): {e}")

    # Run the manifest scenario (V3: includes validation)
    from scenarios.scenario_manifest import ScenarioManifest
    scenario_args = argparse.Namespace(
        manifest=str(manifest_path),
        customer_id=int(customer_id),
        seed=args.seed,
        phase=args.phase,
        validate_strict=args.validate_strict,
        validate_sample_size=args.validate_sample_size,
        health_tolerance=args.health_tolerance,
        extend=getattr(args, 'extend', False),
        extend_months=args.months,
        minimal=getattr(args, 'minimal', False),
        end_date=getattr(args, 'end_date', None),
        playbooks=getattr(args, 'playbooks', False),
    )
    scenario = ScenarioManifest(client=client, args=scenario_args)
    result = scenario.run()

    # Print summary
    logger.info(f"\n{'='*60}")
    logger.info(f"  Result: {result.get('status', 'unknown').upper()}")
    logger.info(f"  {result.get('message', '')}")
    if result.get('duration_seconds'):
        logger.info(f"  Duration: {result['duration_seconds']:.1f}s")
    if result.get('errors'):
        logger.warning(f"  Warnings: {len(result['errors'])}")
        for err in result['errors']:
            logger.warning(f"    - {err}")
    logger.info(f"{'='*60}")

    if result.get('status') != 'success':
        sys.exit(1)


# ═══════════════════════════════════════════════════════════════════════
# Scenario mode (legacy — delegates to LoadDriver)
# ═══════════════════════════════════════════════════════════════════════

def run_scenarios(args):
    """Run numbered scenarios via LoadDriver (existing behavior)."""
    # Import the LoadDriver class inline — it lives in scenarios or is
    # embedded below for legacy support.
    from _legacy_driver import LoadDriver

    scenario_ids = [s.strip() for s in args.scenarios.split(',')]
    customer_ids = [int(c.strip()) for c in args.customers.split(',')]

    driver = LoadDriver(base_url=args.base_url, results_dir=args.results_dir)
    driver.run_all(scenario_ids, customer_ids, args)

    logger.info("\nLoad test complete!")
    logger.info(f"Results: {args.results_dir}/LOAD_TEST_RESULTS.md")


# ═══════════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description='CS Pulse Driver V3 — manifest-driven and scenario-based data loading',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Load Denali gold reference (register new customer)
  python3 cs_pulse_driver.py --manifest manifests/denali_dc2s.json --register

  # Load into existing customer
  python3 cs_pulse_driver.py --manifest manifests/novastar_dc2s.json --customer-id 407

  # Generate CSVs only (no upload)
  python3 cs_pulse_driver.py --manifest manifests/novastar_dc2s.json --generate-only /tmp/novastar/

  # Phase-based ROI loading
  python3 cs_pulse_driver.py --manifest manifests/denali_dc2s.json --register --phase baseline
  python3 cs_pulse_driver.py --manifest manifests/denali_dc2s.json -c 420 --phase intervention

  # Run numbered scenarios (legacy mode)
  python3 cs_pulse_driver.py --scenarios 1,7,8 --customers 407
        """,
    )

    # ── Manifest mode args ──
    parser.add_argument(
        '--manifest', '-m',
        help='Path to manifest JSON file (e.g. manifests/novastar_dc2s.json)',
    )
    parser.add_argument(
        '--generate-only', '-g',
        metavar='DIR',
        help='Generate CSVs to directory without uploading (offline mode)',
    )
    parser.add_argument(
        '--register',
        action='store_true',
        help='Register a new customer from manifest before loading data',
    )
    parser.add_argument(
        '--phase',
        choices=['baseline', 'intervention'],
        default=None,
        help='Manifest time window: baseline=first 2/3, intervention=last 1/3 with recovery',
    )
    parser.add_argument(
        '--extend',
        action='store_true',
        help='Extend existing customer data by generating next N months (use with -c and --months)',
    )
    parser.add_argument(
        '--end-date',
        help='Override manifest end date (YYYY-MM-DD). Truncates KPI generation to this date. '
             'Use for 4-phase testing: --end-date 2025-09-30 for 3-month baseline.',
    )
    parser.add_argument(
        '--minimal',
        action='store_true',
        help='Upload only account_details.csv + kpi_measurements.csv (2-CSV mode for LLM inference). '
             'Context graph CSVs (signals, decisions, outcomes, edges, engagement) are NOT uploaded — '
             'LLM Tier1 infers the context graph from KPI trajectories + account details.',
    )
    parser.add_argument(
        '--playbooks',
        action='store_true',
        help='Execute and close playbooks on at-risk accounts after process-data. '
             'Uses arc→playbook mapping to trigger interventions, then closes with '
             'churn-model revenue attribution. Makes NRR move and ROI accumulate.',
    )

    # ── Validation args (V3: merged from V2) ──
    parser.add_argument(
        '--validate-strict', dest='validate_strict',
        action='store_true', default=True,
        help='Enable strict post-process validation (default: on)',
    )
    parser.add_argument(
        '--no-validate-strict', dest='validate_strict',
        action='store_false',
        help='Disable strict post-process validation',
    )
    parser.add_argument(
        '--validate-sample-size', type=int, default=5,
        help='Number of accounts to sample for validation (default: 5)',
    )
    parser.add_argument(
        '--health-tolerance', type=int, default=1,
        help='Tolerance for health distribution drift (default: 1)',
    )

    # ── Scenario mode args ──
    parser.add_argument(
        '--scenarios',
        help='Comma-separated scenario IDs for scenario mode (e.g. 1,7,8)',
    )
    parser.add_argument(
        '--customers',
        default='1',
        help='Comma-separated customer IDs for scenario mode',
    )
    parser.add_argument(
        '--results-dir',
        default='results',
        help='Directory for scenario test results',
    )

    # ── Common args ──
    parser.add_argument(
        '--customer-id', '-c',
        type=int,
        help='Target customer ID',
    )
    parser.add_argument(
        '--base-url', '-u',
        default=os.getenv('CS_PULSE_BASE_URL', 'http://localhost:5059'),
        help='CS Pulse backend URL (default: $CS_PULSE_BASE_URL or localhost:5059)',
    )
    parser.add_argument(
        '--email',
        help='Admin email (default: $CS_PULSE_ADMIN_EMAIL)',
    )
    parser.add_argument(
        '--password',
        help='Admin password (default: $CS_PULSE_ADMIN_PASSWORD)',
    )
    parser.add_argument(
        '--api-key',
        help='API key for Bearer auth (alternative to email/password). '
             'Use with --customer-id to skip login entirely.',
    )
    parser.add_argument(
        '--seed',
        type=int,
        default=42,
        help='Random seed for reproducible data (default: 42)',
    )
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable debug logging',
    )
    parser.add_argument(
        '--version', action='version',
        version=f'CS Pulse Driver V{__version__}',
    )

    # ── Scenario-specific args (passed through) ──
    parser.add_argument('--arc-id', default='arc_expansion_champion')
    parser.add_argument('--months', type=int, default=6)
    parser.add_argument('--improvement', type=float, default=2.5)
    parser.add_argument('--num-accounts', type=int, default=None)
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument(
        '--signal-360',
        action='store_true',
        help='Run Signal Engine 360 fidelity test after load. '
             'Requires --api-key and --customer-id. Submits CSV signals '
             'as realistic email/slack/transcript, validates enrichment matches.',
    )
    parser.add_argument(
        '--signal-360-wait', type=int, default=60,
        help='Seconds to wait for signal enrichment (default: 60)',
    )

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Route to correct mode
    if args.manifest:
        run_manifest(args)
    elif args.scenarios:
        run_scenarios(args)
    else:
        parser.print_help()
        print("\nError: specify --manifest or --scenarios")
        sys.exit(1)

    # Signal 360 fidelity test (runs after load if requested)
    if getattr(args, 'signal_360', False):
        api_key = getattr(args, 'api_key', None)
        customer_id = getattr(args, 'customer_id', None)
        base_url = getattr(args, 'base_url', None)
        if not all([api_key, customer_id, base_url]):
            logger.error("--signal-360 requires --api-key, --customer-id, and --base-url")
            sys.exit(1)
        from generators.signal_360_generator import run_signal_360
        result = run_signal_360(
            customer_id=int(customer_id),
            base_url=base_url,
            api_key=api_key,
            seed=getattr(args, 'seed', 42),
            enrichment_wait_s=getattr(args, 'signal_360_wait', 60),
            verbose=getattr(args, 'verbose', False),
        )
        if result.get('match_rate_pct', 0) < 50:
            logger.warning("Signal 360: LOW match rate %.1f%%", result.get('match_rate_pct', 0))
            sys.exit(1)


if __name__ == '__main__':
    main()
