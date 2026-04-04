"""
PhaseRunner — orchestrates read → decide → generate → upload → verify for one customer.
"""

import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from simulation.state_reader import StateReader, AccountState
from simulation.phase_decider import PhaseDecider, PhaseDecision
from simulation.data_generator import DataGenerator

logger = logging.getLogger(__name__)


class PhaseRunner:
    """Run simulation phases for a single customer."""

    def __init__(self, client, customer_id: int, kpi_codes: List[str],
                 vertical: str = 'saas_premium', seed: int = 42):
        self.client = client
        self.customer_id = customer_id
        self.kpi_codes = kpi_codes
        self.vertical = vertical
        self.seed = seed

        self.state_reader = StateReader(client, customer_id)
        self.phase_decider = PhaseDecider(seed=seed)
        self.data_generator = DataGenerator(
            customer_id=customer_id,
            kpi_codes=kpi_codes,
            vertical=vertical,
            seed=seed,
        )

        self._phase_dates: Dict[int, datetime] = {}

    def run_phase(self, phase_number: int, total_phases: int,
                  phase_weeks: int = 4) -> Dict:
        """Execute one simulation phase.

        1. Read current state
        2. Decide trajectory per account
        3. Generate CSVs
        4. Upload
        5. Trigger process_data
        6. Verify health moved as expected
        """
        t0 = time.time()
        logger.info(f"\n{'='*60}")
        logger.info(f"  Phase {phase_number}/{total_phases} — customer {self.customer_id}")
        logger.info(f"{'='*60}")

        # 1. Read state
        pre_states = self.state_reader.read_all()
        if not pre_states:
            return {'status': 'error', 'message': 'No accounts found'}

        # 2. Decide trajectories
        account_decisions = self.phase_decider.decide_all(
            pre_states, phase_number, total_phases
        )

        # Log decisions
        for state, decision in account_decisions:
            logger.info(
                f"  {state.account_name:<25s} health={state.health_score:>5.1f} "
                f"({state.health_band:>8s}) → {decision.trajectory:<15s} "
                f"delta={decision.target_health_delta:>+5.0f}  "
                f"[{decision.explanation}]"
            )

        # 3. Compute phase start date
        phase_start = self._compute_phase_start(pre_states, phase_number, phase_weeks)
        self._phase_dates[phase_number] = phase_start
        logger.info(f"  Phase window: {phase_start.strftime('%Y-%m-%d')} → "
                     f"{(phase_start + timedelta(weeks=phase_weeks)).strftime('%Y-%m-%d')}")

        # 4. Generate CSVs
        csvs = self.data_generator.generate_phase_data(
            account_decisions, phase_start, phase_weeks, phase_number
        )

        if not csvs:
            return {'status': 'warning', 'message': 'No CSV data generated'}

        # 5. Upload CSVs
        upload_results = {}
        for file_type, csv_content in csvs.items():
            try:
                self.client.upload_csv(self.customer_id, file_type, csv_content)
                upload_results[file_type] = 'ok'
                logger.info(f"  Uploaded: {file_type} ({len(csv_content)} bytes)")
            except Exception as e:
                upload_results[file_type] = f'error: {e}'
                logger.error(f"  Upload failed: {file_type}: {e}")

        # 6. Trigger process_data
        logger.info(f"  Triggering process_data...")
        try:
            pd_result = self.client.process_data(
                self.customer_id, self.vertical,
                skip_wizard_b=True, skip_wizard_c=True,
            )
            pd_status = pd_result.get('status', 'unknown') if pd_result else 'timeout'
            logger.info(f"  process_data: {pd_status}")
        except Exception as e:
            pd_status = f'error: {e}'
            logger.error(f"  process_data failed: {e}")

        # 7. Verify
        post_states = self.state_reader.read_all()
        verification = self._verify(pre_states, account_decisions, post_states)

        duration = time.time() - t0
        logger.info(f"  Phase {phase_number} complete in {duration:.1f}s — "
                     f"match rate: {verification['match_rate']}")

        return {
            'status': 'success',
            'phase': phase_number,
            'duration_s': round(duration, 1),
            'accounts': len(pre_states),
            'uploads': upload_results,
            'process_data': pd_status,
            'verification': verification,
        }

    def run_cycle(self, total_phases: int = 4, phase_weeks: int = 4,
                  gap_seconds: int = 30) -> Dict:
        """Run full simulation cycle: phases 1..N sequentially."""
        t0 = time.time()
        logger.info(f"\n{'#'*60}")
        logger.info(f"  SIMULATION CYCLE: customer {self.customer_id}")
        logger.info(f"  {total_phases} phases × {phase_weeks} weeks, "
                     f"{gap_seconds}s gap between phases")
        logger.info(f"{'#'*60}")

        phase_results = {}
        for phase in range(1, total_phases + 1):
            result = self.run_phase(phase, total_phases, phase_weeks)
            phase_results[phase] = result

            if phase < total_phases and gap_seconds > 0:
                logger.info(f"  Waiting {gap_seconds}s before next phase...")
                time.sleep(gap_seconds)

        duration = time.time() - t0
        logger.info(f"\n  CYCLE COMPLETE in {duration:.0f}s")

        return {
            'customer_id': self.customer_id,
            'total_phases': total_phases,
            'duration_s': round(duration, 1),
            'phases': phase_results,
        }

    def _compute_phase_start(self, states: List[AccountState],
                              phase_number: int, phase_weeks: int) -> datetime:
        """Compute phase start date from latest KPI date in DB."""
        if phase_number > 1 and (phase_number - 1) in self._phase_dates:
            # Chain from previous phase end
            prev_start = self._phase_dates[phase_number - 1]
            return prev_start + timedelta(weeks=phase_weeks)

        # Phase 1: start from latest KPI date + 1 day
        latest = None
        for s in states:
            if s.last_kpi_date:
                try:
                    d = datetime.strptime(s.last_kpi_date[:10], '%Y-%m-%d')
                    if latest is None or d > latest:
                        latest = d
                except ValueError:
                    pass

        if latest:
            return latest + timedelta(days=1)

        # Fallback: today
        return datetime.utcnow()

    def _verify(self, pre_states: List[AccountState],
                decisions: List[tuple],
                post_states: List[AccountState]) -> Dict:
        """Compare pre vs post health scores against expectations."""
        post_map = {s.account_id: s for s in post_states}
        results = []
        passes = 0
        total = 0

        for state, decision in decisions:
            post = post_map.get(state.account_id)
            if not post:
                results.append({
                    'account': state.account_name,
                    'status': 'MISSING',
                })
                continue

            total += 1
            expected_dir = (
                'down' if decision.target_health_delta < -2 else
                'up' if decision.target_health_delta > 2 else 'flat'
            )
            actual_delta = post.health_score - state.health_score
            actual_dir = 'down' if actual_delta < -2 else ('up' if actual_delta > 2 else 'flat')

            passed = expected_dir == actual_dir or expected_dir == 'flat'
            if passed:
                passes += 1

            results.append({
                'account': state.account_name,
                'pre': round(state.health_score, 1),
                'post': round(post.health_score, 1),
                'delta': round(actual_delta, 1),
                'expected': decision.target_health_delta,
                'direction_match': passed,
            })

            status = 'PASS' if passed else 'MISS'
            logger.info(
                f"  VERIFY: {state.account_name:<22s} "
                f"{state.health_score:>5.1f} → {post.health_score:>5.1f} "
                f"({actual_delta:>+5.1f}) expected {decision.target_health_delta:>+5.0f} "
                f"[{status}]"
            )

        match_rate = f"{passes}/{total}" if total > 0 else "0/0"
        return {
            'match_rate': match_rate,
            'passes': passes,
            'total': total,
            'details': results,
        }
