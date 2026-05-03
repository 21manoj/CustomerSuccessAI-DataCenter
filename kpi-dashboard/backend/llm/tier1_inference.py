"""
Tier-1 LLM context-graph inference (P2 plan).

Two operating modes, auto-detected from account state:

  full        2-CSV mode (accounts + KPIs only). The LLM derives
              signals, decisions, outcomes, and causal edges from
              KPI trajectories alone. Skipped if the account already
              has CSV-uploaded SIGNAL nodes.

  edges_only  3-CSV / 4-CSV mode (accounts + KPIs + signals). CSV
              signals are kept as-is; the LLM is asked only for
              decisions, outcomes, and causal edges that connect
              existing signals to those new nodes. Skipped if the
              account already has ≥10 LLM-enrichment edges (idempotent).

All LLM-written nodes get:
  source = 'inferred'
  source_platform = 'llm_enrichment'

All LLM-written edges get:
  source = 'inferred'
  source_platform = 'llm_enrichment'

Per-edge confidence comes from the LLM. The
`utils.provenance.is_trustworthy_edge` helper (default threshold 0.6)
gates which edges are persisted — low-confidence edges are dropped
at write time so they cannot pollute downstream Wizard B/C
correlation reads later.

Contract:
    run_tier1(customer_id, mode='auto') -> dict
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)

# Sentinel — kept distinct from `wizard_a` and other source_platforms so
# the migration backfill and provenance helpers can target this caller.
SOURCE_PLATFORM = 'llm_enrichment'

# Number of existing LLM-enrichment edges that mark an account as
# already enriched. Skipping above this avoids re-billing on idempotent
# process_data runs.
EDGES_ONLY_SKIP_THRESHOLD = 10

# Default model — Sonnet is cost-balanced; can be overridden by env.
DEFAULT_MODEL = os.environ.get('LLM_TIER1_MODEL', 'claude-sonnet-4-20250514')


def run_tier1(
    customer_id: int,
    *,
    mode: str = 'auto',
    account_ids: Optional[list[int]] = None,
    dry_run: bool = False,
) -> dict:
    """Top-level entry point.

    Args:
        customer_id: Tenant.
        mode: 'auto' | 'full' | 'edges_only'. 'auto' picks per-account.
        account_ids: Restrict to a specific subset (used by incremental
            process_data). None means all accounts for the customer.
        dry_run: If True, build prompts and check prerequisites but do
            not call the LLM or write to the DB.

    Returns:
        {
            'status': 'completed' | 'skipped' | 'error',
            'mode': resolved mode (per-account if 'auto'),
            'accounts_processed': int,
            'nodes_written': int,
            'edges_written': int,
            'edges_dropped_low_confidence': int,
            'cost_usd': float,
            'per_account': {account_id: {...}},
        }
    """
    from models import Account
    from extensions import db  # noqa: F401  -- ensures app context exists

    accounts = Account.query.filter_by(customer_id=customer_id).all()
    if account_ids is not None:
        accounts = [a for a in accounts if a.account_id in account_ids]
    if not accounts:
        return {
            'status': 'skipped',
            'reason': f'No accounts for customer {customer_id}.',
            'accounts_processed': 0,
            'nodes_written': 0,
            'edges_written': 0,
            'edges_dropped_low_confidence': 0,
            'cost_usd': 0.0,
            'per_account': {},
        }

    totals = {
        'nodes_written': 0,
        'edges_written': 0,
        'edges_dropped_low_confidence': 0,
        'cost_usd': 0.0,
    }
    per_account: dict[int, dict] = {}

    for acct in accounts:
        try:
            resolved_mode, reason = _resolve_mode(acct.account_id, mode)
            if resolved_mode == 'skip':
                per_account[acct.account_id] = {
                    'status': 'skipped',
                    'reason': reason,
                }
                continue

            result = _run_for_account(
                customer_id=customer_id,
                account_id=acct.account_id,
                mode=resolved_mode,
                dry_run=dry_run,
            )
            per_account[acct.account_id] = result
            totals['nodes_written'] += result.get('nodes_written', 0)
            totals['edges_written'] += result.get('edges_written', 0)
            totals['edges_dropped_low_confidence'] += result.get(
                'edges_dropped_low_confidence', 0
            )
            totals['cost_usd'] += result.get('cost_usd', 0.0)

        except Exception as e:
            logger.error(
                f'Tier1 failed for account {acct.account_id}: {e}',
                exc_info=True,
            )
            per_account[acct.account_id] = {'status': 'error', 'error': str(e)}

    return {
        'status': 'completed',
        'mode': mode,
        'accounts_processed': len(accounts),
        **totals,
        'per_account': per_account,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Mode resolution
# ─────────────────────────────────────────────────────────────────────────────

def _resolve_mode(account_id: int, requested: str) -> tuple[str, str]:
    """Pick effective mode for one account.

    Returns (mode, reason). `mode` is 'full' | 'edges_only' | 'skip'.
    """
    from models import ContextNode, ContextEdge
    from extensions import db

    if requested not in ('auto', 'full', 'edges_only'):
        return 'skip', f'Unknown mode: {requested}'

    # Count CSV signals + existing LLM edges for this account.
    csv_signals = (
        db.session.query(ContextNode)
        .filter(
            ContextNode.account_id == account_id,
            ContextNode.node_type == 'SIGNAL',
            ContextNode.source.in_(['observed', 'customer']),  # legacy + new
        )
        .count()
    )
    llm_edges = (
        db.session.query(ContextEdge)
        .join(ContextNode, ContextEdge.from_node_id == ContextNode.node_id)
        .filter(
            ContextNode.account_id == account_id,
            ContextEdge.source_platform == SOURCE_PLATFORM,
        )
        .count()
    )

    if requested == 'full':
        if csv_signals > 0:
            return 'skip', (
                f'full mode requested but {csv_signals} CSV signals exist; '
                'use edges_only or auto'
            )
        return 'full', 'explicit full'

    if requested == 'edges_only':
        if csv_signals == 0:
            return 'skip', 'edges_only requires CSV signals; none found'
        if llm_edges >= EDGES_ONLY_SKIP_THRESHOLD:
            return 'skip', f'already enriched ({llm_edges} LLM edges)'
        return 'edges_only', 'explicit edges_only'

    # auto
    if csv_signals == 0:
        return 'full', 'auto: no CSV signals → full inference'
    if llm_edges >= EDGES_ONLY_SKIP_THRESHOLD:
        return 'skip', (
            f'auto: already enriched ({llm_edges} LLM edges ≥ '
            f'{EDGES_ONLY_SKIP_THRESHOLD}); idempotent skip'
        )
    return 'edges_only', f'auto: {csv_signals} signals + thin enrichment'


# ─────────────────────────────────────────────────────────────────────────────
# Per-account driver
# ─────────────────────────────────────────────────────────────────────────────

def _run_for_account(
    *,
    customer_id: int,
    account_id: int,
    mode: str,
    dry_run: bool,
) -> dict:
    summary = _build_account_summary(account_id)
    kpi_trajectory = _build_kpi_trajectory(account_id)
    existing_signals = (
        _build_existing_signals(account_id) if mode == 'edges_only' else ''
    )

    if mode == 'full':
        from llm.prompts.tier1_kpi_inference import render_full_prompt
        prompt = render_full_prompt(
            account_summary=summary, kpi_trajectory=kpi_trajectory,
        )
    else:  # edges_only
        from llm.prompts.tier1_kpi_inference import render_edge_enrichment_prompt
        prompt = render_edge_enrichment_prompt(
            account_summary=summary,
            existing_signals=existing_signals,
            kpi_trajectory=kpi_trajectory,
        )

    if dry_run:
        return {
            'status': 'dry_run',
            'mode': mode,
            'prompt_chars': len(prompt),
            'nodes_written': 0,
            'edges_written': 0,
            'edges_dropped_low_confidence': 0,
            'cost_usd': 0.0,
        }

    # ── Budget check ──
    budget_ok = True
    try:
        from utils.llm_budget_controller import can_call
        budget_ok = can_call(customer_id, 'llm_tier1', estimated_tokens=2500)
    except Exception:
        pass  # fail-open
    if not budget_ok:
        return {
            'status': 'skipped',
            'reason': 'budget exceeded',
            'mode': mode,
            'nodes_written': 0,
            'edges_written': 0,
            'edges_dropped_low_confidence': 0,
            'cost_usd': 0.0,
        }

    # ── LLM call ──
    response_text, tokens_in, tokens_out, cost = _call_llm(prompt)

    # ── Cost record ──
    try:
        from utils.llm_budget_controller import record_usage
        record_usage(
            customer_id, 'llm_tier1', tokens_in, tokens_out,
            model=DEFAULT_MODEL, success=True,
        )
    except Exception:
        pass

    # ── Parse + persist ──
    payload = _safe_parse_json(response_text)
    if payload is None:
        logger.warning(
            f'Tier1 acct={account_id}: LLM did not return valid JSON; skipping persist'
        )
        return {
            'status': 'parse_error',
            'mode': mode,
            'nodes_written': 0,
            'edges_written': 0,
            'edges_dropped_low_confidence': 0,
            'cost_usd': cost,
        }

    written = _persist(
        customer_id=customer_id,
        account_id=account_id,
        mode=mode,
        payload=payload,
    )

    return {
        'status': 'completed',
        'mode': mode,
        'cost_usd': cost,
        **written,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Summary builders
# ─────────────────────────────────────────────────────────────────────────────

def _build_account_summary(account_id: int) -> str:
    from models import Account
    a = Account.query.filter_by(account_id=account_id).first()
    if not a:
        return f'account_id={account_id} (not found)'
    return (
        f'account_id={a.account_id}, name={a.account_name!r}, '
        f'arr=${float(a.revenue or 0):,.0f}, '
        f'arc_type={getattr(a, "arc_type", None)}, '
        f'arc_phase={getattr(a, "arc_phase", None)}'
    )


def _build_kpi_trajectory(account_id: int, months: int = 12) -> str:
    """Compact textual KPI trajectory (last `months` months)."""
    from models import DC2SKPI
    from extensions import db
    from sqlalchemy import func

    rows = (
        db.session.query(
            DC2SKPI.kpi_code,
            func.date_trunc('month', DC2SKPI.measured_at).label('m'),
            func.avg(DC2SKPI.value).label('v'),
        )
        .filter(DC2SKPI.account_id == account_id)
        .group_by(DC2SKPI.kpi_code, 'm')
        .order_by('m')
        .all()
    )
    if not rows:
        return '(no KPI measurements)'

    by_code: dict[str, list[tuple[str, float]]] = {}
    for r in rows:
        ms = r.m.strftime('%Y-%m') if r.m else 'unknown'
        by_code.setdefault(r.kpi_code, []).append((ms, float(r.v)))

    lines = []
    for code, series in sorted(by_code.items()):
        recent = series[-months:]
        compact = ', '.join(f'{m}:{v:.1f}' for m, v in recent)
        lines.append(f'  {code}: {compact}')
    return '\n'.join(lines)


def _build_existing_signals(account_id: int) -> str:
    """Compact list of CSV signal nodes for the LLM to reference by ID."""
    from models import ContextNode
    from extensions import db
    sigs = (
        db.session.query(ContextNode)
        .filter(
            ContextNode.account_id == account_id,
            ContextNode.node_type == 'SIGNAL',
            ContextNode.source.in_(['observed', 'customer']),
        )
        .order_by(ContextNode.occurred_at)
        .limit(40)
        .all()
    )
    if not sigs:
        return '(none)'
    out = []
    for i, s in enumerate(sigs, start=1):
        ts = s.occurred_at.strftime('%Y-%m-%d') if s.occurred_at else '?'
        out.append(
            f'  signal:{i}  node:{s.node_id}  {ts}  {s.node_subtype or "?"}  '
            f'{(s.title or "")[:80]}'
        )
    return '\n'.join(out)


# ─────────────────────────────────────────────────────────────────────────────
# LLM call (Anthropic)
# ─────────────────────────────────────────────────────────────────────────────

def _call_llm(prompt: str) -> tuple[str, int, int, float]:
    """Call Anthropic; return (response_text, tokens_in, tokens_out, cost_usd).

    Resolves the API key via the same path as Ask AI (per-customer or env).
    Errors propagate so the caller can mark the account as failed.
    """
    try:
        from anthropic_key_utils import get_anthropic_api_key
        api_key = get_anthropic_api_key()
    except Exception:
        api_key = os.environ.get('ANTHROPIC_API_KEY')
    if not api_key:
        raise RuntimeError('No Anthropic API key configured')

    import anthropic
    client = anthropic.Anthropic(api_key=api_key)

    msg = client.messages.create(
        model=DEFAULT_MODEL,
        system='You are an expert customer success analyst. Output strict JSON only.',
        messages=[{'role': 'user', 'content': prompt}],
        max_tokens=4096,
        temperature=0.2,
    )

    text = ''.join(
        block.text for block in msg.content if getattr(block, 'type', '') == 'text'
    )
    tokens_in = getattr(msg.usage, 'input_tokens', 0) or 0
    tokens_out = getattr(msg.usage, 'output_tokens', 0) or 0
    try:
        from utils.llm_budget_controller import estimate_cost
        cost = estimate_cost(DEFAULT_MODEL, tokens_in, tokens_out)
    except Exception:
        cost = 0.0
    return text, tokens_in, tokens_out, cost


def _safe_parse_json(text: str) -> Optional[dict]:
    """Tolerant JSON extraction — strips code fences, picks the first {...} block."""
    if not text:
        return None
    t = text.strip()
    # Strip ```json ... ``` fences
    if t.startswith('```'):
        t = t.split('```', 2)
        t = t[1] if len(t) >= 2 else ''
        if t.startswith('json'):
            t = t[4:]
        t = t.strip()
        if t.endswith('```'):
            t = t[:-3].strip()
    # Find first { ... last }
    start = t.find('{')
    end = t.rfind('}')
    if start == -1 or end == -1 or end <= start:
        return None
    try:
        return json.loads(t[start:end + 1])
    except json.JSONDecodeError:
        return None


# ─────────────────────────────────────────────────────────────────────────────
# Persistence — applies provenance + edge confidence threshold
# ─────────────────────────────────────────────────────────────────────────────

def _persist(
    *,
    customer_id: int,
    account_id: int,
    mode: str,
    payload: dict,
) -> dict:
    """Write LLM-returned nodes/edges. Drops edges below confidence threshold."""
    from models import ContextNode, ContextEdge
    from extensions import db
    from utils.provenance import is_trustworthy_edge, INFERRED

    nodes_written = 0
    edges_written = 0
    edges_dropped = 0

    # node_id by ref ("signal:1", "decision:1", "outcome:1", "node:1234")
    ref_to_node_id: dict[str, int] = {}

    # For edges_only: map "signal:N" / "node:N" to existing CSV signals.
    if mode == 'edges_only':
        existing = (
            db.session.query(ContextNode)
            .filter(
                ContextNode.account_id == account_id,
                ContextNode.node_type == 'SIGNAL',
                ContextNode.source.in_(['observed', 'customer']),
            )
            .order_by(ContextNode.occurred_at)
            .limit(40)
            .all()
        )
        for i, s in enumerate(existing, start=1):
            ref_to_node_id[f'signal:{i}'] = s.node_id
            ref_to_node_id[f'node:{s.node_id}'] = s.node_id

    # ── 1. Persist new nodes (only DECISION/OUTCOME in edges_only; all in full)
    def _persist_nodes(kind: str, list_key: str, node_type: str):
        nonlocal nodes_written
        items = payload.get(list_key) or []
        if not isinstance(items, list):
            return
        for idx, item in enumerate(items, start=1):
            if not isinstance(item, dict):
                continue
            occurred = _parse_date(item.get('occurred_at')) or datetime.utcnow()
            try:
                rev = item.get('revenue_impact')
                rev_num = float(rev) if rev is not None else None
            except (TypeError, ValueError):
                rev_num = None
            n = ContextNode(
                customer_id=customer_id,
                account_id=account_id,
                node_type=node_type,
                node_subtype=str(item.get('subtype') or '')[:50] or None,
                title=str(item.get('title') or '')[:500],
                source=INFERRED,
                source_platform=SOURCE_PLATFORM,
                tier=2,
                occurred_at=occurred,
                revenue_impact=rev_num,
                revenue_impact_type=str(item.get('revenue_impact_type') or '')[:30] or None,
                properties={
                    'inferred_by': 'llm_tier1',
                    'mode': mode,
                },
            )
            db.session.add(n)
            db.session.flush()
            ref = item.get('ref') or f'{kind}:{idx}'
            ref_to_node_id[ref] = n.node_id
            nodes_written += 1

    if mode == 'full':
        _persist_nodes('signal', 'signals', 'SIGNAL')
    _persist_nodes('decision', 'decisions', 'DECISION')
    _persist_nodes('outcome', 'outcomes', 'OUTCOME')

    # ── 2. Persist edges with confidence-threshold gate
    edges = payload.get('causal_edges') or []
    if isinstance(edges, list):
        for edge_def in edges:
            if not isinstance(edge_def, dict):
                continue
            from_ref = edge_def.get('from_ref')
            to_ref = edge_def.get('to_ref')
            if not from_ref or not to_ref:
                continue
            from_id = ref_to_node_id.get(from_ref)
            to_id = ref_to_node_id.get(to_ref)
            if from_id is None or to_id is None or from_id == to_id:
                continue

            try:
                conf = float(edge_def.get('confidence', 0.0) or 0.0)
            except (TypeError, ValueError):
                conf = 0.0

            # ── Edge-confidence gate — provenance helper applied here ──
            class _StubEdge:
                def __init__(self, c): self.confidence = c
            if not is_trustworthy_edge(_StubEdge(conf)):
                edges_dropped += 1
                continue

            edge_type = str(edge_def.get('edge_type') or 'LED_TO')[:30]
            try:
                lag = int(edge_def.get('lag_days') or 0)
            except (TypeError, ValueError):
                lag = 0

            db.session.add(ContextEdge(
                customer_id=customer_id,
                from_node_id=from_id,
                to_node_id=to_id,
                edge_type=edge_type,
                confidence=conf,
                lag_days=lag,
                source=INFERRED,
                source_platform=SOURCE_PLATFORM,
                created_by='llm_tier1',
                properties={'mode': mode},
            ))
            edges_written += 1

    db.session.commit()
    logger.info(
        f'Tier1 acct={account_id} mode={mode} '
        f'nodes={nodes_written} edges={edges_written} dropped={edges_dropped}'
    )
    return {
        'nodes_written': nodes_written,
        'edges_written': edges_written,
        'edges_dropped_low_confidence': edges_dropped,
    }


def _parse_date(s) -> Optional[datetime]:
    if not s or not isinstance(s, str):
        return None
    for fmt in ('%Y-%m-%d', '%Y-%m-%dT%H:%M:%S', '%Y-%m-%dT%H:%M:%SZ'):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    return None
