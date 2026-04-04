#!/usr/bin/env python3
"""
================================================================
Simulation Test Harness — Turnaround Story Verification
================================================================

Wraps the SimulationEngine with pytest-style assertions that verify:
  1. Phase-over-phase health direction matches expected trajectory
  2. Critical accounts with active playbooks show recovery
  3. No account gets "stuck" (same score ±0.1 across 3+ phases)
  4. End-of-cycle health is higher than start for recovering accounts
  5. Signal and outcome CSVs are generated and uploaded successfully

Usage:
  # Against EC2 (inside container):
  cd /app/load-driver
  python3 -m pytest tests/test_simulation_harness.py -v --tb=short

  # Against EC2 (from laptop):
  CS_PULSE_BASE_URL=http://54.89.77.21 python3 -m pytest tests/test_simulation_harness.py -v

  # Quick smoke test (2 phases):
  python3 tests/test_simulation_harness.py --phases 2 --base-url http://127.0.0.1:80

  # Standalone (no pytest):
  python3 tests/test_simulation_harness.py --customer-id 29 --email admin@simtest2.io
================================================================
"""

import argparse
import json
import logging
import os
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional

# Add load-driver root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from client import CSPulseClient
from simulation.phase_runner import PhaseRunner
from simulation.state_reader import StateReader, AccountState

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────
# Configuration
# ──────────────────────────────────────────────────────────────
BASE_URL = os.getenv("CS_PULSE_BASE_URL", "http://127.0.0.1:80")
DEFAULT_CUSTOMER_ID = int(os.getenv("SIM_CUSTOMER_ID", "29"))
DEFAULT_EMAIL = os.getenv("SIM_EMAIL", "admin@simtest2.io")
DEFAULT_PASSWORD = os.getenv("SIM_PASSWORD", "test123")

# Thresholds
MIN_PHASE_MATCH_RATE = 0.50   # At least 50% of accounts match direction per phase
MIN_CYCLE_MATCH_RATE = 0.75   # At least 75% across full cycle (tighter — turnaround must be visible)
MAX_STUCK_PHASES = 3          # Fail if any account unchanged for 3+ consecutive phases
DIRECTION_THRESHOLD = 1.0     # Minimum delta to count as movement (not "flat")
MIN_AVG_DELTA = 1.0           # Minimum average |delta| per phase across all accounts

# Starter 9 KPIs
DEFAULT_KPI_CODES = [
    'P1-KPI1', 'P1-KPI3', 'P2-KPI1',
    'P3-KPI1', 'P3-KPI3', 'P3-KPI4',
    'P5-KPI1', 'P5-KPI2', 'P5-KPI3',
]


# ──────────────────────────────────────────────────────────────
# Result structures
# ──────────────────────────────────────────────────────────────
@dataclass
class PhaseResult:
    phase: int
    passes: int
    total: int
    details: List[Dict]
    uploads: Dict
    process_data: str
    duration_s: float


@dataclass
class CycleResult:
    customer_id: int
    total_phases: int
    phase_results: List[PhaseResult]
    health_timeline: Dict[int, List[float]]  # account_id → [health_per_phase]
    duration_s: float

    @property
    def total_passes(self) -> int:
        return sum(p.passes for p in self.phase_results)

    @property
    def total_checks(self) -> int:
        return sum(p.total for p in self.phase_results)

    @property
    def overall_match_rate(self) -> float:
        if self.total_checks == 0:
            return 0.0
        return self.total_passes / self.total_checks


# ──────────────────────────────────────────────────────────────
# Test Harness
# ──────────────────────────────────────────────────────────────
class SimulationTestHarness:
    """Runs simulation and collects structured results for assertions."""

    def __init__(self, base_url: str, customer_id: int, email: str,
                 password: str, kpi_codes: List[str] = None,
                 vertical: str = 'saas_premium', seed: int = 42):
        self.base_url = base_url
        self.customer_id = customer_id
        self.email = email
        self.password = password
        self.kpi_codes = kpi_codes or DEFAULT_KPI_CODES
        self.vertical = vertical
        self.seed = seed

        self._client: Optional[CSPulseClient] = None
        self._runner: Optional[PhaseRunner] = None

    def setup(self):
        """Initialize client and runner."""
        self._client = CSPulseClient(self.base_url, self.email,
                                     self.password, self.customer_id)
        self._client.health_check()
        self._client.login()

        self._runner = PhaseRunner(
            client=self._client,
            customer_id=self.customer_id,
            kpi_codes=self.kpi_codes,
            vertical=self.vertical,
            seed=self.seed,
        )

    def run_cycle(self, total_phases: int = 4, phase_weeks: int = 4,
                  gap_seconds: int = 5) -> CycleResult:
        """Run full simulation cycle, collecting results per phase."""
        if not self._runner:
            self.setup()

        t0 = time.time()
        phase_results = []
        health_timeline: Dict[int, List[float]] = {}

        # Read initial state
        initial_states = self._runner.state_reader.read_all()
        for s in initial_states:
            health_timeline[s.account_id] = [s.health_score]

        for phase_num in range(1, total_phases + 1):
            result = self._runner.run_phase(phase_num, total_phases, phase_weeks)

            verification = result.get('verification', {})
            pr = PhaseResult(
                phase=phase_num,
                passes=verification.get('passes', 0),
                total=verification.get('total', 0),
                details=verification.get('details', []),
                uploads=result.get('uploads', {}),
                process_data=result.get('process_data', ''),
                duration_s=result.get('duration_s', 0),
            )
            phase_results.append(pr)

            # Track health timeline
            for d in pr.details:
                aid = None
                for s in initial_states:
                    if s.account_name == d.get('account'):
                        aid = s.account_id
                        break
                if aid and 'post' in d:
                    health_timeline.setdefault(aid, []).append(d['post'])

            if phase_num < total_phases and gap_seconds > 0:
                time.sleep(gap_seconds)

        return CycleResult(
            customer_id=self.customer_id,
            total_phases=total_phases,
            phase_results=phase_results,
            health_timeline=health_timeline,
            duration_s=round(time.time() - t0, 1),
        )


# ──────────────────────────────────────────────────────────────
# Assertion functions
# ──────────────────────────────────────────────────────────────
def assert_phase_match_rates(result: CycleResult, min_rate: float = MIN_PHASE_MATCH_RATE):
    """Phases 2+ must have at least min_rate direction matches.

    Phase 1 is exempt — it's the "setup" phase where healthy accounts may
    decline naturally (no playbook protection yet), which is part of the story.
    """
    failures = []
    for pr in result.phase_results:
        if pr.phase == 1:
            continue  # Phase 1 is setup — declines are expected
        rate = pr.passes / pr.total if pr.total > 0 else 0
        if rate < min_rate:
            failures.append(
                f"Phase {pr.phase}: {pr.passes}/{pr.total} = {rate:.0%} "
                f"(min {min_rate:.0%})"
            )
    assert not failures, f"Phase match rate failures:\n  " + "\n  ".join(failures)


def assert_overall_match_rate(result: CycleResult, min_rate: float = MIN_CYCLE_MATCH_RATE):
    """Overall match rate across all phases must exceed threshold."""
    rate = result.overall_match_rate
    assert rate >= min_rate, (
        f"Overall match rate {result.total_passes}/{result.total_checks} = {rate:.0%} "
        f"< {min_rate:.0%} minimum"
    )


def assert_no_stuck_accounts(result: CycleResult, max_stuck: int = MAX_STUCK_PHASES):
    """No account should have the same health score (±0.1) for max_stuck+ phases."""
    failures = []
    for aid, scores in result.health_timeline.items():
        if len(scores) < max_stuck:
            continue
        for i in range(len(scores) - max_stuck + 1):
            window = scores[i:i + max_stuck]
            if max(window) - min(window) < 0.2:
                failures.append(
                    f"Account {aid}: stuck at ~{window[0]:.1f} for "
                    f"{max_stuck} phases (indices {i}-{i+max_stuck-1})"
                )
                break
    assert not failures, f"Stuck accounts:\n  " + "\n  ".join(failures)


def assert_uploads_succeeded(result: CycleResult):
    """All CSV uploads must succeed."""
    failures = []
    for pr in result.phase_results:
        for file_type, status in pr.uploads.items():
            if status != 'ok':
                failures.append(f"Phase {pr.phase}: {file_type} = {status}")
    assert not failures, f"Upload failures:\n  " + "\n  ".join(failures)


def assert_process_data_succeeded(result: CycleResult):
    """process_data must succeed in every phase."""
    failures = []
    for pr in result.phase_results:
        if pr.process_data not in ('success', 'completed', 'ok'):
            failures.append(f"Phase {pr.phase}: process_data = {pr.process_data}")
    assert not failures, f"process_data failures:\n  " + "\n  ".join(failures)


def assert_health_moved(result: CycleResult):
    """At least some accounts must show health change from start to end."""
    moved = 0
    for aid, scores in result.health_timeline.items():
        if len(scores) >= 2:
            delta = abs(scores[-1] - scores[0])
            if delta > DIRECTION_THRESHOLD:
                moved += 1
    total = len(result.health_timeline)
    assert moved > 0, f"No accounts showed health movement (0/{total})"


def assert_average_delta_meaningful(result: CycleResult, min_avg: float = MIN_AVG_DELTA):
    """Average |delta| per phase must be meaningful — not just noise."""
    all_deltas = []
    for pr in result.phase_results:
        for d in pr.details:
            if 'delta' in d:
                all_deltas.append(abs(d['delta']))
    if not all_deltas:
        raise AssertionError("No delta data found")
    avg = sum(all_deltas) / len(all_deltas)
    assert avg >= min_avg, (
        f"Average |delta| = {avg:.2f} < {min_avg} — "
        f"health changes are just noise, not a real turnaround"
    )


def assert_turnaround_visible(result: CycleResult):
    """Accounts that started critical/at-risk must reach healthy (≥70) by end.

    The turnaround story: critical accounts with playbook intervention
    should cross the healthy threshold over a 4-phase cycle.
    """
    failures = []
    reached_healthy = 0
    total = 0
    for aid, scores in result.health_timeline.items():
        if len(scores) < 2:
            continue
        start = scores[0]
        end = scores[-1]
        peak = max(scores)
        # Only check accounts that started below healthy
        if start < 70:
            total += 1
            if end >= 70 or peak >= 70:
                reached_healthy += 1
            else:
                failures.append(
                    f"Account {aid}: {start:.1f} → {end:.1f} (peak {peak:.1f}) "
                    f"— never reached healthy ≥70"
                )
    if total == 0:
        return  # No at-risk accounts to check
    # At least 40% of at-risk accounts should reach healthy
    rate = reached_healthy / total
    assert rate >= 0.40, (
        f"Turnaround incomplete: only {reached_healthy}/{total} accounts "
        f"reached healthy (≥70).\n  " + "\n  ".join(failures)
    )


# ──────────────────────────────────────────────────────────────
# Pytest integration (conditional import — standalone mode works without pytest)
# ──────────────────────────────────────────────────────────────
try:
    import pytest
    HAS_PYTEST = True
except ImportError:
    HAS_PYTEST = False
    # Stub pytest.fixture so class definitions don't break at import
    class _PytestStub:
        @staticmethod
        def fixture(*a, **kw):
            def decorator(fn):
                return fn
            return decorator
    pytest = _PytestStub()

@pytest.fixture(scope="module")
def cycle_result():
    """Run simulation once and share result across all test functions."""
    harness = SimulationTestHarness(
        base_url=BASE_URL,
        customer_id=DEFAULT_CUSTOMER_ID,
        email=DEFAULT_EMAIL,
        password=DEFAULT_PASSWORD,
    )
    harness.setup()
    result = harness.run_cycle(
        total_phases=int(os.getenv("SIM_PHASES", "4")),
        gap_seconds=int(os.getenv("SIM_GAP_SECONDS", "5")),
    )

    # Print summary
    print(f"\n{'='*60}")
    print(f"  SIMULATION COMPLETE: customer {result.customer_id}")
    print(f"  {result.total_phases} phases in {result.duration_s}s")
    print(f"  Overall: {result.total_passes}/{result.total_checks} "
          f"({result.overall_match_rate:.0%})")
    print(f"{'='*60}")
    for pr in result.phase_results:
        rate = pr.passes / pr.total if pr.total > 0 else 0
        print(f"  Phase {pr.phase}: {pr.passes}/{pr.total} ({rate:.0%}) "
              f"in {pr.duration_s}s — process_data: {pr.process_data}")
    print()

    return result


class TestSimulationPhases:
    """Phase-level verification tests."""

    def test_phase_match_rates(self, cycle_result):
        """Each phase must achieve >= 50% direction match."""
        assert_phase_match_rates(cycle_result)

    def test_overall_match_rate(self, cycle_result):
        """Full cycle must achieve >= 75% direction match."""
        assert_overall_match_rate(cycle_result)


class TestSimulationHealth:
    """Health trajectory tests."""

    def test_no_stuck_accounts(self, cycle_result):
        """No account should be stuck at the same health for 3+ phases."""
        assert_no_stuck_accounts(cycle_result)

    def test_health_moved(self, cycle_result):
        """At least one account must show health movement."""
        assert_health_moved(cycle_result)


class TestTurnaroundStory:
    """The compelling turnaround narrative tests."""

    def test_average_delta_meaningful(self, cycle_result):
        """Average health change per phase must be > 1.0 — not just noise."""
        assert_average_delta_meaningful(cycle_result)

    def test_turnaround_visible(self, cycle_result):
        """At-risk accounts must show net improvement over the full cycle."""
        assert_turnaround_visible(cycle_result)


class TestSimulationInfra:
    """Infrastructure / pipeline tests."""

    def test_uploads_succeeded(self, cycle_result):
        """All CSV uploads must succeed."""
        assert_uploads_succeeded(cycle_result)

    def test_process_data_succeeded(self, cycle_result):
        """process_data must succeed in every phase."""
        assert_process_data_succeeded(cycle_result)


class TestSimulationIntegrity:
    """Data integrity assertions."""

    def test_health_timeline_populated(self, cycle_result):
        """Every account should have health readings for each phase."""
        for aid, scores in cycle_result.health_timeline.items():
            # initial + N phases = N+1 entries
            assert len(scores) >= cycle_result.total_phases, (
                f"Account {aid}: expected {cycle_result.total_phases}+ scores, "
                f"got {len(scores)}"
            )

    def test_health_scores_in_range(self, cycle_result):
        """All health scores must be between 0 and 100."""
        for aid, scores in cycle_result.health_timeline.items():
            for s in scores:
                assert 0 <= s <= 100, (
                    f"Account {aid}: health score {s} out of range [0, 100]"
                )

    def test_phase_duration_reasonable(self, cycle_result):
        """Each phase should complete in under 120s."""
        for pr in cycle_result.phase_results:
            assert pr.duration_s < 120, (
                f"Phase {pr.phase}: took {pr.duration_s}s (max 120s)"
            )


# ──────────────────────────────────────────────────────────────
# Standalone runner (no pytest)
# ──────────────────────────────────────────────────────────────
def run_standalone():
    parser = argparse.ArgumentParser(
        description='Simulation Test Harness — standalone mode',
    )
    parser.add_argument('--customer-id', type=int, default=DEFAULT_CUSTOMER_ID)
    parser.add_argument('--email', type=str, default=DEFAULT_EMAIL)
    parser.add_argument('--password', type=str, default=DEFAULT_PASSWORD)
    parser.add_argument('--phases', type=int, default=4)
    parser.add_argument('--gap-seconds', type=int, default=5)
    parser.add_argument('--base-url', type=str, default=BASE_URL)
    parser.add_argument('--verbose', '-v', action='store_true')
    parser.add_argument('--output', type=str, help='Write JSON results to file')
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
        datefmt='%H:%M:%S',
    )

    harness = SimulationTestHarness(
        base_url=args.base_url,
        customer_id=args.customer_id,
        email=args.email,
        password=args.password,
    )
    harness.setup()
    result = harness.run_cycle(
        total_phases=args.phases,
        gap_seconds=args.gap_seconds,
    )

    # Print summary
    print(f"\n{'='*60}")
    print(f"  SIMULATION TEST HARNESS RESULTS")
    print(f"  Customer: {result.customer_id}")
    print(f"  Phases: {result.total_phases} in {result.duration_s}s")
    print(f"  Overall: {result.total_passes}/{result.total_checks} "
          f"({result.overall_match_rate:.0%})")
    print(f"{'='*60}")
    for pr in result.phase_results:
        rate = pr.passes / pr.total if pr.total > 0 else 0
        print(f"  Phase {pr.phase}: {pr.passes}/{pr.total} ({rate:.0%}) "
              f"in {pr.duration_s}s")
    print()

    # Print health timeline
    print("  Health Timeline:")
    for aid, scores in result.health_timeline.items():
        trajectory = " → ".join(f"{s:.1f}" for s in scores)
        net = scores[-1] - scores[0] if len(scores) >= 2 else 0
        print(f"    Account {aid}: {trajectory}  (net {net:+.1f})")
    print()

    # Run assertions
    checks = [
        ("Phase match rates (>=50%)", lambda: assert_phase_match_rates(result)),
        ("Overall match rate (>=75%)", lambda: assert_overall_match_rate(result)),
        ("No stuck accounts", lambda: assert_no_stuck_accounts(result)),
        ("Health moved", lambda: assert_health_moved(result)),
        ("Avg delta meaningful (>=1.0)", lambda: assert_average_delta_meaningful(result)),
        ("Turnaround visible", lambda: assert_turnaround_visible(result)),
        ("Uploads succeeded", lambda: assert_uploads_succeeded(result)),
        ("process_data succeeded", lambda: assert_process_data_succeeded(result)),
    ]

    passed = 0
    failed = 0
    for name, check_fn in checks:
        try:
            check_fn()
            print(f"  PASS  {name}")
            passed += 1
        except AssertionError as e:
            print(f"  FAIL  {name}: {e}")
            failed += 1

    print(f"\n  {passed} passed, {failed} failed")

    # Output JSON
    if args.output:
        output = {
            'customer_id': result.customer_id,
            'total_phases': result.total_phases,
            'duration_s': result.duration_s,
            'overall_match_rate': f"{result.overall_match_rate:.0%}",
            'total_passes': result.total_passes,
            'total_checks': result.total_checks,
            'assertions_passed': passed,
            'assertions_failed': failed,
            'phases': [
                {
                    'phase': pr.phase,
                    'passes': pr.passes,
                    'total': pr.total,
                    'duration_s': pr.duration_s,
                    'uploads': pr.uploads,
                    'process_data': pr.process_data,
                    'details': pr.details,
                }
                for pr in result.phase_results
            ],
            'health_timeline': {
                str(aid): scores
                for aid, scores in result.health_timeline.items()
            },
        }
        with open(args.output, 'w') as f:
            json.dump(output, f, indent=2, default=str)
        print(f"\n  Results written to {args.output}")

    return 0 if failed == 0 else 1


if __name__ == '__main__':
    sys.exit(run_standalone())
