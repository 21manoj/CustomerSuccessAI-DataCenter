"""Orchestrates persona-grading: question → Ask AI tool-use loop → grade.

Replicates the ask_ai_endpoint tool-use loop locally so we don't need HTTP
auth. Uses the same TOOL_DEFINITIONS, executor, and persona system prompts
as the production endpoint.
"""
from __future__ import annotations

import json
import logging
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean, pstdev
from typing import Optional

from .schema import (
    GradeResult, PersonaQuestion, PersonaReport,
    LETTER_TO_NUMERIC, numeric_to_letter,
)
from .grader import grade_response
from .fixtures import BY_PERSONA

logger = logging.getLogger(__name__)


def _run_ask_ai_for_question(
    question: PersonaQuestion,
    customer_id: int,
    *,
    anthropic_client,
    model: str = "claude-sonnet-4-20250514",
    max_rounds: int = 5,
) -> tuple[str, list[str]]:
    """Run the Ask AI tool-use loop for one question.

    Returns (final_response_text, list_of_tools_called).
    """
    # Imports happen here so the test framework can be loaded without the
    # production app context — but the runner needs them at runtime.
    from ask_ai_endpoint import _build_system_prompt, _build_portfolio_summary, PERSONA_PROMPTS
    from ask_ai_tools import TOOL_DEFINITIONS, execute_tool

    persona = question.persona
    # 'csm' is not yet in PERSONA_PROMPTS (Apr 25 2026); fall back to 'vpcs'.
    # The framework reveals this gap in its output report.
    if persona not in PERSONA_PROMPTS:
        persona = 'vpcs'

    portfolio_summary = _build_portfolio_summary(customer_id)
    system_prompt = _build_system_prompt(persona, portfolio_summary)

    messages = [{"role": "user", "content": question.question}]
    tools_called: list[str] = []
    final_text_parts: list[str] = []

    for _ in range(max_rounds):
        try:
            response = anthropic_client.messages.create(
                model=model,
                system=system_prompt,
                messages=messages,
                tools=TOOL_DEFINITIONS,
                # Sprint 1.1 (Apr 25 2026): bumped 4096→6144 to match the
                # production ask_ai_v2 token budget. Sprint 1 saw multi-tool
                # synthesis questions truncate mid-final-paragraph at 4096.
                max_tokens=6144,
                temperature=0.3,
            )
        except Exception as e:
            err_str = str(e)
            logger.error("ask-ai API call failed for %s: %s", question.id, e)
            # Sprint 1.3 (Apr 26 2026): fail-fast on credit-balance / auth
            # errors. The 3-shot run on Apr 26 burned through 27 questions
            # producing F's after credit ran dry — wasting wall-clock and
            # contaminating the result file. Re-raise so run_one_persona /
            # run_all_personas surface the real error and abort the run.
            fatal_markers = (
                'credit balance is too low',
                'invalid_request_error',
                'authentication_error',
                'invalid x-api-key',
                'rate_limit_exceeded',
            )
            if any(m in err_str.lower() for m in fatal_markers):
                logger.error(
                    "FATAL: account-level error detected — aborting run "
                    "instead of producing junk grades. Resolve and re-run."
                )
                raise RuntimeError(f"Aborting persona-grading run: {err_str[:200]}") from e
            return f"[runner error: {e}]", tools_called

        text_parts: list[str] = []
        tool_use_blocks = []
        for block in response.content:
            if block.type == "text":
                text_parts.append(block.text)
            elif block.type == "tool_use":
                tool_use_blocks.append(block)

        if text_parts:
            final_text_parts.extend(text_parts)

        # If no tool calls this round, we're done
        if not tool_use_blocks:
            break

        # Execute each tool, feed results back as user message
        messages.append({"role": "assistant", "content": response.content})
        tool_results = []
        for tu in tool_use_blocks:
            tools_called.append(tu.name)
            try:
                result = execute_tool(tu.name, tu.input or {}, customer_id)
                # execute_tool returns a dict — serialize for the message
                result_str = json.dumps(result, default=str)[:8000]
            except Exception as e:
                result_str = json.dumps({"error": f"tool execution failed: {e}"})
            tool_results.append({
                "type": "tool_result",
                "tool_use_id": tu.id,
                "content": result_str,
            })
        messages.append({"role": "user", "content": tool_results})

        if response.stop_reason == "end_turn":
            break

    return "\n".join(final_text_parts), tools_called


def _persona_avg_stddev(persona_dict: dict) -> Optional[float]:
    """Average of per-question stddevs across a persona's report.

    Returns None if the report doesn't have shot_stats (single-shot run).
    """
    grades = persona_dict.get('grades') or []
    stddevs = [g.get('shot_stats', {}).get('stddev') for g in grades]
    stddevs = [s for s in stddevs if s is not None]
    if not stddevs:
        return None
    return round(sum(stddevs) / len(stddevs), 3)


def _shots_to_summary_grade(shots: list[GradeResult]) -> GradeResult:
    """Aggregate N shot-level grades into a single summary GradeResult.

    Sprint 1.3 (Apr 26 2026): added multi-shot averaging because single-shot
    grading variance (±0.2 typical, ±3.7 observed on csm-q01 / vpcs-q06)
    was indistinguishable from real prompt-rule effects across Sprints
    1.0/1.1/1.2. Mean of N shots gives a stable signal; stddev surfaces
    instability worth investigating.
    """
    assert shots, "_shots_to_summary_grade requires at least one shot"
    first = shots[0]
    nums = [s.grade_numeric for s in shots]
    avg = mean(nums)
    stddev = pstdev(nums) if len(nums) > 1 else 0.0
    # The "summary" grade keeps the original schema so downstream comparison
    # scripts continue to work unchanged. Two new fields surface the
    # underlying shot detail.
    summary = GradeResult(
        question_id=first.question_id,
        persona=first.persona,
        grade=numeric_to_letter(avg),
        grade_numeric=round(avg, 2),
        rationale=(
            f"[{len(shots)}-shot mean] " + first.rationale
            if len(shots) > 1 else first.rationale
        ),
        must_cite_check=first.must_cite_check,
        must_call_tools_check=first.must_call_tools_check,
        tone_pass=all(s.tone_pass for s in shots),
        anti_hallucination_pass=all(s.anti_hallucination_pass for s in shots),
        specific_concerns=first.specific_concerns,
        raw_response=first.raw_response,
        raw_tool_calls=first.raw_tool_calls,
        grader_model=first.grader_model,
        weight=first.weight,
    )
    # Tack shot-level detail onto the dict via __dict__ so to_dict() picks them
    # up. (asdict() walks dataclass fields only, so attributes added at runtime
    # won't show; instead we wrap to_dict in the persona report aggregator.)
    summary._shots = [
        {
            'shot': i + 1,
            'grade': s.grade,
            'grade_numeric': s.grade_numeric,
            'rationale': s.rationale[:300],
            'tone_pass': s.tone_pass,
            'anti_hallucination_pass': s.anti_hallucination_pass,
        }
        for i, s in enumerate(shots)
    ]
    summary._shot_stats = {
        'n_shots': len(shots),
        'mean': round(avg, 3),
        'stddev': round(stddev, 3),
        'min': min(nums),
        'max': max(nums),
        'range_pp': round(max(nums) - min(nums), 2),
    }
    return summary


def run_one_persona(
    persona: str,
    customer_id: int,
    *,
    anthropic_client=None,
    model: str = "claude-sonnet-4-20250514",
    sleep_between_questions: float = 1.0,
    n_shots: int = 1,
) -> PersonaReport:
    """Run all questions for one persona, return aggregated report.

    Sprint 1.3 (Apr 26 2026): n_shots=1 is the default (back-compat with
    earlier single-shot baselines). n_shots=3 is the recommended setting
    for evaluating prompt changes — single-shot grade variance was high
    enough to mask real effects in Sprints 1.0/1.1/1.2.
    """
    if anthropic_client is None:
        import anthropic
        anthropic_client = anthropic.Anthropic()

    questions = BY_PERSONA.get(persona, [])
    if not questions:
        raise ValueError(f"No fixtures for persona: {persona}")

    summary_grades: list[GradeResult] = []
    total_weight = 0.0
    weighted_sum = 0.0
    for i, q in enumerate(questions, 1):
        logger.info("[%s] %d/%d: %s (n_shots=%d)", persona, i, len(questions), q.id, n_shots)
        shot_grades: list[GradeResult] = []
        for shot in range(1, n_shots + 1):
            if n_shots > 1:
                logger.info("  [shot %d/%d]", shot, n_shots)
            # 1. Run Ask AI to produce response (fresh tool-use loop each shot)
            response_text, tools_called = _run_ask_ai_for_question(
                q, customer_id, anthropic_client=anthropic_client, model=model)
            # 2. Grade the response
            grade = grade_response(
                q, response_text, tools_called,
                anthropic_client=anthropic_client, model=model,
            )
            shot_grades.append(grade)
            if n_shots > 1:
                logger.info("    shot %d grade: %s (%.1f)", shot, grade.grade, grade.grade_numeric)
            # Pace between shots within a question too
            if shot < n_shots and sleep_between_questions > 0:
                time.sleep(sleep_between_questions / 2)

        # Aggregate N shots into one summary grade for downstream consumers
        summary = _shots_to_summary_grade(shot_grades)
        summary_grades.append(summary)
        total_weight += q.weight
        weighted_sum += summary.grade_numeric * q.weight
        if n_shots > 1:
            stats = summary._shot_stats
            logger.info(
                "  → mean %s (%.2f), stddev %.2f, range %.1f pp",
                summary.grade, stats['mean'], stats['stddev'], stats['range_pp'],
            )
        # Polite pacing between questions
        if i < len(questions) and sleep_between_questions > 0:
            time.sleep(sleep_between_questions)

    avg = (weighted_sum / total_weight) if total_weight > 0 else 0.0
    return PersonaReport(
        persona=persona,
        n_questions=len(summary_grades),
        grades=summary_grades,
        avg_grade_numeric=avg,
        avg_grade_letter=numeric_to_letter(avg),
        customer_id=customer_id,
        timestamp_utc=datetime.now(timezone.utc).isoformat(),
    )


def _report_to_dict_with_shots(report: PersonaReport) -> dict:
    """Like report.to_dict() but enriches each grade with _shots / _shot_stats."""
    out = report.to_dict()
    enriched_grades = []
    for g, summary in zip(out['grades'], report.grades):
        if hasattr(summary, '_shots'):
            g['shots'] = summary._shots
            g['shot_stats'] = summary._shot_stats
        enriched_grades.append(g)
    out['grades'] = enriched_grades
    return out


def run_all_personas(
    customer_id: int,
    *,
    output_path: Optional[Path] = None,
    personas: Optional[list[str]] = None,
    n_shots: int = 1,
) -> dict:
    """Run all 5 personas, write JSON, return the aggregated report.

    n_shots=1 (default) reproduces the original single-shot behavior.
    n_shots=3 enables multi-shot averaging (Sprint 1.3, Apr 26 2026) —
    recommended for any prompt-rule evaluation since single-shot variance
    can be ±3.7 grade-pts per question (csm-q01 in Sprint 1.2).
    """
    import anthropic
    client = anthropic.Anthropic()
    personas = personas or list(BY_PERSONA.keys())

    reports: dict[str, dict] = {}
    for p in personas:
        try:
            report = run_one_persona(p, customer_id, anthropic_client=client, n_shots=n_shots)
            reports[p] = _report_to_dict_with_shots(report)
            logger.info("[%s] avg %s (%.2f) over %d questions (n_shots=%d)",
                        p, report.avg_grade_letter, report.avg_grade_numeric,
                        report.n_questions, n_shots)
        except RuntimeError as e:
            # Sprint 1.3 (Apr 26 2026): _run_ask_ai_for_question raises
            # RuntimeError for fatal account-level errors (credit balance,
            # auth, rate limit). Don't continue to other personas — surface
            # the real error and abort cleanly.
            logger.error("ABORTING RUN: fatal error on persona %s — %s", p, e)
            raise
        except Exception as e:
            logger.error("Failed to grade persona %s: %s", p, e)
            reports[p] = {"error": str(e)}

    payload = {
        "framework_version": "v1.1" if n_shots > 1 else "v1.0",
        "n_shots_per_question": n_shots,
        "run_at_utc": datetime.now(timezone.utc).isoformat(),
        "customer_id": customer_id,
        "methodology": (
            "LLM-as-judge with persona role-play (15-yr veteran for senior "
            "personas, 5-yr for CSM). Same approach as the Apr 14-15 audit. "
            f"Each question graded {n_shots}× with mean reported as headline."
        ),
        "grader_model": "claude-sonnet-4-20250514",
        "personas": reports,
        "summary": {
            p: {
                "avg_grade": (r.get('avg_grade_letter') if isinstance(r, dict) else None),
                "avg_numeric": (r.get('avg_grade_numeric') if isinstance(r, dict) else None),
                "n_questions": (r.get('n_questions') if isinstance(r, dict) else None),
                "n_shots": n_shots,
                # Per-persona stddev across all questions: how noisy is this
                # persona's grading right now? High stddev → run more shots.
                "avg_question_stddev": _persona_avg_stddev(r) if isinstance(r, dict) else None,
            } for p, r in reports.items()
        },
    }

    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(payload, indent=2, default=str))
        logger.info("wrote %s", output_path)

    return payload


# CLI entry point: `python -m tests.persona_grading.runner --customer 331`
if __name__ == "__main__":
    import argparse
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    ap = argparse.ArgumentParser()
    ap.add_argument("--customer", type=int, required=True, help="Customer ID")
    ap.add_argument("--personas", help="Comma-separated subset (default: all 5)")
    ap.add_argument(
        "--shots", type=int, default=1,
        help="Run each question N times and report the mean grade. "
             "Default 1 (single-shot, fast). Recommend 3 for prompt-rule "
             "evaluation — single-shot variance can be ±3.7 grade-pts.",
    )
    ap.add_argument(
        "--output",
        type=Path,
        default=Path("/app/scripts/datasets/persona_grades_latest.json"),
        help="Output JSON path",
    )
    args = ap.parse_args()

    personas = args.personas.split(",") if args.personas else None
    # Need Flask app context for the imported helpers
    import sys
    from pathlib import Path as _Path
    _backend = _Path(__file__).resolve().parents[2]
    for _p in (str(_backend), "/app/backend"):
        if _p not in sys.path:
            sys.path.insert(0, _p)
    from app_v3_minimal import app
    with app.app_context():
        run_all_personas(
            args.customer,
            output_path=args.output,
            personas=personas,
            n_shots=args.shots,
        )
