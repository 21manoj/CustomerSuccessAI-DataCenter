"""LLM-as-judge grader for persona-grading framework.

Mirrors the Apr 14-15 audit methodology: an LLM is asked to role-play as a
15-year-experienced persona and grade the AI assistant's response. Same model
class (Claude Sonnet) used in the original audit.
"""
from __future__ import annotations

import json
import logging
import os
from dataclasses import asdict
from typing import Optional

from .schema import GradeResult, PersonaQuestion, LETTER_TO_NUMERIC

logger = logging.getLogger(__name__)


# Persona role descriptions for the grader's "you are..." framing.
# Mirrors the Session 8 (Apr 14-15) audit prompt pattern.
GRADER_PERSONA_ROLES: dict[str, str] = {
    'cro': (
        "a 15-year-experienced Chief Revenue Officer who has run customer "
        "success and revenue functions at multiple SaaS companies. You think "
        "in dollars first, percentages second. You expect specific account "
        "names, traceable evidence, and honest forecasting."
    ),
    'cfo': (
        "a 15-year-experienced Chief Financial Officer with a finance "
        "background covering CS investment ROI, payback analysis, and budget "
        "allocation. You expect numerator/denominator transparency, comparison "
        "to projections, and industry-benchmark calibration."
    ),
    'ceo': (
        "a 15-year-experienced Chief Executive Officer who synthesizes across "
        "the entire portfolio for board-level communication. You expect tight "
        "summaries (top 2-3 things), strategic framing rather than tactical "
        "lists, and honesty about both upside and risk."
    ),
    'vpcs': (
        "a 15-year-experienced Vice President of Customer Success focused on "
        "operational excellence, CSM productivity, and playbook governance. "
        "You expect operational tone (names, numbers, specific actions), "
        "willingness to retire failing playbooks, and gap detection."
    ),
    'csm': (
        "a 5-year-experienced Customer Success Manager — frontline operator "
        "who needs to know what to do today on which accounts. You expect "
        "specific actions, traceable to your assigned accounts, with "
        "$-impact or urgency rationale."
    ),
}


GRADER_SYSTEM_PROMPT = """You are role-playing as {persona_role}.

You are reviewing the response of a customer success AI assistant to a question
you (or a colleague in your role) asked. Your job is to grade the response
against an explicit rubric.

GRADING SCALE:
  A   excellent — meets all criteria, would deploy as-is
  A-  very good — minor polish needed
  B+  good — solid but missing 1 small item
  B   acceptable — missing 1-2 medium items
  B-  marginal — usable but with caveats
  C+  weak — multiple gaps
  C   poor — substantial gaps
  C-  failing — would not use
  D+  bad — fabricated or misleading content present
  D   very bad — substantively wrong
  F   unusable — major hallucination, wrong answer, dangerous to act on

Be honest. Avoid grade inflation. A 15-yr veteran in your role would not give
an A to a response that's merely "fine". Reserve A for responses that would
make you confident handing them to your board / your CSM team / your CFO.

OUTPUT FORMAT (strict JSON, no markdown):
{{
  "grade": "A" | "A-" | "B+" | "B" | "B-" | "C+" | "C" | "C-" | "D+" | "D" | "F",
  "rationale": "2-3 sentence explanation, persona-grounded",
  "must_cite_check": {{ "<criterion>": true|false, ... }},
  "must_call_tools_check": {{ "<tool_name>": true|false, ... }},
  "tone_pass": true|false,
  "anti_hallucination_pass": true|false,
  "specific_concerns": ["concern 1", "concern 2", ...]
}}
"""


GRADER_USER_PROMPT = """QUESTION YOU ASKED:
{question}

WHAT THIS QUESTION PROBES:
{intent}

RUBRIC:

Must cite (each is true/false based on whether it appears in the response):
{must_cite_block}

Must call at least {must_call_at_least} of these tools:
{must_call_tools_block}
Tools actually called: {tools_called}

Tone check: {tone_check}

Anti-hallucination — the response must NOT do any of these:
{anti_hallucination_block}

────────────────────────────────────────────────────
ACTUAL RESPONSE FROM THE AI ASSISTANT:

{response_text}
────────────────────────────────────────────────────

Grade this response. Return ONLY the JSON object specified in the system prompt.
"""


def _format_block(items: list[str]) -> str:
    if not items:
        return "  (none)"
    return "\n".join(f"  - {item}" for item in items)


def grade_response(
    question: PersonaQuestion,
    response_text: str,
    tools_called: list[str],
    *,
    anthropic_client=None,
    model: str = "claude-sonnet-4-6",
) -> GradeResult:
    """Run the LLM-as-judge for one (question, response) pair.

    Returns a GradeResult. Network call to Anthropic API; expect ~$0.02-0.05
    per call at Sonnet rates.
    """
    if anthropic_client is None:
        import anthropic
        anthropic_client = anthropic.Anthropic()

    persona_role = GRADER_PERSONA_ROLES.get(
        question.persona, GRADER_PERSONA_ROLES['cro']
    )
    system = GRADER_SYSTEM_PROMPT.format(persona_role=persona_role)

    user = GRADER_USER_PROMPT.format(
        question=question.question,
        intent=question.intent,
        must_cite_block=_format_block(question.must_cite),
        must_call_tools_block=_format_block(question.must_call_tools),
        must_call_at_least=question.must_call_at_least,
        tools_called=", ".join(tools_called) if tools_called else "(none)",
        tone_check=question.tone_check or "(none specified)",
        anti_hallucination_block=_format_block(question.anti_hallucination),
        response_text=response_text or "(empty response)",
    )

    try:
        msg = anthropic_client.messages.create(
            model=model,
            max_tokens=1500,
            temperature=0.0,  # Deterministic grading
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        text = msg.content[0].text if msg.content else ""
    except Exception as e:
        logger.error("grader API call failed for %s: %s", question.id, e)
        return GradeResult(
            question_id=question.id,
            persona=question.persona,
            grade="F",
            grade_numeric=0.0,
            rationale=f"Grader API error: {e}",
            specific_concerns=[f"Could not grade due to API error: {e}"],
            raw_response=response_text,
            raw_tool_calls=tools_called,
            grader_model=model,
            weight=question.weight,
        )

    # Parse JSON output (strip markdown fence if model added one)
    text_clean = text.strip()
    if text_clean.startswith("```"):
        text_clean = text_clean.split("\n", 1)[1] if "\n" in text_clean else text_clean
        if text_clean.rstrip().endswith("```"):
            text_clean = text_clean.rstrip()[:-3]

    try:
        parsed = json.loads(text_clean)
    except json.JSONDecodeError as e:
        logger.error("grader JSON parse failed for %s: %s\n%s", question.id, e, text[:500])
        return GradeResult(
            question_id=question.id,
            persona=question.persona,
            grade="F",
            grade_numeric=0.0,
            rationale=f"Grader returned non-JSON output: {text[:200]}",
            specific_concerns=["Grader output not parseable"],
            raw_response=response_text,
            raw_tool_calls=tools_called,
            grader_model=model,
            weight=question.weight,
        )

    grade_letter = parsed.get("grade", "F")
    grade_numeric = LETTER_TO_NUMERIC.get(grade_letter, 0.0)

    return GradeResult(
        question_id=question.id,
        persona=question.persona,
        grade=grade_letter,
        grade_numeric=grade_numeric,
        rationale=parsed.get("rationale", ""),
        must_cite_check=parsed.get("must_cite_check", {}),
        must_call_tools_check=parsed.get("must_call_tools_check", {}),
        tone_pass=bool(parsed.get("tone_pass", False)),
        anti_hallucination_pass=bool(parsed.get("anti_hallucination_pass", False)),
        specific_concerns=parsed.get("specific_concerns", []),
        raw_response=response_text,
        raw_tool_calls=tools_called,
        grader_model=model,
        weight=question.weight,
    )
