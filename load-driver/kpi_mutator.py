#!/usr/bin/env python3
"""
KPI Mutator — Applies realistic drift profiles to KPI values over time

Drift Profiles:
  - healthy: Stable or improving (value ±2-5% around target)
  - declining: Gradual degradation (1-3% per month)
  - critical: Sharp drop (5-10% per month for 3 months, then stabilize)
  - recovering: Was critical, now improving (3-5% per month)
  - seasonal: Cyclical pattern (±10% over 6-month cycle)

Power-of-1 Alignment:
  Maps DC2_S KPI codes to Power-of-1 metrics so ROI can be verified:
  - P1-KPI1 (Time-to-First-Workload) → TTFV
  - P5-KPI3 (Expansion Pipeline) → expansion_rate
  - P3-KPI1 (GPU Utilization) → product_adoption
  - P2-KPI1 (Uptime SLA) → ticket_resolution_time
  - P5-KPI1 (Capacity Utilization) → NRR
  - P4-KPI1 (Partner Engagement) → GRR
"""

import random
import math
from typing import Dict, List, Tuple
from datetime import datetime, timedelta


# KPI codes grouped by pillar
KPI_CODES = {
    'AI': ['AI-KPI1', 'AI-KPI2', 'AI-KPI3'],
    'CH': ['CH-KPI1', 'CH-KPI2', 'CH-KPI3'],
    'DV': ['DV-KPI1', 'DV-KPI2', 'DV-KPI3'],
    'EX': ['EX-KPI1', 'EX-KPI2', 'EX-KPI3'],
    'OS': ['OS-KPI1', 'OS-KPI2', 'OS-KPI3'],
}

ALL_KPI_CODES = [code for codes in KPI_CODES.values() for code in codes]

# Default targets per KPI code
DEFAULT_TARGETS = {code: 85.0 for code in ALL_KPI_CODES}

# Power-of-1 metric mapping (DC2_S KPI → Power-of-1 metric)
POWER_OF_1_MAP = {
    'DV-KPI3': 'TTFV',                    # Time-to-First-Workload → TTFV
    'EX-KPI2': 'expansion_rate',           # Expansion Pipeline → expansion_rate
    'AI-KPI1': 'product_adoption',         # GPU Utilization → product_adoption
    'OS-KPI2': 'ticket_resolution_time',   # Mean Time to Recovery → ticket_resolution
    'EX-KPI1': 'NRR',                      # Capacity Utilization → NRR
    'CH-KPI1': 'GRR',                      # Partner Engagement → GRR
}


class KPIMutator:
    """
    Applies realistic drift profiles to KPI values over 12 months

    Usage:
        mutator = KPIMutator(seed=42)
        month_data = mutator.generate_12_months(
            account_id=1001,
            baseline_values={'AI-KPI1': 82.0, ...},
            profile='declining'
        )
    """

    def __init__(self, seed: int = None):
        if seed is not None:
            random.seed(seed)
        self.noise_scale = 2.0  # Base noise in percentage points

    def generate_12_months(
        self,
        account_id: int,
        baseline_values: Dict[str, float],
        profile: str = 'healthy',
        start_month: str = '2024-01-01'
    ) -> List[Dict]:
        """
        Generate 12 months of KPI data with drift applied

        Args:
            account_id: Account ID
            baseline_values: Dict of kpi_code → initial value
            profile: One of 'healthy', 'declining', 'critical', 'recovering', 'seasonal'
            start_month: Start date (YYYY-MM-DD)

        Returns:
            List of dicts with keys: account_id, kpi_code, measured_at, value, target, pillar, weight, status
        """
        rows = []
        start = datetime.strptime(start_month, '%Y-%m-%d')

        for month_offset in range(12):
            measured_at = (start + timedelta(days=30 * month_offset)).strftime('%Y-%m-%d')

            for kpi_code, baseline in baseline_values.items():
                pillar = kpi_code.split('-')[0]
                target = DEFAULT_TARGETS.get(kpi_code, 85.0)

                # Apply drift profile
                value = self._apply_drift(baseline, target, month_offset, profile)

                # Determine status
                if value >= target * 0.95:
                    status = 'healthy'
                elif value >= target * 0.75:
                    status = 'risk'
                else:
                    status = 'critical'

                rows.append({
                    'account_id': account_id,
                    'kpi_code': kpi_code,
                    'measured_at': measured_at,
                    'value': round(value, 2),
                    'target': target,
                    'pillar': pillar,
                    'weight': 0.25,
                    'status': status
                })

        return rows

    def _apply_drift(
        self,
        baseline: float,
        target: float,
        month: int,
        profile: str
    ) -> float:
        """Apply drift profile to a single KPI value"""
        noise = random.gauss(0, self.noise_scale)

        if profile == 'healthy':
            # Stable: small random walk around baseline, slight improvement
            drift = month * 0.3 + noise
            return max(0, min(100, baseline + drift))

        elif profile == 'declining':
            # Gradual degradation: -1.5% per month
            drift = -month * 1.5 + noise
            return max(0, min(100, baseline + drift))

        elif profile == 'critical':
            # Sharp drop months 0-3, then stabilize at low level
            if month <= 3:
                drift = -month * 5.0 + noise
            else:
                drift = -15.0 + noise * 0.5  # Stabilize at ~15 points below
            return max(0, min(100, baseline + drift))

        elif profile == 'recovering':
            # Was low, now improving: +3% per month
            low_start = baseline - 20.0
            drift = month * 3.0 + noise
            return max(0, min(100, low_start + drift))

        elif profile == 'seasonal':
            # Cyclical: ±10% over 6-month cycle
            cycle = 10.0 * math.sin(2 * math.pi * month / 6)
            return max(0, min(100, baseline + cycle + noise))

        else:
            return baseline + noise

    def assign_profiles(
        self,
        num_accounts: int,
        distribution: Dict[str, float] = None
    ) -> Dict[int, str]:
        """
        Assign drift profiles to accounts based on distribution

        Default distribution (realistic):
          60% healthy, 20% declining, 10% critical, 5% recovering, 5% seasonal

        Returns:
            Dict of account_offset → profile name
        """
        if distribution is None:
            distribution = {
                'healthy': 0.60,
                'declining': 0.20,
                'critical': 0.10,
                'recovering': 0.05,
                'seasonal': 0.05
            }

        assignments = {}
        profiles = list(distribution.keys())
        weights = list(distribution.values())

        for i in range(num_accounts):
            assignments[i] = random.choices(profiles, weights=weights, k=1)[0]

        return assignments

    def generate_power_of_1_improvement(
        self,
        baseline_values: Dict[str, float],
        improvement_pct: float = 4.0
    ) -> Dict[str, float]:
        """
        Generate target values for Power-of-1 ROI validation

        Args:
            baseline_values: Starting KPI values
            improvement_pct: Target improvement (1%, 4%, or 6%)

        Returns:
            Dict of kpi_code → improved value
        """
        improved = {}
        for kpi_code, baseline in baseline_values.items():
            target = DEFAULT_TARGETS.get(kpi_code, 85.0)
            # Improvement = move X% toward target
            gap = target - baseline
            improvement = gap * (improvement_pct / 100.0)
            improved[kpi_code] = round(baseline + improvement, 2)
        return improved
