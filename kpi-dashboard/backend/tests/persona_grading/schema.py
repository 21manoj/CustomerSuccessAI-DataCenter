"""Data classes for persona-grading framework."""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Optional


@dataclass
class PersonaQuestion:
    """One canonical question a persona would ask the product.

    Used both as input (the question to send to Ask AI) and as a rubric
    (what the grader checks for in the response).
    """
    id: str                          # Unique within persona, e.g. 'cro-q01-revenue-at-risk'
    persona: str                     # 'cro' | 'cfo' | 'ceo' | 'vpcs' | 'csm'
    question: str                    # Natural-language question
    intent: str                      # One-sentence summary of what this probes
    must_cite: list[str] = field(default_factory=list)
    """Facts the response MUST contain. Examples:
        'specific dollar amount', 'specific account name', 'context graph evidence'
    Each entry is judged true/false by the LLM grader.
    """
    must_call_tools: list[str] = field(default_factory=list)
    """Ask AI tools the response should invoke. Names from ask_ai_tools.py.
    A subset is acceptable — grader checks 'at least N of these were called'.
    """
    must_call_at_least: int = 1
    """Minimum number of must_call_tools that must actually have been invoked."""
    tone_check: str = ''
    """One-sentence stylistic requirement, e.g. 'leads with $ amounts not %'."""
    anti_hallucination: list[str] = field(default_factory=list)
    """Things the response must NOT do. Examples:
        'no invented account names', 'no fabricated numbers', 'no guessed account_ids'
    """
    weight: float = 1.0
    """Relative weight of this question in the persona's average."""


@dataclass
class GradeResult:
    """Output of grading one (question, response) pair."""
    question_id: str
    persona: str
    grade: str                       # 'A'|'A-'|'B+'|'B'|'B-'|'C+'|'C'|'C-'|'D+'|'D'|'F'
    grade_numeric: float             # 4.0 (A) → 0.0 (F)
    rationale: str
    must_cite_check: dict[str, bool] = field(default_factory=dict)
    must_call_tools_check: dict[str, bool] = field(default_factory=dict)
    tone_pass: bool = True
    anti_hallucination_pass: bool = True
    specific_concerns: list[str] = field(default_factory=list)
    raw_response: str = ''
    raw_tool_calls: list[str] = field(default_factory=list)
    grader_model: str = ''
    weight: float = 1.0

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class PersonaReport:
    """Aggregated grades for one persona across all its questions."""
    persona: str
    n_questions: int
    grades: list[GradeResult]
    avg_grade_numeric: float
    avg_grade_letter: str
    customer_id: int
    timestamp_utc: str

    def to_dict(self) -> dict:
        return {
            'persona': self.persona,
            'n_questions': self.n_questions,
            'avg_grade_numeric': round(self.avg_grade_numeric, 2),
            'avg_grade_letter': self.avg_grade_letter,
            'customer_id': self.customer_id,
            'timestamp_utc': self.timestamp_utc,
            'grades': [g.to_dict() for g in self.grades],
        }


# Letter ↔ numeric (4.0 scale)
LETTER_TO_NUMERIC: dict[str, float] = {
    'A':  4.0, 'A-': 3.7,
    'B+': 3.3, 'B':  3.0, 'B-': 2.7,
    'C+': 2.3, 'C':  2.0, 'C-': 1.7,
    'D+': 1.3, 'D':  1.0,
    'F':  0.0,
}


def numeric_to_letter(val: float) -> str:
    """Inverse of LETTER_TO_NUMERIC, rounded to nearest letter."""
    closest = min(LETTER_TO_NUMERIC.items(), key=lambda kv: abs(kv[1] - val))
    return closest[0]
