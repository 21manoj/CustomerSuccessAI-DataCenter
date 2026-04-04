"""
CLI entry point for the Simulation Engine.

Usage:
    # Single customer, 4 phases
    python3 simulation_engine.py --customer-id 27 --email admin@x.io --password test123 \
        --phases 4 --base-url http://54.89.77.21

    # Multiple customers in parallel
    python3 simulation_engine.py \
        --customers '27:admin@x.io:test123,28:admin@y.io:test123' \
        --phases 4 --parallel 5 --base-url http://54.89.77.21
"""

import argparse
import json
import logging
import sys
import os

# Ensure load-driver root is on path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def main():
    parser = argparse.ArgumentParser(
        description='CS Pulse Simulation Engine — stateful, phase-aware data injection',
    )

    # Customer targeting
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--customer-id', type=int, help='Single customer ID')
    group.add_argument('--customers', type=str,
                       help='Comma-separated customer specs: "id:email:password,..."')

    # Auth (for single customer)
    parser.add_argument('--email', type=str, help='Admin email (for --customer-id)')
    parser.add_argument('--password', type=str, default='test123', help='Admin password')

    # Simulation params
    parser.add_argument('--phases', type=int, default=4, help='Number of phases (default 4)')
    parser.add_argument('--phase', type=int, help='Run single phase N only')
    parser.add_argument('--weeks-per-phase', type=int, default=4, help='Weeks per phase (default 4)')
    parser.add_argument('--gap-seconds', type=int, default=30, help='Gap between phases (default 30)')

    # Server
    parser.add_argument('--base-url', type=str, required=True, help='CS Pulse base URL')
    parser.add_argument('--vertical', type=str, default='saas_premium',
                        help='Vertical (default saas_premium)')
    parser.add_argument('--kpi-codes', type=str,
                        help='Comma-separated KPI codes (default: Starter 9)')

    # Concurrency
    parser.add_argument('--parallel', type=int, default=5, help='Max concurrent customers (default 5)')
    parser.add_argument('--seed', type=int, default=42, help='Random seed (default 42)')

    # Output
    parser.add_argument('--verbose', '-v', action='store_true', help='Debug logging')
    parser.add_argument('--output', type=str, help='Write results JSON to file')

    args = parser.parse_args()

    # Setup logging
    level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
        datefmt='%H:%M:%S',
    )

    # Parse KPI codes
    kpi_codes = None
    if args.kpi_codes:
        kpi_codes = [k.strip() for k in args.kpi_codes.split(',')]

    # Build customer list
    customers = []
    if args.customer_id:
        if not args.email:
            parser.error('--email required with --customer-id')
        customers.append({
            'customer_id': args.customer_id,
            'email': args.email,
            'password': args.password,
        })
    else:
        for spec in args.customers.split(','):
            parts = spec.strip().split(':')
            if len(parts) != 3:
                parser.error(f'Invalid customer spec: {spec} (expected id:email:password)')
            customers.append({
                'customer_id': int(parts[0]),
                'email': parts[1],
                'password': parts[2],
            })

    # Single phase mode
    if args.phase:
        from client import CSPulseClient
        from simulation.phase_runner import PhaseRunner

        cust = customers[0]
        client = CSPulseClient(args.base_url, cust['email'], cust['password'], cust['customer_id'])
        client.health_check()
        client.login()

        runner = PhaseRunner(
            client=client,
            customer_id=cust['customer_id'],
            kpi_codes=kpi_codes or [
                'P1-KPI1', 'P1-KPI3', 'P2-KPI1',
                'P3-KPI1', 'P3-KPI3', 'P3-KPI4',
                'P5-KPI1', 'P5-KPI2', 'P5-KPI3',
            ],
            vertical=args.vertical,
            seed=args.seed,
        )
        result = runner.run_phase(args.phase, args.phases, args.weeks_per_phase)
        print(json.dumps(result, indent=2, default=str))
        return

    # Full cycle mode
    from simulation.engine import SimulationEngine

    engine = SimulationEngine(
        base_url=args.base_url,
        vertical=args.vertical,
        kpi_codes=kpi_codes,
        max_parallel=args.parallel,
        seed=args.seed,
    )

    result = engine.run(
        customers=customers,
        total_phases=args.phases,
        phase_weeks=args.weeks_per_phase,
        gap_seconds=args.gap_seconds,
    )

    # Output
    print(json.dumps({
        'total_customers': result['total_customers'],
        'succeeded': result['succeeded'],
        'duration_s': result['duration_s'],
    }, indent=2))

    if args.output:
        with open(args.output, 'w') as f:
            json.dump(result, f, indent=2, default=str)
        print(f"\nFull results written to {args.output}")


if __name__ == '__main__':
    main()
