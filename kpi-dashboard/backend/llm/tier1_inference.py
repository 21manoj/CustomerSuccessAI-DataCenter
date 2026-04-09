"""
Tier 1 KPI Inference — Infer context graph from accounts + KPI data only.

When a customer provides only accounts.csv + kpi_measurements.csv (no signals,
outcomes, decisions, or edges), this module uses Claude to infer what likely
happened based on KPI patterns and health score trajectories.

Gated behind WITH_LLM feature flag. Uses Claude Haiku for speed and cost.

Usage:
    from llm.tier1_inference import infer_context_from_kpis
    result = infer_context_from_kpis(customer_id=123)
"""

import json
import logging
import time
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Model: Haiku for structured inference (fast, cheap, reliable JSON output)
LLM_MODEL = 'claude-haiku-4-5-20251001'
MAX_ACCOUNTS_PER_BATCH = 5
MAX_TOKENS = 4096


def _check_prerequisites(customer_id: int) -> Tuple[bool, str]:
    """Check if LLM inference should run for this customer.

    Returns (should_run, reason).
    """
    # Check 1: WITH_LLM feature flag (per-customer DB toggle)
    try:
        from models import FeatureToggle as FTModel
        toggle = FTModel.query.filter_by(
            customer_id=customer_id, feature_name='with_llm',
        ).first()
        if not (toggle and toggle.enabled):
            # Also check global feature flag
            from feature_toggles import feature_toggles, FeatureToggle
            if not feature_toggles.is_enabled(FeatureToggle.WITH_LLM):
                return False, 'WITH_LLM feature flag disabled'
    except Exception:
        return False, 'Feature toggle check failed'

    # Check 2: Anthropic API key available
    try:
        from anthropic_key_utils import has_anthropic_api_key
        if not has_anthropic_api_key(customer_id):
            return False, 'No Anthropic API key configured'
    except Exception:
        import os
        if not os.environ.get('ANTHROPIC_API_KEY'):
            return False, 'No ANTHROPIC_API_KEY environment variable'

    # Check 3: Customer has KPI data but lacks context graph nodes
    try:
        from models import Account, DC2SKPI, ContextNode
        acct_ids = [a.account_id for a in
                    Account.query.filter_by(customer_id=customer_id).all()]
        if not acct_ids:
            return False, 'No accounts found'

        kpi_count = DC2SKPI.query.filter(
            DC2SKPI.account_id.in_(acct_ids)
        ).count()
        if kpi_count == 0:
            return False, 'No KPI data found'

        # Skip if customer already has LLM-inferred or CSV-provided signals
        existing_signals = ContextNode.query.filter(
            ContextNode.customer_id == customer_id,
            ContextNode.node_type == 'SIGNAL',
            ContextNode.source_platform.in_(['csv_import', 'llm_inference']),
        ).count()
        if existing_signals > 0:
            return False, f'Context already exists ({existing_signals} signal nodes)'
    except Exception as e:
        return False, f'Prerequisite check error: {e}'

    return True, 'Ready'


def _build_account_summaries(customer_id: int) -> List[Dict]:
    """Build KPI trajectory summaries for each account.

    Returns list of dicts with account metadata + KPI change analysis.
    """
    from models import Account, DC2SKPI, HealthScore
    from sqlalchemy import desc
    import utils.health_thresholds as ht

    accounts = Account.query.filter_by(customer_id=customer_id).all()
    summaries = []

    for acct in accounts:
        # Health score history (monthly)
        scores = (
            HealthScore.query
            .filter_by(account_id=acct.account_id)
            .order_by(HealthScore.measurement_month.asc())
            .all()
        )
        if not scores:
            continue

        health_values = [float(s.health_score) for s in scores]
        current_health = health_values[-1]
        peak_health = max(health_values)
        lowest_health = min(health_values)
        health_delta = health_values[-1] - health_values[0]

        # Skip stable accounts (health didn't move significantly)
        if abs(health_delta) < 8 and (peak_health - lowest_health) < 15:
            continue

        # Top KPI changes (biggest movers)
        kpis = (
            DC2SKPI.query
            .filter_by(account_id=acct.account_id)
            .order_by(DC2SKPI.measured_at.asc())
            .all()
        )

        # Group by KPI code, find biggest changes
        kpi_series = defaultdict(list)
        for k in kpis:
            kpi_series[k.kpi_code].append((str(k.measured_at)[:10], float(k.value)))

        kpi_changes = []
        for code, series in kpi_series.items():
            if len(series) < 2:
                continue
            first_val = series[0][1]
            last_val = series[-1][1]
            if first_val == 0:
                continue
            pct_change = (last_val - first_val) / first_val * 100
            if abs(pct_change) > 15:  # Only significant changes
                # Find the steepest month-over-month change
                max_drop_date = series[0][0]
                max_drop_pct = 0
                for i in range(1, len(series)):
                    if series[i - 1][1] != 0:
                        month_pct = (series[i][1] - series[i - 1][1]) / series[i - 1][1] * 100
                        if abs(month_pct) > abs(max_drop_pct):
                            max_drop_pct = month_pct
                            max_drop_date = series[i][0]

                kpi_changes.append({
                    'code': code,
                    'pillar': code.split('-')[0] if '-' in code else '',
                    'total_change_pct': round(pct_change, 1),
                    'steepest_date': max_drop_date,
                    'steepest_pct': round(max_drop_pct, 1),
                    'first_val': round(first_val, 1),
                    'last_val': round(last_val, 1),
                })

        # Sort by absolute change (biggest movers first)
        kpi_changes.sort(key=lambda x: abs(x['total_change_pct']), reverse=True)

        health_trajectory_str = ' → '.join(
            [f'{h:.0f}' for h in health_values]
        )

        summaries.append({
            'account_id': acct.account_id,
            'account_name': acct.account_name,
            'arr': float(acct.revenue or 0),
            'industry': acct.industry or 'Unknown',
            'current_health': current_health,
            'health_status': ht.classify(current_health),
            'health_delta': health_delta,
            'health_trajectory': health_trajectory_str,
            'months': len(health_values),
            'kpi_changes': kpi_changes[:5],  # Top 5 movers
            'peak_health': peak_health,
            'lowest_health': lowest_health,
        })

    return summaries


def _call_claude(summaries: List[Dict], customer_id: int) -> List[Dict]:
    """Call Claude API with account summaries, return inferred context.

    Batches accounts into groups of MAX_ACCOUNTS_PER_BATCH.
    """
    from llm.prompts.tier1_kpi_inference import (
        SYSTEM_PROMPT, ACCOUNT_TEMPLATE, BATCH_PROMPT, FEW_SHOT_EXAMPLE,
    )

    try:
        from anthropic_key_utils import get_anthropic_api_key
        api_key = get_anthropic_api_key(customer_id)
    except Exception:
        import os
        api_key = os.environ.get('ANTHROPIC_API_KEY')

    if not api_key:
        logger.warning('No API key for LLM inference')
        return []

    import anthropic
    client = anthropic.Anthropic(api_key=api_key)

    all_inferences = []

    # Batch accounts
    for batch_start in range(0, len(summaries), MAX_ACCOUNTS_PER_BATCH):
        batch = summaries[batch_start:batch_start + MAX_ACCOUNTS_PER_BATCH]

        # Build per-account blocks
        account_blocks = []
        for s in batch:
            kpi_text = '\n'.join(
                f"  {c['code']}: {c['first_val']} → {c['last_val']} ({c['total_change_pct']:+.0f}%), "
                f"steepest change {c['steepest_pct']:+.0f}% around {c['steepest_date']}"
                for c in s['kpi_changes']
            ) or '  (no significant KPI changes)'

            account_blocks.append(ACCOUNT_TEMPLATE.format(
                account_name=s['account_name'],
                arr=s['arr'],
                industry=s['industry'],
                health_trajectory=s['health_trajectory'],
                current_health=s['current_health'],
                health_status=s['health_status'],
                health_delta=s['health_delta'],
                months=s['months'],
                kpi_changes=kpi_text,
            ))

        prompt = BATCH_PROMPT.format(
            n_accounts=len(batch),
            accounts_block='\n---\n'.join(account_blocks),
        )

        # Include few-shot example for first batch
        if batch_start == 0:
            prompt = FEW_SHOT_EXAMPLE + '\n\nNow analyze these accounts:\n\n' + prompt

        try:
            t0 = time.time()
            response = client.messages.create(
                model=LLM_MODEL,
                system=SYSTEM_PROMPT,
                messages=[{'role': 'user', 'content': prompt}],
                max_tokens=MAX_TOKENS,
                temperature=0.2,  # Low temp for structured output
            )
            duration = time.time() - t0

            # Parse response
            text = response.content[0].text if response.content else ''
            # Strip markdown code fences if present
            if text.strip().startswith('```'):
                text = text.strip().split('\n', 1)[1]
                if text.strip().endswith('```'):
                    text = text.strip()[:-3]

            inferences = json.loads(text)
            if isinstance(inferences, dict):
                inferences = [inferences]

            logger.info(
                'LLM Tier 1: batch %d-%d → %d inferences (%.1fs, %d input + %d output tokens)',
                batch_start, batch_start + len(batch),
                len(inferences), duration,
                response.usage.input_tokens, response.usage.output_tokens,
            )
            all_inferences.extend(inferences)

        except json.JSONDecodeError as e:
            logger.warning('LLM Tier 1: JSON parse error for batch %d: %s', batch_start, e)
        except Exception as e:
            logger.warning('LLM Tier 1: API call failed for batch %d: %s', batch_start, e)

    return all_inferences


def _write_inferred_nodes(
    customer_id: int,
    inferences: List[Dict],
    account_map: Dict[str, int],  # name → account_id
    arr_map: Dict[int, float],    # account_id → ARR
) -> Dict[str, int]:
    """Write LLM-inferred context nodes and edges to the database.

    Returns counts: {signals_created, outcomes_created, decisions_created, edges_created}
    """
    from utils.context_graph import upsert_node, upsert_edge
    from extensions import db
    from datetime import datetime as dt

    counts = {'signals': 0, 'outcomes': 0, 'decisions': 0, 'edges': 0}

    for inf in inferences:
        account_name = inf.get('account_name', '')
        account_id = account_map.get(account_name)
        if not account_id:
            continue

        arr = arr_map.get(account_id, 0)
        created_node_ids = {}  # track for edge creation

        # Write inferred signals
        for sig in inf.get('inferred_signals', []):
            try:
                sig_date = sig.get('date', dt.utcnow().strftime('%Y-%m-%d'))
                source_eid = f'llm_sig:{account_id}:{sig["type"]}:{sig_date}'
                node = upsert_node(
                    customer_id=customer_id,
                    account_id=account_id,
                    node_type='SIGNAL',
                    title=sig.get('content', f'Inferred: {sig["type"]}')[:500],
                    occurred_at=dt.strptime(sig_date[:10], '%Y-%m-%d'),
                    properties={
                        'signal_type': sig['type'],
                        'sentiment': sig.get('sentiment', 'negative'),
                        'inferred_by': 'llm_tier1',
                        'confidence': str(sig.get('confidence', 0.7)),
                    },
                    source_platform='llm_inference',
                    source_event_id=source_eid,
                    node_subtype=sig['type'],
                    tier=2,
                    confidence=sig.get('confidence', 0.7),
                )
                if node:
                    created_node_ids[f'signal:{sig["type"]}'] = node.node_id
                    counts['signals'] += 1
            except Exception as e:
                logger.debug('LLM signal write error: %s', e)

        # Write inferred decisions
        for dec in inf.get('inferred_decisions', []):
            try:
                dec_date = dec.get('date', dt.utcnow().strftime('%Y-%m-%d'))
                source_eid = f'llm_dec:{account_id}:{dec["type"]}:{dec_date}'
                node = upsert_node(
                    customer_id=customer_id,
                    account_id=account_id,
                    node_type='DECISION',
                    title=dec.get('title', f'Inferred: {dec["type"]}')[:500],
                    occurred_at=dt.strptime(dec_date[:10], '%Y-%m-%d'),
                    properties={
                        'decision_type': dec['type'],
                        'inferred_by': 'llm_tier1',
                        'confidence': str(dec.get('confidence', 0.7)),
                    },
                    source_platform='llm_inference',
                    source_event_id=source_eid,
                    node_subtype=dec['type'],
                    tier=2,
                    confidence=dec.get('confidence', 0.7),
                )
                if node:
                    created_node_ids[f'decision:{dec["type"]}'] = node.node_id
                    counts['decisions'] += 1
            except Exception as e:
                logger.debug('LLM decision write error: %s', e)

        # Write inferred outcomes
        for out in inf.get('inferred_outcomes', []):
            try:
                source_eid = f'llm_out:{account_id}:{out["type"]}'
                rev_impact = out.get('revenue_impact', 0)
                # Scale revenue impact to ARR if it looks like a percentage
                if rev_impact and 0 < abs(rev_impact) < 1:
                    rev_impact = arr * rev_impact

                node = upsert_node(
                    customer_id=customer_id,
                    account_id=account_id,
                    node_type='OUTCOME',
                    title=out.get('title', f'Inferred: {out["type"]}')[:500],
                    occurred_at=dt.utcnow(),
                    properties={
                        'outcome_type': out['type'],
                        'inferred_by': 'llm_tier1',
                        'confidence': str(out.get('confidence', 0.7)),
                    },
                    source_platform='llm_inference',
                    source_event_id=source_eid,
                    node_subtype=out['type'],
                    tier=2,
                    confidence=out.get('confidence', 0.7),
                    revenue_impact=rev_impact if rev_impact else None,
                    revenue_impact_type=out['type'] if rev_impact else None,
                )
                if node:
                    created_node_ids[f'outcome:{out["type"]}'] = node.node_id
                    counts['outcomes'] += 1
            except Exception as e:
                logger.debug('LLM outcome write error: %s', e)

        # Write causal edges: signal → decision → outcome
        signal_ids = [v for k, v in created_node_ids.items() if k.startswith('signal:')]
        decision_ids = [v for k, v in created_node_ids.items() if k.startswith('decision:')]
        outcome_ids = [v for k, v in created_node_ids.items() if k.startswith('outcome:')]

        # Signal → first Decision
        if signal_ids and decision_ids:
            for sig_id in signal_ids:
                try:
                    edge, created = upsert_edge(
                        from_node_id=sig_id,
                        to_node_id=decision_ids[0],
                        edge_type='LED_TO',
                        confidence=0.65,
                        source_platform='llm_inference',
                        created_by='llm_tier1',
                        customer_id=customer_id,
                        properties={'inferred_by': 'llm_tier1'},
                    )
                    if created:
                        counts['edges'] += 1
                except Exception:
                    pass

        # Decision → Outcome
        if decision_ids and outcome_ids:
            for dec_id in decision_ids:
                for out_id in outcome_ids:
                    try:
                        edge, created = upsert_edge(
                            from_node_id=dec_id,
                            to_node_id=out_id,
                            edge_type='LED_TO',
                            confidence=0.65,
                            source_platform='llm_inference',
                            created_by='llm_tier1',
                            customer_id=customer_id,
                            properties={'inferred_by': 'llm_tier1'},
                        )
                        if created:
                            counts['edges'] += 1
                    except Exception:
                        pass

    try:
        db.session.commit()
    except Exception as e:
        logger.warning('LLM inference commit failed: %s', e)
        db.session.rollback()

    return counts


def infer_context_from_kpis(customer_id: int) -> Dict:
    """Main entry point: infer context graph from KPI data.

    Returns:
        {
            'status': 'completed' | 'skipped' | 'error',
            'reason': str,
            'accounts_analyzed': int,
            'accounts_with_inferences': int,
            'signals_created': int,
            'outcomes_created': int,
            'decisions_created': int,
            'edges_created': int,
            'duration_s': float,
        }
    """
    t0 = time.time()

    # Prerequisites
    should_run, reason = _check_prerequisites(customer_id)
    if not should_run:
        return {
            'status': 'skipped',
            'reason': reason,
            'duration_s': round(time.time() - t0, 2),
        }

    # Build account summaries from KPI data
    summaries = _build_account_summaries(customer_id)
    if not summaries:
        return {
            'status': 'skipped',
            'reason': 'No accounts with significant health changes',
            'duration_s': round(time.time() - t0, 2),
        }

    logger.info(
        'LLM Tier 1: analyzing %d accounts (of %d total) for customer %d',
        len(summaries), len(summaries), customer_id,
    )

    # Call Claude
    inferences = _call_claude(summaries, customer_id)
    if not inferences:
        return {
            'status': 'completed',
            'reason': 'LLM returned no inferences',
            'accounts_analyzed': len(summaries),
            'accounts_with_inferences': 0,
            'duration_s': round(time.time() - t0, 2),
        }

    # Build lookup maps
    from models import Account
    accounts = Account.query.filter_by(customer_id=customer_id).all()
    account_map = {a.account_name: a.account_id for a in accounts}
    arr_map = {a.account_id: float(a.revenue or 0) for a in accounts}

    # Write to DB
    counts = _write_inferred_nodes(customer_id, inferences, account_map, arr_map)

    duration = round(time.time() - t0, 2)
    logger.info(
        'LLM Tier 1 complete: customer=%d %d signals, %d decisions, %d outcomes, '
        '%d edges created in %.1fs',
        customer_id, counts['signals'], counts['decisions'],
        counts['outcomes'], counts['edges'], duration,
    )

    return {
        'status': 'completed',
        'reason': 'OK',
        'accounts_analyzed': len(summaries),
        'accounts_with_inferences': len(inferences),
        **counts,
        'duration_s': duration,
    }
