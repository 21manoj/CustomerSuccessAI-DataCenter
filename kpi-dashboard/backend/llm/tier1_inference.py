"""
Tier 1 KPI Inference — Infer context graph from accounts + KPI data only.

Two modes:
- 'full': Customer provides only accounts.csv + kpi_measurements.csv (no signals).
  Claude infers signals, decisions, outcomes, and causal edges from KPI patterns.
- 'edges_only': Customer provides accounts + KPIs + qualitative signals (3-CSV mode).
  Claude uses existing signals + KPI patterns to infer decisions, outcomes, and causal
  edges — but does NOT create new signal nodes. This enriches the thin 3-CSV graph
  with LLM-inferred causal reasoning.

Gated behind WITH_LLM feature flag. Uses Claude Haiku for speed and cost.

Usage:
    from llm.tier1_inference import infer_context_from_kpis
    result = infer_context_from_kpis(customer_id=123)            # auto-detect mode
    result = infer_context_from_kpis(customer_id=123, mode='edges_only')  # force mode
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
MAX_ACCOUNTS_PER_BATCH_EDGES = 3  # Fewer per batch in edges_only (richer output)
MAX_TOKENS = 4096
MAX_TOKENS_EDGES = 8192  # Edge enrichment needs more tokens (decisions + outcomes + edges per account)


def _check_prerequisites(customer_id: int, mode: str = 'auto') -> Tuple[bool, str, str]:
    """Check if LLM inference should run for this customer.

    Returns (should_run, reason, resolved_mode).
    resolved_mode is 'full', 'edges_only', or '' if should_run is False.

    Gate policy (Apr 2026): LLM Tier 1 is default-ON for 4-CSV onboarding
    (where decisions.csv was NOT uploaded — the context graph needs
    template+LLM enrichment to be useful) and default-OFF for 11-CSV
    onboarding (customer provided their own decisions; extra LLM work
    is redundant). Either default can be overridden by an explicit
    per-customer `with_llm` toggle.
    """
    # Check 1: Detect CSV mode from customer-sourced DECISION nodes.
    # 4-CSV mode: customer didn't upload decisions.csv → 0 customer DECISION nodes
    # 11-CSV mode: customer uploaded decisions.csv → >0 customer DECISION nodes
    try:
        from models import ContextNode, FeatureToggle as FTModel
        customer_decisions = ContextNode.query.filter(
            ContextNode.customer_id == customer_id,
            ContextNode.node_type == 'DECISION',
            ContextNode.source.in_(['observed','customer']),
        ).count()
        is_four_csv_mode = (customer_decisions == 0)

        toggle = FTModel.query.filter_by(
            customer_id=customer_id, feature_name='with_llm',
        ).first()

        if toggle is not None:
            # Explicit per-customer override wins.
            if not toggle.enabled:
                return False, 'with_llm toggle explicitly disabled for this customer', ''
            # else: toggle says on → proceed
        else:
            # No explicit toggle → apply CSV-mode default.
            if not is_four_csv_mode:
                return False, '11-CSV mode (customer decisions uploaded); LLM default-off', ''
            # 4-CSV mode with no explicit toggle → default-on. Fall through.

        # Global kill switch — only blocks if FEATURE_WITH_LLM is explicitly
        # set to "false"/"0" (emergency cost control). Unset/default means
        # let the customer/mode policy above decide. This lets 4-CSV auto-
        # enable work out of the box without requiring an env var.
        import os as _os
        global_flag = (_os.environ.get('FEATURE_WITH_LLM') or '').strip().lower()
        if global_flag in ('false', '0', 'off', 'no'):
            return False, 'Global FEATURE_WITH_LLM=false kill switch active', ''
    except Exception as e:
        return False, f'Feature toggle check failed: {e}', ''

    # Check 2: Anthropic API key available
    try:
        from anthropic_key_utils import has_anthropic_api_key
        if not has_anthropic_api_key(customer_id):
            return False, 'No Anthropic API key configured', ''
    except Exception:
        import os
        if not os.environ.get('ANTHROPIC_API_KEY'):
            return False, 'No ANTHROPIC_API_KEY environment variable', ''

    # Check 3: Customer has KPI data; determine mode based on signal state
    try:
        from models import Account, DC2SKPI, ContextNode, ContextEdge
        acct_ids = [a.account_id for a in
                    Account.query.filter_by(customer_id=customer_id).all()]
        if not acct_ids:
            return False, 'No accounts found', ''

        kpi_count = DC2SKPI.query.filter(
            DC2SKPI.account_id.in_(acct_ids)
        ).count()
        if kpi_count == 0:
            return False, 'No KPI data found', ''

        # Count existing signals by source
        csv_signals = ContextNode.query.filter(
            ContextNode.customer_id == customer_id,
            ContextNode.node_type == 'SIGNAL',
            ContextNode.source_platform == 'csv_import',
        ).count()

        llm_signals = ContextNode.query.filter(
            ContextNode.customer_id == customer_id,
            ContextNode.node_type == 'SIGNAL',
            ContextNode.source_platform == 'llm_inference',
        ).count()

        llm_enrichment_edges = ContextEdge.query.filter(
            ContextEdge.customer_id == customer_id,
            ContextEdge.source_platform == 'llm_enrichment',
        ).count()

        # Resolve mode
        if mode == 'auto':
            if csv_signals > 0 and llm_signals == 0:
                # CSV signals exist, no LLM signals → edge enrichment mode
                resolved_mode = 'edges_only'
            elif csv_signals == 0 and llm_signals == 0:
                # No signals at all → full inference mode
                resolved_mode = 'full'
            else:
                # LLM signals already exist → skip
                return False, f'LLM inference already ran ({llm_signals} LLM signals exist)', ''
        else:
            resolved_mode = mode

        # Mode-specific gate checks
        if resolved_mode == 'full':
            if csv_signals > 0 or llm_signals > 0:
                return False, f'Context already exists ({csv_signals} CSV + {llm_signals} LLM signal nodes)', ''

        elif resolved_mode == 'edges_only':
            if csv_signals == 0:
                return False, 'No CSV signals found for edge-only mode', ''
            if llm_enrichment_edges > 0:
                return False, f'LLM enrichment already ran ({llm_enrichment_edges} edges exist)', ''

    except Exception as e:
        return False, f'Prerequisite check error: {e}', ''

    return True, 'Ready', resolved_mode


def _build_account_summaries(customer_id: int, mode: str = 'full') -> List[Dict]:
    """Build KPI trajectory summaries for each account.

    Returns list of dicts with account metadata + KPI change analysis.
    In edges_only mode, also includes existing signals per account.
    """
    from models import Account, DC2SKPI, HealthScore, ContextNode
    from sqlalchemy import desc
    import utils.health_thresholds as ht

    accounts = Account.query.filter_by(customer_id=customer_id).all()
    summaries = []

    # Pre-load existing signals if in edges_only mode
    signals_by_account = {}
    if mode == 'edges_only':
        signals = (
            ContextNode.query
            .filter(
                ContextNode.customer_id == customer_id,
                ContextNode.node_type == 'SIGNAL',
            )
            .order_by(ContextNode.occurred_at.asc())
            .all()
        )
        for sig in signals:
            signals_by_account.setdefault(sig.account_id, []).append(sig)

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
        # In edges_only mode, also include accounts with signals even if health is stable
        has_signals = bool(signals_by_account.get(acct.account_id))
        if not has_signals and abs(health_delta) < 8 and (peak_health - lowest_health) < 15:
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

        # ── Enriched context: products, stakeholders, contract ──
        pm = acct.profile_metadata or {}

        # Products from profile_metadata
        products_list = pm.get('products', [])
        product_names = []
        for p in (products_list if isinstance(products_list, list) else []):
            if isinstance(p, dict):
                pname = p.get('name', '')
                parr = p.get('arr', '')
                padopt = p.get('adoption', '')
                product_names.append(f"{pname} (ARR: ${parr:,})" if parr else pname)
            elif isinstance(p, str):
                product_names.append(p)

        # Stakeholders from profile_metadata
        stakeholder_summary = []
        champ = pm.get('primary_champion_name', '')
        champ_title = pm.get('primary_champion_title', '')
        champ_score = pm.get('primary_champion_engagement_score', '')
        if champ:
            stakeholder_summary.append(f"{champ} ({champ_title}, engagement: {champ_score})" if champ_title else champ)
        exec_sp = pm.get('executive_sponsor', '')
        if exec_sp:
            stakeholder_summary.append(f"{exec_sp} (Executive Sponsor)")
        csm = pm.get('csm_name', '')
        if csm:
            stakeholder_summary.append(f"{csm} (CSM)")

        # Contract dates
        renewal_date = pm.get('renewal_date', '')
        days_until_renewal = None
        if renewal_date:
            try:
                from datetime import datetime as _dtparse, date as _dtoday
                rd = _dtparse.strptime(str(renewal_date)[:10], '%Y-%m-%d').date()
                days_until_renewal = (rd - _dtoday.today()).days
            except (ValueError, TypeError):
                pass

        product_adoption = pm.get('product_adoption', '')

        summary = {
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
            # Enriched context
            'products': product_names,
            'stakeholders': stakeholder_summary,
            'product_adoption': product_adoption,
            'days_until_renewal': days_until_renewal,
        }

        # In edges_only mode, include existing signals for context
        if mode == 'edges_only':
            acct_signals = signals_by_account.get(acct.account_id, [])
            summary['existing_signals'] = [
                {
                    'signal_ref': sig.source_event_id or f'sig_{sig.node_id}',
                    'node_id': sig.node_id,
                    'type': sig.node_subtype or (sig.properties or {}).get('signal_type', 'unknown'),
                    'date': str(sig.occurred_at)[:10] if sig.occurred_at else '',
                    'title': sig.title or '',
                    'sentiment': (sig.properties or {}).get('sentiment', 'neutral'),
                    'confidence': float(sig.confidence or 0.7),
                }
                for sig in acct_signals[:15]  # Cap at 15 signals per account
            ]

        summaries.append(summary)

    return summaries


def _salvage_truncated_json(text: str) -> List[Dict]:
    """Try to extract complete JSON objects from a truncated response.

    When max_tokens cuts off mid-JSON, we try to find the last complete
    account inference object by progressively truncating and re-parsing.
    """
    if not text or not text.strip():
        return []

    # If it starts with '[', try to find complete objects in the array
    text = text.strip()
    if text.startswith('['):
        # Find positions of '}, {' or '}\n{' which separate array elements
        # Try truncating at each one from the end
        for i in range(len(text) - 1, 0, -1):
            if text[i] == '}':
                candidate = text[:i + 1] + ']'
                try:
                    result = json.loads(candidate)
                    if isinstance(result, list) and result:
                        return result
                except json.JSONDecodeError:
                    continue

    return []


def _derivation_payload(mode: str = 'full') -> Dict[str, str]:
    """Reproducibility breadcrumbs for every LLM-written node/edge (WS-1.5,
    edge-provenance work, Aug 2026).

    Before this, an llm_enrichment edge's entire properties payload was
    {"inferred_by": ..., "label": ...} — no model id, no prompt version, no
    inference timestamp. ~4,663 such rows exist and can never be
    retrofitted (a prompt version that was never recorded is not
    recoverable); this stops the count growing.

    prompt_version is a content hash of the active system prompt rather
    than a hand-bumped constant — it can't drift from the prompt it
    describes.
    """
    import hashlib
    from datetime import datetime as _dt

    try:
        if mode == 'edges_only':
            from llm.prompts.tier1_kpi_inference import (
                EDGE_ENRICHMENT_SYSTEM_PROMPT as _SP,
            )
        else:
            from llm.prompts.tier1_kpi_inference import SYSTEM_PROMPT as _SP
        prompt_version = 'sha256:' + hashlib.sha256(_SP.encode()).hexdigest()[:12]
    except Exception:
        prompt_version = 'unknown'

    return {
        'model_id': LLM_MODEL,
        'prompt_version': prompt_version,
        'inferred_at': _dt.utcnow().isoformat(),
    }


def _call_claude(summaries: List[Dict], customer_id: int, mode: str = 'full') -> List[Dict]:
    """Call Claude API with account summaries, return inferred context.

    Batches accounts into groups of MAX_ACCOUNTS_PER_BATCH.
    In edges_only mode, uses the edge enrichment prompt that includes existing signals.
    """
    if mode == 'edges_only':
        from llm.prompts.tier1_kpi_inference import (
            EDGE_ENRICHMENT_SYSTEM_PROMPT as SYSTEM_PROMPT,
            EDGE_ENRICHMENT_ACCOUNT_TEMPLATE as ACCOUNT_TEMPLATE,
            EDGE_ENRICHMENT_BATCH_PROMPT as BATCH_PROMPT,
            EDGE_ENRICHMENT_FEW_SHOT as FEW_SHOT_EXAMPLE,
        )
    else:
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

    # Batch accounts — fewer per batch in edges_only mode (richer output per account)
    batch_size = MAX_ACCOUNTS_PER_BATCH_EDGES if mode == 'edges_only' else MAX_ACCOUNTS_PER_BATCH
    max_tokens = MAX_TOKENS_EDGES if mode == 'edges_only' else MAX_TOKENS
    for batch_start in range(0, len(summaries), batch_size):
        batch = summaries[batch_start:batch_start + batch_size]

        # Build per-account blocks
        account_blocks = []
        for s in batch:
            kpi_text = '\n'.join(
                f"  {c['code']}: {c['first_val']} → {c['last_val']} ({c['total_change_pct']:+.0f}%), "
                f"steepest change {c['steepest_pct']:+.0f}% around {c['steepest_date']}"
                for c in s['kpi_changes']
            ) or '  (no significant KPI changes)'

            # Build enriched context strings
            products_str = ', '.join(s.get('products', [])) or '(none)'
            stakeholders_str = '; '.join(s.get('stakeholders', [])) or '(none)'
            adoption_str = f"{s.get('product_adoption', 'N/A')}"
            days_renewal = s.get('days_until_renewal')
            if days_renewal is not None:
                contract_str = f"Renews in {days_renewal} days" + (' ⚠️ URGENT' if days_renewal < 90 else '')
            else:
                contract_str = '(unknown)'

            if mode == 'edges_only':
                # Build existing signals text
                signals_text = ''
                for sig in s.get('existing_signals', []):
                    signals_text += (
                        f"  [{sig['signal_ref']}] {sig['type']} ({sig['date']}): "
                        f'"{sig["title"]}" ({sig["sentiment"]}, confidence {sig["confidence"]:.1f})\n'
                    )
                signals_text = signals_text.strip() or '  (no signals)'

                account_blocks.append(ACCOUNT_TEMPLATE.format(
                    account_name=s['account_name'],
                    arr=s['arr'],
                    industry=s['industry'],
                    products=products_str,
                    stakeholders=stakeholders_str,
                    product_adoption=adoption_str,
                    contract_info=contract_str,
                    health_trajectory=s['health_trajectory'],
                    current_health=s['current_health'],
                    health_status=s['health_status'],
                    health_delta=s['health_delta'],
                    months=s['months'],
                    kpi_changes=kpi_text,
                    existing_signals=signals_text,
                ))
            else:
                account_blocks.append(ACCOUNT_TEMPLATE.format(
                    account_name=s['account_name'],
                    arr=s['arr'],
                    industry=s['industry'],
                    products=products_str,
                    stakeholders=stakeholders_str,
                    product_adoption=adoption_str,
                    contract_info=contract_str,
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
                max_tokens=max_tokens,
                temperature=0.2,  # Low temp for structured output
            )
            duration = time.time() - t0

            # Cost tracking — canonical path via llm_budget_controller (MOD-007).
            try:
                from utils.llm_budget_controller import record_usage as _record_usage
                _record_usage(
                    customer_id=customer_id,
                    module='llm_tier1_enrichment',
                    tokens_in=response.usage.input_tokens,
                    tokens_out=response.usage.output_tokens,
                    model=LLM_MODEL,
                    success=True,
                )
            except Exception as _cost_err:
                logger.debug('LLM Tier 1: cost tracking failed: %s', _cost_err)

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
                'LLM Tier 1 (%s): batch %d-%d → %d inferences (%.1fs, %d input + %d output tokens)',
                mode, batch_start, batch_start + len(batch),
                len(inferences), duration,
                response.usage.input_tokens, response.usage.output_tokens,
            )
            all_inferences.extend(inferences)

        except json.JSONDecodeError as e:
            logger.warning('LLM Tier 1: JSON parse error for batch %d: %s', batch_start, e)
            # Try to salvage truncated JSON by finding last complete object
            salvaged = _salvage_truncated_json(text)
            if salvaged:
                logger.info('LLM Tier 1: salvaged %d inferences from truncated JSON', len(salvaged))
                all_inferences.extend(salvaged)
        except Exception as e:
            logger.warning('LLM Tier 1: API call failed for batch %d: %s', batch_start, e)
            # Record failure — tokens unknown on API errors; log with 0.
            try:
                from utils.llm_budget_controller import record_usage as _record_usage
                _record_usage(
                    customer_id=customer_id,
                    module='llm_tier1_enrichment',
                    tokens_in=0, tokens_out=0,
                    model=LLM_MODEL,
                    success=False,
                    error_message=str(e)[:500],
                )
            except Exception:
                pass

    return all_inferences


def _write_inferred_nodes(
    customer_id: int,
    inferences: List[Dict],
    account_map: Dict[str, int],  # name → account_id
    arr_map: Dict[int, float],    # account_id → ARR
    mode: str = 'full',
    signal_ref_to_node_id: Optional[Dict[str, int]] = None,
) -> Dict[str, int]:
    """Write LLM-inferred context nodes and edges to the database.

    In 'full' mode: creates signals + decisions + outcomes + edges.
    In 'edges_only' mode: creates decisions + outcomes + explicit causal edges
    using existing signal node IDs from signal_ref_to_node_id map.

    Returns counts: {signals, outcomes, decisions, edges}
    """
    from utils.context_graph import upsert_node, upsert_edge
    from extensions import db
    from datetime import datetime as dt

    source_platform = 'llm_enrichment' if mode == 'edges_only' else 'llm_inference'
    created_by = 'llm_tier1_enrichment' if mode == 'edges_only' else 'llm_tier1'

    # WS-1.5: one derivation payload per write batch, merged into every
    # node/edge properties dict below — model id + prompt hash + timestamp.
    derivation = _derivation_payload(mode)

    counts = {'signals': 0, 'outcomes': 0, 'decisions': 0, 'edges': 0}

    for inf in inferences:
        account_name = inf.get('account_name', '')
        account_id = account_map.get(account_name)
        if not account_id:
            continue

        arr = arr_map.get(account_id, 0)
        created_node_ids = {}  # track for edge creation

        # ── Signals: only in full mode ──
        if mode == 'full':
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
                            'inferred_by': created_by,
                            'confidence': str(sig.get('confidence', 0.7)),
                            **derivation,
                        },
                        source_platform=source_platform,
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

        # ── Decisions: both modes ──
        for idx, dec in enumerate(inf.get('inferred_decisions', [])):
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
                        'inferred_by': created_by,
                        'confidence': str(dec.get('confidence', 0.7)),
                        'triggered_by_signals': dec.get('triggered_by_signals', []),
                        **derivation,
                    },
                    source_platform=source_platform,
                    source_event_id=source_eid,
                    node_subtype=dec['type'],
                    tier=2,
                    confidence=dec.get('confidence', 0.7),
                )
                if node:
                    created_node_ids[f'decision:{idx}'] = node.node_id
                    counts['decisions'] += 1
            except Exception as e:
                logger.debug('LLM decision write error: %s', e)

        # ── Outcomes: both modes ──
        # NOTE: revenue_impact is NOT set from LLM inference — LLM guesses are
        # non-deterministic and cause 30-50% variance in revenue-at-risk numbers.
        # Revenue is computed deterministically by the ROI engine from health × ARR.
        for idx, out in enumerate(inf.get('inferred_outcomes', [])):
            try:
                out_date = out.get('date', dt.utcnow().strftime('%Y-%m-%d'))
                source_eid = f'llm_out:{account_id}:{out["type"]}:{out_date}'

                node = upsert_node(
                    customer_id=customer_id,
                    account_id=account_id,
                    node_type='OUTCOME',
                    title=out.get('title', f'Inferred: {out["type"]}')[:500],
                    occurred_at=dt.strptime(out_date[:10], '%Y-%m-%d'),
                    properties={
                        'outcome_type': out['type'],
                        'inferred_by': created_by,
                        'confidence': str(out.get('confidence', 0.7)),
                        **derivation,
                    },
                    source_platform=source_platform,
                    source_event_id=source_eid,
                    node_subtype=out['type'],
                    tier=2,
                    confidence=out.get('confidence', 0.7),
                    revenue_impact=None,  # deterministic: computed by ROI engine from health × ARR
                    revenue_impact_type=out['type'],
                )
                if node:
                    created_node_ids[f'outcome:{idx}'] = node.node_id
                    counts['outcomes'] += 1
            except Exception as e:
                logger.debug('LLM outcome write error: %s', e)

        # ── Edges ──
        if mode == 'edges_only':
            # Use explicit causal_edges from LLM response
            counts['edges'] += _write_explicit_edges(
                customer_id, inf, created_node_ids,
                signal_ref_to_node_id or {}, source_platform, created_by,
                derivation=derivation,
            )
        else:
            # Original simple edge logic: signal → first decision → all outcomes
            counts['edges'] += _write_simple_edges(
                customer_id, created_node_ids, source_platform, created_by,
                derivation=derivation,
            )

    try:
        db.session.commit()
    except Exception as e:
        logger.warning('LLM inference commit failed: %s', e)
        db.session.rollback()

    return counts


def _write_simple_edges(
    customer_id: int,
    created_node_ids: Dict[str, int],
    source_platform: str,
    created_by: str,
    derivation: Optional[Dict[str, str]] = None,
) -> int:
    """Original edge logic: all signals → first decision, all decisions → all outcomes."""
    from utils.context_graph import upsert_edge

    edge_count = 0
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
                    source_platform=source_platform,
                    created_by=created_by,
                    customer_id=customer_id,
                    properties={'inferred_by': created_by, **(derivation or {})},
                )
                if created:
                    edge_count += 1
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
                        source_platform=source_platform,
                        created_by=created_by,
                        customer_id=customer_id,
                        properties={'inferred_by': created_by, **(derivation or {})},
                    )
                    if created:
                        edge_count += 1
                except Exception:
                    pass

    return edge_count


def _resolve_ref(ref: str, created_node_ids: Dict[str, int],
                 signal_ref_to_node_id: Dict[str, int]) -> Optional[int]:
    """Resolve a from_ref/to_ref string to a node_id.

    Handles:
    - "decision:0" → created_node_ids['decision:0']
    - "outcome:1" → created_node_ids['outcome:1']
    - "sig_df_001" → signal_ref_to_node_id['sig_df_001']
    - Any other string → try signal_ref_to_node_id[ref]
    """
    if not ref:
        return None

    # Try created nodes first (decision:0, outcome:1, etc.)
    if ref in created_node_ids:
        return created_node_ids[ref]

    # Try signal ref map
    if ref in signal_ref_to_node_id:
        return signal_ref_to_node_id[ref]

    return None


def _write_explicit_edges(
    customer_id: int,
    inference: Dict,
    created_node_ids: Dict[str, int],
    signal_ref_to_node_id: Dict[str, int],
    source_platform: str,
    created_by: str,
    derivation: Optional[Dict[str, str]] = None,
) -> int:
    """Write explicit causal edges from LLM edge enrichment response.

    Handles both causal_edges (signal→decision, decision→outcome) and
    signal_to_signal_edges (signal→signal).
    """
    from utils.context_graph import upsert_edge

    edge_count = 0

    # Process causal_edges
    for edge_spec in inference.get('causal_edges', []):
        try:
            from_id = _resolve_ref(edge_spec.get('from_ref', ''),
                                   created_node_ids, signal_ref_to_node_id)
            to_id = _resolve_ref(edge_spec.get('to_ref', ''),
                                 created_node_ids, signal_ref_to_node_id)
            if not from_id or not to_id:
                continue

            edge_type = edge_spec.get('edge_type', 'LED_TO')
            if edge_type not in ('LED_TO', 'TRIGGERED', 'CAUSED_BY', 'AMPLIFIED', 'INDICATES'):
                edge_type = 'LED_TO'

            edge, created = upsert_edge(
                from_node_id=from_id,
                to_node_id=to_id,
                edge_type=edge_type,
                confidence=min(float(edge_spec.get('confidence', 0.65)), 0.85),
                source_platform=source_platform,
                created_by=created_by,
                customer_id=customer_id,
                properties={
                    'inferred_by': created_by,
                    'label': edge_spec.get('label', ''),
                    'input_refs': [edge_spec.get('from_ref', ''), edge_spec.get('to_ref', '')],
                    **(derivation or {}),
                },
            )
            if created:
                edge_count += 1
        except Exception as e:
            logger.debug('LLM causal edge write error: %s', e)

    # Process signal_to_signal_edges
    for edge_spec in inference.get('signal_to_signal_edges', []):
        try:
            from_id = signal_ref_to_node_id.get(edge_spec.get('from_signal_ref', ''))
            to_id = signal_ref_to_node_id.get(edge_spec.get('to_signal_ref', ''))
            if not from_id or not to_id:
                continue

            edge_type = edge_spec.get('edge_type', 'LED_TO')
            if edge_type not in ('LED_TO', 'TRIGGERED', 'CAUSED_BY', 'AMPLIFIED', 'INDICATES'):
                edge_type = 'LED_TO'

            edge, created = upsert_edge(
                from_node_id=from_id,
                to_node_id=to_id,
                edge_type=edge_type,
                confidence=min(float(edge_spec.get('confidence', 0.65)), 0.85),
                source_platform=source_platform,
                created_by=created_by,
                customer_id=customer_id,
                properties={
                    'inferred_by': created_by,
                    'label': edge_spec.get('label', ''),
                    'edge_class': 'signal_to_signal',
                    'input_refs': [edge_spec.get('from_signal_ref', ''), edge_spec.get('to_signal_ref', '')],
                    **(derivation or {}),
                },
            )
            if created:
                edge_count += 1
        except Exception as e:
            logger.debug('LLM signal-to-signal edge write error: %s', e)

    # Fallback: if LLM didn't return explicit causal_edges, create edges from
    # triggered_by_signals references on decisions
    if not inference.get('causal_edges') and not inference.get('signal_to_signal_edges'):
        decisions = inference.get('inferred_decisions', [])
        outcomes = inference.get('inferred_outcomes', [])

        for idx, dec in enumerate(decisions):
            dec_node_id = created_node_ids.get(f'decision:{idx}')
            if not dec_node_id:
                continue

            # Signal → Decision edges from triggered_by_signals
            for sig_ref in dec.get('triggered_by_signals', []):
                sig_node_id = signal_ref_to_node_id.get(sig_ref)
                if sig_node_id:
                    try:
                        edge, created = upsert_edge(
                            from_node_id=sig_node_id,
                            to_node_id=dec_node_id,
                            edge_type='TRIGGERED',
                            confidence=0.7,
                            source_platform=source_platform,
                            created_by=created_by,
                            customer_id=customer_id,
                            properties={'inferred_by': created_by, 'fallback': True, **(derivation or {})},
                        )
                        if created:
                            edge_count += 1
                    except Exception:
                        pass

            # Decision → Outcome edges
            for out_idx, out in enumerate(outcomes):
                out_node_id = created_node_ids.get(f'outcome:{out_idx}')
                if out_node_id:
                    try:
                        edge, created = upsert_edge(
                            from_node_id=dec_node_id,
                            to_node_id=out_node_id,
                            edge_type='LED_TO',
                            confidence=0.6,
                            source_platform=source_platform,
                            created_by=created_by,
                            customer_id=customer_id,
                            properties={'inferred_by': created_by, 'fallback': True, **(derivation or {})},
                        )
                        if created:
                            edge_count += 1
                    except Exception:
                        pass

    return edge_count


def infer_context_from_kpis(customer_id: int, mode: str = 'auto') -> Dict:
    """Main entry point: infer context graph from KPI data.

    Args:
        customer_id: The customer (tenant) ID
        mode: 'auto' (detect from data), 'full' (infer everything),
              or 'edges_only' (enrich existing signals with edges)

    Returns:
        {
            'status': 'completed' | 'skipped' | 'error',
            'mode': str,
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
    should_run, reason, resolved_mode = _check_prerequisites(customer_id, mode)
    if not should_run:
        return {
            'status': 'skipped',
            'mode': mode,
            'reason': reason,
            'duration_s': round(time.time() - t0, 2),
        }

    # Build account summaries from KPI data (+ existing signals in edges_only mode)
    summaries = _build_account_summaries(customer_id, resolved_mode)
    if not summaries:
        return {
            'status': 'skipped',
            'mode': resolved_mode,
            'reason': 'No accounts with significant health changes',
            'duration_s': round(time.time() - t0, 2),
        }

    logger.info(
        'LLM Tier 1 (%s): analyzing %d accounts for customer %d',
        resolved_mode, len(summaries), customer_id,
    )

    # Build signal_ref → node_id map for edges_only mode
    signal_ref_to_node_id = {}
    if resolved_mode == 'edges_only':
        for s in summaries:
            for sig in s.get('existing_signals', []):
                signal_ref_to_node_id[sig['signal_ref']] = sig['node_id']

    # Call Claude
    inferences = _call_claude(summaries, customer_id, resolved_mode)
    if not inferences:
        return {
            'status': 'completed',
            'mode': resolved_mode,
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
    counts = _write_inferred_nodes(
        customer_id, inferences, account_map, arr_map,
        mode=resolved_mode, signal_ref_to_node_id=signal_ref_to_node_id,
    )

    duration = round(time.time() - t0, 2)
    logger.info(
        'LLM Tier 1 (%s) complete: customer=%d %d signals, %d decisions, %d outcomes, '
        '%d edges created in %.1fs',
        resolved_mode, customer_id, counts['signals'], counts['decisions'],
        counts['outcomes'], counts['edges'], duration,
    )

    return {
        'status': 'completed',
        'mode': resolved_mode,
        'reason': 'OK',
        'accounts_analyzed': len(summaries),
        'accounts_with_inferences': len(inferences),
        **counts,
        'duration_s': duration,
    }
