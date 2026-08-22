"""
Vertical-Agnostic API v1 Handlers — relocated from verticals/dc2_s/api_routes.py

Phase 5 of the vertical-registry fail-closed refactor (2026-08-22). These 7
handlers were audited and confirmed to contain ZERO DC2_S-specific taxonomy
coupling (no direct references to DC2S_KPIS / DC2S_PILLARS / PLAYBOOK_CONFIG
in their bodies) — they were simply homed in the wrong package. Moving them
here clears 7 of api_v1_routes.py's 11 `verticals.dc2_s.api_routes` import
sites flagged by tests/test_cross_vertical_import_inventory.py.

One exception found during the move: `get_dc2s_health_score` unconditionally
called `_sync_journey_phase()`, which persists a DC2_S-specific lifecycle
label ("deployment"/"performance"/"excellence", from
verticals/dc2_s/vertical_config.py::determine_customer_phase) into
Account.profile_metadata for ANY vertical's account. That call is now gated
to dc2_s only (see `_resolve_vertical_safe` below) — journey_phase has no
defined meaning for saas_premium/datacenter_v1 accounts today.

A handful of scoring/query helpers used by these handlers
(calculate_kpi_health, get_weights_for_customer, get_precalculated_scores,
_get_trailing_kpi_values, _filter_user_accounts, _sync_journey_phase) are
themselves vertical-agnostic in behavior (calculate_kpi_health resolves the
customer's own vertical via utils.vertical_registry internally) but remain
physically defined in verticals/dc2_s/api_routes.py — moving THEM is a
separate, larger cleanup (they're imported from there by several other
files already; see the test_cross_vertical_import_inventory.py baseline for
scripts/generate_context_graph_data.py, utils/vpcs_dashboard_helpers.py,
tests/test_account_health_convergence.py, tests/test_scorer_parity.py).
Importing them here — once, in a single statement — is intentional and
tracked as its own baseline entry rather than silently duplicating scoring
logic in a second location.

verticals/dc2_s/api_routes.py keeps thin delegating wrappers (decorated with
the legacy @dc2s_api.route(...)) so the /api/dc2s/* backward-compat aliases
keep working unchanged; those wrappers import from this module lazily
(inside the function body) to avoid a load-time circular import, since this
module imports FROM verticals.dc2_s.api_routes at module scope.
"""

import logging
from collections import defaultdict
from datetime import datetime, timedelta

from flask import request, jsonify

from auth_middleware import get_current_customer_id
from models import Account, HealthScore, PlaybookExecutionV2
import utils.health_thresholds as ht

# Shared helpers, still homed in verticals/dc2_s/api_routes.py — see module
# docstring above for why they aren't relocated as part of this change.
from verticals.dc2_s.api_routes import (
    calculate_kpi_health,
    get_weights_for_customer,
    get_precalculated_scores,
    _get_trailing_kpi_values,
    _filter_user_accounts,
    _sync_journey_phase,
)

logger = logging.getLogger(__name__)


def _resolve_vertical_safe(customer_id):
    """Best-effort vertical lookup for gating dc2_s-only behavior.

    Returns None (never 'dc2_s') on any failure, so callers that gate
    dc2_s-only side effects (like journey_phase persistence) fail closed —
    skip the dc2_s-only behavior — rather than treating an unresolvable
    customer as if it were dc2_s.
    """
    try:
        from utils.vertical_registry import get_vertical_for_customer
        return get_vertical_for_customer(int(customer_id))
    except Exception:
        return None


# =============================================================================
# Health Score — single account
# =============================================================================

def get_dc2s_health_score(account_id):
    """
    Get health score for a specific account.
    GET /api/dc2s/health-score/123?month=aggregate  (legacy alias)
    GET /api/v1/health-scores/123
    """
    try:
        customer_id = get_current_customer_id()

        if not customer_id:
            return jsonify({'error': 'Customer ID required'}), 400

        # Verify account belongs to customer
        account = Account.query.filter_by(
            account_id=account_id,
            customer_id=int(customer_id),
        ).first()

        if not account:
            return jsonify({'error': 'Account not found'}), 404

        # Get month parameter (for DC, we'll use 'aggregate' to show all KPIs)
        month = request.args.get('month', 'aggregate')
        is_aggregate = (month == 'aggregate')

        # Get all KPIs for this account
        from models import DC2SKPI
        all_kpis = DC2SKPI.query.filter_by(
            account_id=account_id
        ).order_by(DC2SKPI.measured_at.desc()).all()

        # Group by kpi_code, keeping latest (DC KPIs don't have monthly data like SaaS)
        latest_kpis = {}
        for kpi in all_kpis:
            if kpi.kpi_code not in latest_kpis:
                latest_kpis[kpi.kpi_code] = kpi

        # Convert to dict for calculate_kpi_health function
        kpi_values = {kpi_code: float(kpi.value) for kpi_code, kpi in latest_kpis.items()}

        # Calculate overall health score and pillar scores (config-aware)
        overall_health, pillar_scores = calculate_kpi_health(kpi_values, customer_id=customer_id)

        # Phase 0.2: persist journey_phase on every health recalculation.
        # journey_phase (deployment/performance/excellence) is a DC2_S-specific
        # lifecycle concept — applying it to other verticals' accounts would
        # silently mislabel profile_metadata with a phase vocabulary that
        # means nothing for their vertical. Found live on customer 400
        # (datacenter_v1) during the 2026-08-22 cross-vertical cleanup;
        # scoped to dc2_s only here rather than generalizing journey_phase.
        if _resolve_vertical_safe(customer_id) == 'dc2_s':
            _sync_journey_phase(account)

        health_status = ht.classify(overall_health)

        # Format category scores for frontend
        category_scores = {}
        for pillar, score in pillar_scores.items():
            category_scores[pillar] = {
                'score': score,
                'weight': get_weights_for_customer(customer_id).get(pillar, {}).get('weight', 0.2)
            }

        return jsonify({
            'account_id': account_id,
            'account_name': account.account_name,
            'overall_score': round(overall_health, 2),
            'health_status': health_status,
            'category_scores': category_scores,
            'kpi_count': len(latest_kpis),
            'month': month if not is_aggregate else None,
            'is_aggregate': is_aggregate,
            'timestamp': datetime.utcnow().isoformat()
        })

    except Exception as e:
        logger.error(f"Error fetching health score: {e}", exc_info=True)
        return jsonify({'error': 'Failed to fetch health score'}), 500


# =============================================================================
# Health Summary — portfolio
# =============================================================================

def get_dc2s_health_summary():
    """
    Get health summary across all accounts for current customer.
    GET /api/dc2s/health-summary  (legacy alias)
    GET /api/v1/health-summary
    """
    try:
        customer_id = get_current_customer_id()

        if not customer_id:
            return jsonify({'error': 'Customer ID required'}), 400

        accounts = Account.query.filter(
            Account.customer_id == int(customer_id),
        ).all()

        # Apply user-level account filtering (contractors/restricted users)
        accounts = _filter_user_accounts(accounts, key='account_id')

        account_health = []  # list of (health_score, revenue)
        healthy_count = 0
        risk_count = 0
        critical_count = 0

        for account in accounts:
            # Trailing 30-day weighted average for stable health scores
            trailing_kpis = _get_trailing_kpi_values(account.account_id, days=30)

            if trailing_kpis:
                health, _ = calculate_kpi_health(trailing_kpis, customer_id=customer_id)
                revenue = float(account.revenue) if account.revenue else 0
                account_health.append((health, revenue))

                if health >= ht.healthy_min():
                    healthy_count += 1
                elif health >= ht.at_risk_min():
                    risk_count += 1
                else:
                    critical_count += 1

        # L4: Revenue-weighted average of L3 account health scores
        total_revenue = sum(rev for _, rev in account_health)
        if total_revenue > 0:
            avg_health = sum(h * r for h, r in account_health) / total_revenue
        else:
            avg_health = sum(h for h, _ in account_health) / len(account_health) if account_health else 0

        # Also compute simple (unweighted) average for comparison
        simple_avg = (
            round(sum(h for h, _ in account_health) / len(account_health), 1)
            if account_health else 0
        )

        # ARR Exposure = total ARR sitting in at-risk/critical accounts
        arr_exposure = sum(
            rev for h, rev in account_health
            if h < ht.healthy_min()
        )

        return jsonify({
            'total_accounts': len(accounts),
            'average_health': round(avg_health, 1),
            'avg_health_simple': simple_avg,
            'health_avg_method': 'revenue_weighted' if total_revenue > 0 else 'simple',
            'health_avg_method_label': (
                'Revenue-weighted average' if total_revenue > 0
                else 'Simple average (no revenue data)'
            ),
            'healthy_accounts': healthy_count,
            'risk_accounts': risk_count,
            'critical_accounts': critical_count,
            'total_arr': round(total_revenue),
            'arr_exposure': round(arr_exposure, 2),
            'arr_exposure_label': 'Exposure (ARR in at-risk accounts)',
            'health_distribution': {
                'healthy': healthy_count,
                'risk': risk_count,
                'critical': critical_count
            }
        })

    except Exception as e:
        logger.error(f"Error fetching health summary: {e}", exc_info=True)
        return jsonify({'error': 'Failed to fetch health summary'}), 500


# =============================================================================
# Health Score History — portfolio trajectory + per-account monthly scores
# =============================================================================

def get_health_score_history_api():
    """GET /api/dc2s/health-score-history?account_id=<optional>&months=<optional>  (legacy alias)
    GET /api/v1/health-score-history
    Returns monthly health score trajectory for portfolio (account_id=0 or omitted)
    or a single account.
    """
    try:
        customer_id = get_current_customer_id()
        if not customer_id:
            return jsonify({'error': 'Customer ID required'}), 400

        account_id = request.args.get('account_id', 0, type=int)
        months = min(max(request.args.get('months', 6, type=int), 1), 12)

        cutoff = (datetime.utcnow() - timedelta(days=months * 31)).replace(
            day=1, hour=0, minute=0, second=0, microsecond=0,
        )

        if account_id and account_id != 0:
            accounts = [Account.query.filter_by(
                account_id=account_id, customer_id=int(customer_id)
            ).first()]
            if not accounts[0]:
                return jsonify({'error': f'Account {account_id} not found'}), 404
        else:
            accounts = Account.query.filter_by(customer_id=int(customer_id)).all()

        if not accounts:
            return jsonify({'error': 'No accounts found'}), 404

        portfolio_history = []
        transitions = []

        for acct in accounts:
            scores = (HealthScore.query
                .filter(
                    HealthScore.account_id == acct.account_id,
                    HealthScore.measurement_month >= cutoff,
                )
                .order_by(HealthScore.measurement_month.asc())
                .all())

            if not scores:
                continue

            monthly = []
            prev_status = None
            for s in scores:
                score_val = float(s.health_score) if s.health_score else 0
                status = ht.classify(score_val)
                change = float(s.change_from_last_month) if s.change_from_last_month else 0

                entry = {
                    'month': s.measurement_month.strftime('%Y-%m'),
                    'health_score': round(score_val, 1),
                    'status': status,
                    'change': round(change, 1),
                    'pillars': s.contributing_pillars or {},
                }
                monthly.append(entry)

                if prev_status and prev_status != status:
                    transitions.append({
                        'account_id': acct.account_id,
                        'account_name': acct.account_name,
                        'month': s.measurement_month.strftime('%Y-%m'),
                        'from_status': prev_status,
                        'to_status': status,
                        'score': round(score_val, 1),
                        'arr': float(acct.revenue or 0),
                    })
                prev_status = status

            if monthly:
                first_score = monthly[0]['health_score']
                last_score = monthly[-1]['health_score']
                portfolio_history.append({
                    'account_id': acct.account_id,
                    'account_name': acct.account_name,
                    'arr': float(acct.revenue or 0),
                    'current_health': last_score,
                    'current_status': monthly[-1]['status'],
                    'starting_health': first_score,
                    'net_change': round(last_score - first_score, 1),
                    'trajectory': (
                        'improving' if last_score - first_score > 5
                        else 'declining' if last_score - first_score < -5
                        else 'stable'
                    ),
                    'monthly_scores': monthly,
                })

        portfolio_history.sort(key=lambda x: x['net_change'])

        improving = [a for a in portfolio_history if a['trajectory'] == 'improving']
        declining = [a for a in portfolio_history if a['trajectory'] == 'declining']
        stable = [a for a in portfolio_history if a['trajectory'] == 'stable']

        turnarounds = [
            {'account': a['account_name'], 'arr': a['arr'], 'change': a['net_change']}
            for a in portfolio_history
            if a.get('current_status') == 'healthy' and a['starting_health'] < ht.healthy_min()
        ]
        deteriorations = [
            {'account': a['account_name'], 'arr': a['arr'], 'change': a['net_change']}
            for a in portfolio_history
            if a['current_health'] < ht.healthy_min() and a['starting_health'] >= ht.healthy_min()
        ]

        # Portfolio trajectory
        total_arr = sum(a['arr'] for a in portfolio_history) or 1
        portfolio_trajectory = {
            'improving_count': len(improving),
            'declining_count': len(declining),
            'stable_count': len(stable),
            'improving_arr_pct': round(sum(a['arr'] for a in improving) / total_arr * 100, 1),
            'declining_arr_pct': round(sum(a['arr'] for a in declining) / total_arr * 100, 1),
        }

        return jsonify({
            'months': months,
            'account_count': len(portfolio_history),
            'accounts': portfolio_history,
            'transitions': transitions,
            'turnarounds': turnarounds,
            'deteriorations': deteriorations,
            'portfolio_trajectory': portfolio_trajectory,
        })

    except Exception as e:
        logger.error(f"Error computing health score history: {e}", exc_info=True)
        return jsonify({'error': 'Failed to compute health score history'}), 500


# =============================================================================
# CSM Scorecard
# =============================================================================

def get_csm_scorecard_api():
    """GET /api/dc2s/csm-scorecard?csm_name=<optional>  (legacy alias)
    GET /api/v1/csm-scorecard
    Returns per-CSM accounts managed, health delta, playbook success, revenue impact.
    """
    try:
        customer_id = get_current_customer_id()
        if not customer_id:
            return jsonify({'error': 'Customer ID required'}), 400

        csm_name_filter = request.args.get('csm_name', None)
        accounts = Account.query.filter_by(customer_id=int(customer_id)).all()

        # Group accounts by assigned CSM from profile metadata
        csm_accounts = defaultdict(list)
        for acct in accounts:
            meta = acct.profile_metadata if hasattr(acct, 'profile_metadata') and acct.profile_metadata else {}
            csm = meta.get('assigned_csm') or meta.get('csm_name') or 'Unassigned'
            if csm_name_filter and csm_name_filter.lower() not in csm.lower():
                continue
            csm_accounts[csm].append(acct)

        scorecards = {}
        for csm, accts in csm_accounts.items():
            acct_ids = [a.account_id for a in accts]
            total_arr = sum(float(a.revenue or 0) for a in accts)

            # Health deltas from HealthScore table
            health_deltas = []
            for aid in acct_ids:
                scores = (HealthScore.query
                    .filter_by(account_id=aid)
                    .order_by(HealthScore.measurement_month.asc())
                    .all())
                if len(scores) >= 2:
                    delta = float(scores[-1].health_score or 0) - float(scores[0].health_score or 0)
                    health_deltas.append(delta)

            # Playbook executions on this CSM's accounts
            try:
                execs = PlaybookExecutionV2.query.filter(
                    PlaybookExecutionV2.account_id.in_(acct_ids),
                    PlaybookExecutionV2.customer_id == int(customer_id),
                ).all()
            except Exception:
                execs = []

            resolved = sum(1 for e in execs if e.outcome == 'resolved')
            rev_protected = sum(float(e.revenue_protected or 0) for e in execs)
            rev_expanded = sum(float(e.revenue_expanded or 0) for e in execs)

            scorecards[csm] = {
                'csm_name': csm,
                'accounts_managed': len(accts),
                'total_arr': total_arr,
                'avg_health_delta': round(sum(health_deltas) / len(health_deltas), 1) if health_deltas else 0,
                'accounts_improving': sum(1 for d in health_deltas if d > 5),
                'accounts_declining': sum(1 for d in health_deltas if d < -5),
                'playbooks_executed': len(execs),
                'playbooks_resolved': resolved,
                'success_rate_pct': round(resolved / len(execs) * 100, 1) if execs else 0,
                'revenue_protected': rev_protected,
                'revenue_expanded': rev_expanded,
                'total_revenue_impact': rev_protected + rev_expanded,
            }

        return jsonify({
            'csm_count': len(scorecards),
            'scorecards': scorecards,
        })

    except Exception as e:
        logger.error(f"Error computing CSM scorecard: {e}", exc_info=True)
        return jsonify({'error': 'Failed to compute CSM scorecard'}), 500


# =============================================================================
# Team Capacity — FTE utilization by role
# =============================================================================

def get_team_capacity_api():
    """GET /api/dc2s/team-capacity  (legacy alias)
    GET /api/v1/team-capacity
    Returns team capacity utilization, bottleneck detection, portfolio context.
    """
    try:
        customer_id = get_current_customer_id()
        if not customer_id:
            return jsonify({'error': 'Customer ID required'}), 400

        accounts = Account.query.filter_by(customer_id=int(customer_id)).all()
        total_arr = sum(float(a.revenue or 0) for a in accounts)

        # Pre-load health scores for at-risk count
        _health_map = {}
        for acct in accounts:
            h, _, _, _ = get_precalculated_scores(acct.account_id)
            _health_map[acct.account_id] = h or 100
        at_risk_count = sum(1 for a in accounts if _health_map.get(a.account_id, 100) < ht.healthy_min())

        # Group accounts by CSM for real CSM count
        csm_set = set()
        for acct in accounts:
            meta = acct.profile_metadata if hasattr(acct, 'profile_metadata') and acct.profile_metadata else {}
            csm = meta.get('assigned_csm') or meta.get('csm_name')
            if csm and csm != 'Unassigned':
                csm_set.add(csm)
        csm_count = max(len(csm_set), 1)
        accounts_per_csm = round(len(accounts) / csm_count, 1)

        # Active playbook executions
        try:
            active_execs = PlaybookExecutionV2.query.filter_by(
                customer_id=int(customer_id)
            ).filter(
                PlaybookExecutionV2.outcome.is_(None)
            ).all()
            recent_cutoff = datetime.utcnow() - timedelta(days=90)
            recent_execs = PlaybookExecutionV2.query.filter(
                PlaybookExecutionV2.customer_id == int(customer_id),
                PlaybookExecutionV2.triggered_at >= recent_cutoff,
            ).all()
        except Exception:
            active_execs = []
            recent_execs = []

        active_csm_hours = sum(float(e.csm_hours_planned or 0) for e in active_execs)
        target_per_csm = 6

        # ── Per-CSM capacity breakdown ──
        per_csm_breakdown = []
        acct_by_csm = {}
        for acct in accounts:
            meta = acct.profile_metadata if hasattr(acct, 'profile_metadata') and acct.profile_metadata else {}
            csm = meta.get('assigned_csm') or meta.get('csm_name') or 'Unassigned'
            acct_by_csm.setdefault(csm, []).append(acct)

        # Map active playbook executions to accounts for per-CSM aggregation
        active_exec_by_acct = {}
        for ex in active_execs:
            active_exec_by_acct.setdefault(ex.account_id, []).append(ex)

        hours_per_week = 40  # Standard CSM work week
        for csm_name in sorted(acct_by_csm.keys()):
            csm_accts = acct_by_csm[csm_name]
            csm_acct_ids = {a.account_id for a in csm_accts}
            csm_active_execs = [ex for aid in csm_acct_ids for ex in active_exec_by_acct.get(aid, [])]
            hours_committed = sum(float(e.csm_hours_planned or 0) for e in csm_active_execs)
            csm_arr = sum(float(a.revenue or 0) for a in csm_accts)
            csm_at_risk = sum(1 for a in csm_accts if _health_map.get(a.account_id, 100) < ht.healthy_min())
            per_csm_breakdown.append({
                'csm_name': csm_name,
                'accounts_managed': len(csm_accts),
                'total_arr': csm_arr,
                'active_playbooks': len(csm_active_execs),
                'hours_committed': round(hours_committed, 1),
                'hours_available': hours_per_week,
                'utilization_pct': round(hours_committed / hours_per_week * 100, 1) if hours_per_week > 0 else 0,
                'at_risk_accounts': csm_at_risk,
            })

        # ── Hours-based resource-pool view (mirrors MCP get_team_capacity) ──
        resource_pool = None
        hours_utilization_pct = {}
        hours_feasible = True
        bottleneck_roles: list = []
        overflow_hours = 0.0
        recommendation_text = ''
        try:
            import resource_capacity_model as rcm
            resource_pool = rcm.get_resource_pool_summary()

            # Roll planned hours across the 5 roles using the same heuristic
            # as the MCP tool: CSM hours come from PlaybookExecutionV2; CS_OPS
            # and PLATFORM are approximated as a fraction of CSM hours so the
            # gauge reflects multi-role load, not just CSM.
            hours_by_role = {
                rcm.CSRole.CSM: 0.0,
                rcm.CSRole.CS_OPS: 0.0,
                rcm.CSRole.PRODUCT: 0.0,
                rcm.CSRole.PLATFORM: 0.0,
                rcm.CSRole.LEADERSHIP: 0.0,
            }
            for e in active_execs:
                csm_hrs = float(getattr(e, 'csm_hours_planned', 0) or 0)
                hours_by_role[rcm.CSRole.CSM] += csm_hrs
                hours_by_role[rcm.CSRole.CS_OPS] += csm_hrs * 0.5
                hours_by_role[rcm.CSRole.PLATFORM] += csm_hrs * 0.2

            try:
                cap = rcm.check_capacity(hours_by_role)
                hours_feasible = cap.is_feasible
                hours_utilization_pct = {r: round(u * 100, 1) for r, u in cap.utilization_by_role.items()}
                bottleneck_roles = [cap.bottleneck_role] if cap.bottleneck_role and not cap.is_feasible else []
                overflow_hours = float(cap.overflow_hours or 0.0)
            except Exception:
                hours_utilization_pct = {r.value: 0.0 for r in hours_by_role.keys()}

            planned_hours_out = {r.value: round(h, 1) for r, h in hours_by_role.items()}

            # Aggregate annual hours/cost across the pool
            totals = (resource_pool or {}).get('totals', {}) or {}
            total_hours_available = float(totals.get('total_hours', 0) or 0)
            total_hours_planned = sum(planned_hours_out.values())
            total_hours_utilization_pct = round(
                (total_hours_planned / total_hours_available * 100), 1
            ) if total_hours_available > 0 else 0.0

            recommendation_text = (
                f"Team is {'within' if hours_feasible else 'over'} capacity. "
                + ("No bottlenecks." if not bottleneck_roles else f"Bottleneck roles: {', '.join(bottleneck_roles)}.")
                + f" {at_risk_count} at-risk accounts need attention."
            )
        except Exception as _cap_err:
            logger.debug("team-capacity hours rollup unavailable: %s", _cap_err)
            planned_hours_out = {}
            total_hours_available = 0.0
            total_hours_planned = 0.0
            total_hours_utilization_pct = 0.0

        capacity_planning = {}
        uncovered_at_risk = []
        try:
            from utils.vpcs_dashboard_helpers import (
                build_capacity_planning,
                build_uncovered_at_risk,
            )
            capacity_planning = build_capacity_planning(int(customer_id), accounts)
            uncovered_at_risk = build_uncovered_at_risk(int(customer_id), accounts)
        except Exception as _vpcs_err:
            logger.debug("VPCS capacity planning unavailable: %s", _vpcs_err)

        return jsonify({
            # ── Legacy fields (preserved for callers that consume them) ──
            'csm_count': csm_count,
            'csm_names': sorted(csm_set),
            'accounts_per_csm': accounts_per_csm,
            'target_per_csm': target_per_csm,
            'total_accounts': len(accounts),
            'active_playbooks': len(active_execs),
            'recent_playbooks_90d': len(recent_execs),
            'active_csm_hours': round(active_csm_hours, 1),
            'at_risk_accounts': at_risk_count,
            'total_arr': total_arr,
            'utilization_pct': round(accounts_per_csm / target_per_csm * 100, 1),
            'per_csm_breakdown': per_csm_breakdown,
            # ── Hours-based resource view (new, mirrors MCP get_team_capacity) ──
            'resource_pool': resource_pool,
            'planned_hours': planned_hours_out,
            'hours_utilization_pct': hours_utilization_pct,
            'total_hours_available': total_hours_available,
            'total_hours_planned': total_hours_planned,
            'total_hours_utilization_pct': total_hours_utilization_pct,
            'feasible': hours_feasible,
            'bottleneck_roles': bottleneck_roles,
            'overflow_hours': overflow_hours,
            'recommendation': recommendation_text,
            'capacity_planning': capacity_planning,
            'uncovered_at_risk': uncovered_at_risk,
        })

    except Exception as e:
        logger.error(f"Error computing team capacity: {e}", exc_info=True)
        return jsonify({'error': 'Failed to compute team capacity'}), 500


# =============================================================================
# Renewals Pipeline — accounts with upcoming renewals + risk assessment
# =============================================================================

def get_renewals_api():
    """GET /api/dc2s/renewals?days=90  (legacy alias)
    GET /api/v1/renewals
    Returns accounts with renewal_date within window, sorted by risk.
    Risk = health score × days until renewal.
    """
    try:
        customer_id = get_current_customer_id()
        if not customer_id:
            return jsonify({'error': 'Customer ID required'}), 400

        days_window = int(request.args.get('days', 90))
        accounts = Account.query.filter_by(customer_id=int(customer_id)).all()

        from datetime import date as _date
        today = _date.today()
        renewals = []

        for acct in accounts:
            meta = acct.profile_metadata or {}
            rd_str = meta.get('renewal_date') or meta.get('contract_renewal_date') or meta.get('contract_end')
            if not rd_str:
                continue
            try:
                rd = datetime.strptime(str(rd_str)[:10], '%Y-%m-%d').date()
            except (ValueError, TypeError):
                continue

            days_until = (rd - today).days
            if days_until < 0 or days_until > days_window:
                continue

            # Get health score
            h, status, _, _ = get_precalculated_scores(acct.account_id)
            health = h or 50

            # Risk level based on health + days
            if health < ht.at_risk_min() and days_until <= 30:
                risk_level = 'critical'
            elif health < ht.healthy_min() and days_until <= 60:
                risk_level = 'high'
            elif health < ht.healthy_min() or days_until <= 30:
                risk_level = 'medium'
            else:
                risk_level = 'low'

            csm = meta.get('assigned_csm') or meta.get('csm_name') or 'Unassigned'
            champion = meta.get('primary_champion_name')

            renewals.append({
                'account_id': acct.account_id,
                'account_name': acct.account_name,
                'arr': float(acct.revenue or 0),
                'health_score': round(health, 1),
                'renewal_date': str(rd),
                'days_until': days_until,
                'risk_level': risk_level,
                'csm_name': csm,
                'champion_name': champion,
                'industry': acct.industry,
            })

        # Sort: critical first, then by days_until ascending
        risk_order = {'critical': 0, 'high': 1, 'medium': 2, 'low': 3}
        renewals.sort(key=lambda r: (risk_order.get(r['risk_level'], 9), r['days_until']))

        total_arr = sum(r['arr'] for r in renewals)
        critical_count = sum(1 for r in renewals if r['risk_level'] in ('critical', 'high'))
        critical_arr = sum(r['arr'] for r in renewals if r['risk_level'] in ('critical', 'high'))

        return jsonify({
            'renewals': renewals,
            'summary': {
                'total_count': len(renewals),
                'total_arr': total_arr,
                'critical_count': critical_count,
                'critical_arr': critical_arr,
                'days_window': days_window,
            },
        })

    except Exception as e:
        logger.error(f"Error computing renewals: {e}", exc_info=True)
        return jsonify({'error': 'Failed to compute renewals'}), 500


# =============================================================================
# Playbook Success Metrics — aggregated by playbook_id
# =============================================================================

def get_playbook_success_metrics_api():
    """GET /api/dc2s/playbook-success-metrics  (legacy alias)
    GET /api/v1/playbook-success-metrics
    Returns per-playbook execution outcomes, success rates, and ROI.
    """
    try:
        customer_id = get_current_customer_id()
        if not customer_id:
            return jsonify({'error': 'Customer ID required'}), 400

        try:
            execs = PlaybookExecutionV2.query.filter_by(customer_id=int(customer_id)).all()
        except Exception:
            execs = []

        if not execs:
            return jsonify({
                'total_executions': 0,
                'playbooks': {},
                'portfolio_summary': {
                    'total_runs': 0,
                    'overall_success_rate_pct': 0,
                    'total_revenue_impact': 0,
                },
            })

        by_pb = defaultdict(list)
        for e in execs:
            by_pb[e.playbook_id].append(e)

        playbooks = {}
        total_resolved = 0
        total_runs = 0
        total_revenue = 0

        for pb_id, pb_execs in by_pb.items():
            n = len(pb_execs)
            resolved = sum(1 for e in pb_execs if e.outcome == 'resolved')
            rev_protected = sum(float(e.revenue_protected or 0) for e in pb_execs)
            rev_expanded = sum(float(e.revenue_expanded or 0) for e in pb_execs)
            health_deltas = [float(e.health_delta or 0) for e in pb_execs if e.health_delta]

            playbooks[pb_id] = {
                'playbook_id': pb_id,
                'total_executions': n,
                'resolved': resolved,
                'success_rate_pct': round(resolved / n * 100, 1) if n else 0,
                'avg_health_delta': round(sum(health_deltas) / len(health_deltas), 1) if health_deltas else 0,
                'total_revenue_protected': rev_protected,
                'total_revenue_expanded': rev_expanded,
            }

            total_resolved += resolved
            total_runs += n
            total_revenue += rev_protected + rev_expanded

        return jsonify({
            'total_executions': total_runs,
            'playbooks': playbooks,
            'portfolio_summary': {
                'total_runs': total_runs,
                'overall_success_rate_pct': round(total_resolved / total_runs * 100, 1) if total_runs else 0,
                'total_revenue_impact': total_revenue,
            },
        })

    except Exception as e:
        logger.error(f"Error computing playbook success metrics: {e}", exc_info=True)
        return jsonify({'error': 'Failed to compute playbook success metrics'}), 500
