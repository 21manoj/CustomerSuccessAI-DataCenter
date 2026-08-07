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

**The Build Prompt and Known Gotchas are one unit, not two.** A Gotcha that exists
specifically to correct something the Build Prompt itself says wrong is a bug in
the spec, not a valid gotcha — fix the Build Prompt directly instead. (Found during
the Module 03 pilot validation: the Build Prompt told an agent to gate a check on
a condition that Gotcha 4, two sections later, named as the exact anti-pattern to
avoid. An agent that only reads the Build Prompt — which is the whole point of a
Build Prompt being self-contained — would reproduce the bug.) When authoring or
reviewing a module, re-read the Build Prompt against every Gotcha and ask: if an
agent followed this prompt literally, would it walk straight into this Gotcha?

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
