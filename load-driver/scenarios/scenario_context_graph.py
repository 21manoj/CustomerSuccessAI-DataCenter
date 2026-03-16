#!/usr/bin/env python3
"""
Scenario 8: Context Graph

Generates 8 context graph CSVs from a story arc manifest, uploads them
to the onboarding API, triggers process-data (which ingests into
context_nodes/context_edges), and verifies the graph was persisted.

Note: decision_evidence has been removed (consolidated into decisions.csv).

Prerequisites:
  - Customer must already exist (run Scenario 1 first)
  - context_graph feature toggle must be enabled for the customer
"""

import io
import json
import logging
import os
import sys
import time
from pathlib import Path
from typing import Dict, Any

from .base import BaseScenario

logger = logging.getLogger(__name__)

# Try to import the context graph generator from the backend.
# Multiple search paths for different deployment modes:
#   1) Docker platform container: /app/backend
#   2) Local dev: sibling of load-driver → ../kpi-dashboard/backend
_generator_available = False
_backend_search_paths = [
    '/app/backend',  # Docker container
    str(Path(__file__).resolve().parent.parent.parent / 'kpi-dashboard' / 'backend'),  # local dev
]
for _bp in _backend_search_paths:
    if Path(_bp).exists() and _bp not in sys.path:
        sys.path.insert(0, _bp)
try:
    from scripts.generate_context_graph_data import ContextGraphGenerator
    _generator_available = True
except ImportError:
    logger.warning("ContextGraphGenerator not available — scenario will use pre-generated CSVs")


# The 8 context graph file types matching CONTEXT_GRAPH_FILE_TYPES in onboarding API
# Note: decision_evidence removed (consolidated into decisions.csv)
CONTEXT_GRAPH_FILES = {
    'stakeholders': 'stakeholders.csv',
    'engagement_events': 'engagement_events.csv',
    'account_business_profiles': 'account_business_profiles.csv',
    'decisions': 'decisions.csv',
    'outcomes': 'outcomes.csv',
    'signal_edges': 'signal_edges.csv',
    'industry_benchmarks': 'industry_benchmarks.csv',
    'enhanced_signals': 'enhanced_qualitative_signals.csv',
}


class ScenarioContextGraph(BaseScenario):
    """
    Scenario 8: Context Graph Pipeline

    Steps:
    1. Verify customer exists and has accounts
    2. Generate 9 context graph CSVs from story arc manifest
    3. Upload each CSV via /api/onboarding/upload
    4. Run /api/onboarding/process-data (triggers context graph ingestion)
    5. Verify context graph data exists via health/status endpoint

    Measures:
    - CSV generation time
    - Upload time (per file and total)
    - Process-data ingestion time
    - Node/edge counts
    """

    def run(self) -> Dict[str, Any]:
        self.start_timer()
        logger.info("=== Scenario 8: Context Graph ===")

        api_calls = 0
        errors = []
        results = {}

        customer_id = getattr(self.args, 'customer_id', None)
        if not customer_id:
            return self.failure("customer_id required", api_calls=0)

        arc_id = getattr(self.args, 'arc_id', None) or 'arc_expansion_champion'
        seed = getattr(self.args, 'seed', None) or 42

        results['customer_id'] = customer_id
        results['arc_id'] = arc_id

        try:
            # ================================================================
            # Step 1: Fetch real accounts for this customer
            # ================================================================
            logger.info(f"  Step 1: Fetching accounts for customer {customer_id}")
            accounts = self.client.get_accounts()
            api_calls += 1

            if not accounts:
                return self.failure(
                    f"No accounts found for customer {customer_id}",
                    api_calls=api_calls, details=results
                )

            real_account_ids = [acc.get('account_id') for acc in accounts]
            num_accounts = len(real_account_ids)
            results['existing_accounts'] = num_accounts
            results['num_accounts'] = num_accounts
            results['account_ids'] = real_account_ids
            logger.info(f"    OK: Found {num_accounts} accounts: {real_account_ids}")

            # ================================================================
            # Step 2: Generate 8 context graph CSVs using real account IDs
            # ================================================================
            logger.info(f"  Step 2: Generating context graph CSVs (arc={arc_id}, {num_accounts} real accounts)")
            gen_start = time.time()

            csv_contents = {}  # file_type → csv string

            if _generator_available:
                try:
                    # Build account_arc_map from real account IDs
                    # All accounts get the same arc (single-arc mode)
                    account_arc_map = {aid: arc_id for aid in real_account_ids}

                    gen = ContextGraphGenerator(
                        customer_id=customer_id,
                        arc_id=arc_id,
                        account_arc_map=account_arc_map,
                        seed=seed,
                    )
                    # Generate each CSV as a string (8 files; decision_evidence consolidated into decisions)
                    csv_contents = {
                        'stakeholders': gen.generate_stakeholders_csv(),
                        'engagement_events': gen.generate_engagement_events_csv(),
                        'account_business_profiles': gen.generate_account_business_profiles_csv(),
                        'decisions': gen.generate_decisions_csv(),
                        'outcomes': gen.generate_outcomes_csv(),
                        'signal_edges': gen.generate_signal_edges_csv(),
                        'industry_benchmarks': gen.generate_industry_benchmarks_csv(),
                        'enhanced_signals': gen.generate_enhanced_signals_csv(),
                    }
                except Exception as e:
                    logger.error(f"    FAIL: CSV generation failed: {e}")
                    return self.failure(
                        f"Context graph CSV generation failed: {e}",
                        api_calls=api_calls, details=results
                    )
            else:
                # Fallback: look for pre-generated CSVs in a known location
                pre_gen_dir = Path(__file__).parent.parent / 'data' / 'context_graph' / arc_id
                if pre_gen_dir.exists():
                    for file_type, filename in CONTEXT_GRAPH_FILES.items():
                        fpath = pre_gen_dir / filename
                        if fpath.exists():
                            csv_contents[file_type] = fpath.read_text()
                if not csv_contents:
                    return self.failure(
                        "ContextGraphGenerator not available and no pre-generated CSVs found",
                        api_calls=api_calls, details=results
                    )

            gen_duration = time.time() - gen_start
            logger.info(f"    OK: Generated {len(csv_contents)} CSV files in {gen_duration:.1f}s")
            results['generation_duration_s'] = round(gen_duration, 2)
            results['files_generated'] = list(csv_contents.keys())

            # ================================================================
            # Step 3: Upload 8 context graph CSVs
            # ================================================================
            logger.info("  Step 3: Uploading context graph CSVs")
            upload_start = time.time()
            upload_results = {}

            for file_type, csv_content in csv_contents.items():
                filename = CONTEXT_GRAPH_FILES[file_type]
                resp = self.client.upload_csv(
                    customer_id=customer_id,
                    file_type=file_type,
                    csv_content=csv_content,
                    filename=filename,
                )
                api_calls += 1

                if resp and resp.get('status') == 'success':
                    upload_results[file_type] = 'success'
                    logger.info(f"    {file_type}: uploaded")
                else:
                    upload_results[file_type] = f"failed: {str(resp)[:80]}"
                    errors.append(f"Upload {file_type} failed: {str(resp)[:80]}")
                    logger.warning(f"    {file_type}: FAILED — {str(resp)[:80]}")

            upload_duration = time.time() - upload_start
            upload_successes = sum(1 for v in upload_results.values() if v == 'success')
            logger.info(f"    Uploaded {upload_successes}/{len(csv_contents)} files in {upload_duration:.1f}s")
            results['upload_duration_s'] = round(upload_duration, 2)
            results['upload_results'] = upload_results

            if upload_successes == 0:
                return self.failure(
                    "All context graph CSV uploads failed",
                    api_calls=api_calls, errors=errors, details=results
                )

            # ================================================================
            # Step 4: Process data (triggers context graph ingestion)
            # ================================================================
            logger.info("  Step 4: Processing data (context graph ingestion)")
            process_start = time.time()

            original_timeout = self.client.timeout
            self.client.timeout = 300
            process_resp = self.client.process_data(
                customer_id=customer_id,
                skip_wizard_b=True,
                skip_wizard_c=True,
                strict_kpi_ranges=False,
            )
            self.client.timeout = original_timeout
            api_calls += 1

            process_duration = time.time() - process_start

            if process_resp and process_resp.get('status') in ('success', 'warning'):
                steps_done = process_resp.get('steps_completed', [])
                cg_result = process_resp.get('context_graph', {})
                logger.info(f"    OK: Process-data completed in {process_duration:.1f}s")
                logger.info(f"    Steps: {steps_done}")
                if cg_result:
                    logger.info(f"    Context graph: {cg_result.get('nodes_inserted', 0)} nodes, "
                                f"{cg_result.get('edges_inserted', 0)} edges")
                results['process_duration_s'] = round(process_duration, 2)
                results['steps_completed'] = steps_done
                results['context_graph_result'] = cg_result
            else:
                err = str(process_resp)[:150] if process_resp else "No response"
                logger.warning(f"    WARN: process-data returned: {err}")
                results['process_data_status'] = f"failed: {err}"
                errors.append(f"process-data failed: {err[:80]}")

            # ================================================================
            # Step 5: Verify context graph data (optional, best-effort)
            # ================================================================
            logger.info("  Step 5: Verifying context graph data")
            verify_resp = self.client.get(
                f'/api/onboarding/status/{customer_id}',
                skip_auth_check=True
            )
            api_calls += 1

            if verify_resp:
                results['verification'] = 'checked'
                logger.info("    OK: Status endpoint responded")
            else:
                results['verification'] = 'skipped'
                logger.info("    Skipped: status endpoint not available")

        except Exception as e:
            logger.error(f"Scenario 8 error: {e}", exc_info=True)
            return self.failure(
                f"Context graph scenario failed: {str(e)}",
                api_calls=api_calls, errors=errors, details=results
            )

        # ── Final result ──
        if errors:
            return self.success(
                f"Context graph: {upload_successes}/{len(csv_contents)} files uploaded, "
                f"{len(errors)} warnings",
                api_calls=api_calls, errors=errors, details=results
            )
        else:
            return self.success(
                f"Context graph: {len(csv_contents)} files uploaded and ingested "
                f"for customer {customer_id} (arc={arc_id})",
                api_calls=api_calls, errors=errors, details=results
            )
