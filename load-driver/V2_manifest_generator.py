#!/usr/bin/env python3
"""
V2 manifest CSV generator: zen-golick phase + intervention support.

- phase=None: full manifest time range (default; same as base generator).
- phase='baseline': first ~2/3 of data points (declining narratives).
- phase='intervention': last ~1/3 of points + recovery KPI trajectories +
  optional per-account `intervention` blocks (signals, decisions, outcomes, edges).

Headers use `source_account_id` in line with the base generator; ScenarioManifestV2
applies `_header_use_account_id()` before upload so onboarding accepts `account_id`.
"""

from __future__ import annotations

import csv
import io
import logging
import random
import uuid as uuid_mod
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from scenarios.scenario_manifest import ManifestCSVGenerator

logger = logging.getLogger(__name__)


class ManifestCSVGeneratorV2(ManifestCSVGenerator):
    """
    Extends ManifestCSVGenerator with phase windowing and intervention narratives
    (ported from `.claude/worktrees/zen-golick/load-driver/scenarios/scenario_manifest.py`).
    """

    def __init__(
        self,
        manifest_path: str,
        customer_id: int = 0,
        seed: int = 42,
        phase: Optional[str] = None,
    ):
        super().__init__(manifest_path, customer_id, seed)
        self.phase = phase
        self.vertical = self.customer_info.get("vertical", "dc2_s")

        raw_dp = int(self.time_range.get("data_points_per_kpi", 26))
        self.start_date = datetime.strptime(self.time_range["start"], "%Y-%m-%d")

        if phase == "baseline":
            self.data_points = int(raw_dp * 2 / 3)
            logger.info("  Phase=baseline: generating %s data points (≈ months 1–4)", self.data_points)
        elif phase == "intervention":
            baseline_points = int(raw_dp * 2 / 3)
            self.data_points = raw_dp - baseline_points
            if self.frequency == "weekly":
                self.start_date += timedelta(weeks=baseline_points)
            elif self.frequency == "daily":
                self.start_date += timedelta(days=baseline_points)
            else:
                self.start_date += timedelta(days=baseline_points * 30)
            logger.info(
                "  Phase=intervention: generating %s data points from %s",
                self.data_points,
                self.start_date.strftime("%Y-%m-%d"),
            )

        self.dates = self._build_dates()

    def _generate_kpi_series(
        self,
        target_health: float,
        trajectory: str,
        decline_start_month: Optional[int],
        kpi_code: str,
    ) -> List[float]:
        if self.phase == "intervention" and trajectory in ("declining", "slow_decline"):
            target_health = min(target_health + 15, 95)
            trajectory = "improving"
        return super()._generate_kpi_series(
            target_health, trajectory, decline_start_month, kpi_code
        )

    @staticmethod
    def _header_use_account_id(csv_content: str) -> str:
        if not csv_content:
            return csv_content
        first_nl = csv_content.find("\n")
        if first_nl == -1:
            header, rest = csv_content, ""
        else:
            header, rest = csv_content[:first_nl], csv_content[first_nl:]
        header = header.replace("source_account_id", "account_id")
        return header + rest

    def generate_signals_csv(self) -> str:
        """enhanced_qualitative_signals — zen layout + intervention extras + signal_ref."""
        out = io.StringIO()
        w = csv.writer(out)
        w.writerow(
            [
                "signal_id",
                "source_account_id",
                "signal_date",
                "signal_type",
                "content",
                "sentiment",
                "sentiment_score",
                "arc_id",
                "story_phase",
                "linked_node_id",
                "signal_ref",
            ]
        )

        phase_prefix = f"{self.phase}_" if self.phase else ""
        counter = 0
        for idx, acct in enumerate(self.accounts):
            aid = self._account_id(idx)
            arc = acct.get("story_arc", "")

            for sig in acct.get("key_signals", []):
                counter += 1
                sentiment = sig.get("sentiment", "neutral")
                score_map = {
                    "very_positive": 0.9,
                    "positive": 0.7,
                    "neutral": 0.1,
                    "negative": -0.6,
                    "very_negative": -0.9,
                }
                sig_ref = f"{phase_prefix}sig_{aid}_{counter}"
                w.writerow(
                    [
                        sig_ref,
                        aid,
                        sig.get("date", "2026-01-01"),
                        sig.get("type", "observation"),
                        sig.get("content", ""),
                        sentiment.replace("very_", ""),
                        score_map.get(sentiment, 0.0),
                        arc,
                        "",
                        "",
                        sig_ref,
                    ]
                )

            cls = acct.get("classification", "healthy")
            for month in range(6):
                for _ in range(2):
                    counter += 1
                    date = self.start_date + timedelta(days=30 * month + random.randint(0, 29))

                    if cls == "critical":
                        templates = [
                            "Escalation review meeting conducted",
                            "Support ticket volume above normal",
                            "Performance metrics under review",
                            "Stakeholder alignment meeting scheduled",
                        ]
                        sentiment = random.choice(["negative", "neutral"])
                    elif cls == "at_risk":
                        templates = [
                            "Quarterly check-in completed",
                            "Usage patterns reviewed with team",
                            "Renewal discussion in progress",
                            "Technical review session held",
                        ]
                        sentiment = random.choice(["neutral", "negative", "neutral"])
                    else:
                        templates = [
                            "Regular QBR completed successfully",
                            "Product adoption metrics trending well",
                            "Champion engagement remains strong",
                            "Expansion discussion in early stages",
                        ]
                        sentiment = random.choice(["positive", "neutral", "positive"])

                    score = {"positive": 0.6, "neutral": 0.1, "negative": -0.5}[sentiment]
                    sig_ref = f"{phase_prefix}sig_{aid}_{counter}"
                    w.writerow(
                        [
                            sig_ref,
                            aid,
                            date.strftime("%Y-%m-%d"),
                            random.choice(
                                [
                                    "meeting",
                                    "health_check",
                                    "observation",
                                    "customer_feedback",
                                ]
                            ),
                            random.choice(templates),
                            sentiment,
                            round(score + random.gauss(0, 0.1), 2),
                            arc,
                            "",
                            "",
                            sig_ref,
                        ]
                    )

            intervention = acct.get("intervention", {})
            if self.phase == "intervention" and intervention.get("recovery_signals"):
                for rs in intervention["recovery_signals"]:
                    counter += 1
                    sig_ref = f"{phase_prefix}recovery_{aid}_{counter}"
                    w.writerow(
                        [
                            sig_ref,
                            aid,
                            rs.get("date", "2026-03-01"),
                            rs.get("type", "recovery_signal"),
                            rs.get("content", ""),
                            rs.get("sentiment", "positive"),
                            0.7 if rs.get("sentiment") == "positive" else 0.1,
                            arc,
                            "recovery",
                            "",
                            sig_ref,
                        ]
                    )

            if self.phase == "intervention" and intervention.get("csm_actions"):
                for ca in intervention["csm_actions"]:
                    counter += 1
                    sig_ref = f"{phase_prefix}csm_action_{aid}_{counter}"
                    w.writerow(
                        [
                            sig_ref,
                            aid,
                            ca.get("date", "2026-02-01"),
                            "csm_action",
                            f'{ca["action"]} → {ca["outcome"]}',
                            "positive",
                            0.8,
                            arc,
                            "intervention",
                            "",
                            sig_ref,
                        ]
                    )

        return out.getvalue()

    def generate_outcomes_csv(self) -> str:
        out = io.StringIO()
        w = csv.writer(out)
        w.writerow(
            [
                "source_account_id",
                "outcome_date",
                "outcome_type",
                "title",
                "description",
                "revenue_impact",
                "status",
                "linked_signal_id",
            ]
        )

        phase_prefix = f"{self.phase}_" if self.phase else ""
        counter = 0
        for idx, acct in enumerate(self.accounts):
            aid = self._account_id(idx)
            cls = acct.get("classification", "healthy")
            arr = acct["arr"]

            if cls == "critical":
                outcomes = [
                    (
                        "revenue_at_risk",
                        f'Churn risk — {acct["name"]}',
                        f"Account showing signs of churn. ARR at risk: ${arr:,.0f}",
                        -arr * 0.5,
                        "open",
                    ),
                    (
                        "engagement_decline",
                        f'Engagement decline — {acct["name"]}',
                        "Stakeholder engagement dropped significantly",
                        -arr * 0.1,
                        "in_progress",
                    ),
                ]
            elif cls == "at_risk":
                outcomes = [
                    (
                        "renewal_risk",
                        f'Renewal uncertainty — {acct["name"]}',
                        "Renewal discussion stalled or delayed",
                        -arr * 0.2,
                        "in_progress",
                    ),
                ]
            else:
                outcomes = [
                    (
                        "expansion_opportunity",
                        f'Expansion potential — {acct["name"]}',
                        "Account showing expansion signals",
                        arr * 0.15,
                        "open",
                    ),
                ]

            for otype, title, desc, impact, status in outcomes:
                counter += 1
                outcome_date = (self.end_date - timedelta(days=random.randint(0, 60))).strftime("%Y-%m-%d")
                w.writerow(
                    [
                        aid,
                        outcome_date,
                        otype,
                        title,
                        desc,
                        round(impact, 2),
                        status,
                        f"{phase_prefix}sig_{aid}_1",
                    ]
                )

            intervention = acct.get("intervention", {})
            if self.phase == "intervention" and intervention.get("revenue_outcome"):
                ro = intervention["revenue_outcome"]
                counter += 1
                w.writerow(
                    [
                        aid,
                        self.end_date.strftime("%Y-%m-%d"),
                        ro["type"],
                        f'{ro["type"].replace("_", " ").title()} — {acct["name"]}',
                        ro.get("description", ""),
                        round(ro["amount"], 2),
                        "resolved",
                        f"{phase_prefix}sig_{aid}_1",
                    ]
                )

        return out.getvalue()

    def generate_decisions_csv(self) -> str:
        out = io.StringIO()
        w = csv.writer(out)
        w.writerow(
            [
                "source_account_id",
                "decision_date",
                "decision_id",
                "title",
                "decision_maker_role",
                "chosen_option",
                "outcome_description",
                "risk_level",
                "revenue_impact",
            ]
        )

        phase_prefix = f"{self.phase}_" if self.phase else ""

        decision_templates = {
            "critical": [
                ("Escalation to executive sponsor", "executive_sponsor", "Escalate account risk", "Risk review initiated", "high"),
                ("Emergency retention plan", "champion", "Launch retention playbook", "Retention plan in progress", "critical"),
            ],
            "at_risk": [
                ("Renewal strategy review", "executive_sponsor", "Adjust contract terms", "Renewal discussion underway", "medium"),
                ("Feature adoption push", "champion", "Schedule training sessions", "Training plan approved", "medium"),
            ],
            "healthy": [
                ("Expansion discussion", "champion", "Propose upsell package", "Expansion opportunity identified", "low"),
            ],
        }

        for idx, acct in enumerate(self.accounts):
            aid = self._account_id(idx)
            cls = acct.get("classification", "healthy")
            arr = acct["arr"]
            templates = decision_templates.get(cls, decision_templates["healthy"])

            for di, (title, role, chosen, outcome_desc, risk) in enumerate(templates):
                decision_date = (self.end_date - timedelta(days=random.randint(10, 45))).strftime("%Y-%m-%d")
                rev_impact = -arr * 0.1 if cls == "critical" else (-arr * 0.05 if cls == "at_risk" else arr * 0.1)
                w.writerow(
                    [
                        aid,
                        decision_date,
                        f"{phase_prefix}dec_{aid}_{di+1}",
                        f"{title} — {acct['name']}",
                        role,
                        chosen,
                        outcome_desc,
                        risk,
                        round(rev_impact, 2),
                    ]
                )

            intervention = acct.get("intervention", {})
            if self.phase == "intervention" and intervention.get("decisions"):
                for di, dec in enumerate(intervention["decisions"]):
                    w.writerow(
                        [
                            aid,
                            dec["date"],
                            f"int_dec_{aid}_{di+1}",
                            dec["title"],
                            dec.get("decision_maker", "executive_sponsor"),
                            dec.get("rationale", ""),
                            f'Intervention: {dec["title"]}',
                            dec.get("impact", "high"),
                            round(arr * 0.1, 2),
                        ]
                    )

        return out.getvalue()

    def generate_signal_edges_csv(self) -> str:
        out = io.StringIO()
        w = csv.writer(out)
        w.writerow(
            [
                "source_account_id",
                "from_signal_ref",
                "to_signal_ref",
                "edge_type",
                "label",
                "confidence",
                "lag_days",
            ]
        )

        for idx, acct in enumerate(self.accounts):
            aid = self._account_id(idx)
            cls = acct.get("classification", "healthy")

            if cls == "critical":
                edges = [
                    (f"sig_{aid}_1", f"decision:dec_{aid}_1", "TRIGGERED", "Signal triggered escalation", 0.9, 7),
                    (f"decision:dec_{aid}_1", "outcome:revenue_at_risk", "LED_TO", "Escalation revealed risk", 0.85, 14),
                    (f"sig_{aid}_1", f"decision:dec_{aid}_2", "TRIGGERED", "Signal triggered retention plan", 0.85, 10),
                    (f"decision:dec_{aid}_2", "outcome:engagement_decline", "LED_TO", "Retention plan in response to decline", 0.8, 21),
                ]
            elif cls == "at_risk":
                edges = [
                    (f"sig_{aid}_1", f"decision:dec_{aid}_1", "TRIGGERED", "Signal triggered renewal review", 0.8, 14),
                    (f"decision:dec_{aid}_1", "outcome:renewal_risk", "LED_TO", "Review surfaced renewal risk", 0.75, 21),
                ]
            else:
                edges = [
                    (f"sig_{aid}_1", f"decision:dec_{aid}_1", "TRIGGERED", "Positive signal prompted expansion", 0.85, 7),
                    (f"decision:dec_{aid}_1", "outcome:expansion_opportunity", "LED_TO", "Discussion identified expansion", 0.8, 14),
                ]

            for from_ref, to_ref, etype, label, conf, lag in edges:
                w.writerow([aid, from_ref, to_ref, etype, label, conf, lag])

            intervention = acct.get("intervention", {})
            if self.phase == "intervention" and intervention.get("decisions"):
                n_decisions = len(intervention["decisions"])
                n_recovery = len(intervention.get("recovery_signals", []))

                for di in range(min(n_decisions, n_recovery)):
                    w.writerow(
                        [
                            aid,
                            f"decision:int_dec_{aid}_{di+1}",
                            f"intervention_recovery_{aid}_{di+100}",
                            "LED_TO",
                            f'Intervention: {intervention["decisions"][di]["title"]}',
                            0.9,
                            14,
                        ]
                    )

                if intervention.get("revenue_outcome"):
                    amt = intervention["revenue_outcome"]["amount"]
                    w.writerow(
                        [
                            aid,
                            f"decision:int_dec_{aid}_{n_decisions}",
                            "outcome:revenue_protected",
                            "LED_TO",
                            f"Intervention protected ${amt/1e6:.1f}M ARR",
                            0.95,
                            30,
                        ]
                    )

        return out.getvalue()

    def get_upload_file_map(self) -> Dict[str, str]:
        return {
            "accounts": self._header_use_account_id(self.generate_accounts_csv()),
            "kpi_measurements": self._header_use_account_id(self.generate_kpi_measurements_csv()),
            "enhanced_signals": self._header_use_account_id(self.generate_signals_csv()),
            "products": self._header_use_account_id(self.generate_products_csv()),
            "stakeholders": self._header_use_account_id(self.generate_stakeholders_csv()),
            "engagement_events": self._header_use_account_id(self.generate_engagement_events_csv()),
            "account_business_profiles": self._header_use_account_id(self.generate_profiles_csv()),
            "outcomes": self._header_use_account_id(self.generate_outcomes_csv()),
            "decisions": self._header_use_account_id(self.generate_decisions_csv()),
            "signal_edges": self._header_use_account_id(self.generate_signal_edges_csv()),
        }
