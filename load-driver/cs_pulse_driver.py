#!/usr/bin/env python3
"""
CS Pulse Driver — CLI for manifest-driven and scenario-based data loading.

Manifest mode (primary):
    python3 cs_pulse_driver.py --manifest manifests/novastar_dc2s.json

    Reads a curated manifest JSON, generates deterministic CSVs, uploads
    them via the onboarding API, and triggers process-data. Produces
    gold-reference demo data with named accounts, stakeholders, and
    realistic health trajectories.

Scenario mode (existing):
    python3 cs_pulse_driver.py --scenarios 1,7,8 --customers 407

    Runs numbered load-test scenarios via the LoadDriver orchestrator.

Generate-only mode (offline):
    python3 cs_pulse_driver.py --manifest manifests/novastar_dc2s.json --generate-only /tmp/novastar/

    Generates CSVs to disk without uploading. Useful for inspection.
"""

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
       (register only creates the DB row; complete provisions the upload directory)
    3. Generate CSVs from manifest
    4. Upload CSVs to onboarding API
    5. Trigger process-data
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
    logger.info(f"CS Pulse Driver — Manifest Mode")
    logger.info(f"{'='*60}")
    logger.info(f"  Manifest:  {manifest_path.name}")
    logger.info(f"  Customer:  {customer_info['name']}")
    logger.info(f"  Vertical:  {customer_info.get('vertical', 'dc2_s')}")
    logger.info(f"  Accounts:  {len(manifest['accounts'])}")
    logger.info(f"  KPIs:      {manifest['kpis']['count']}")
    logger.info(f"  Time:      {manifest['time_range']['start']} → {manifest['time_range']['end']}")

    # ── Generate-only mode ──
    if args.generate_only:
        output_dir = args.generate_only
        logger.info(f"\n  Generate-only mode → {output_dir}")
        gen = ManifestCSVGenerator(
            manifest_path=str(manifest_path),
            customer_id=args.customer_id or 0,
            seed=args.seed,
        )
        files = gen.generate_all(output_dir)
        logger.info(f"\n  Generated {len(files)} files:")
        for name, path in files.items():
            logger.info(f"    {name}")
        return

    # ── Online mode: need a server ──
    base_url = args.base_url
    email = args.email or os.getenv('CS_PULSE_ADMIN_EMAIL', 'admin@sacme.com')
    password = args.password or os.getenv('CS_PULSE_ADMIN_PASSWORD', 'test123')

    logger.info(f"  Server:    {base_url}")

    # Create or use existing customer
    customer_id = args.customer_id

    if args.register:
        logger.info("\n  Registering new customer...")
        client = CSPulseClient(base_url=base_url, timeout=30)
        resp = client.register_customer(
            company_name=customer_info['name'],
            admin_name=customer_info.get('admin_name', 'Admin'),
            email=customer_info.get('admin_email', email),
            password=password,
            vertical=customer_info.get('vertical', 'dc2_s'),
        )
        if resp and resp.get('customer_id'):
            customer_id = resp['customer_id']
            logger.info(f"  Registered: customer_id={customer_id}")
        else:
            logger.error(f"  Registration failed: {resp}")
            sys.exit(1)

        # /api/register only inserts the customer + user; /api/onboarding/upload requires
        # the per-customer directory created by /api/onboarding/complete.
        num_accounts = len(manifest.get('accounts', [])) or 3
        logger.info(
            f"  Provisioning onboarding (POST /api/onboarding/complete, "
            f"num_accounts={num_accounts})..."
        )
        complete = client.complete_onboarding(
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

    if not customer_id:
        logger.error("  --customer-id required (or use --register to create new)")
        sys.exit(1)

    # Authenticate
    client = CSPulseClient(
        base_url=base_url,
        email=email,
        password=password,
        customer_id=customer_id,
        timeout=60,
    )

    if not client.health_check():
        logger.error(f"  Server not reachable: {base_url}")
        sys.exit(1)

    if not client.login():
        logger.error("  Login failed")
        sys.exit(1)

    # Run the manifest scenario
    scenario_args = argparse.Namespace(
        manifest=str(manifest_path),
        customer_id=customer_id,
        seed=args.seed,
    )

    from scenarios.scenario_manifest import ScenarioManifest
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
# Scenario mode (delegates to existing LoadDriver)
# ═══════════════════════════════════════════════════════════════════════

def run_scenarios(args):
    """Run numbered scenarios via LoadDriver (existing behavior)."""
    from driver import LoadDriver

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
        description='CS Pulse Driver — manifest-driven and scenario-based data loading',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Load NovaStar gold reference into customer 407
  python3 cs_pulse_driver.py --manifest manifests/novastar_dc2s.json --customer-id 407

  # Register new customer and load manifest
  python3 cs_pulse_driver.py --manifest manifests/novastar_dc2s.json --register

  # Generate CSVs only (no upload)
  python3 cs_pulse_driver.py --manifest manifests/novastar_dc2s.json --generate-only /tmp/novastar/

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

    # ── Scenario-specific args (passed through) ──
    parser.add_argument('--arc-id', default='arc_expansion_champion')
    parser.add_argument('--months', type=int, default=6)
    parser.add_argument('--improvement', type=float, default=2.5)
    parser.add_argument('--num-accounts', type=int, default=None)
    parser.add_argument('--dry-run', action='store_true')

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


if __name__ == '__main__':
    main()
