#!/usr/bin/env python3
"""
CS Pulse MCP — Admin / Operational Intelligence Tools.

5 tools moved from cs_pulse_mcp_server.py:
  - get_crm_account_data
  - get_support_tickets
  - get_customer_feedback
  - get_csm_daily_actions
  - partner_portal

All tools register on the shared `mcp` instance from cs_pulse_mcp_server.
"""

import os

from cs_pulse_mcp_server import (
    mcp,
    _check_mcp_enabled,
    _require_auth,
    _require_account_auth,
    _get_flask_app,
    _validate_account_ownership,
    _get_account_arr,
    _resolve_customer_vertical,
    _get_health_functions,
    _get_kpi_definitions,
    _get_playbook_config,
    _get_pillar_labels,
    _ensure_registry,
    _backend_dir,
    ToolError,
)


# ---------------------------------------------------------------------------
# Helpers for CRM / feedback tools (local to this module)
# ---------------------------------------------------------------------------

def _get_account_profile(account) -> dict:
    """Safely extract profile_metadata fields with defaults.
    Falls back to context graph STAKEHOLDER nodes for champion data
    when profile_metadata is empty (common for load-driver provisioned accounts).
    """
    meta = account.profile_metadata if isinstance(account.profile_metadata, dict) else {}

    champion_name = meta.get("primary_champion_name", "")
    champion_title = meta.get("champion_title", "")
    champion_email = meta.get("champion_email", "")
    champion_status = meta.get("champion_status", "Unknown")
    executive_sponsor = meta.get("executive_sponsor", "")
    assigned_csm = meta.get("assigned_csm", "Unassigned")

    # Fall back to context graph stakeholder nodes if champion is empty
    if not champion_name:
        try:
            from models import ContextNode
            stakeholders = ContextNode.query.filter_by(
                account_id=account.account_id,
                node_type='STAKEHOLDER',
            ).all()
            for s in stakeholders:
                props = s.properties if isinstance(s.properties, dict) else {}
                role = s.node_subtype or props.get('role', '')
                if role in ('champion', 'executive_sponsor', 'VP Product', 'primary_contact'):
                    champion_name = s.title or ''
                    # Title is stored as "Name (Job Title)" — extract job title
                    if '(' in champion_name and ')' in champion_name:
                        champion_title = champion_name.split('(')[1].rstrip(')')
                        champion_name = champion_name.split('(')[0].strip()
                    else:
                        champion_title = props.get('job_title', role)
                    champion_email = props.get('email', '')
                    champion_status = 'Active' if role != 'departed' else 'Departed'
                    break
            # Also find executive sponsor
            if not executive_sponsor:
                for s in stakeholders:
                    role = s.node_subtype or ''
                    if role == 'executive_sponsor':
                        executive_sponsor = s.title or ''
                        if '(' in executive_sponsor:
                            executive_sponsor = executive_sponsor.split('(')[0].strip()
            # Find CSM from engagement signals
            if assigned_csm == "Unassigned":
                for s in stakeholders:
                    props = s.properties if isinstance(s.properties, dict) else {}
                    role = s.node_subtype or ''
                    if 'csm' in role.lower():
                        assigned_csm = s.title or ''
                        if '(' in assigned_csm:
                            assigned_csm = assigned_csm.split('(')[0].strip()
                        break
        except Exception:
            pass

        # Write back resolved CSM to profile_metadata for fast subsequent lookups
        if assigned_csm != "Unassigned" and not meta.get('assigned_csm'):
            try:
                from app_v3_minimal import db as _wdb
                account.profile_metadata = {**(account.profile_metadata or {}), 'assigned_csm': assigned_csm}
                _wdb.session.commit()
            except Exception:
                pass

    return {
        "assigned_csm": assigned_csm,
        "executive_sponsor": executive_sponsor,
        "contract_start_date": meta.get("contract_start_date", ""),
        "contract_end_date": meta.get("contract_end_date", ""),
        "renewal_date": meta.get("renewal_date", ""),
        "champion_name": champion_name,
        "champion_title": champion_title,
        "champion_email": champion_email,
        "champion_status": champion_status,
        "champion_influence_level": meta.get("champion_influence_level", ""),
        "economic_buyer": meta.get("economic_buyer_name", ""),
        "industry": meta.get("industry", ""),
        "region": meta.get("region", ""),
        "tier": meta.get("account_tier", ""),
        "products_used": meta.get("products_used", ""),
    }


def _compute_renewal_stage(days_until_renewal: int, health_status: str) -> dict:
    """Derive CRM renewal stage and probability from days remaining and health."""
    if days_until_renewal > 180:
        stage, forecast = "Early Renewal", "Pipeline"
    elif days_until_renewal > 90:
        stage, forecast = "Renewal Discussion", "Best Case"
    elif days_until_renewal > 30:
        stage, forecast = "Negotiation", "Commit"
    elif days_until_renewal > 0:
        stage, forecast = "Final Review", "Commit"
    else:
        stage, forecast = "Overdue", "Omitted"

    prob = {"healthy": 90, "at_risk": 65, "critical": 35}.get(health_status, 70)
    return {"stage": stage, "probability": prob, "forecast_category": forecast}


def _derive_nps_from_signals(signals) -> dict:
    """Compute NPS proxy from QualitativeSignal sentiment distribution."""
    if not signals:
        return {"score": 0, "trend": "unknown", "response_count": 0}

    total = len(signals)
    positive = sum(1 for s in signals if getattr(s, 'sentiment', '') == 'positive')
    negative = sum(1 for s in signals if getattr(s, 'sentiment', '') == 'negative')

    nps = int(((positive - negative) / total) * 100) if total else 0

    mid = total // 2
    if mid > 0:
        older_half_pos = sum(1 for s in signals[mid:] if getattr(s, 'sentiment', '') == 'positive')
        newer_half_pos = sum(1 for s in signals[:mid] if getattr(s, 'sentiment', '') == 'positive')
        trend = "improving" if newer_half_pos > older_half_pos else (
            "declining" if newer_half_pos < older_half_pos else "stable"
        )
    else:
        trend = "stable"

    return {"score": nps, "trend": trend, "response_count": total}


# ===================================================================
# Tool: get_crm_account_data
# ===================================================================

@mcp.tool
def get_crm_account_data(customer_id: int, account_id: int) -> dict:
    """Pull CRM data for an account — contract details, renewal opportunity, champion contacts, usage metrics. Simulates Salesforce integration; reads from CS Pulse platform data.

    Args:
        customer_id: The customer (tenant) ID
        account_id: The account to pull CRM data for
    """
    _check_mcp_enabled()
    _require_account_auth(customer_id, account_id)
    app = _get_flask_app()

    with app.app_context():
        vertical = _resolve_customer_vertical(customer_id)
        calculate_kpi_health, _get_trailing_kpi_values, get_precalculated_scores = _get_health_functions(vertical)
        import utils.health_thresholds as ht
        from datetime import datetime, date

        account = _validate_account_ownership(customer_id, account_id)

        profile = _get_account_profile(account)
        arr = _get_account_arr(account)

        precalc_health, precalc_status, precalc_pillars = get_precalculated_scores(account_id)
        kpi_values = _get_trailing_kpi_values(account_id)

        if precalc_health is not None:
            health = precalc_health
            health_status = precalc_status
        else:
            health, pillars = calculate_kpi_health(kpi_values, customer_id)
            health_status = ht.classify(health)

        days_until_renewal = 180
        if profile["contract_end_date"]:
            try:
                end_date = datetime.strptime(str(profile["contract_end_date"])[:10], "%Y-%m-%d").date()
                days_until_renewal = (end_date - date.today()).days
            except (ValueError, TypeError):
                pass

        renewal = _compute_renewal_stage(days_until_renewal, health_status)

        gpu_util = kpi_values.get("P3-KPI1", 0)
        capacity_util = kpi_values.get("P5-KPI1", 0)
        uptime = kpi_values.get("P2-KPI4", 0)

        return {
            "scope": "account",
            "source": "salesforce_simulated",
            "account_id": account_id,
            "account_name": account.account_name,
            "crm_id": f"SF-{account_id}",
            "industry": profile["industry"] or getattr(account, 'industry', ''),
            "region": profile["region"] or getattr(account, 'region', ''),
            "contract": {
                "start_date": profile["contract_start_date"],
                "end_date": profile["contract_end_date"],
                "renewal_date": profile["renewal_date"],
                "days_until_renewal": days_until_renewal,
                "arr": arr,
                "mrr": round(arr / 12, 2) if arr else 0,
            },
            "renewal_opportunity": {
                "stage": renewal["stage"],
                "probability": renewal["probability"],
                "amount": arr,
                "forecast_category": renewal["forecast_category"],
            },
            "champion": {
                "name": profile["champion_name"],
                "title": profile["champion_title"],
                "email": profile["champion_email"],
                "status": profile["champion_status"],
                "influence_level": profile["champion_influence_level"],
            },
            "executive_sponsor": profile["executive_sponsor"],
            "assigned_csm": profile["assigned_csm"],
            "account_tier": profile["tier"],
            "health_score": round(health, 1),
            "health_status": health_status,
            "usage_summary": {
                "gpu_utilization_pct": round(gpu_util, 1),
                "capacity_utilization_pct": round(capacity_util, 1),
                "system_uptime_pct": round(uptime, 1),
            },
        }


# ===================================================================
# Tool: get_support_tickets
# ===================================================================

@mcp.tool
def get_support_tickets(customer_id: int, account_id: int) -> dict:
    """Pull support ticket summary for an account — open tickets, SLA compliance, escalations, risk indicators. Simulates ServiceNow integration; derives ticket data from operational KPIs and qualitative signals.

    Args:
        customer_id: The customer (tenant) ID
        account_id: The account to pull ticket data for
    """
    _check_mcp_enabled()
    _require_account_auth(customer_id, account_id)
    app = _get_flask_app()

    with app.app_context():
        from models import QualitativeSignal
        vertical = _resolve_customer_vertical(customer_id)
        _, _get_trailing_kpi_values, _ = _get_health_functions(vertical)
        import math

        account = _validate_account_ownership(customer_id, account_id)

        kpi_values = _get_trailing_kpi_values(account_id)

        critical_incidents = kpi_values.get("P2-KPI3", 0)
        mttr_hours = kpi_values.get("P2-KPI7", 4.0)
        uptime_pct = kpi_values.get("P2-KPI4", 99.9)
        mtbf_hours = kpi_values.get("P2-KPI2", 720)
        rma_rate = kpi_values.get("P2-KPI1", 2.0)
        thermal_score = kpi_values.get("P2-KPI5", 85)
        preventive_maint = kpi_values.get("P2-KPI8", 90)

        open_tickets = max(0, math.ceil(critical_incidents))
        resolved_last_30d = max(0, open_tickets + int(critical_incidents * 1.5))

        resolution_target_hours = 4.0
        resolution_sla_met = mttr_hours <= resolution_target_hours
        sla_breaches = max(0, math.ceil((mttr_hours - resolution_target_hours) * 2)) if not resolution_sla_met else 0

        from datetime import date
        recent_signals = QualitativeSignal.query.filter(
            QualitativeSignal.customer_id == int(customer_id),
            QualitativeSignal.account_id == int(account_id),
            QualitativeSignal.sentiment == 'negative',
            QualitativeSignal.signal_date <= date.today(),
        ).order_by(QualitativeSignal.signal_date.desc()).limit(10).all()

        escalation_entries = []
        for sig in recent_signals[:3]:
            escalation_entries.append({
                "date": sig.signal_date.strftime('%Y-%m-%d') if sig.signal_date else "",
                "summary": (getattr(sig, 'content', '') or "")[:200],
                "stakeholder": getattr(sig, 'stakeholder_level', '') or "",
            })

        return {
            "scope": "account",
            "source": "servicenow_simulated",
            "account_id": account_id,
            "account_name": account.account_name,
            "ticket_summary": {
                "open_tickets": open_tickets,
                "resolved_last_30d": resolved_last_30d,
                "critical_incidents_30d": round(critical_incidents, 1),
                "avg_resolution_hours": round(mttr_hours, 1),
                "mtbf_hours": round(mtbf_hours, 1),
                "system_uptime_pct": round(uptime_pct, 2),
            },
            "sla_compliance": {
                "overall_pct": round(uptime_pct, 2),
                "response_sla_met": uptime_pct >= 99.5,
                "resolution_sla_met": resolution_sla_met,
                "resolution_target_hours": resolution_target_hours,
                "breaches_last_30d": sla_breaches,
            },
            "escalations": {
                "count": len(recent_signals),
                "recent": escalation_entries,
            },
            "risk_indicators": {
                "rma_rate_pct": round(rma_rate, 2),
                "preventive_maintenance_compliance_pct": round(preventive_maint, 1),
                "thermal_management_score": round(thermal_score, 1),
            },
        }


# ===================================================================
# Tool: get_customer_feedback
# ===================================================================

@mcp.tool
def get_customer_feedback(customer_id: int, account_id: int) -> dict:
    """Pull customer feedback for an account — NPS trend, CSAT indicators, VoC summaries, CSM relationship assessment. Simulates survey system integration; derives sentiment from qualitative signals and health data.

    Args:
        customer_id: The customer (tenant) ID
        account_id: The account to pull feedback for
    """
    _check_mcp_enabled()
    _require_account_auth(customer_id, account_id)
    app = _get_flask_app()

    with app.app_context():
        from models import QualitativeSignal
        vertical = _resolve_customer_vertical(customer_id)
        calculate_kpi_health, _get_trailing_kpi_values, get_precalculated_scores = _get_health_functions(vertical)
        import utils.health_thresholds as ht

        account = _validate_account_ownership(customer_id, account_id)

        kpi_values = _get_trailing_kpi_values(account_id)

        precalc_health, precalc_status, precalc_pillars = get_precalculated_scores(account_id)
        if precalc_health is not None:
            health = precalc_health
            health_status = precalc_status
            pillars = precalc_pillars or {}
        else:
            health, pillars = calculate_kpi_health(kpi_values, customer_id)
            health_status = ht.classify(health)

        signals = QualitativeSignal.query.filter(
            QualitativeSignal.customer_id == int(customer_id),
            QualitativeSignal.account_id == int(account_id),
        ).order_by(QualitativeSignal.signal_date.desc()).limit(20).all()

        partner_nps = kpi_values.get("P4-KPI6")
        if partner_nps is not None and partner_nps > 0:
            nps_data = {"score": int(partner_nps), "trend": "stable", "source": "kpi_data", "response_count": 1}
        else:
            nps_data = _derive_nps_from_signals(signals)
            nps_data["source"] = "signal_derived"

        sentiment_scores = [
            s.sentiment_score for s in signals
            if hasattr(s, 'sentiment_score') and s.sentiment_score is not None
        ]
        avg_sentiment = round(sum(sentiment_scores) / len(sentiment_scores), 2) if sentiment_scores else 0.0
        csat_score = round(max(1.0, min(5.0, (avg_sentiment + 1) * 2 + 1)), 1)

        positive_count = sum(1 for s in signals if getattr(s, 'sentiment', '') == 'positive')
        negative_count = sum(1 for s in signals if getattr(s, 'sentiment', '') == 'negative')
        neutral_count = len(signals) - positive_count - negative_count

        voc_entries = []
        for sig in signals[:5]:
            text = getattr(sig, 'content', '') or ''
            if text and len(text) > 20:
                voc_entries.append({
                    "date": sig.signal_date.strftime('%Y-%m-%d') if sig.signal_date else "",
                    "type": getattr(sig, 'signal_type', 'general'),
                    "summary": text[:300],
                    "sentiment": getattr(sig, 'sentiment', 'neutral'),
                })
            if len(voc_entries) >= 3:
                break

        relationship_strength = min(5, max(1, int(health / 20)))
        expansion_kpi = kpi_values.get("P5-KPI7", 0)
        champion_engagement = kpi_values.get("P5-KPI8", kpi_values.get("P4-KPI1", 0))

        return {
            "scope": "account",
            "source": "survey_simulated",
            "account_id": account_id,
            "account_name": account.account_name,
            "nps": nps_data,
            "csat": {
                "score": csat_score,
                "avg_sentiment_score": avg_sentiment,
            },
            "voice_of_customer": voc_entries,
            "csm_assessment": {
                "relationship_strength": relationship_strength,
                "churn_risk": health_status,
                "expansion_potential": f"{expansion_kpi:.0f}%" if expansion_kpi else "Unknown",
                "champion_engagement_score": round(champion_engagement, 1),
                "health_score": round(health, 1),
                "recommended_focus": min(pillars, key=pillars.get) if pillars else "Unknown",
            },
            "sentiment_distribution": {
                "positive": positive_count,
                "neutral": neutral_count,
                "negative": negative_count,
                "total_signals": len(signals),
            },
        }


# ===================================================================
# Tool: get_csm_daily_actions
# ===================================================================

@mcp.tool
def get_csm_daily_actions(customer_id: int, csm_name: str = None) -> dict:
    """Get top-10 prioritized CSM actions across all accounts (portfolio-level). Each action includes the linked playbook, urgency level, estimated effort hours, and projected dollar impact via Power-of-1 ROI metric correlation.

    Use for "What should I do today?" or "Morning briefing" questions.
    Priority formula: (impact × 0.6 × arr_weight) - (effort × 0.4)

    Args:
        customer_id: The customer (tenant) ID — actions span ALL accounts for this tenant
        csm_name: Optional CSM name to filter actions to their assigned accounts only
    """
    _check_mcp_enabled()
    _require_auth(customer_id)
    app = _get_flask_app()

    with app.app_context():
        from models import Account
        from datetime import datetime
        import utils.health_thresholds as ht

        vertical = _resolve_customer_vertical(customer_id)
        calculate_kpi_health, _get_trailing_kpi_values, get_precalculated_scores = _get_health_functions(vertical)
        PLAYBOOK_CONFIG, should_trigger_playbook = _get_playbook_config(vertical)
        KPI_DEFS = _get_kpi_definitions(vertical)

        # Aug 21 2026 vertical-coupling audit (Bug 1): resolve this vertical's
        # own "expansion probability/rate" KPI from its actual catalog instead
        # of hardcoding dc2_s's 'P5-KPI7' for every vertical. dc2_s calls it
        # P5-KPI7 ("Expansion Probability (90d)"), datacenter_v1 calls it
        # P5-KPI4, saas_premium calls it P5-KPI3 ("Expansion Revenue Rate") —
        # different codes per vertical, and healthcare_provider has no such
        # KPI at all, so this must resolve to None (no expansion boost)
        # rather than silently reading a KPI that isn't this tenant's.
        _expansion_kpi_code = next(
            (code for code, kdef in (KPI_DEFS or {}).items()
             if 'expansion' in (kdef.get('name', '') or '').lower()),
            None,
        )

        # Aug 21 2026 vertical-coupling audit (Bug 1): this used to be
        # "if saas_premium use its own functions, else unconditionally fall
        # through to dc2_s" — but verticals/saas_premium/api_routes.py never
        # defined _normalize_kpi_code_for_health/_compute_impact_score/etc,
        # so that import always raised and EVERY vertical (saas_premium
        # included) silently inherited dc2_s's PB-01..PB-06 playbook→ROI
        # mapping. _compute_impact_score/_compute_effort_score/_determine_urgency
        # only operate on health/churn/expansion numbers and playbook
        # sub-component counts — no vertical-specific KPI codes or playbook
        # IDs — so they're genuinely vertical-neutral and safe to reuse from
        # dc2_s's module for every vertical. _get_roi_context is NOT neutral:
        # it hardcodes dc2_s's own playbook IDs (PB-01..PB-06) mapped to
        # dc2_s's Power-of-1 metrics, so it's only valid for dc2_s tenants.
        from verticals.dc2_s.api_routes import (
            _compute_impact_score, _compute_effort_score, _determine_urgency,
        )
        from utils.vertical_health import normalize_kpi_code
        _normalize_kpi_code_for_health = lambda c: normalize_kpi_code(c)

        def _no_roi_context(action_type, playbook_id, account_revenue=0):
            """Honest 'not available' ROI context for verticals with no
            verified Power-of-1 playbook/action mapping yet — instead of
            fabricating one by borrowing dc2_s's PB-01..PB-06 map."""
            return {
                'roi_metric_id': None,
                'roi_metric_name': None,
                'roi_projected_impact': 0,
                'roi_impact_type': None,
                'roi_context_available': False,
            }

        if vertical == 'dc2_s':
            from verticals.dc2_s.api_routes import _get_roi_context
        else:
            _get_roi_context = _no_roi_context

        DC2S_KPIS = KPI_DEFS

        accounts = Account.query.filter(
            Account.customer_id == int(customer_id),
        ).all()

        if csm_name:
            accounts = [a for a in accounts
                        if csm_name.lower() in (
                            (a.profile_metadata or {}).get('assigned_csm', '') or ''
                        ).lower()]

        if not accounts:
            return {
                "scope": "portfolio",
                "date": datetime.utcnow().strftime('%Y-%m-%d'),
                "actions": [],
                "summary": {
                    "total_actions": 0, "critical_count": 0,
                    "high_count": 0, "opportunity_count": 0,
                    "total_estimated_hours": 0,
                    "total_roi_projected_impact": 0,
                },
            }

        acct_csm = {
            a.account_id: (
                (a.profile_metadata or {}).get('assigned_csm')
                or (a.profile_metadata or {}).get('csm_name')
                or 'Unassigned'
            )
            for a in accounts
        }

        # Load pillar labels from vertical config (not hardcoded)
        PILLAR_LABELS = _get_pillar_labels(vertical)

        # Build pillar → playbook mapping dynamically from trigger_kpis
        PILLAR_PLAYBOOK_MAP = {}
        for pb_id, pb_cfg in PLAYBOOK_CONFIG.items():
            for tk in pb_cfg.get('trigger_kpis', []):
                pillar = tk.split('-')[0]  # "P1-KPI1" → "P1"
                if pillar not in PILLAR_PLAYBOOK_MAP:
                    PILLAR_PLAYBOOK_MAP[pillar] = pb_id

        all_actions = []
        account_ids = [a.account_id for a in accounts]

        # ── Load DB-stored playbook templates when vertical has no config ──
        from models import QualitativeSignal, CustomerPlaybook
        db_playbooks = []
        if not PLAYBOOK_CONFIG:
            db_playbooks = CustomerPlaybook.query.filter_by(
                customer_id=int(customer_id), is_system=True,
            ).all()

        # ── Build playbook_id → execution_backend map from DB templates ──
        # Reads from `steps` (new format) or `actions` (legacy format)
        db_pb_lookup = {}  # playbook_id → CustomerPlaybook
        if not db_playbooks:
            # Also load for vertical-config playbooks to enrich with execution_backend
            all_db_pbs = CustomerPlaybook.query.filter_by(
                customer_id=int(customer_id),
            ).all()
            for dbpb in all_db_pbs:
                db_pb_lookup[dbpb.playbook_id] = dbpb
        else:
            for dbpb in db_playbooks:
                db_pb_lookup[dbpb.playbook_id] = dbpb

        def _get_execution_info(playbook_id):
            """Extract execution_backend and first_step info from DB playbook."""
            dbpb = db_pb_lookup.get(playbook_id)
            if not dbpb:
                return {}
            # Try new `steps` format first, fall back to `actions`
            steps = getattr(dbpb, 'steps', None) or dbpb.actions or []
            if not steps:
                return {}
            first_step = steps[0] if steps else {}
            backend = first_step.get('execution_backend', 'manual')
            backend_config = first_step.get('backend_config', {})
            return {
                'execution_backend': backend,
                'execution_config': backend_config,
                'total_steps': len(steps),
                'first_step': first_step.get('description', ''),
            }

        # ── Pre-load recent qualitative signals for signal-driven actions ──
        recent_signals = QualitativeSignal.query.filter(
            QualitativeSignal.customer_id == int(customer_id),
            QualitativeSignal.account_id.in_(account_ids),
            QualitativeSignal.sentiment.in_(['negative', 'critical']),
        ).order_by(QualitativeSignal.signal_date.desc()).limit(30).all()

        # Group signals by account_id
        signals_by_account = {}
        for sig in recent_signals:
            signals_by_account.setdefault(sig.account_id, []).append(sig)

        for account in accounts:
            precalc_health, precalc_status, precalc_pillars = get_precalculated_scores(account.account_id)
            trailing_kpis = _get_trailing_kpi_values(account.account_id, days=30)

            if precalc_health is not None:
                overall_health = precalc_health
                pillar_averages = precalc_pillars or {}
            else:
                overall_health, pillar_averages = calculate_kpi_health(
                    trailing_kpis, customer_id=customer_id
                )

            normalized_kpis = {}
            for code, val in trailing_kpis.items():
                norm = _normalize_kpi_code_for_health(code)
                if norm:
                    normalized_kpis[norm] = val
            normalized_kpis['OVERALL_HEALTH'] = overall_health

            arr = _get_account_arr(account)
            if arr > 10_000_000:
                arr_weight = 1.5
            elif arr > 5_000_000:
                arr_weight = 1.3
            elif arr > 2_000_000:
                arr_weight = 1.1
            elif arr > 0:
                arr_weight = 1.0
            else:
                arr_weight = 0.8

            h_cls = ht.classify(overall_health)
            churn_prob = 80 if h_cls == 'critical' else (40 if h_cls == 'at_risk' else 15)
            expansion_prob_val = 75 if h_cls == 'healthy' else (30 if h_cls == 'at_risk' else 5)

            exp_kpi = normalized_kpis.get(_expansion_kpi_code) if _expansion_kpi_code else None
            if exp_kpi is not None:
                expansion_prob_val = max(expansion_prob_val, exp_kpi)

            has_playbook_action = False

            # ── Playbook triggers (strict: ALL conditions met) ──
            for pb_id, pb_cfg in PLAYBOOK_CONFIG.items():
                if should_trigger_playbook(pb_id, normalized_kpis):
                    impact = _compute_impact_score(overall_health, churn_prob, expansion_prob_val, pillar_averages)
                    effort = _compute_effort_score(pb_cfg)
                    priority_index = round((impact * 0.6 * arr_weight) - (effort * 0.4), 1)

                    total_hours = sum(s.get('estimated_hours', 0) for s in pb_cfg.get('sub_components', []))

                    trigger_details = []
                    for tk in pb_cfg.get('trigger_kpis', []):
                        if tk in normalized_kpis:
                            cond = pb_cfg.get('trigger_conditions', {}).get(tk, {})
                            threshold = cond.get('value', '?')
                            kpi_name = DC2S_KPIS.get(tk, {}).get('name', tk)
                            trigger_details.append(f"{kpi_name}: {normalized_kpis[tk]:.1f} (threshold {threshold})")

                    description = '; '.join(trigger_details) if trigger_details else pb_cfg.get('estimated_impact', '')

                    roi_ctx = _get_roi_context('playbook', pb_id, arr)
                    exec_info = _get_execution_info(pb_id)
                    all_actions.append({
                        'account_id': account.account_id,
                        'account_name': account.account_name,
                        'action_title': f"Run {pb_cfg['name']}",
                        'action_description': description,
                        'action_type': 'playbook',
                        'related_playbook_id': pb_id,
                        'urgency': _determine_urgency(overall_health, churn_prob, expansion_prob_val),
                        'impact_score': impact,
                        'effort_score': effort,
                        'priority_index': priority_index,
                        'account_health': round(overall_health, 1),
                        'estimated_hours': total_hours,
                        'estimated_duration_display': pb_cfg.get('estimated_duration_display', ''),
                        **roi_ctx,
                        **exec_info,
                    })
                    has_playbook_action = True

            # ── DB playbook triggers (for verticals without config, e.g. SaaS) ──
            if db_playbooks:
                for dbpb in db_playbooks:
                    conditions = dbpb.trigger_conditions or []
                    logic = (dbpb.trigger_logic or 'OR').upper()
                    met_details = []
                    all_met = True
                    for cond in conditions:
                        kpi_code = cond.get('kpi_code', '')
                        val = normalized_kpis.get(kpi_code)
                        if val is None:
                            if logic == 'AND':
                                all_met = False
                            continue
                        op = cond.get('operator', '')
                        threshold = cond.get('threshold', 0)
                        triggered = False
                        if op in ('less_than', '<', 'lt') and val < threshold:
                            triggered = True
                        elif op in ('greater_than', '>', 'gt') and val > threshold:
                            triggered = True
                        elif op in ('<=', 'lte', 'less_than_or_equal') and val <= threshold:
                            triggered = True
                        elif op in ('>=', 'gte', 'greater_than_or_equal') and val >= threshold:
                            triggered = True
                        if triggered:
                            kpi_name = DC2S_KPIS.get(kpi_code, {}).get('name', kpi_code)
                            met_details.append(f"{kpi_name}: {val:.1f} (threshold {threshold})")
                        elif logic == 'AND':
                            all_met = False

                    should_fire = (logic == 'OR' and met_details) or (logic == 'AND' and all_met and met_details)
                    if should_fire:
                        impact = _compute_impact_score(overall_health, churn_prob, expansion_prob_val, pillar_averages)
                        actions_list = dbpb.actions or []
                        est_hours = sum(a.get('estimated_hours', 2) for a in actions_list) if actions_list else 8
                        effort = min(est_hours * 2, 60)
                        priority_index = round((impact * 0.6 * arr_weight) - (effort * 0.4), 1)
                        roi_ctx = _get_roi_context('playbook', dbpb.playbook_id, arr)
                        exec_info = _get_execution_info(dbpb.playbook_id)
                        all_actions.append({
                            'account_id': account.account_id,
                            'account_name': account.account_name,
                            'action_title': f"Run {dbpb.name}",
                            'action_description': '; '.join(met_details),
                            'action_type': 'playbook',
                            'related_playbook_id': dbpb.playbook_id,
                            'urgency': _determine_urgency(overall_health, churn_prob, expansion_prob_val),
                            'impact_score': impact, 'effort_score': effort,
                            'priority_index': priority_index,
                            'account_health': round(overall_health, 1),
                            'estimated_hours': est_hours,
                            'estimated_duration_display': f"{max(1, est_hours // 8)} days",
                            **roi_ctx,
                            **exec_info,
                        })
                        has_playbook_action = True
                        break  # one DB playbook per account

            # ── Soft playbook triggers: ANY trigger condition met ──
            for pb_id, pb_cfg in PLAYBOOK_CONFIG.items():
                conditions = pb_cfg.get('trigger_conditions', {})
                met_details = []
                for kpi_code, cond in conditions.items():
                    val = normalized_kpis.get(kpi_code)
                    if val is None:
                        continue
                    op, threshold = cond.get('operator'), cond.get('value')
                    triggered = (op == '>' and val > threshold) or (op == '<' and val < threshold)
                    if triggered:
                        kpi_name = DC2S_KPIS.get(kpi_code, {}).get('name', kpi_code)
                        met_details.append(f"{kpi_name}: {val:.1f} (threshold {threshold})")
                if met_details:
                    impact = _compute_impact_score(overall_health, churn_prob, expansion_prob_val, pillar_averages)
                    effort = _compute_effort_score(pb_cfg) * 0.7  # lighter since partial trigger
                    priority_index = round((impact * 0.6 * arr_weight) - (effort * 0.4), 1)
                    total_hours = sum(s.get('estimated_hours', 0) for s in pb_cfg.get('sub_components', []))
                    roi_ctx = _get_roi_context('playbook', pb_id, arr)
                    exec_info = _get_execution_info(pb_id)
                    all_actions.append({
                        'account_id': account.account_id,
                        'account_name': account.account_name,
                        'action_title': f"Evaluate {pb_cfg['name']}",
                        'action_description': '; '.join(met_details),
                        'action_type': 'playbook_evaluate',
                        'related_playbook_id': pb_id,
                        'urgency': _determine_urgency(overall_health, churn_prob, expansion_prob_val),
                        'impact_score': impact, 'effort_score': effort,
                        'priority_index': priority_index,
                        'account_health': round(overall_health, 1),
                        'estimated_hours': total_hours,
                        'estimated_duration_display': pb_cfg.get('estimated_duration_display', ''),
                        **roi_ctx,
                        **exec_info,
                    })
                    has_playbook_action = True
                    break  # one soft trigger per account

            # ── Pillar-specific intervention (replaces generic "Health Check") ──
            if overall_health < ht.healthy_min():
                # Find the weakest pillar to make the action specific
                weakest_pillar = None
                weakest_score = 999
                for pc, score in pillar_averages.items():
                    if score is not None and score < weakest_score:
                        weakest_score = score
                        weakest_pillar = pc

                pillar_label = PILLAR_LABELS.get(weakest_pillar, 'Overall Health')
                recommended_pb = PILLAR_PLAYBOOK_MAP.get(weakest_pillar)
                pb_name = PLAYBOOK_CONFIG.get(recommended_pb, {}).get('name', '') if recommended_pb else ''

                if h_cls == 'critical':
                    title = f"Urgent: {pillar_label} Critical"
                    desc = (f"Health {overall_health:.0f} (critical). {pillar_label} at {weakest_score:.0f}. "
                            f"{'Recommend ' + pb_name + ' playbook. ' if pb_name else ''}"
                            f"ARR ${arr/1e6:.1f}M at risk.")
                else:
                    title = f"Investigate {pillar_label} Decline"
                    desc = (f"Health {overall_health:.0f} (at-risk). {pillar_label} at {weakest_score:.0f}. "
                            f"{'Consider ' + pb_name + '. ' if pb_name else ''}"
                            f"Schedule root-cause review.")

                impact = _compute_impact_score(overall_health, churn_prob, expansion_prob_val, pillar_averages)
                effort = 20
                priority_index = round((impact * 0.6 * arr_weight) - (effort * 0.4), 1)
                roi_ctx = _get_roi_context('follow_up', recommended_pb, arr)
                all_actions.append({
                    'account_id': account.account_id,
                    'account_name': account.account_name,
                    'action_title': title,
                    'action_description': desc,
                    'action_type': 'pillar_intervention',
                    'related_playbook_id': recommended_pb,
                    'urgency': _determine_urgency(overall_health, churn_prob, expansion_prob_val),
                    'impact_score': impact, 'effort_score': effort,
                    'priority_index': priority_index,
                    'account_health': round(overall_health, 1),
                    'estimated_hours': 2,
                    'estimated_duration_display': '1 day',
                    **roi_ctx,
                    **(_get_execution_info(recommended_pb) if recommended_pb else {}),
                })

            # ── Signal-driven actions (from qualitative signals) ──
            acct_signals = signals_by_account.get(account.account_id, [])
            if acct_signals:
                sig = acct_signals[0]  # most recent negative signal
                signal_type = getattr(sig, 'signal_type', 'risk')
                signal_text = getattr(sig, 'content', '') or getattr(sig, 'raw_text', '') or ''
                snippet = signal_text[:120] + ('...' if len(signal_text) > 120 else '')

                title_map = {
                    'champion_loss': 'Stakeholder Risk: Champion Change',
                    'escalation': 'Escalation Alert',
                    'sentiment_drop': 'Sentiment Decline Detected',
                    'support_spike': 'Support Volume Spike',
                    'usage_drop': 'Usage Drop Alert',
                    'executive_change': 'Executive Sponsor Change',
                }
                action_title = title_map.get(signal_type, f"Signal Alert: {signal_type.replace('_', ' ').title()}")

                impact = _compute_impact_score(overall_health, churn_prob, expansion_prob_val, pillar_averages)
                effort = 15
                priority_index = round((impact * 0.7 * arr_weight) - (effort * 0.3), 1)
                roi_ctx = _get_roi_context('follow_up', None, arr)
                all_actions.append({
                    'account_id': account.account_id,
                    'account_name': account.account_name,
                    'action_title': action_title,
                    'action_description': snippet,
                    'action_type': 'signal_driven',
                    'related_playbook_id': None,
                    'urgency': 'critical' if sig.sentiment == 'critical' else 'high',
                    'impact_score': impact, 'effort_score': effort,
                    'priority_index': priority_index,
                    'account_health': round(overall_health, 1),
                    'estimated_hours': 2,
                    'estimated_duration_display': '1 day',
                    **roi_ctx,
                })

            # ── QBR action ──
            qbr_val = normalized_kpis.get('P4-KPI3')
            if qbr_val is not None and qbr_val < 3:
                impact = _compute_impact_score(overall_health, churn_prob, expansion_prob_val, pillar_averages)
                effort = 25
                priority_index = round((impact * 0.6 * arr_weight) - (effort * 0.4), 1)
                roi_ctx = _get_roi_context('qbr', None, arr)
                all_actions.append({
                    'account_id': account.account_id,
                    'account_name': account.account_name,
                    'action_title': 'Schedule QBR',
                    'action_description': f'QBR frequency at {qbr_val:.0f}/yr (target 3+). Schedule next review.',
                    'action_type': 'qbr',
                    'related_playbook_id': None,
                    'urgency': 'high',
                    'impact_score': impact, 'effort_score': effort,
                    'priority_index': priority_index,
                    'account_health': round(overall_health, 1),
                    'estimated_hours': 4,
                    'estimated_duration_display': '1-2 days',
                    **roi_ctx,
                })

            # ── Expansion opportunity ──
            if exp_kpi is not None and exp_kpi > 70:
                impact = _compute_impact_score(overall_health, churn_prob, expansion_prob_val, pillar_averages)
                effort = 30
                priority_index = round((impact * 0.6 * arr_weight) - (effort * 0.4), 1)
                roi_ctx = _get_roi_context('expansion', None, arr)
                all_actions.append({
                    'account_id': account.account_id,
                    'account_name': account.account_name,
                    'action_title': 'Expansion Opportunity Call',
                    'action_description': f'Expansion probability at {exp_kpi:.0f}%. Schedule capacity planning discussion.',
                    'action_type': 'expansion',
                    'related_playbook_id': None,
                    'urgency': 'opportunity',
                    'impact_score': impact, 'effort_score': effort,
                    'priority_index': priority_index,
                    'account_health': round(overall_health, 1),
                    'estimated_hours': 3,
                    'estimated_duration_display': '1 day',
                    **roi_ctx,
                })

        all_actions.sort(key=lambda a: a['priority_index'], reverse=True)

        # Diversity-aware selection: round-robin across action types, cap 2 per account
        from collections import defaultdict
        by_type = defaultdict(list)
        for a in all_actions:
            by_type[a['action_type']].append(a)

        seen_accounts = defaultdict(int)
        top_actions = []
        type_keys = list(by_type.keys())
        idx = 0
        while len(top_actions) < 10 and type_keys:
            action_type = type_keys[idx % len(type_keys)]
            candidates = by_type[action_type]
            picked = False
            while candidates and not picked:
                candidate = candidates.pop(0)
                acct_id = candidate.get('account_id')
                if seen_accounts[acct_id] < 2:
                    top_actions.append(candidate)
                    seen_accounts[acct_id] += 1
                    picked = True
            if not candidates:
                type_keys.remove(action_type)
                if type_keys:
                    idx = idx % len(type_keys)
            else:
                idx += 1

        # If still < 10, fill from remaining by priority
        if len(top_actions) < 10:
            remaining = [a for a in all_actions if a not in top_actions]
            for a in remaining:
                if len(top_actions) >= 10:
                    break
                if seen_accounts[a.get('account_id')] < 3:
                    top_actions.append(a)
                    seen_accounts[a.get('account_id')] += 1

        for i, action in enumerate(top_actions, 1):
            action['rank'] = i
            action['id'] = f"act-{i:03d}"
            action['assigned_csm'] = acct_csm.get(
                action.get('account_id'), 'Unassigned'
            )

        urgency_counts = {'critical': 0, 'high': 0, 'opportunity': 0, 'medium': 0}
        total_hours = 0
        for a in top_actions:
            urg = a.get('urgency', 'medium')
            urgency_counts[urg] = urgency_counts.get(urg, 0) + 1
            total_hours += a.get('estimated_hours', 0)

        total_roi_impact = sum(a.get('roi_projected_impact', 0) for a in top_actions)
        roi_metrics_involved = list({a['roi_metric_name'] for a in top_actions if a.get('roi_metric_name')})

        return {
            "scope": "portfolio",
            "date": datetime.utcnow().strftime('%Y-%m-%d'),
            "actions": top_actions,
            "summary": {
                "total_actions": len(top_actions),
                "critical_count": urgency_counts.get('critical', 0),
                "high_count": urgency_counts.get('high', 0),
                "opportunity_count": urgency_counts.get('opportunity', 0),
                "total_estimated_hours": total_hours,
                "total_roi_projected_impact": total_roi_impact,
                "roi_metrics_involved": roi_metrics_involved,
            },
        }


# ===================================================================
# Tool: partner_portal
# ===================================================================

@mcp.tool
def partner_portal(
    customer_id: int,
    partner_id: int,
    action: str = "scorecard",
    data_type: str = None,
    csv_content: str = None,
    metric_id: str = "partner_nps",
) -> dict:
    """Partner-scoped portal for P4 (Channel & Partner Health) operations.

    Consolidates all partner interactions into one tool. All responses are
    scoped to P4 pillar only — no revenue, ARR, or other pillar data exposed.

    Actions:
      - scorecard: P4 health scores and KPI breakdown per account
      - submit_data: Upload partner engagement data (requires data_type + csv_content)
      - actions: P4 playbook recommendations for partner improvement
      - benchmarks: Anonymized P4 performance vs portfolio average
      - impact: Power-of-1 analysis for a P4 metric (uses metric_id param)

    Args:
        customer_id: The customer (tenant) ID
        partner_id: The partner ID (used for scoping)
        action: One of: scorecard, submit_data, actions, benchmarks, impact
        data_type: For submit_data only: 'engagement_events', 'stakeholders', or 'signals'
        csv_content: For submit_data only: raw CSV content string
        metric_id: For impact only: partner_engagement, var_performance, qbr_frequency,
                   channel_conflict, co_selling, partner_nps (default)
    """
    _check_mcp_enabled()
    app = _get_flask_app()
    valid_actions = ('scorecard', 'submit_data', 'actions', 'benchmarks', 'impact')
    if action not in valid_actions:
        raise ToolError(f"Invalid action '{action}'. Use one of: {', '.join(valid_actions)}")

    if action != 'submit_data':
        _require_auth(customer_id)

    def _get_p4_score(acct_id):
        from models import PillarScore, HealthScore
        ps = PillarScore.query.filter_by(account_id=acct_id, pillar_code='P4') \
            .order_by(PillarScore.measurement_month.desc()).first()
        if ps and ps.pillar_score is not None:
            return float(ps.pillar_score)
        hs = HealthScore.query.filter_by(account_id=acct_id) \
            .order_by(HealthScore.measurement_month.desc()).first()
        if hs and hs.contributing_pillars:
            return float(hs.contributing_pillars.get('P4', 0))
        return None

    def _get_p4_kpis(acct_id):
        from models import DC2SKPI
        kpi_rows = DC2SKPI.query.filter(
            DC2SKPI.account_id == acct_id, DC2SKPI.kpi_code.like('P4-%'),
        ).order_by(DC2SKPI.measured_at.desc()).all()
        result, seen = {}, set()
        for k in kpi_rows:
            if k.kpi_code not in seen:
                result[k.kpi_code] = round(float(k.value), 2)
                seen.add(k.kpi_code)
        return result

    with app.app_context():
        from models import Account
        import utils.health_thresholds as ht

        # Gate on content, not vertical identity: this portal hardcodes P4 as
        # "the partner pillar," but pillar index is stable across verticals
        # while pillar meaning is not (P4 = Power & Facility in datacenter_v1,
        # Compliance & Risk in healthcare_provider — neither is a partner
        # pillar). Rather than add a per-vertical lookup table here — which
        # would just relocate the same defect — refuse to serve unless this
        # tenant's own declared P4 pillar name is actually a partner pillar.
        #
        # An exact match against dc2_s's name ("Channel & Partner Health")
        # was tried first and found wrong by testing against a second real
        # vertical: saas_premium's own equivalent is genuinely named
        # "Partner & Ecosystem Health" — different string, same role — and
        # the exact match incorrectly refused a vertical that legitimately
        # has one. Checked all four registered verticals directly: both real
        # partner pillars contain "partner"; neither Power & Facility
        # (datacenter_v1) nor Compliance & Risk (healthcare_provider) does.
        # A real pillar_roles registry replaces this substring check with a
        # proper role lookup later; this is the interim control that stops
        # the leak today without also blocking legitimate use.
        from mcp_server.cs_pulse_mcp_server import _resolve_customer_vertical
        from utils.vertical_registry import get_pillars as _vr_get_pillars
        _tenant_vertical = _resolve_customer_vertical(customer_id)
        _p4_name = (_vr_get_pillars(_tenant_vertical).get('P4') or {}).get('name', '')
        if 'partner' not in _p4_name.lower():
            raise ToolError(
                f"partner_portal is not available for customer {customer_id} "
                f"(vertical={_tenant_vertical!r}). This vertical's P4 pillar is "
                f"{_p4_name!r}, not a partner pillar — serving it under partner "
                f"labels would expose the wrong data to the partner."
            )

        if action == 'submit_data':
            if not data_type or not csv_content:
                raise ToolError("submit_data requires both data_type and csv_content parameters.")
            TYPE_MAP = {
                'engagement_events': 'engagement_events.csv',
                'stakeholders': 'stakeholders.csv',
                'signals': 'enhanced_qualitative_signals.csv',
            }
            ft = TYPE_MAP.get(data_type)
            if not ft:
                raise ToolError(f"Invalid data_type '{data_type}'. Allowed: {sorted(TYPE_MAP.keys())}")

            import json as _json, csv as _csv, io as _io
            schemas_path = os.path.join(_backend_dir, 'config', 'csv_schemas.json')
            with open(schemas_path, 'r') as f:
                schemas = _json.load(f)
            schema = None
            for mk in ('regular_model', 'context_graph_model'):
                model = schemas.get(mk, {})
                if isinstance(model, dict) and ft in model.get('files', {}):
                    schema = model['files'][ft]
                    break
                if isinstance(model, dict):
                    for sub in ('customer_provided', 'auto_generated', 'files'):
                        if isinstance(model.get(sub), dict) and ft in model[sub]:
                            schema = model[sub][ft]
                            break
                    if schema:
                        break
            if not schema:
                raise ToolError(f"Schema not found for {ft}.")

            required = set(schema.get('required_columns', []))
            reader = _csv.DictReader(_io.StringIO(csv_content))
            headers = set(reader.fieldnames or [])
            rows = list(reader)
            missing = required - headers
            if missing:
                return {'scope': 'partner', 'status': 'validation_failed', 'errors': [f"Missing: {sorted(missing)}"]}
            if not rows:
                return {'scope': 'partner', 'status': 'validation_failed', 'errors': ['No data rows.']}

            from models import Customer
            from extensions import db
            from pathlib import Path
            customer = db.session.get(Customer, int(customer_id))
            if not customer:
                raise ToolError(f"Customer {customer_id} not found.")
            vertical = getattr(customer, 'vertical', 'dc2_s') or 'dc2_s'
            data_dir = Path(__file__).parent.parent / 'verticals' / f'customer{customer_id}-{vertical}' / 'data'
            data_dir.mkdir(parents=True, exist_ok=True)
            output = _io.StringIO()
            all_cols = list(headers) + (['partner_id'] if 'partner_id' not in headers else [])
            writer = _csv.DictWriter(output, fieldnames=all_cols, extrasaction='ignore')
            writer.writeheader()
            for row in rows:
                row['partner_id'] = str(partner_id)
                writer.writerow(row)
            (data_dir / ft).write_text(output.getvalue(), encoding='utf-8')
            return {'scope': 'partner', 'customer_id': customer_id, 'partner_id': partner_id,
                    'action': 'submit_data', 'status': 'accepted', 'rows_accepted': len(rows),
                    'message': f"Accepted {len(rows)} rows. Use process_data() to ingest."}

        accounts = Account.query.filter_by(customer_id=int(customer_id)).all()
        if not accounts:
            raise ToolError(f"No accounts found for customer {customer_id}.")

        if action == 'scorecard':
            scorecard = []
            for acct in accounts:
                p4 = _get_p4_score(acct.account_id)
                scorecard.append({
                    'account_id': acct.account_id, 'account_name': acct.account_name,
                    'p4_score': round(p4, 1) if p4 is not None else None,
                    'p4_status': ht.classify(p4) if p4 is not None else 'unknown',
                    'p4_kpis': _get_p4_kpis(acct.account_id),
                })
            avg = [s['p4_score'] for s in scorecard if s['p4_score'] is not None]
            return {'scope': 'partner', 'customer_id': customer_id, 'partner_id': partner_id,
                    'action': 'scorecard', 'account_count': len(scorecard),
                    'avg_p4_score': round(sum(avg) / len(avg), 1) if avg else None,
                    'accounts': scorecard}

        elif action == 'actions':
            _ensure_registry()
            from agent_tool_registry import get_tool_registry
            vertical = _resolve_customer_vertical(customer_id)
            _, _get_trailing_kpi_values, get_precalculated_scores = _get_health_functions(vertical)
            registry = get_tool_registry()
            partner_actions = []
            for acct in accounts:
                kpi_vals = _get_trailing_kpi_values(acct.account_id)
                health, _, _ = get_precalculated_scores(acct.account_id)
                try:
                    res = registry.invoke("playbook_recommend", account_id=acct.account_id,
                                          customer_id=customer_id, health_score=round(health or 0, 1), kpi_values=kpi_vals)
                    if res.success and res.result:
                        for pb in res.result.get('playbooks', []):
                            if pb.get('trigger_pillar') == 'P4' or pb.get('playbook_id') in ('PB-04',):
                                partner_actions.append({
                                    'account_id': acct.account_id, 'account_name': acct.account_name,
                                    'action': pb.get('name', ''), 'urgency': pb.get('urgency', 'medium'),
                                    'effort_hours': pb.get('effort_hours', 0),
                                })
                except Exception:
                    pass
            return {'scope': 'partner', 'customer_id': customer_id, 'partner_id': partner_id,
                    'action': 'actions', 'total_actions': len(partner_actions), 'actions': partner_actions}

        elif action == 'benchmarks':
            all_p4, kpi_totals = [], {}
            for acct in accounts:
                p4 = _get_p4_score(acct.account_id)
                if p4 is not None:
                    all_p4.append(p4)
                for code, val in _get_p4_kpis(acct.account_id).items():
                    kpi_totals.setdefault(code, []).append(val)
            avg = round(sum(all_p4) / len(all_p4), 1) if all_p4 else None
            kpi_avgs = {c: round(sum(v) / len(v), 2) for c, v in kpi_totals.items() if v}
            return {'scope': 'partner', 'customer_id': customer_id, 'partner_id': partner_id,
                    'action': 'benchmarks', 'partner_p4_avg': avg, 'portfolio_p4_avg': avg,
                    'top_kpi': max(kpi_avgs, key=kpi_avgs.get) if kpi_avgs else None,
                    'weakest_kpi': min(kpi_avgs, key=kpi_avgs.get) if kpi_avgs else None,
                    'kpi_averages': kpi_avgs, 'accounts_with_p4_data': len(all_p4)}

        elif action == 'impact':
            P4_MAP = {'partner_engagement': 'P4-KPI1', 'var_performance': 'P4-KPI2',
                      'qbr_frequency': 'P4-KPI3', 'channel_conflict': 'P4-KPI4',
                      'co_selling': 'P4-KPI5', 'partner_nps': 'P4-KPI6'}
            if metric_id not in P4_MAP:
                raise ToolError(f"Unknown metric '{metric_id}'. Available: {sorted(P4_MAP.keys())}")
            from models import DC2SKPI
            kpi_code = P4_MAP[metric_id]
            kpi_vals = []
            for acct in accounts:
                row = DC2SKPI.query.filter(DC2SKPI.account_id == acct.account_id,
                                           DC2SKPI.kpi_code == kpi_code) \
                    .order_by(DC2SKPI.measured_at.desc()).first()
                if row:
                    kpi_vals.append(float(row.value))
            current = round(sum(kpi_vals) / len(kpi_vals), 2) if kpi_vals else None
            arr = sum(_get_account_arr(a) for a in accounts)
            impact = round(arr * 0.003, 2) if arr else None
            return {'scope': 'partner', 'customer_id': customer_id, 'partner_id': partner_id,
                    'action': 'impact', 'metric': metric_id, 'kpi_code': kpi_code,
                    'current_value': current, 'improved_value': round(current * 1.01, 2) if current else None,
                    'annual_revenue_impact': impact}


@mcp.tool
def get_csm_scorecard(customer_id: int, csm_name: str = None) -> dict:
    """Get CSM performance scorecard — accounts managed, health improvements, revenue impact, rescue attribution.

    v2 (Apr 21, 2026) — added metrics:
    - `actions_taken`: count of user-action audit events on the CSM's book
      (playbook_execute + playbook_complete + other write-path events). Derived
      from the ActivityLog table populated by MCP tool wrappers.
    - `accounts_rescued`: count of accounts that moved from critical (<50)
      to healthy (>=70) during the available trajectory — the canonical
      CSM impact metric.
    - `accounts_lost`: count that moved from healthy to critical on the CSM's
      watch. Honest counterweight to rescued count.

    Buyer-requested (Apr 21 demo feedback). Attribution today goes via
    `Account.profile_metadata.assigned_csm` name string — full user-FK
    propagation is Phase 1 item B2 Part 2.

    Args:
        customer_id: The customer (tenant) ID
        csm_name: Optional CSM name to filter (case-insensitive substring match)
    """
    _ensure_registry()
    app = _get_flask_app()

    with app.app_context():
        _require_auth(customer_id)

        from models import Account, HealthScore, PlaybookExecutionV2, ActivityLog
        from sqlalchemy import func, desc
        from collections import defaultdict

        accounts = Account.query.filter_by(customer_id=customer_id).all()

        # Group accounts by assigned CSM
        csm_accounts = defaultdict(list)
        for acct in accounts:
            profile = _get_account_profile(acct)
            csm = profile.get('assigned_csm', 'Unassigned')
            if csm_name and csm_name.lower() not in csm.lower():
                continue
            csm_accounts[csm].append(acct)

        scorecards = {}
        for csm, accts in csm_accounts.items():
            acct_ids = [a.account_id for a in accts]
            total_arr = sum(float(a.revenue or 0) for a in accts)

            # Health deltas + rescue/lost classification per account
            health_deltas = []
            accounts_rescued = 0
            accounts_lost = 0
            for aid in acct_ids:
                scores = (HealthScore.query
                    .filter_by(account_id=aid)
                    .order_by(HealthScore.measurement_month.asc())
                    .all())
                if len(scores) >= 2:
                    earliest = float(scores[0].health_score or 0)
                    latest = float(scores[-1].health_score or 0)
                    health_deltas.append(latest - earliest)
                    # Rescue: started critical (<50), ended healthy (>=70)
                    if earliest < 50 and latest >= 70:
                        accounts_rescued += 1
                    # Lost: started healthy (>=70), ended critical (<50)
                    if earliest >= 70 and latest < 50:
                        accounts_lost += 1

            # Playbook executions on this CSM's accounts
            execs = PlaybookExecutionV2.query.filter(
                PlaybookExecutionV2.account_id.in_(acct_ids),
                PlaybookExecutionV2.customer_id == customer_id,
            ).all()

            resolved = sum(1 for e in execs if e.outcome == 'resolved')
            rev_protected = sum(float(e.revenue_protected or 0) for e in execs)
            rev_expanded = sum(float(e.revenue_expanded or 0) for e in execs)

            # v2: audit-trail-derived actions_taken count.
            # Spans 'playbook' (playbook_execute/complete) + 'signal'
            # (signal_submit/enrich/review/escalate) categories — i.e. every
            # CSM-initiated event that's scoped to an account.
            actions_taken = 0
            try:
                str_acct_ids = [str(aid) for aid in acct_ids]
                actions_taken = ActivityLog.query.filter(
                    ActivityLog.customer_id == customer_id,
                    ActivityLog.resource_type == 'account',
                    ActivityLog.resource_id.in_(str_acct_ids),
                    ActivityLog.action_category.in_(['playbook', 'signal']),
                ).count()
            except Exception:
                actions_taken = 0  # ActivityLog table may not exist on older tenants

            scorecards[csm] = {
                'csm_name': csm,
                'accounts_managed': len(accts),
                'total_arr': total_arr,
                'avg_health_delta': round(sum(health_deltas) / len(health_deltas), 1) if health_deltas else 0,
                'accounts_improving': sum(1 for d in health_deltas if d > 5),
                'accounts_declining': sum(1 for d in health_deltas if d < -5),
                # v2: rescue attribution (started-critical → ended-healthy)
                'accounts_rescued': accounts_rescued,
                'accounts_lost': accounts_lost,
                'playbooks_executed': len(execs),
                'playbooks_resolved': resolved,
                'success_rate_pct': round(resolved / len(execs) * 100, 1) if execs else 0,
                # v2: audit-derived activity count
                'actions_taken': actions_taken,
                'revenue_protected': rev_protected,
                'revenue_expanded': rev_expanded,
                'total_revenue_impact': rev_protected + rev_expanded,
            }

        return {
            'scope': 'portfolio',
            'customer_id': customer_id,
            'csm_count': len(scorecards),
            'scorecards': scorecards,
        }


# ===================================================================
# Tool: get_csm_ranking (v2 — Apr 21 addition per buyer feedback)
# ===================================================================

@mcp.tool
def get_csm_ranking(customer_id: int, metric: str = 'composite') -> dict:
    """Rank CSMs by performance metric across the portfolio.

    Consumes get_csm_scorecard output and sorts CSMs by a chosen metric.
    Answers the buyer question "how do I grade people perf on the CS team."

    Metrics available:
    - 'composite' (default): weighted combination of rescue count (40%),
      revenue impact (30%), playbook success rate (20%), activity level (10%).
      Normalized by book size so larger books don't automatically win.
    - 'rescue_count': accounts_rescued sorted high-to-low
    - 'revenue_impact': total revenue_protected + revenue_expanded
    - 'success_rate': playbook success_rate_pct
    - 'activity': actions_taken normalized by accounts_managed

    Args:
        customer_id: The customer (tenant) ID
        metric: Sort metric (default 'composite')
    """
    _check_mcp_enabled()
    _require_auth(customer_id)
    app = _get_flask_app()

    with app.app_context():
        # Delegate to get_csm_scorecard for the raw data, then rank.
        scorecard_result = get_csm_scorecard.fn(customer_id=customer_id)
        scorecards = scorecard_result.get('scorecards', {})

        def _score(sc: dict) -> float:
            accts = max(sc.get('accounts_managed', 1), 1)
            if metric == 'rescue_count':
                return sc.get('accounts_rescued', 0)
            if metric == 'revenue_impact':
                return sc.get('total_revenue_impact', 0)
            if metric == 'success_rate':
                return sc.get('success_rate_pct', 0)
            if metric == 'activity':
                return sc.get('actions_taken', 0) / accts
            # composite (default): weighted normalized score
            rescue_norm = sc.get('accounts_rescued', 0) / accts  # 0..1
            # Revenue scaled to per-account-managed then log-ish via sqrt
            rev_per_acct = (sc.get('total_revenue_impact', 0) / accts) / 1_000_000  # $M per account
            success = sc.get('success_rate_pct', 0) / 100  # 0..1
            activity = min((sc.get('actions_taken', 0) / accts) / 3, 1.0)  # 0..1 capped
            return round(
                (0.40 * rescue_norm)
                + (0.30 * rev_per_acct)
                + (0.20 * success)
                + (0.10 * activity),
                4,
            )

        ranked = sorted(
            [
                {**sc, 'composite_score': _score(sc)}
                for sc in scorecards.values()
            ],
            key=lambda r: r['composite_score'] if metric == 'composite' else _score(r),
            reverse=True,
        )

        return {
            'scope': 'portfolio',
            'customer_id': customer_id,
            'metric': metric,
            'csm_count': len(ranked),
            'ranking': [
                {
                    'rank': i + 1,
                    'csm_name': r['csm_name'],
                    'accounts_managed': r['accounts_managed'],
                    'accounts_rescued': r['accounts_rescued'],
                    'accounts_lost': r['accounts_lost'],
                    'total_revenue_impact': r['total_revenue_impact'],
                    'success_rate_pct': r['success_rate_pct'],
                    'actions_taken': r['actions_taken'],
                    'composite_score': r['composite_score'],
                }
                for i, r in enumerate(ranked)
            ],
        }


# ===================================================================
# Tool: get_calibration_history
# ===================================================================

@mcp.tool
def get_calibration_history(customer_id: int, limit: int = 10) -> dict:
    """Weight calibration history for Wizard C and manual KPI weight changes.

    Use for drift detection and what-if analysis on pillar/KPI weights.

    Args:
        customer_id: The customer (tenant) ID
        limit: Max records to return (default 10)
    """
    _check_mcp_enabled()
    _require_auth(customer_id)
    app = _get_flask_app()

    with app.app_context():
        from utils.calibration_history import fetch_calibration_history
        return fetch_calibration_history(customer_id, limit=limit)


# ===================================================================
# Tool: get_llm_cost_summary
# ===================================================================

@mcp.tool
def get_llm_cost_summary(customer_id: int, period: str = 'daily') -> dict:
    """Get LLM cost and budget status for a customer — daily or monthly total spend, call count, per-module breakdown, remaining budget, and circuit-breaker state.

    Backed by the canonical llm_budget_controller (llm_usage_log table).
    Use this to answer: "how much have we spent on LLM calls today/this month",
    "which module is driving cost", "are we close to the budget cap".

    Args:
        customer_id: The customer (tenant) ID
        period: 'daily' (default) or 'monthly'
    """
    _check_mcp_enabled()
    _require_auth(customer_id)
    app = _get_flask_app()

    with app.app_context():
        if period not in ('daily', 'monthly'):
            raise ToolError("period must be 'daily' or 'monthly'")

        from utils.llm_budget_controller import get_usage_summary, get_budget_status

        usage = get_usage_summary(customer_id, period=period)
        budget = get_budget_status(customer_id)

        circuit_statuses = {
            status for status in (
                budget.get('circuit_breaker', {}).get('daily_calls_status'),
                budget.get('circuit_breaker', {}).get('daily_spend_status'),
                budget.get('circuit_breaker', {}).get('monthly_spend_status'),
            ) if status
        }
        if 'blocked' in circuit_statuses:
            overall_state = 'blocked'
        elif 'warning' in circuit_statuses:
            overall_state = 'warning'
        else:
            overall_state = 'ok'

        return {
            'scope': 'customer',
            'customer_id': customer_id,
            'period': period,
            'totals': {
                'call_count': usage.get('call_count', 0),
                'cost_usd': round(usage.get('total_cost_usd', 0.0), 4),
                'tokens_in': usage.get('total_tokens_in', 0),
                'tokens_out': usage.get('total_tokens_out', 0),
            },
            'by_module': usage.get('by_module', {}),
            'budget': {
                'daily': budget.get('daily', {}),
                'monthly': budget.get('monthly', {}),
                'limits': budget.get('limits', {}),
            },
            'circuit_breaker_state': overall_state,
            'circuit_breaker_detail': budget.get('circuit_breaker', {}),
        }
