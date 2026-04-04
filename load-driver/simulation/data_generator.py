"""
DataGenerator — produces CSV content for one simulation phase.

Generates kpi_measurements, enhanced_qualitative_signals, outcomes,
and signal_edges CSVs using existing catalog_loader for KPI metadata
and trajectory models from ManifestCSVGenerator.
"""

import csv
import io
import logging
import random
from datetime import datetime, timedelta
from typing import Dict, List, Tuple

from simulation.state_reader import AccountState
from simulation.phase_decider import PhaseDecision

logger = logging.getLogger(__name__)


class DataGenerator:
    """Generates CSV data for one simulation phase."""

    def __init__(self, customer_id: int, kpi_codes: List[str],
                 vertical: str = 'saas_premium', seed: int = 42):
        self.customer_id = customer_id
        self.kpi_codes = kpi_codes
        self.vertical = vertical
        self._rng = random.Random(seed)

        # Load catalog for KPI ranges
        try:
            import catalog_loader
            catalog_loader.set_vertical(vertical)
            self._catalog = catalog_loader
        except Exception:
            self._catalog = None

    def generate_phase_data(
        self,
        account_decisions: List[Tuple[AccountState, PhaseDecision]],
        phase_start: datetime,
        phase_weeks: int = 4,
        phase_number: int = 1,
    ) -> Dict[str, str]:
        """Generate all CSVs for this phase.

        Returns: {file_type: csv_content_string}
        """
        all_kpi_rows = []
        all_signal_rows = []
        all_outcome_rows = []

        for state, decision in account_decisions:
            # Generate KPI measurements
            kpi_rows = self._generate_kpi_measurements(
                state, decision, phase_start, phase_weeks, phase_number
            )
            all_kpi_rows.extend(kpi_rows)

            # Generate signals
            signal_rows = self._generate_signals(
                state, decision, phase_start, phase_weeks, phase_number
            )
            all_signal_rows.extend(signal_rows)

            # Generate outcomes
            outcome_rows = self._generate_outcomes(
                state, decision, phase_start, phase_weeks, phase_number
            )
            all_outcome_rows.extend(outcome_rows)

        csvs = {}

        if all_kpi_rows:
            csvs['kpi_measurements.csv'] = self._rows_to_csv(all_kpi_rows)
        if all_signal_rows:
            csvs['enhanced_qualitative_signals.csv'] = self._rows_to_csv(all_signal_rows)
        if all_outcome_rows:
            csvs['outcomes.csv'] = self._rows_to_csv(all_outcome_rows)

        logger.info(
            f"DataGenerator: phase {phase_number} — "
            f"{len(all_kpi_rows)} KPI rows, "
            f"{len(all_signal_rows)} signal rows, "
            f"{len(all_outcome_rows)} outcome rows"
        )

        return csvs

    def _generate_kpi_measurements(
        self,
        state: AccountState,
        decision: PhaseDecision,
        phase_start: datetime,
        phase_weeks: int,
        phase_number: int,
    ) -> List[Dict]:
        """Generate KPI measurement rows for one account in this phase."""
        rows = []
        target_health = max(5, min(95, state.health_score + decision.target_health_delta))

        for kpi_code in self.kpi_codes:
            # Get KPI metadata from catalog
            kpi_target = 85.0
            higher_is_better = True
            if self._catalog:
                try:
                    kpi_meta = self._catalog.get_kpis().get(kpi_code, {})
                    kpi_target = kpi_meta.get('target', {}).get('value', 85.0)
                    higher_is_better = kpi_meta.get('higher_is_better', True)
                except Exception:
                    pass

            # Map target_health (0-100) to KPI value
            base_value = self._health_to_kpi_value(target_health, kpi_target, higher_is_better)

            # Generate weekly data points with trajectory
            for week in range(phase_weeks):
                t = week / max(1, phase_weeks - 1)  # 0.0 → 1.0
                value = self._apply_trajectory(base_value, t, decision.trajectory, kpi_target)

                # Add noise
                noise = self._rng.gauss(0, base_value * 0.03)
                value = max(0, value + noise)

                measured_at = phase_start + timedelta(weeks=week)

                rows.append({
                    'account_id': state.account_id,
                    'kpi_code': kpi_code,
                    'value': round(value, 4),
                    'measured_at': measured_at.strftime('%Y-%m-%d'),
                    'source': 'simulation',
                })

        return rows

    def _generate_signals(
        self,
        state: AccountState,
        decision: PhaseDecision,
        phase_start: datetime,
        phase_weeks: int,
        phase_number: int,
    ) -> List[Dict]:
        """Generate qualitative signal rows for one account."""
        rows = []
        signals = decision.signals_to_inject

        for i, sig in enumerate(signals):
            # Spread signals across the phase window
            offset_days = int((i + 1) / (len(signals) + 1) * phase_weeks * 7)
            signal_date = phase_start + timedelta(days=offset_days)

            rows.append({
                'account_id': state.account_id,
                'signal_type': sig.get('signal_type', 'observation'),
                'signal_date': signal_date.strftime('%Y-%m-%d'),
                'content': sig.get('content', ''),
                'sentiment': sig.get('sentiment', 'negative'),
                'source': 'simulation',
                'severity': 'high' if sig.get('sentiment') == 'negative' else 'medium',
                'signal_ref': f'sim_p{phase_number}_{state.account_id}_{i+1}',
            })

        return rows

    def _generate_outcomes(
        self,
        state: AccountState,
        decision: PhaseDecision,
        phase_start: datetime,
        phase_weeks: int,
        phase_number: int,
    ) -> List[Dict]:
        """Generate outcome rows for one account."""
        rows = []
        outcomes = decision.outcomes_to_inject

        for i, out in enumerate(outcomes):
            # Outcomes appear near end of phase
            offset_days = int(phase_weeks * 7 * 0.8) + i * 3
            outcome_date = phase_start + timedelta(days=offset_days)

            rows.append({
                'account_id': state.account_id,
                'outcome_type': out.get('subtype', 'observation'),
                'outcome_date': outcome_date.strftime('%Y-%m-%d'),
                'title': out.get('title', ''),
                'revenue_impact': out.get('revenue_impact', 0),
                'revenue_impact_type': out.get('revenue_impact_type', 'at_risk'),
                'source': 'simulation',
                'outcome_ref': f'sim_p{phase_number}_out_{state.account_id}_{i+1}',
            })

        return rows

    def _health_to_kpi_value(self, health: float, target: float, higher_is_better: bool) -> float:
        """Map health score (0-100) to a KPI value.

        At health=100, KPI is at target (excellent).
        At health=0, KPI is at 20% of target (terrible).
        Linear interpolation between.
        """
        ratio = health / 100.0
        floor = target * 0.20
        if higher_is_better:
            return floor + (target - floor) * ratio
        else:
            # Lower is better: invert — health=100 → low value, health=0 → high value
            ceiling = target * 3.0
            return ceiling - (ceiling - target) * ratio

    def _apply_trajectory(self, base: float, t: float, trajectory: str, target: float) -> float:
        """Apply trajectory modifier to a base KPI value.

        t: normalized time (0.0 = start of phase, 1.0 = end of phase)
        """
        if trajectory == 'declining':
            return base * (1.0 - 0.15 * t)
        elif trajectory == 'slow_decline':
            return base * (1.0 - 0.07 * t)
        elif trajectory == 'improving':
            return base * (1.0 + 0.12 * t)
        elif trajectory == 'recovering':
            # V-shape: dip first 40%, then recover
            if t < 0.4:
                return base * (1.0 - 0.08 * (t / 0.4))
            else:
                recovery = (t - 0.4) / 0.6
                return base * (0.92 + 0.15 * recovery)
        elif trajectory == 'stable':
            return base * (1.0 + self._rng.gauss(0, 0.02))
        elif trajectory == 'flat_high_risk':
            return base
        else:
            return base

    def _rows_to_csv(self, rows: List[Dict]) -> str:
        """Convert list of dicts to CSV string."""
        if not rows:
            return ''
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
        return output.getvalue()
