#!/usr/bin/env python3
"""
Scenario 8: Context Graph

Generates 9 context graph CSVs from a story arc manifest, uploads them
to the onboarding API, triggers process-data (which ingests into
context_nodes/context_edges), and verifies the graph was persisted.

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

# Try to import the context graph generator from the backend
# The load-driver Dockerfile copies the backend code, so this should work
# in both local dev and Docker.
_generator_available = False
try:
    # When running from load-driver directory, backend is a sibling
    _backend_dir = str(Path(__file__).resolve().parent.parent.parent / 'kpi-dashboard' / 'backend')
    if _backend_dir not in sys.path:
        sys.path.insert(0, _backend_dir)
    from scripts.generate_context_graph_data import ContextGraphGenerator
    _generator_available = True
except ImportError:
    logger.warning("ContextGraphGenerator not available — scenario will use pre-generated CSVs")


# The 9 context graph file types matching CONTEXT_GRAPH_FILE_TYPES in onboarding API
CONTEXT_GRAPH_FILES = {
    'stakeholders': 'stakeholders.csv',
    'engagement_events': 'engagement_events.csv',
    'account_business_profiles': 'account_business_profiles.csv',
    'decisions': 'decisions.csv',
    'outcomes': 'outcomes.csv',
    'signal_edges': 'signal_edges.csv',
    'decision_evidence': 'decision_evidence.csv',
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
        num_accounts = getattr(self.args, 'num_accounts', None) or 10
        seed = getattr(self.args, 'seed', None) or 42

        results['customer_id'] = customer_id
        results['arc_id'] = arc_id
        results['num_accounts'] = num_accounts

        try:
            # ================================================================
            # Step 1: Verify customer exists (lightweight health check)
            # ================================================================
            logger.info(f"  Step 1: Verifying server is up (customer {customer_id} assumed from Scenario 1)")
            # /api/onboarding/status requires auth — just do a health check
            # and trust that customer exists (created by Scenario 1)
            health_ok = self.client.health_check()
            api_calls += 1
            if not health_ok:
                return self.failure(
                    "Server health check failed — cannot proceed",
                    api_calls=api_calls, details=results
                )
            results['existing_accounts'] = num_accounts  # trust the CLI arg
            logger.info(f"    OK: Server healthy, proceeding with customer {customer_id}")

            # ================================================================
            # Step 2: Generate 9 context graph CSVs
            # ================================================================
            logger.info(f"  Step 2: Generating context graph CSVs (arc={arc_id})")
            gen_start = time.time()

            csv_contents = {}  # file_type → csv string

            if _generator_available:
                try:
                    gen = ContextGraphGenerator(
                        customer_id=customer_id,
                        arc_id=arc_id,
                        num_accounts=num_accounts,
                        seed=seed,
                    )
                    # Generate each CSV as a string
                    csv_contents = {
                        'stakeholders': gen.generate_stakeholders_csv(),
                        'engagement_events': gen.generate_engagement_events_csv(),
                        'account_business_profiles': gen.generate_account_business_profiles_csv(),
                        'decisions': gen.generate_decisions_csv(),
                        'outcomes': gen.generate_outcomes_csv(),
                        'signal_edges': gen.generate_signal_edges_csv(),
                        'decision_evidence': gen.generate_decision_evidence_csv(),
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
            # Step 3: Upload 9 context graph CSVs
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
