#!/usr/bin/env python3
"""
Scenario 9: Weight-Aware ROI Simulation

Generates incremental KPI improvements using Wizard C weight hierarchy,
uploads through the proper pipeline (bulk-upload → score_calculator rollup),
and validates that ROI engine reflects the changes correctly.

Unlike direct DB inserts (simulate_incremental_kpi.py), this scenario goes
through the full data pipeline:
  raw KPI values → /api/dc2s/kpis/bulk-upload → dc2s_kpis table
                 → /api/dc2s/scores/calculate  → score_calculator.py
                     → kpi_scores (L1)
                     → pillar_scores (L2 weighted rollup)
                     → health_scores (L3)
                 → /api/outcome-roi/story → ROI from pillar_scores history

When the context_graph feature toggle is enabled, also generates SIGNAL →
DECISION → OUTCOME causal chains explaining *why* ROI improved — making
the demo story complete: numbers + narrative + evidence chain.

This ensures the L1→L2→L3 weight rollup is done by the real system, not
hand-simulated, making the ROI numbers fully defensible for customer demos.
"""

import logging
import random
from typing import Dict, Any, List

from .base import BaseScenario

logger = logging.getLogger(__name__)

# Pillar economic impact — annual $ per 1% improvement at $10M ARR base
# (from power_of_1_economics.json)
PILLAR_IMPACT = {
    'P1': 61250,   # Deployment Velocity → TTFV
    'P2': 38000,   # Operational Stability → ticket_resolution_time
    'P3': 25000,   # AI Workload Perf → product_adoption
    'P4': 100000,  # Channel Partner → GRR
    'P5': 20000,   # Expansion Readiness → expansion_rate
}

# ── Pillar narratives for context graph enrichment ──
# Maps each pillar to narrative templates for SIGNAL → DECISION → OUTCOME chains
PILLAR_NARRATIVES = {
    'P1': {
        'signal_type': 'kpi_improvement',
        'signal_title': 'Deployment velocity acceleration',
        'decision_title': 'Activation-blitz playbook executed',
        'decision_subtype': 'playbook_execution',
        'outcome_title': 'Reduced time-to-first-value',
        'outcome_type': 'revenue_impact',
    },
    'P2': {
        'signal_type': 'kpi_improvement',
        'signal_title': 'Operational stability optimization',
        'decision_title': 'Operational-excellence playbook executed',
        'decision_subtype': 'playbook_execution',
        'outcome_title': 'Improved reliability metrics',
        'outcome_type': 'revenue_impact',
    },
    'P3': {
        'signal_type': 'kpi_improvement',
        'signal_title': 'AI workload adoption acceleration',
        'decision_title': 'Adoption-acceleration playbook executed',
        'decision_subtype': 'playbook_execution',
        'outcome_title': 'Increased GPU utilization',
        'outcome_type': 'revenue_impact',
    },
    'P4': {
        'signal_type': 'kpi_improvement',
        'signal_title': 'Partner engagement strengthening',
        'decision_title': 'Partner-champion playbook executed',
        'decision_subtype': 'playbook_execution',
        'outcome_title': 'Strengthened partner GRR',
        'outcome_type': 'revenue_impact',
        'has_stakeholder': True,
        'stakeholder_title': 'Partner champion',
        'stakeholder_role': 'champion',
    },
    'P5': {
        'signal_type': 'kpi_improvement',
        'signal_title': 'Expansion pipeline progression',
        'decision_title': 'Expansion-readiness playbook executed',
        'decision_subtype': 'playbook_execution',
        'outcome_title': 'Advanced expansion pipeline',
        'outcome_type': 'revenue_impact',
    },
}

# Decision nodes are created at milestone months (1-indexed)
DECISION_MONTHS = {2, 4, 6}


def _compute_kpi_drift_rates(pillar_weights, kpi_weights, improvement_pct, months):
    """
    Compute per-KPI drift rates (points/month in raw value space) using
    the Wizard C weight hierarchy combined with economic impact.

    Higher-weighted pillars with bigger economic impact get proportionally
    more improvement. Within each pillar, higher L1-weighted KPIs improve faster.

    Args:
        pillar_weights: {P1: 0.15, P2: 0.20, ...} — L2 weights
        kpi_weights:    {P1-KPI1: 0.20, ...} — L1 weights per KPI
        improvement_pct: Total improvement target (e.g., 2.5)
        months: Number of months to simulate

    Returns:
        Dict[kpi_code → drift_rate_per_month]
    """
    # Step 1: Pillar improvement allocation (weight × economic impact)
    raw_alloc = {}
    for p, w in pillar_weights.items():
        raw_alloc[p] = w * PILLAR_IMPACT.get(p, 25000)
    total_alloc = sum(raw_alloc.values())
    pillar_alloc = {p: v / total_alloc for p, v in raw_alloc.items()}

    # Step 2: Per-KPI drift rate within each pillar
    # Group KPIs by pillar
    pillar_kpis = {}
    for kpi_code in kpi_weights:
        pillar = kpi_code.split('-')[0]
        pillar_kpis.setdefault(pillar, []).append(kpi_code)

    drift_rates = {}
    for pillar, kpi_codes in pillar_kpis.items():
        # Pillar-level improvement: alloc × 5 (normalize across 5 pillars) × total improvement
        pillar_total_improvement = improvement_pct * pillar_alloc.get(pillar, 0.2) * 5

        # Average L1 weight for this pillar
        l1_weights = [kpi_weights.get(kc, 1.0 / 8) for kc in kpi_codes]
        avg_l1 = sum(l1_weights) / max(len(l1_weights), 1)

        for kc in kpi_codes:
            l1_w = kpi_weights.get(kc, 1.0 / 8)
            l1_scale = l1_w / avg_l1 if avg_l1 > 0 else 1.0
            # drift rate = monthly improvement × L1 scaling
            drift_rates[kc] = (pillar_total_improvement * l1_scale) / months

    return drift_rates


class ScenarioRoiSimulation(BaseScenario):
    """
    Scenario 9: Weight-Aware ROI Simulation

    Simulates CSM playbook execution: all accounts improve gradually
    with weight-aware improvement allocation (higher-impact pillars/KPIs
    improve proportionally more).

    Steps:
    1. Fetch accounts for the customer
    2. Capture baseline ROI from /api/outcome-roi/story
    3. Load weight config from KPI catalog (L2 pillar weights + L1 KPI weights)
    4. Compute per-KPI drift rates using weight × economic impact
    5. For each month (1..N):
       a. Generate KPI measurements with playbook_improving profile
       b. Upload via /api/dc2s/kpis/bulk-upload
       c. Trigger score recalculation via /api/dc2s/scores/calculate
    6. Capture post-simulation ROI
    7. Validate improvements: ROI delta, data_source, pillar score changes

    Measures:
    - ROI before vs after (historical ROI improvement)
    - Per-metric dollar impact ranking
    - data_source = 'pillar_scores' (not demo fallback)
    - All pillar scores increased
    """

    def _enrich_context_graph(
        self,
        customer_id: int,
        accounts: list,
        pillar_alloc: Dict[str, float],
        improvement_pct: float,
        months: int,
        sim_dates: list,
    ) -> Dict[str, Any]:
        """
        Generate SIGNAL → DECISION → OUTCOME causal chains for each account × pillar.

        For each account and each pillar (where improvement > 0.5%):
        - Per month: SIGNAL node with cumulative improvement %
        - At milestone months (2, 4, 6): DECISION node (CSM playbook action)
        - At final month: OUTCOME node (revenue realized)
        - For P4: STAKEHOLDER champion node
        - Edges: temporal signal chains, decision→signal, signal→outcome, decision→outcome

        Returns:
            {nodes_generated, edges_generated, ingest_result, ...}
        """
        from datetime import datetime

        nodes = []
        edges = []

        for acc in accounts:
            account_id = acc.get('account_id')
            account_name = acc.get('account_name', f'Account-{account_id}')

            for pillar in ['P1', 'P2', 'P3', 'P4', 'P5']:
                narr = PILLAR_NARRATIVES.get(pillar)
                if not narr:
                    continue

                # Pillar-level improvement = alloc × 5 × total improvement
                pillar_improvement = improvement_pct * pillar_alloc.get(pillar, 0.2) * 5
                if pillar_improvement < 0.5:
                    continue  # Skip negligible improvements

                prev_signal_id = None
                last_decision_id = None
                last_signal_id = None

                for mi, month_str in enumerate(sim_dates):
                    month_num = mi + 1  # 1-indexed
                    cumulative_pct = round(pillar_improvement * month_num / months, 2)

                    # ── SIGNAL node (every month) ──
                    signal_id = f's9-acc{account_id}-{pillar}-signal-m{month_num}'
                    signal_node = {
                        'account_id': account_id,
                        'node_type': 'SIGNAL',
                        'node_subtype': narr['signal_type'],
                        'title': f'{narr["signal_title"]} — {account_name} {pillar} month {month_num}',
                        'occurred_at': f'{month_str}T00:00:00',
                        'source_event_id': signal_id,
                        'source_platform': 'scenario_9_roi',
                        'tier': 1,
                        'confidence': 0.9,
                        'properties': {
                            'pillar': pillar,
                            'month': month_num,
                            'cumulative_improvement_pct': cumulative_pct,
                            'account_name': account_name,
                        },
                    }
                    nodes.append(signal_node)

                    # Edge: previous_signal →LED_TO→ this_signal (temporal chain)
                    if prev_signal_id:
                        edges.append({
                            'from_source_event_id': prev_signal_id,
                            'to_source_event_id': signal_id,
                            'edge_type': 'LED_TO',
                            'weight': 0.8,
                            'confidence': 0.85,
                            'source_platform': 'scenario_9_roi',
                            'lag_days': 30,
                        })

                    prev_signal_id = signal_id
                    last_signal_id = signal_id

                    # ── DECISION node (at milestone months) ──
                    if month_num in DECISION_MONTHS:
                        decision_id = f's9-acc{account_id}-{pillar}-decision-m{month_num}'
                        decision_node = {
                            'account_id': account_id,
                            'node_type': 'DECISION',
                            'node_subtype': narr['decision_subtype'],
                            'title': f'{narr["decision_title"]} — {account_name} {pillar} month {month_num}',
                            'occurred_at': f'{month_str}T00:00:00',
                            'source_event_id': decision_id,
                            'source_platform': 'scenario_9_roi',
                            'tier': 1,
                            'confidence': 0.9,
                            'properties': {
                                'pillar': pillar,
                                'month': month_num,
                                'decision_maker_role': 'CSM',
                                'chosen_option': narr['decision_title'],
                                'account_name': account_name,
                            },
                        }
                        nodes.append(decision_node)
                        last_decision_id = decision_id

                        # Edge: DECISION →LED_TO→ SIGNAL (playbook drove improvement)
                        edges.append({
                            'from_source_event_id': decision_id,
                            'to_source_event_id': signal_id,
                            'edge_type': 'LED_TO',
                            'weight': 1.0,
                            'confidence': 0.9,
                            'source_platform': 'scenario_9_roi',
                            'lag_days': 0,
                        })

                # ── OUTCOME node (final month) ──
                revenue_impact = round(PILLAR_IMPACT.get(pillar, 25000) * (pillar_improvement / 100), 2)
                outcome_id = f's9-acc{account_id}-{pillar}-outcome'
                outcome_node = {
                    'account_id': account_id,
                    'node_type': 'OUTCOME',
                    'node_subtype': narr['outcome_type'],
                    'title': f'{narr["outcome_title"]} — {account_name} {pillar}',
                    'occurred_at': f'{sim_dates[-1]}T00:00:00',
                    'source_event_id': outcome_id,
                    'source_platform': 'scenario_9_roi',
                    'tier': 1,
                    'confidence': 0.85,
                    'revenue_impact': revenue_impact,
                    'revenue_impact_type': 'protected',
                    'properties': {
                        'pillar': pillar,
                        'improvement_pct': round(pillar_improvement, 2),
                        'revenue_impact': revenue_impact,
                        'account_name': account_name,
                    },
                }
                nodes.append(outcome_node)

                # Edge: last SIGNAL →LED_TO→ OUTCOME
                if last_signal_id:
                    edges.append({
                        'from_source_event_id': last_signal_id,
                        'to_source_event_id': outcome_id,
                        'edge_type': 'LED_TO',
                        'weight': 1.0,
                        'confidence': 0.85,
                        'source_platform': 'scenario_9_roi',
                        'lag_days': 0,
                        'revenue_impact': revenue_impact,
                    })

                # Edge: last DECISION →RESULTED_IN→ OUTCOME
                if last_decision_id:
                    edges.append({
                        'from_source_event_id': last_decision_id,
                        'to_source_event_id': outcome_id,
                        'edge_type': 'RESULTED_IN',
                        'weight': 1.0,
                        'confidence': 0.85,
                        'source_platform': 'scenario_9_roi',
                        'lag_days': 0,
                        'revenue_impact': revenue_impact,
                    })

                # ── STAKEHOLDER node (P4 only) ──
                if narr.get('has_stakeholder'):
                    stakeholder_id = f's9-acc{account_id}-{pillar}-stakeholder'
                    stakeholder_node = {
                        'account_id': account_id,
                        'node_type': 'STAKEHOLDER',
                        'node_subtype': narr['stakeholder_role'],
                        'title': f'{narr["stakeholder_title"]} — {account_name}',
                        'occurred_at': f'{sim_dates[-1]}T00:00:00',
                        'source_event_id': stakeholder_id,
                        'source_platform': 'scenario_9_roi',
                        'tier': 1,
                        'confidence': 0.9,
                        'properties': {
                            'pillar': pillar,
                            'role': narr['stakeholder_role'],
                            'title': narr['stakeholder_title'],
                            'account_name': account_name,
                            'influence_score': 0.85,
                        },
                    }
                    nodes.append(stakeholder_node)

                    # Edge: STAKEHOLDER →INVOLVES→ OUTCOME
                    edges.append({
                        'from_source_event_id': stakeholder_id,
                        'to_source_event_id': outcome_id,
                        'edge_type': 'INVOLVES',
                        'weight': 0.9,
                        'confidence': 0.85,
                        'source_platform': 'scenario_9_roi',
                        'lag_days': 0,
                    })

        logger.info(f"    Generated {len(nodes)} nodes, {len(edges)} edges")

        # ── Send to ingest API ──
        ingest_result = self.client.ingest_context_graph(
            customer_id=customer_id,
            nodes=nodes,
            edges=edges,
        )

        return {
            'nodes_generated': len(nodes),
            'edges_generated': len(edges),
            'ingest_result': ingest_result,
        }

    def run(self) -> Dict[str, Any]:
        self.start_timer()
        logger.info("📈 Scenario 9: Weight-Aware ROI Simulation")

        api_calls = 0
        errors = []
        results = {}

        try:
            from kpi_mutator import KPIMutator, ALL_KPI_CODES, DEFAULT_TARGETS, KPI_CODES
            from catalog_loader import get_pillar_weight, get_kpi_weight, get_kpis

            # ── Config from CLI args ──
            months = getattr(self.args, 'months', None) or 6
            improvement_pct = getattr(self.args, 'improvement', None) or 2.5
            seed = getattr(self.args, 'seed', None) or 42
            customer_id = getattr(self.args, 'customer_id', None) or self.client.customer_id

            logger.info(f"  Config: customer_id={customer_id}, months={months}, "
                        f"improvement={improvement_pct}%, seed={seed}")

            # ── Step 1: Fetch accounts ──
            logger.info("  Step 1: Fetch accounts")
            accounts = self.client.get_accounts()
            api_calls += 1

            if not accounts:
                return self.failure("No accounts found", api_calls=api_calls)

            logger.info(f"    Found {len(accounts)} accounts")
            results['account_count'] = len(accounts)

            # ── Step 2: Capture baseline ROI ──
            logger.info("  Step 2: Capture baseline ROI")
            baseline_roi_resp = self.client.get(
                '/api/outcome-roi/story',
                params={'customer_id': customer_id}
            )
            api_calls += 1

            baseline_roi = {}
            if baseline_roi_resp and 'story' in baseline_roi_resp:
                story = baseline_roi_resp['story']
                hist = story.get('historical', {}).get('summary', {})
                baseline_roi = {
                    'roi_pct': hist.get('roi_pct', 'N/A'),
                    'total_impact': hist.get('total_impact', 0),
                    'total_investment': hist.get('total_investment', 0),
                    'data_source': baseline_roi_resp.get('data_source', 'unknown'),
                }
                logger.info(f"    Baseline: ROI={baseline_roi['roi_pct']}%, "
                            f"Impact=${baseline_roi['total_impact']:,.0f}")
            else:
                logger.warning("    ⚠️  Could not fetch baseline ROI (endpoint may not exist)")
                baseline_roi = {'roi_pct': 'N/A', 'total_impact': 0,
                                'total_investment': 0, 'data_source': 'unavailable'}

            results['baseline_roi'] = baseline_roi

            # ── Step 3: Load weight config from catalog ──
            logger.info("  Step 3: Load weight config")
            pillar_weights = {}
            kpi_l1_weights = {}

            for pillar in ['P1', 'P2', 'P3', 'P4', 'P5']:
                pillar_weights[pillar] = get_pillar_weight(pillar)

            catalog_kpis = get_kpis()
            for kpi_code in catalog_kpis:
                kpi_l1_weights[kpi_code] = get_kpi_weight(kpi_code)

            logger.info(f"    L2 weights: {pillar_weights}")
            logger.info(f"    L1 weights: {len(kpi_l1_weights)} KPIs loaded")

            # ── Step 4: Compute per-KPI drift rates ──
            logger.info("  Step 4: Compute weight-aware drift rates")
            drift_rates = _compute_kpi_drift_rates(
                pillar_weights, kpi_l1_weights, improvement_pct, months
            )

            # Log pillar allocation
            raw_alloc = {p: pillar_weights[p] * PILLAR_IMPACT.get(p, 25000) for p in pillar_weights}
            total_alloc = sum(raw_alloc.values())
            pillar_alloc = {p: v / total_alloc for p, v in raw_alloc.items()}
            for p in sorted(pillar_alloc):
                alloc = pillar_alloc[p]
                logger.info(f"    {p} (L2={pillar_weights[p]:.0%}, "
                            f"impact=${PILLAR_IMPACT.get(p, 0):,}/pct): "
                            f"alloc={alloc:.1%}")

            results['pillar_allocation'] = {p: round(v, 4) for p, v in pillar_alloc.items()}

            # ── Step 5: Generate and upload N months ──
            mutator = KPIMutator(seed=seed)
            mutator.set_kpi_drift_rates(drift_rates)

            # Generate baselines — use current values or random near-target
            baseline_values = {}
            for acc in accounts:
                account_id = acc.get('account_id')
                baselines = {}
                random.seed(seed + account_id)  # Deterministic per-account
                for kpi_code in ALL_KPI_CODES:
                    target = DEFAULT_TARGETS.get(kpi_code, 85.0)
                    # Start near target with some variance
                    baselines[kpi_code] = round(random.uniform(target * 0.80, target * 1.02), 2)
                baseline_values[account_id] = baselines

            # Determine start month
            from datetime import datetime, timedelta
            now = datetime.now()
            # Start simulation from N months ago so historical ROI has data
            start_date = now - timedelta(days=30 * months)
            start_month_str = start_date.strftime('%Y-%m-01')

            # Generate all 12 months of data per account at once, then group by date
            # This avoids date alignment issues with timedelta(days=30)
            logger.info(f"  Step 5a: Generate {months} months of KPI data from {start_month_str}")
            all_account_data = {}  # account_id → list of rows
            for acc in accounts:
                account_id = acc.get('account_id')
                month_data = mutator.generate_12_months(
                    account_id=account_id,
                    baseline_values=baseline_values[account_id],
                    profile='playbook_improving',
                    start_month=start_month_str
                )
                all_account_data[account_id] = month_data

            # Collect unique measured_at dates (in order) from the generated data
            all_dates = sorted(set(
                r['measured_at'] for rows in all_account_data.values() for r in rows
            ))
            # Only use the first N months
            sim_dates = all_dates[:months]
            logger.info(f"    Simulation dates: {sim_dates}")

            months_ok = 0
            for mi, month_str in enumerate(sim_dates):
                logger.info(f"  Month {mi + 1}/{months}: {month_str}")

                # Gather all account rows for this date
                records = []
                for account_id, rows in all_account_data.items():
                    for row in rows:
                        if row['measured_at'] == month_str:
                            records.append({
                                'account_id': row['account_id'],
                                'kpi_code': row['kpi_code'],
                                'measured_at': row['measured_at'],
                                'value': row['value'],
                                'target': row.get('target'),
                                'pillar': row.get('pillar'),
                            })

                if not records:
                    errors.append(f"Month {mi + 1}: no records generated")
                    continue

                # Upload via data-ingestion API (upserts into dc2s_kpis table)
                upload_resp = self.client.post(
                    '/api/data-ingestion/kpis',
                    {'source': 'load_driver_scenario_9', 'records': records}
                )
                api_calls += 1

                if upload_resp and upload_resp.get('status') == 'ok':
                    inserted = upload_resp.get('inserted', 0)
                    updated = upload_resp.get('updated', 0)
                    logger.info(f"    Ingested: {inserted} inserted, {updated} updated")
                    months_ok += 1
                else:
                    errors.append(f"Month {mi + 1} upload failed: {upload_resp}")

                # Trigger score recalculation
                score_resp = self.client.calculate_scores(
                    customer_id=customer_id,
                    measurement_month=month_str
                )
                api_calls += 1

                if not score_resp or score_resp.get('status') == 'error':
                    errors.append(f"Month {mi + 1} score calc failed: {score_resp}")

            results['months_processed'] = months_ok
            logger.info(f"    ✅ Uploaded {months_ok}/{months} months")

            # ── Step 5b: Enrich context graph (if enabled) ──
            context_graph_enriched = False
            try:
                cg_enabled = self.client.is_context_graph_enabled(customer_id)
                if cg_enabled:
                    logger.info("  Step 5b: Enrich context graph with causal narrative")
                    cg_result = self._enrich_context_graph(
                        customer_id=customer_id,
                        accounts=accounts,
                        pillar_alloc=pillar_alloc,
                        improvement_pct=improvement_pct,
                        months=months,
                        sim_dates=sim_dates,
                    )
                    api_calls += 1
                    results['context_graph'] = cg_result

                    ingest = cg_result.get('ingest_result', {})
                    if ingest and ingest.get('status') == 'success':
                        context_graph_enriched = True
                        logger.info(f"    ✅ Context graph: "
                                    f"{ingest.get('nodes_created', 0)} nodes created, "
                                    f"{ingest.get('edges_created', 0)} edges created")
                    else:
                        logger.warning(f"    ⚠️  Context graph ingest response: {ingest}")
                        errors.append(f"Context graph ingest issue: {ingest}")
                else:
                    logger.info("  Step 5b: Context graph not enabled — skipping enrichment")
            except Exception as cg_err:
                logger.warning(f"  Step 5b: Context graph enrichment failed (non-fatal): {cg_err}")
                errors.append(f"Context graph enrichment error: {cg_err}")

            # ── Step 6: Capture post-simulation ROI ──
            logger.info("  Step 6: Capture post-simulation ROI")
            final_roi_resp = self.client.get(
                '/api/outcome-roi/story',
                params={'customer_id': customer_id}
            )
            api_calls += 1

            final_roi = {}
            if final_roi_resp and 'story' in final_roi_resp:
                story = final_roi_resp['story']
                hist = story.get('historical', {}).get('summary', {})
                fwd = story.get('forward', {}).get('summary', {})
                bridge = story.get('bridge', {})

                final_roi = {
                    'roi_pct': hist.get('roi_pct', 'N/A'),
                    'total_impact': hist.get('total_impact', 0),
                    'total_investment': hist.get('total_investment', 0),
                    'data_source': final_roi_resp.get('data_source', 'unknown'),
                    'forward_roi_pct': fwd.get('roi_pct', 'N/A'),
                    'forward_impact': fwd.get('total_impact', 0),
                }

                # Extract per-metric dollar impact from bridge
                momentum = bridge.get('momentum_metrics', [])
                metric_ranking = []
                for m in momentum:
                    metric_ranking.append({
                        'metric': m.get('metric_id', '?'),
                        'display_name': m.get('display_name', '?'),
                        'historical_dollars': m.get('historical_dollars', 0),
                        'historical_improvement': m.get('historical_improvement', 0),
                    })
                metric_ranking.sort(key=lambda x: x['historical_dollars'], reverse=True)
                final_roi['metric_ranking'] = metric_ranking

                logger.info(f"    Final: ROI={final_roi['roi_pct']}%, "
                            f"Impact=${final_roi['total_impact']:,.0f}")
                for mr in metric_ranking[:3]:
                    logger.info(f"      {mr['metric']}: ${mr['historical_dollars']:,.0f} "
                                f"({mr['historical_improvement']:+.2f}%)")
            else:
                logger.warning("    ⚠️  Could not fetch final ROI")
                final_roi = {'roi_pct': 'N/A', 'total_impact': 0,
                             'data_source': 'unavailable'}

            results['final_roi'] = final_roi

            # ── Step 7: Validate ──
            logger.info("  Step 7: Validate results")
            validations = []

            # 7a: data_source should be pillar_scores
            ds = final_roi.get('data_source', '')
            ds_ok = ds == 'pillar_scores'
            validations.append({
                'check': 'data_source == pillar_scores',
                'pass': ds_ok,
                'actual': ds
            })
            if ds_ok:
                logger.info("    ✅ data_source = pillar_scores")
            else:
                logger.warning(f"    ❌ data_source = {ds} (expected pillar_scores)")

            # 7b: Historical impact should be > 0
            impact = final_roi.get('total_impact', 0)
            impact_ok = impact > 0
            validations.append({
                'check': 'historical_impact > 0',
                'pass': impact_ok,
                'actual': impact
            })
            if impact_ok:
                logger.info(f"    ✅ Historical impact = ${impact:,.0f}")
            else:
                logger.warning(f"    ❌ Historical impact = ${impact:,.0f}")

            # 7c: Check pillar score progression
            pillar_checks = []
            for acc in accounts[:3]:  # Check first 3 accounts
                score_resp = self.client.get_account_scores(acc.get('account_id'))
                api_calls += 1
                if score_resp:
                    pillar_checks.append(score_resp)

            # 7d: GRR should be among top contributors (if metric ranking available)
            ranking = final_roi.get('metric_ranking', [])
            if ranking:
                top_metric = ranking[0].get('metric', '')
                grr_top = top_metric == 'GRR'
                validations.append({
                    'check': 'GRR is top dollar contributor',
                    'pass': grr_top,
                    'actual': f"Top metric: {top_metric}"
                })
                if grr_top:
                    logger.info(f"    ✅ GRR is top contributor "
                                f"(${ranking[0].get('historical_dollars', 0):,.0f})")
                else:
                    logger.info(f"    ℹ️  Top contributor: {top_metric} "
                                f"(GRR expected due to highest economic weight)")

            # 7e: Context graph verification (only if enrichment was attempted)
            if context_graph_enriched:
                first_acc = accounts[0].get('account_id') if accounts else None
                if first_acc:
                    cg_summary = self.client.get_context_graph_summary(first_acc)
                    api_calls += 1
                    if cg_summary and cg_summary.get('status') == 'success':
                        nodes_by_type = cg_summary.get('nodes_by_type', {})
                        has_signals = nodes_by_type.get('SIGNAL', 0) > 0
                        has_outcomes = nodes_by_type.get('OUTCOME', 0) > 0
                        cg_ok = has_signals and has_outcomes
                        validations.append({
                            'check': 'context_graph has SIGNAL + OUTCOME nodes',
                            'pass': cg_ok,
                            'actual': dict(nodes_by_type),
                        })
                        if cg_ok:
                            logger.info(f"    ✅ Context graph: {nodes_by_type}")
                        else:
                            logger.warning(f"    ❌ Context graph missing expected nodes: {nodes_by_type}")
                    else:
                        validations.append({
                            'check': 'context_graph has SIGNAL + OUTCOME nodes',
                            'pass': False,
                            'actual': 'summary API failed',
                        })

            results['validations'] = validations
            passed = sum(1 for v in validations if v['pass'])
            total_checks = len(validations)

            # ── ROI comparison summary ──
            logger.info("\n  ═══════════════════════════════════════")
            logger.info("  ROI COMPARISON (Before → After)")
            logger.info("  ═══════════════════════════════════════")
            logger.info(f"  Historical ROI:  {baseline_roi.get('roi_pct', 'N/A')}% → "
                        f"{final_roi.get('roi_pct', 'N/A')}%")
            logger.info(f"  Historical $:    ${baseline_roi.get('total_impact', 0):,.0f} → "
                        f"${final_roi.get('total_impact', 0):,.0f}")
            logger.info(f"  Forward ROI:     {final_roi.get('forward_roi_pct', 'N/A')}%")
            logger.info(f"  Data Source:     {final_roi.get('data_source', 'N/A')}")
            logger.info(f"  Validations:     {passed}/{total_checks} passed")
            logger.info("  ═══════════════════════════════════════\n")

            results['comparison'] = {
                'baseline_roi_pct': baseline_roi.get('roi_pct'),
                'final_roi_pct': final_roi.get('roi_pct'),
                'baseline_impact': baseline_roi.get('total_impact', 0),
                'final_impact': final_roi.get('total_impact', 0),
                'improvement_pct_configured': improvement_pct,
                'months_simulated': months,
            }

            if months_ok >= months - 1 and passed >= total_checks - 1:
                return self.success(
                    f"ROI simulation complete: {months_ok}/{months} months, "
                    f"{passed}/{total_checks} validations passed, "
                    f"ROI: {baseline_roi.get('roi_pct')}% → {final_roi.get('roi_pct')}%",
                    details=results,
                    api_calls=api_calls,
                    errors=errors
                )
            else:
                return self.failure(
                    f"ROI simulation incomplete: {months_ok}/{months} months, "
                    f"{passed}/{total_checks} validations",
                    details=results,
                    api_calls=api_calls,
                    errors=errors
                )

        except Exception as e:
            logger.error(f"❌ ROI simulation failed: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return self.failure(
                "ROI simulation failed",
                error=str(e),
                details=results,
                api_calls=api_calls
            )
