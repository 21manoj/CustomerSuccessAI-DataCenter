"""
SimulationEngine — concurrent multi-customer orchestrator.

Uses threading (not asyncio) to run multiple PhaseRunners in parallel,
since CSPulseClient uses synchronous requests.
"""

import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List

logger = logging.getLogger(__name__)


class SimulationEngine:
    """Run simulation cycles for multiple customers concurrently."""

    def __init__(self, base_url: str, vertical: str = 'saas_premium',
                 kpi_codes: List[str] = None, max_parallel: int = 5,
                 seed: int = 42):
        self.base_url = base_url
        self.vertical = vertical
        self.kpi_codes = kpi_codes or [
            'P1-KPI1', 'P1-KPI3', 'P2-KPI1',
            'P3-KPI1', 'P3-KPI3', 'P3-KPI4',
            'P5-KPI1', 'P5-KPI2', 'P5-KPI3',
        ]
        self.max_parallel = max_parallel
        self.seed = seed

    def run(self, customers: List[Dict], total_phases: int = 4,
            phase_weeks: int = 4, gap_seconds: int = 30) -> Dict:
        """Run simulation for multiple customers.

        Args:
            customers: List of {customer_id, email, password}
            total_phases: Number of phases per customer
            phase_weeks: Weeks of data per phase
            gap_seconds: Gap between phases

        Returns: {customer_id: cycle_result, ...}
        """
        t0 = time.time()
        logger.info(f"\n{'#'*60}")
        logger.info(f"  SIMULATION ENGINE")
        logger.info(f"  {len(customers)} customers × {total_phases} phases")
        logger.info(f"  Max parallel: {self.max_parallel}")
        logger.info(f"{'#'*60}")

        results = {}

        with ThreadPoolExecutor(max_workers=self.max_parallel) as executor:
            futures = {}
            for cust in customers:
                cid = cust['customer_id']
                future = executor.submit(
                    self._run_one_customer,
                    cust, total_phases, phase_weeks, gap_seconds,
                )
                futures[future] = cid

            for future in as_completed(futures):
                cid = futures[future]
                try:
                    result = future.result()
                    results[cid] = result
                    logger.info(f"  Customer {cid}: completed in {result.get('duration_s', 0)}s")
                except Exception as e:
                    results[cid] = {'status': 'error', 'message': str(e)}
                    logger.error(f"  Customer {cid}: FAILED — {e}")

        duration = time.time() - t0
        succeeded = sum(1 for r in results.values()
                        if isinstance(r, dict) and r.get('status') != 'error')

        logger.info(f"\n  ENGINE COMPLETE: {succeeded}/{len(customers)} succeeded in {duration:.0f}s")

        return {
            'total_customers': len(customers),
            'succeeded': succeeded,
            'duration_s': round(duration, 1),
            'results': results,
        }

    def _run_one_customer(self, cust: Dict, total_phases: int,
                          phase_weeks: int, gap_seconds: int) -> Dict:
        """Run simulation cycle for one customer (runs in thread)."""
        import sys, os
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

        from client import CSPulseClient
        from simulation.phase_runner import PhaseRunner

        cid = cust['customer_id']
        email = cust['email']
        password = cust['password']

        # Each customer gets its own client + seed
        client = CSPulseClient(self.base_url, email, password, cid)
        client.health_check()
        client.login()

        runner = PhaseRunner(
            client=client,
            customer_id=cid,
            kpi_codes=self.kpi_codes,
            vertical=self.vertical,
            seed=self.seed + cid,  # deterministic per customer
        )

        return runner.run_cycle(total_phases, phase_weeks, gap_seconds)
