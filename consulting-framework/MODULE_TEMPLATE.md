# Module Spec Template

Copy this structure for every new module. Delete this comment block once filled in.

---

## `NN` — Module Name

**Layer:** Foundation | Intelligence | Interface | Ops

### Purpose
One paragraph: what this module is for, in business terms, not implementation terms.

### Boundary
Explicit list of what this module **owns** and what it **explicitly does not own**
(with a pointer to which other module owns the excluded thing). Scope-creep between
modules is the main way a "modular" library stops being modular — be strict here.

### Dependencies
What must already exist (which other modules, in what state) before this one can be
built. State the actual interface/contract expected from each dependency, not just
its name.

### Engine vs. Config
Two lists:
- **Engine** (build once, an FDE should rarely edit): the logic, algorithms, data
  contracts.
- **Config** (an FDE fills in per client): the parameters, catalogs, thresholds,
  overrides.

### Build Prompt
The literal text an FDE pastes to a coding agent to scaffold this module for a new
client. Written as a self-contained prompt — assume the agent has the codebase but
no memory of this conversation. Reference real file paths from the origin system
where the agent should look for patterns to follow, not reinvent. Prefer literal
pseudocode over prose for any formula, normalization, or edge-case-heavy logic —
prose reads as unambiguous to the author and ambiguous to everyone else; pseudocode
forces the ambiguity into the open while writing it.

**Every section pair must be cross-checked against the Build Prompt, not just
Gotchas.** A Gotcha, an Acceptance Criterion, or a Data Shapes entry that exists
specifically to correct or add something the Build Prompt itself omits or says
wrong is a bug in the spec — fix the Build Prompt directly instead of leaving the
correction to live only in the other section. Two confirmed instances so far:
- Module 03 pilot: the Build Prompt told an agent to gate a weight-override check
  on a condition that Gotcha 4, two sections later, named as the exact
  anti-pattern to avoid.
- Module 01: the Build Prompt's literal access-control code omitted an expiry
  check required by both Acceptance Criteria and a Gotcha's own "Fix" text —
  proven to be a real access-control bypass, not a theoretical gap. Separately,
  the same module's Build Prompt required a `uuid` column on an entity that Data
  Shapes didn't list, while also instructing the reader to "match Data Shapes
  exactly" — a second, independent contradiction in the same document.

An agent that only reads the Build Prompt — which is the whole point of a Build
Prompt being self-contained — will reproduce whatever bug or gap the other
sections were trying to prevent. When authoring or reviewing a module, re-read
the Build Prompt against every other section (Gotchas, Acceptance Criteria, Data
Shapes) and ask: if an agent followed this prompt literally and nothing else,
would it walk straight into a problem a later section warns about, or contradict
a requirement a later section states?

**A second, subtler shape of the same failure: unspecified pseudocode, not
just contradictory pseudocode.** Module 02 rewrote its Build Prompt carefully
enough to avoid textually contradicting its own Gotchas (the Module 01/03
shape) — and a Gotcha still reappeared anyway, because a piece of the Build
Prompt's pseudocode was left as `if module_exists(x): ...`, and the one
natural way to implement that ellipsis in Python (a bare `try/except
ImportError`) happens to BE the anti-pattern a different Gotcha in the same
document warns against. No amount of re-reading two finished sections side by
side would have caught this — it only surfaces once someone actually fills in
the gap, which is exactly what the adversarial fresh-agent rebuild forces to
happen. Treat any ellipsis, "your choice," or unresolved branch in a Build
Prompt as a specific risk, not a harmless simplification: either fully
specify it, or explicitly flag in-line which Gotcha the implementer must
re-check before filling it in themselves.

**A third shape: a whole deliverable promised in Boundary/Engine that never
appears in the Build Prompt at all.** Module 04's spec committed to "tiered
decay" as owned, built-once Engine logic in two separate sections — and the
Build Prompt's own enumerated task list simply never mentioned it. An agent
following the Build Prompt literally (again, the entire point of it being
self-contained) would never build a piece the spec elsewhere promises exists.
Unlike shapes (a) and (b), this isn't a contradiction or an ellipsis to spot
— it's an absence, which is much easier to miss on a read-through because
there's nothing wrong on the page you're looking at, only something missing
from a different page. Checklist for this shape specifically: enumerate
every bullet in Boundary's "Owns" and every bullet in Engine, and confirm
each one has a corresponding numbered piece in the Build Prompt — not just a
mention somewhere in prose.

**Also worth naming directly: a lesson learned in one module does not
reliably carry over to the next one, even for the same failure sub-type.**
Module 03's Validation Note documented, in detail, "rollup math was prose,
not pseudocode... forcing the agent to invent defensible-but-arbitrary
answers," and fixed it. Module 04's Build Prompt — written after that
lesson was recorded — left arc classification as equally pure prose with
the same consequence, verbatim. Do not treat a lesson recorded in an earlier
module's Validation Note as protection against the same author making the
same mistake in a later one; the adversarial rebuild is what actually
catches it, not memory of having caught it before.

Five-for-five validated modules have each surfaced at least one real
instance of one of these failure shapes — treat this as the default outcome
to expect, not an edge case, and always run the adversarial rebuild rather
than trusting inspection alone, prior lessons, or author care to catch any
of them.

**The trend is the opposite of reassuring.** Module 05 — the most complex
spec written so far, and written immediately after Module 04's note warned
that lessons don't transfer between modules — reproduced ALL FOUR shapes at
once, including shape (d) three separate times (two of them recurrences of
Module 01's own findings). Defect count per module is not going down as the
library matures; if anything it tracks spec complexity. Do not taper off the
adversarial rebuild for later modules on the theory that the process is
now well-understood.

**Two habits that came out of Module 05, worth applying to every spec:**
- **Ask a validation agent to PROVE defects, not report them.** Module 05's
  agent wrote tests that execute the spec's own literal pseudocode and
  demonstrate the failure (two active rows, a real `IntegrityError`, a blank
  trigger source accepted), then the corrected version alongside. A proof is
  unarguable and self-documents the fix; a report is a claim you then have to
  evaluate. Ask for this explicitly in the validation prompt.
- **Any nullable column mentioned in Data Shapes needs its NULL case
  explicitly tested.** Module 05's platform-level (`customer_id IS NULL`)
  path silently broke the module's core invariant while every
  customer-scoped test passed. If a column is nullable, the spec must say so
  AND an Acceptance Criterion must exercise the NULL case — passing tests on
  the non-NULL path prove nothing about it.

### Acceptance Criteria
Concrete, testable statements. Prefer "given X, the system does Y" over vague
adjectives like "works correctly."

### Reference Test Harness
How to actually verify the acceptance criteria — a real test file pattern, a script,
or a manual verification sequence.

### Known Gotchas
Each entry: **Symptom** → **Root cause** → **Fix**. Only real, previously-hit issues
go here — not hypothetical risks. Cite the commit/session where it was found when
available; that provenance is what makes this trustworthy to a future reader.

### Provenance
Origin file paths in the reference system, and the session/date this spec was
authored or last validated against real code.
