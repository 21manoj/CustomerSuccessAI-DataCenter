#!/usr/bin/env python3
"""
V2 manifest-driven scenario with stronger post-process assertions.

This keeps existing ingest behavior, but fails runs when data correctness
checks show partial/invalid backend state after process-data.
"""

import logging
import time
from pathlib import Path
from typing import Any, Dict, List, Tuple

from scenarios.base import BaseScenario

from V2_manifest_generator import ManifestCSVGeneratorV2

logger = logging.getLogger(__name__)


class ScenarioManifestV2(BaseScenario):
    """Manifest-driven data load + post-process validation checks."""

    def _expected_distribution(self, accounts: List[Dict[str, Any]]) -> Dict[str, int]:
        out = {"critical": 0, "at_risk": 0, "healthy": 0}
        for acct in accounts:
            cls = str(acct.get("classification", "healthy")).lower()
            if cls in out:
                out[cls] += 1
            else:
                out["healthy"] += 1
        return out

    @staticmethod
    def _manifest_class_for_account(acct: Dict[str, Any]) -> str:
        cls = str(acct.get("classification", "healthy")).lower()
        if cls in ("critical", "at_risk", "healthy"):
            return cls
        return "healthy"

    def _expected_account_ids(self, customer_id: int, n_accounts: int) -> List[int]:
        base = customer_id * 1000 + 1
        return [base + i for i in range(n_accounts)]

    def _status_from_score(self, score: float) -> str:
        if score >= 70:
            return "healthy"
        if score >= 50:
            return "at_risk"
        return "critical"

    def _extract_score_and_status(self, payload: Dict[str, Any]) -> Tuple[float, str]:
        if not payload:
            return 0.0, "critical"
        # /api/dc2s/health-score/{id} (on-the-fly from dc2s_kpis)
        if payload.get("overall_score") is not None:
            try:
                score_f = float(payload["overall_score"])
            except Exception:
                score_f = 0.0
            status = str(payload.get("health_status") or "").lower()
            if status == "risk":
                status = "at_risk"
            if status not in ("critical", "at_risk", "healthy"):
                status = self._status_from_score(score_f)
            return score_f, status

        # GET /api/dc2s/scores/account/{id}/latest — nested health_score dict
        hs = payload.get("health_score")
        if isinstance(hs, dict):
            score = hs.get("health_score")
            status_raw = hs.get("health_status")
        else:
            score = hs
            status_raw = payload.get("health_status")

        if score is None and isinstance(payload.get("health"), dict):
            score = payload["health"].get("score")
        if score is None and isinstance(payload.get("data"), dict):
            score = payload["data"].get("health_score")
        try:
            score_f = float(score) if score is not None else 0.0
        except Exception:
            score_f = 0.0

        def _norm(s: Any) -> str:
            r = str(s or "").lower().strip()
            if r in ("excellent", "good", "healthy"):
                return "healthy"
            if r in ("warning", "at_risk", "risk"):
                return "at_risk"
            if r == "critical":
                return "critical"
            return ""

        status = _norm(status_raw)
        if not status:
            status = _norm(payload.get("health_status"))
        if not status:
            st = payload.get("status")
            if st not in ("success", "warning", "error", None):
                status = _norm(st)
        if not status:
            status = self._status_from_score(score_f)
        if status not in ("critical", "at_risk", "healthy"):
            status = self._status_from_score(score_f)
        return score_f, status

    def _extract_kpi_count(self, payload: Dict[str, Any]) -> int:
        if not payload:
            return 0
        kc = payload.get("kpi_count")
        if kc is not None:
            try:
                return int(kc)
            except Exception:
                pass
        for key in ("kpi_scores", "kpis", "kpi_data"):
            v = payload.get(key)
            if isinstance(v, list):
                return len(v)
            if isinstance(v, dict):
                return len(v)
        if isinstance(payload.get("pillars"), list):
            total = 0
            for p in payload["pillars"]:
                if isinstance(p, dict):
                    k = p.get("kpis")
                    if isinstance(k, list):
                        total += len(k)
            if total > 0:
                return total
        return 0

    def _validate_post_process(
        self,
        customer_id: int,
        expected_account_ids: List[int],
        manifest_accounts: List[Dict[str, Any]],
        expected_kpi_count: int,
        expected_distribution: Dict[str, int],
        sample_size: int,
        health_tolerance: int,
        strict: bool,
    ) -> Dict[str, Any]:
        checks: Dict[str, Any] = {"passed": True, "errors": [], "metrics": {}}

        accounts_resp = self.client.get_accounts() or []
        actual_ids = []
        for row in accounts_resp:
            if not isinstance(row, dict):
                continue
            aid = row.get("account_id") or row.get("source_account_id") or row.get("id")
            if aid is None:
                continue
            try:
                actual_ids.append(int(aid))
            except Exception:
                continue

        exp_set = set(expected_account_ids)
        act_set = set(actual_ids)
        missing_ids = sorted(exp_set - act_set)
        checks["metrics"]["accounts_expected"] = len(expected_account_ids)
        checks["metrics"]["accounts_found"] = len(act_set)
        checks["metrics"]["missing_account_ids"] = missing_ids[:20]
        if missing_ids:
            checks["passed"] = False
            checks["errors"].append(f"Missing expected account IDs: {missing_ids[:10]}")

        sample_ids = expected_account_ids[: max(1, min(sample_size, len(expected_account_ids)))]
        id_to_manifest: Dict[int, str] = {}
        for i, aid in enumerate(expected_account_ids):
            if i < len(manifest_accounts):
                id_to_manifest[aid] = self._manifest_class_for_account(manifest_accounts[i])
            else:
                id_to_manifest[aid] = "healthy"
        expected_sample_manifest = {"critical": 0, "at_risk": 0, "healthy": 0}
        for aid in sample_ids:
            c = id_to_manifest.get(aid, "healthy")
            expected_sample_manifest[c] += 1

        endpoint_failures = []
        actual_distribution = {"critical": 0, "at_risk": 0, "healthy": 0}
        kpi_count_failures = []
        validation_call_seconds: Dict[str, float] = {}
        for aid in sample_ids:
            # Prefer health-score route: reads dc2s_kpis after onboarding without health_scores.
            t_call = time.time()
            payload = self.client.get_dc2s_health_score(aid)
            validation_call_seconds[str(aid)] = round(time.time() - t_call, 3)
            if not payload:
                endpoint_failures.append(aid)
                continue
            score, status = self._extract_score_and_status(payload)
            actual_distribution[status] += 1
            kpi_count = self._extract_kpi_count(payload)
            if strict and kpi_count < expected_kpi_count:
                kpi_count_failures.append((aid, kpi_count))
            if kpi_count == 0 or payload.get("error"):
                endpoint_failures.append(aid)
            checks["metrics"].setdefault("sample_scores", {})[str(aid)] = {
                "health_score": round(score, 2),
                "status": status,
                "kpi_count": kpi_count,
            }

        checks["metrics"]["sample_size"] = len(sample_ids)
        checks["metrics"]["endpoint_failures"] = endpoint_failures
        checks["metrics"]["validation_call_seconds"] = validation_call_seconds
        if validation_call_seconds:
            vals = list(validation_call_seconds.values())
            checks["metrics"]["validation_latency_summary_s"] = {
                "min": round(min(vals), 3),
                "max": round(max(vals), 3),
                "avg": round(sum(vals) / len(vals), 3),
            }
        if endpoint_failures:
            checks["passed"] = False
            checks["errors"].append(f"Account score endpoint failed/empty for IDs: {endpoint_failures[:10]}")

        checks["metrics"]["sample_distribution_actual"] = actual_distribution
        # Expect manifest narrative labels for the *same* sampled account IDs (not global % × n).
        checks["metrics"]["sample_distribution_expected"] = dict(expected_sample_manifest)
        for cls in ("critical", "at_risk", "healthy"):
            expected_sample = expected_sample_manifest[cls]
            if abs(actual_distribution[cls] - expected_sample) > health_tolerance:
                checks["passed"] = False
                checks["errors"].append(
                    f"Health distribution drift for {cls}: actual={actual_distribution[cls]} "
                    f"expected~={expected_sample} tolerance={health_tolerance}"
                )

        checks["metrics"]["kpi_count_failures"] = kpi_count_failures[:10]
        if kpi_count_failures:
            checks["passed"] = False
            checks["errors"].append(f"KPI cardinality shortfall in sample accounts: {kpi_count_failures[:5]}")

        return checks

    def run(self) -> Dict[str, Any]:
        self.start_timer()
        logger.info("=== Scenario: Manifest-Driven Load V2 ===")

        api_calls = 0
        errors: List[str] = []
        results: Dict[str, Any] = {}

        manifest_path = getattr(self.args, "manifest", None)
        if not manifest_path:
            return self.failure("--manifest path required")
        manifest_path = Path(manifest_path)
        if not manifest_path.exists():
            return self.failure(f"Manifest not found: {manifest_path}")

        customer_id = getattr(self.args, "customer_id", None) or getattr(self.client, "customer_id", None)
        if not customer_id:
            return self.failure("--customer-id required for manifest scenario")
        seed = getattr(self.args, "seed", None) or 42
        phase = getattr(self.args, "phase", None)

        strict = bool(getattr(self.args, "validate_strict", True))
        sample_size = int(getattr(self.args, "validate_sample_size", 5))
        health_tolerance = int(getattr(self.args, "health_tolerance", 1))

        try:
            gen = ManifestCSVGeneratorV2(
                manifest_path=str(manifest_path),
                customer_id=int(customer_id),
                seed=seed,
            )

            expected_ids = self._expected_account_ids(int(customer_id), len(gen.accounts))
            expected_kpi_count = len(gen.kpi_codes)
            expected_distribution = self._expected_distribution(gen.accounts)

            results["manifest"] = str(manifest_path)
            results["customer_id"] = int(customer_id)
            results["customer_name"] = gen.customer_info["name"]
            results["phase"] = phase
            results["expected"] = {
                "accounts": len(gen.accounts),
                "kpi_count_per_account": expected_kpi_count,
                "expected_account_ids_preview": expected_ids[:5],
                "expected_distribution": expected_distribution,
            }

            logger.info("  Step 1/2: Generate + upload CSVs (streamed per file)")
            filename_map = {
                "accounts": "accounts.csv",
                "kpi_measurements": "kpi_measurements.csv",
                "enhanced_signals": "enhanced_qualitative_signals.csv",
                "products": "products.csv",
                "stakeholders": "stakeholders.csv",
                "engagement_events": "engagement_events.csv",
                "account_business_profiles": "account_business_profiles.csv",
                "outcomes": "outcomes.csv",
                "decisions": "decisions.csv",
                "signal_edges": "signal_edges.csv",
            }
            generators = {
                "accounts": gen.generate_accounts_csv,
                "kpi_measurements": gen.generate_kpi_measurements_csv,
                "enhanced_signals": gen.generate_signals_csv,
                "products": gen.generate_products_csv,
                "stakeholders": gen.generate_stakeholders_csv,
                "engagement_events": gen.generate_engagement_events_csv,
                "account_business_profiles": gen.generate_profiles_csv,
                "outcomes": gen.generate_outcomes_csv,
                "decisions": gen.generate_decisions_csv,
                "signal_edges": gen.generate_signal_edges_csv,
            }
            upload_results = {}
            endpoint_metrics = {
                "generate_seconds": {},
                "upload_seconds": {},
                "upload_bytes": {},
                "upload_status": {},
            }
            t_step12 = time.time()
            for file_type, gen_fn in generators.items():
                t_gen = time.time()
                csv_content = ManifestCSVGeneratorV2._header_use_account_id(gen_fn())
                endpoint_metrics["generate_seconds"][file_type] = round(time.time() - t_gen, 3)
                endpoint_metrics["upload_bytes"][file_type] = len(csv_content.encode("utf-8"))

                t_up = time.time()
                resp = self.client.upload_csv(
                    customer_id=int(customer_id),
                    file_type=file_type,
                    csv_content=csv_content,
                    filename=filename_map.get(file_type, f"{file_type}.csv"),
                )
                endpoint_metrics["upload_seconds"][file_type] = round(time.time() - t_up, 3)
                api_calls += 1
                ok = bool(resp and resp.get("status") == "success")
                upload_results[file_type] = "success" if ok else f"failed: {str(resp)[:80]}"
                endpoint_metrics["upload_status"][file_type] = "success" if ok else "failed"
                if not ok:
                    errors.append(f"Upload failed: {file_type}")
            results["upload_results"] = upload_results
            total_upload_bytes = sum(endpoint_metrics["upload_bytes"].values())
            total_upload_s = sum(endpoint_metrics["upload_seconds"].values())
            endpoint_metrics["upload_throughput_bytes_per_s"] = round(
                total_upload_bytes / max(total_upload_s, 0.001), 2
            )
            endpoint_metrics["step12_duration_s"] = round(time.time() - t_step12, 2)
            results["endpoint_metrics"] = endpoint_metrics
            results["generation_duration_s"] = round(
                sum(endpoint_metrics["generate_seconds"].values()), 2
            )
            results["upload_duration_s"] = round(total_upload_s, 2)

            if not any(v == "success" for v in upload_results.values()):
                return self.failure("All CSV uploads failed", api_calls=api_calls, errors=errors, details=results)

            logger.info("  Step 3: process-data")
            original_timeout = self.client.timeout
            self.client.timeout = 300
            t1 = time.time()
            process_resp = self.client.process_data(
                customer_id=int(customer_id),
                skip_wizard_b=True,
                skip_wizard_c=False,
                strict_kpi_ranges=False,
            )
            self.client.timeout = original_timeout
            api_calls += 1
            results["process_duration_s"] = round(time.time() - t1, 2)
            results["process_response"] = process_resp or {}
            results.setdefault("endpoint_metrics", {})["process_data_seconds"] = round(
                time.time() - t1, 3
            )
            results["endpoint_metrics"]["process_data_status"] = (
                process_resp.get("status") if process_resp else "failed"
            )
            if not (process_resp and process_resp.get("status") in ("success", "warning")):
                return self.failure(
                    f"process-data failed: {str(process_resp)[:150]}",
                    api_calls=api_calls,
                    errors=errors,
                    details=results,
                )

            logger.info("  Step 4: post-process validations")
            validation = self._validate_post_process(
                customer_id=int(customer_id),
                expected_account_ids=expected_ids,
                manifest_accounts=gen.accounts,
                expected_kpi_count=expected_kpi_count,
                expected_distribution=expected_distribution,
                sample_size=sample_size,
                health_tolerance=health_tolerance,
                strict=strict,
            )
            results["validation"] = validation
            if not validation["passed"]:
                return self.failure(
                    "Manifest ingest completed but validation checks failed",
                    api_calls=api_calls,
                    errors=errors + validation.get("errors", []),
                    details=results,
                )

        except Exception as e:
            logger.error(f"Manifest V2 scenario error: {e}", exc_info=True)
            return self.failure(
                f"Manifest V2 scenario failed: {str(e)}",
                api_calls=api_calls,
                errors=errors,
                details=results,
            )

        return self.success(
            f"Manifest V2 loaded + validated: {results['customer_name']} "
            f"({results['expected']['accounts']} accounts)",
            api_calls=api_calls,
            errors=errors,
            details=results,
        )
