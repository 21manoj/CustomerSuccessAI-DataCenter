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
from statistics import mean
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
            logger.error("ask-ai API call failed for %s: %s", question.id, e)
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


def run_one_persona(
    persona: str,
    customer_id: int,
    *,
    anthropic_client=None,
    model: str = "claude-sonnet-4-20250514",
    sleep_between_questions: float = 1.0,
) -> PersonaReport:
    """Run all questions for one persona, return aggregated report."""
    if anthropic_client is None:
        import anthropic
        anthropic_client = anthropic.Anthropic()

    questions = BY_PERSONA.get(persona, [])
    if not questions:
        raise ValueError(f"No fixtures for persona: {persona}")

    grades: list[GradeResult] = []
    total_weight = 0.0
    weighted_sum = 0.0
    for i, q in enumerate(questions, 1):
        logger.info("[%s] %d/%d: %s", persona, i, len(questions), q.id)
        # 1. Run Ask AI to produce response
        response_text, tools_called = _run_ask_ai_for_question(
            q, customer_id, anthropic_client=anthropic_client, model=model)
        # 2. Grade the response
        grade = grade_response(
            q, response_text, tools_called,
            anthropic_client=anthropic_client, model=model,
        )
        grades.append(grade)
        total_weight += q.weight
        weighted_sum += grade.grade_numeric * q.weight
        # Polite pacing
        if i < len(questions) and sleep_between_questions > 0:
            time.sleep(sleep_between_questions)

    avg = (weighted_sum / total_weight) if total_weight > 0 else 0.0
    return PersonaReport(
        persona=persona,
        n_questions=len(grades),
        grades=grades,
        avg_grade_numeric=avg,
        avg_grade_letter=numeric_to_letter(avg),
        customer_id=customer_id,
        timestamp_utc=datetime.now(timezone.utc).isoformat(),
    )


def run_all_personas(
    customer_id: int,
    *,
    output_path: Optional[Path] = None,
    personas: Optional[list[str]] = None,
) -> dict:
    """Run all 5 personas, write JSON, return the aggregated report."""
    import anthropic
    client = anthropic.Anthropic()
    personas = personas or list(BY_PERSONA.keys())

    reports: dict[str, dict] = {}
    for p in personas:
        try:
            report = run_one_persona(p, customer_id, anthropic_client=client)
            reports[p] = report.to_dict()
            logger.info("[%s] avg %s (%.2f) over %d questions",
                        p, report.avg_grade_letter, report.avg_grade_numeric, report.n_questions)
        except Exception as e:
            logger.error("Failed to grade persona %s: %s", p, e)
            reports[p] = {"error": str(e)}

    payload = {
        "framework_version": "v1.0",
        "run_at_utc": datetime.now(timezone.utc).isoformat(),
        "customer_id": customer_id,
        "methodology": (
            "LLM-as-judge with persona role-play (15-yr veteran for senior "
            "personas, 5-yr for CSM). Same approach as the Apr 14-15 audit."
        ),
        "grader_model": "claude-sonnet-4-20250514",
        "personas": reports,
        "summary": {
            p: {
                "avg_grade": (r.get('avg_grade_letter') if isinstance(r, dict) else None),
                "avg_numeric": (r.get('avg_grade_numeric') if isinstance(r, dict) else None),
                "n_questions": (r.get('n_questions') if isinstance(r, dict) else None),
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
        "--output",
        type=Path,
        default=Path("/app/scripts/datasets/persona_grades_latest.json"),
        help="Output JSON path",
    )
    args = ap.parse_args()

    personas = args.personas.split(",") if args.personas else None
    # Need Flask app context for the imported helpers
    import sys
    sys.path.insert(0, "/app/backend")
    from app_v3_minimal import app
    with app.app_context():
        run_all_personas(args.customer, output_path=args.output, personas=personas)
