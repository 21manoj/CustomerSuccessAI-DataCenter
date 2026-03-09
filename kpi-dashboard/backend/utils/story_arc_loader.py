"""
Story Arc Manifest Loader & Validator

Loads story arc JSON manifests from config/story_arcs/ and validates
them against the schema and DC2_S KPI definitions.

Usage:
    from utils.story_arc_loader import load_arc, load_all_arcs, validate_arc, get_arc_summary

    arc = load_arc('arc_expansion_champion')
    errors = validate_arc(arc)
    all_arcs = load_all_arcs()
"""

import json
import logging
import os
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Path to story arc manifests
ARCS_DIR = Path(__file__).parent.parent / 'config' / 'story_arcs'
SCHEMA_PATH = ARCS_DIR / 'schema.json'

# Valid KPI codes from DC2_S vertical (38 KPIs)
VALID_KPI_CODES = set()
try:
    from verticals.dc2_s.kpi_definitions import DC2S_KPIS
    VALID_KPI_CODES = set(DC2S_KPIS.keys())
except ImportError:
    # Fallback: generate expected codes
    for p, count in [('P1', 8), ('P2', 8), ('P3', 8), ('P4', 6), ('P5', 8)]:
        for i in range(1, count + 1):
            VALID_KPI_CODES.add(f'{p}-KPI{i}')

VALID_NODE_TYPES = {'SIGNAL', 'STAKEHOLDER', 'DECISION', 'OUTCOME', 'EXTERNAL_CONTEXT', 'ACCOUNT'}
VALID_EDGE_TYPES = {'CAUSED_BY', 'INDICATES', 'LED_TO', 'CORRELATES_WITH',
                    'INVOLVES', 'BELONGS_TO', 'BENCHMARKED_BY', 'SOURCED_FROM', 'SUPERSEDES'}
VALID_EVENT_TYPES = {'signal', 'meeting', 'incident', 'decision', 'milestone',
                     'escalation', 'stakeholder_change', 'external'}
VALID_AUDIENCES = {'CRO', 'CFO', 'CEO'}
VALID_OUTCOME_TYPES = {'retention', 'expansion', 'churn_averted', 'cost_reduction', 'churn_loss'}
VALID_REVENUE_IMPACT_TYPES = {'none', 'at_risk', 'protected', 'expansion', 'lost'}


def load_arc(arc_id: str) -> Optional[Dict[str, Any]]:
    """
    Load a single story arc manifest by ID.

    Args:
        arc_id: e.g. 'arc_expansion_champion' (with or without .json extension)
    Returns:
        Parsed manifest dict or None if not found
    """
    if not arc_id.endswith('.json'):
        arc_id = f'{arc_id}.json'

    arc_path = ARCS_DIR / arc_id
    if not arc_path.exists():
        logger.error(f"Story arc not found: {arc_path}")
        return None

    try:
        with open(arc_path, 'r') as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in {arc_path}: {e}")
        return None


def load_all_arcs() -> Dict[str, Dict[str, Any]]:
    """
    Load all story arc manifests from the arcs directory.

    Returns:
        Dict of arc_id → manifest dict
    """
    arcs = {}
    for path in sorted(ARCS_DIR.glob('arc_*.json')):
        try:
            with open(path, 'r') as f:
                arc = json.load(f)
                arcs[arc['arc_id']] = arc
        except (json.JSONDecodeError, KeyError) as e:
            logger.error(f"Error loading {path}: {e}")
    return arcs


def validate_arc(arc: Dict[str, Any]) -> List[str]:
    """
    Validate a story arc manifest against schema and KPI definitions.

    Returns:
        List of error strings. Empty list = valid.
    """
    errors = []

    # Required top-level fields
    required = ['arc_id', 'arc_name', 'version', 'revenue_narrative',
                'cast', 'phases', 'causal_chains', 'kpi_trajectories',
                'decisions', 'outcomes', 'edges_template']
    for field in required:
        if field not in arc:
            errors.append(f"Missing required field: {field}")

    if errors:
        return errors  # Can't validate further without required fields

    # arc_id format
    if not arc['arc_id'].startswith('arc_'):
        errors.append(f"arc_id must start with 'arc_': got '{arc['arc_id']}'")

    # Target audience
    audience = arc.get('target_audience')
    if audience and audience not in VALID_AUDIENCES:
        errors.append(f"Invalid target_audience: {audience}. Must be one of {VALID_AUDIENCES}")

    # Revenue narrative consistency
    rn = arc['revenue_narrative']
    _validate_revenue_narrative(rn, errors)

    # Cast
    num_phases = len(arc['phases'])
    for i, member in enumerate(arc['cast']):
        _validate_cast_member(member, i, num_phases, errors)

    # Phases
    total_weeks = 0
    for phase in arc['phases']:
        _validate_phase(phase, errors)
        total_weeks += phase.get('duration_weeks', 0)

    if rn.get('time_horizon_weeks') and total_weeks != rn['time_horizon_weeks']:
        errors.append(f"Phase durations sum to {total_weeks}w but time_horizon_weeks is {rn['time_horizon_weeks']}w")

    # KPI code validation across all plot points
    _validate_kpi_references(arc, errors)

    # Causal chains
    for chain in arc.get('causal_chains', []):
        _validate_causal_chain(chain, errors)

    # Decisions
    for decision in arc.get('decisions', []):
        _validate_decision(decision, arc['phases'], errors)

    # Outcomes
    for outcome in arc.get('outcomes', []):
        _validate_outcome(outcome, errors)

    # Edges template
    for edge in arc.get('edges_template', []):
        if 'edge_type' in edge and edge['edge_type'] not in VALID_EDGE_TYPES:
            errors.append(f"Invalid edge_type in edges_template: {edge['edge_type']}")

    return errors


def _validate_revenue_narrative(rn: Dict, errors: List[str]):
    """Validate revenue_narrative internal consistency."""
    required = ['arr_start', 'arr_end', 'arr_at_risk_peak', 'roi_of_intervention',
                'cost_of_inaction', 'time_horizon_weeks']
    for field in required:
        if field not in rn:
            errors.append(f"revenue_narrative missing: {field}")

    # Basic sanity checks
    if rn.get('arr_start', 0) <= 0:
        errors.append("revenue_narrative.arr_start must be positive")
    if rn.get('arr_at_risk_peak', 0) > rn.get('arr_start', 0) * 2:
        errors.append("revenue_narrative.arr_at_risk_peak seems unreasonably high (>2x arr_start)")


def _validate_cast_member(member: Dict, index: int, num_phases: int, errors: List[str]):
    """Validate a cast member."""
    sentiment_arc = member.get('sentiment_arc', [])
    if sentiment_arc and len(sentiment_arc) != num_phases:
        errors.append(f"Cast[{index}] sentiment_arc has {len(sentiment_arc)} values but there are {num_phases} phases")
    for val in sentiment_arc:
        if not -1 <= val <= 1:
            errors.append(f"Cast[{index}] sentiment value {val} out of range [-1, 1]")


def _validate_phase(phase: Dict, errors: List[str]):
    """Validate a phase definition."""
    health = phase.get('health_range', {})
    start = health.get('start', 0)
    end = health.get('end', 0)
    if not (0 <= start <= 100 and 0 <= end <= 100):
        errors.append(f"Phase '{phase.get('name')}' health_range out of bounds: {start}-{end}")

    rit = phase.get('revenue_impact_type')
    if rit and rit not in VALID_REVENUE_IMPACT_TYPES:
        errors.append(f"Phase '{phase.get('name')}' invalid revenue_impact_type: {rit}")

    for pp in phase.get('plot_points', []):
        et = pp.get('event_type')
        if et and et not in VALID_EVENT_TYPES:
            errors.append(f"Phase '{phase.get('name')}' plot_point has invalid event_type: {et}")

        gnt = pp.get('generates_node_type')
        if gnt and gnt not in VALID_NODE_TYPES:
            errors.append(f"Phase '{phase.get('name')}' plot_point has invalid generates_node_type: {gnt}")


def _validate_kpi_references(arc: Dict, errors: List[str]):
    """Validate all KPI codes referenced in the manifest are valid DC2_S codes."""
    referenced_codes = set()

    # Collect from plot_points
    for phase in arc.get('phases', []):
        for pp in phase.get('plot_points', []):
            for impact in pp.get('kpi_impacts', []):
                code = impact.get('kpi_code', '')
                referenced_codes.add(code)

    # Collect from kpi_trajectories
    for pillar_key, traj in arc.get('kpi_trajectories', {}).items():
        for override in traj.get('kpi_overrides', []):
            code = override.get('kpi_code', '')
            referenced_codes.add(code)

    # Collect from industry_benchmarks
    for bench in arc.get('industry_benchmarks', []):
        code = bench.get('kpi_code', '')
        referenced_codes.add(code)

    # Validate
    invalid = referenced_codes - VALID_KPI_CODES
    if invalid:
        errors.append(f"Invalid KPI codes referenced: {sorted(invalid)}")


def _validate_causal_chain(chain: Dict, errors: List[str]):
    """Validate a causal chain."""
    for link in chain.get('links', []):
        et = link.get('edge_type')
        if et and et not in VALID_EDGE_TYPES:
            errors.append(f"Causal chain '{chain.get('name')}' has invalid edge_type: {et}")
        conf = link.get('confidence', 1.0)
        if not 0 <= conf <= 1:
            errors.append(f"Causal chain '{chain.get('name')}' has confidence {conf} out of [0, 1]")


def _get_phase_for_week(week: int, phases: List[Dict]) -> int:
    """Derive the correct phase_id from an absolute week number."""
    cumulative = 0
    for i, phase in enumerate(phases):
        cumulative += phase.get('duration_weeks', 0)
        if week <= cumulative:
            return i
    return len(phases) - 1  # Last phase if week exceeds total


def _validate_decision(decision: Dict, phases: List[Dict], errors: List[str]):
    """Validate a decision point.

    Uses the absolute `week` as source of truth.  If `phase_id` doesn't match
    the week, this is logged as a warning (not error) because the week is
    authoritative for timing.
    """
    week = decision.get('week', 0)
    total_weeks = sum(p.get('duration_weeks', 0) for p in phases)

    if week > total_weeks:
        errors.append(
            f"Decision '{decision.get('title')}' at week {week} exceeds total arc duration {total_weeks}w"
        )

    options = decision.get('options', [])
    chosen = decision.get('chosen_option')
    if chosen is not None and chosen >= len(options):
        errors.append(f"Decision '{decision.get('title')}' chosen_option {chosen} >= len(options) {len(options)}")


def _validate_outcome(outcome: Dict, errors: List[str]):
    """Validate an outcome."""
    ot = outcome.get('outcome_type')
    if ot and ot not in VALID_OUTCOME_TYPES:
        errors.append(f"Outcome '{outcome.get('title')}' has invalid outcome_type: {ot}")
    conf = outcome.get('confidence', 1.0)
    if not 0 <= conf <= 1:
        errors.append(f"Outcome '{outcome.get('title')}' confidence {conf} out of [0, 1]")


def get_arc_summary(arc: Dict[str, Any]) -> Dict[str, Any]:
    """
    Get a concise summary of a story arc for display/logging.
    """
    rn = arc.get('revenue_narrative', {})
    return {
        'arc_id': arc.get('arc_id'),
        'arc_name': arc.get('arc_name'),
        'target_audience': arc.get('target_audience'),
        'duration_weeks': rn.get('time_horizon_weeks'),
        'arr_start': rn.get('arr_start'),
        'arr_end': rn.get('arr_end'),
        'roi_of_intervention': rn.get('roi_of_intervention'),
        'num_phases': len(arc.get('phases', [])),
        'num_decisions': len(arc.get('decisions', [])),
        'num_causal_chains': len(arc.get('causal_chains', [])),
        'num_outcomes': len(arc.get('outcomes', [])),
        'intelligence_dimensions': arc.get('intelligence_dimensions', []),
    }


def get_arcs_by_audience(audience: str) -> List[Dict[str, Any]]:
    """Get all arcs targeting a specific audience (CRO, CFO, CEO)."""
    all_arcs = load_all_arcs()
    return [arc for arc in all_arcs.values() if arc.get('target_audience') == audience]


def validate_all_arcs() -> Dict[str, List[str]]:
    """
    Validate all loaded story arc manifests.

    Returns:
        Dict of arc_id → list of errors (empty list = valid)
    """
    results = {}
    all_arcs = load_all_arcs()
    for arc_id, arc in all_arcs.items():
        results[arc_id] = validate_arc(arc)
    return results


def fix_phase_ids(arc: Dict[str, Any]) -> int:
    """
    Auto-correct decision phase_id values based on absolute week numbers.

    Returns:
        Number of phase_ids corrected
    """
    fixes = 0
    phases = arc.get('phases', [])
    for decision in arc.get('decisions', []):
        week = decision.get('week', 0)
        correct_phase = _get_phase_for_week(week, phases)
        if decision.get('phase_id') != correct_phase:
            decision['phase_id'] = correct_phase
            fixes += 1
    return fixes


def repair_all_arcs(write: bool = False) -> Dict[str, int]:
    """
    Auto-repair all manifests (fix phase_ids). Optionally write back to disk.

    Args:
        write: If True, write corrected manifests back to JSON files
    Returns:
        Dict of arc_id → number of fixes applied
    """
    results = {}
    all_arcs = load_all_arcs()
    for arc_id, arc in all_arcs.items():
        fixes = fix_phase_ids(arc)
        results[arc_id] = fixes
        if fixes > 0 and write:
            arc_path = ARCS_DIR / f'{arc_id}.json'
            with open(arc_path, 'w') as f:
                json.dump(arc, f, indent=2)
            logger.info(f"Repaired {arc_id}: {fixes} phase_ids corrected")
    return results
