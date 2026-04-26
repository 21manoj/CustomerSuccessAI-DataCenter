# Persona Grading Framework

Internal evaluation tool. Grades CS Pulse's Ask AI responses against persona-specific rubrics using LLM-as-judge. Mirrors the methodology of the Apr 14-15 (Session 8) audit so results are comparable over time.

## What it measures

For each of 5 personas (CRO, CFO, CEO, VP CS, CSM), grades the AI's response to a curated set of canonical questions that persona would ask. Each question has an explicit rubric:

- **must_cite** — facts the response must contain (e.g., "specific dollar amount", "specific account name")
- **must_call_tools** — Ask AI tools that should have been invoked
- **tone_check** — stylistic requirement (e.g., "leads with $ first")
- **anti_hallucination** — things the response must NOT do (e.g., "no fabricated account_ids")

The grader is a Claude Sonnet call role-playing as a 15-year-experienced version of the persona (5-yr for CSM). It returns a letter grade A–F with rationale.

## How to run

```bash
# Inside the cspulse-platform container (where TOOL_DEFINITIONS, execute_tool, etc. are importable):

DATABASE_URL=postgresql://.../cs_pulse \
ANTHROPIC_API_KEY=sk-ant-... \
python3 -m tests.persona_grading.runner \
  --customer 331 \
  --output /app/scripts/datasets/persona_grades_$(date +%Y%m%d).json
```

Or via pytest (opt-in):

```bash
PERSONA_GRADING_ENABLED=1 \
PERSONA_GRADING_CUSTOMER_ID=331 \
ANTHROPIC_API_KEY=sk-ant-... \
python3 -m pytest tests/persona_grading/ -v
```

## Cost

~$0.10-0.15 per question (1 Ask-AI tool-use loop + 1 grader call). 30 questions ≈ $3-5. Default model: `claude-sonnet-4-20250514`. Override via `--model`.

## Output schema

```json
{
  "framework_version": "v1.0",
  "run_at_utc": "2026-04-25T22:30:00Z",
  "customer_id": 331,
  "methodology": "LLM-as-judge with persona role-play...",
  "grader_model": "claude-sonnet-4-20250514",
  "personas": {
    "cro": {
      "persona": "cro",
      "n_questions": 6,
      "avg_grade_numeric": 3.4,
      "avg_grade_letter": "A-",
      "grades": [ { question_id, grade, rationale, must_cite_check, ... } ]
    },
    "cfo": { ... },
    ...
  },
  "summary": {
    "cro": { "avg_grade": "A-", "avg_numeric": 3.4, "n_questions": 6 },
    ...
  }
}
```

## Comparing across runs

The point of this framework is to track persona-quality progress over time:

| Date | Source | CRO | CFO | CEO | VP CS | CSM |
|---|---|---|---|---|---|---|
| Apr 14-15 (Session 8 audit) | UI | B+ | B+ | n/a | C+ | B |
| Apr 14-15 (Session 8 audit) | Claude.ai | A | A | n/a | A | A |
| Apr 25 (this framework, run 1) | TBD | TBD | TBD | TBD | TBD | TBD |

Re-run after each release that touches Ask AI prompts, tools, or persona-relevant data paths.

## Known gaps the framework reveals

- **No 'csm' entry in `PERSONA_PROMPTS`** today. CSM questions fall back to 'vpcs' persona prompt at runtime. Adding a dedicated CSM persona prompt is a future enhancement; the framework will surface this in CSM-question grades being lower than expected.
- **No 'ceo' grade in Apr 14-15 audit** to compare against. CEO is graded for the first time today.
- **"UI grade" not available in this framework yet** — the Apr 14-15 audit produced both UI-grade (browse the dashboard) and Claude.ai-grade (Ask AI response). This framework only does the latter. UI grading via Claude-in-Chrome browser automation is a future enhancement.

## Files

- `schema.py` — `PersonaQuestion`, `GradeResult`, `PersonaReport` dataclasses
- `fixtures/` — one file per persona with canonical questions + rubrics
- `grader.py` — LLM-as-judge implementation with persona role-play
- `runner.py` — orchestrates question → tool-use loop → grade
- `test_persona_grading.py` — opt-in pytest entry
