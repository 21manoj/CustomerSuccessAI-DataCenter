# Pre-Commit Cleanup Evaluation (branch: dc2s-implementation)

**Branch:** `dc2s-implementation`  
**Scope:** What to clean up before committing to GitHub.

---

## 1. Summary

| Category | Count | Action |
|----------|--------|--------|
| **Modified (tracked)** | ~77 files | Review diff; stage intentional changes only. |
| **Deleted (tracked)** | ~25 files | Confirm deletions are intentional (DC cleanup, onboarding refactor). |
| **Untracked** | 400+ items | **Do not add all.** Add to `.gitignore` or exclude from commit as below. |

**Diff size:** ~4,470 insertions, ~4,908 deletions (net −438 lines).

---

## 2. Do NOT Commit (sensitive / runtime / junk)

Add these to `.gitignore` or ensure they stay untracked. **Never commit:**

| Item | Reason |
|------|--------|
| **kpi-dashboard/backend/DC2S_TEST_USER_CREDENTIALS.txt** | Contains **password** (e.g. `DC2_Super_2024!`). **Remove from repo if ever added.** |
| **kpi-dashboard/backend/E2E_UI_CREDENTIALS.txt** | Likely test credentials. |
| **kpi_dashboard.db** (repo root) | Database file; can contain sensitive data. |
| **frontend.log** | Log file. |
| **.DS_Store** | macOS metadata; junk. |
| **kpi-dashboard/backend/server.pid** | Runtime PID file. |
| **kpi-dashboard/frontend.pid** | Runtime PID file. |
| **kpi-dashboard/backend/backend.pid** | Runtime PID file. |
| **kpi-dashboard/backend/analyst.out** | Build/run artifact. |
| **kpi-dashboard/backend/*.backup**, ***.bak**, ***.old** | Backup copies; do not commit. |
| **kpi-dashboard/backend/product_rag_test_results_*.json** | Test artifacts. |
| **kpi-dashboard/backend/rag_test_results*.txt** | Test output. |
| **kpi-dashboard/backend/test_score_calc.out** | Test output. |
| **kpi-dashboard/backend/backups/** | DB backups. |
| **kpi-dashboard/backend/qdrant_temporal_storage_default/** | Local Qdrant data. |

**Action:** Add/update `.gitignore` (see Section 6). Ensure no credentials or `*.db` are ever staged.

---

## 3. Untracked Folders – Decide Scope

| Path | Note |
|------|------|
| **client/** | Separate app (Vite). Commit only if it belongs to this repo. |
| **new-app/** | Separate app. Same as above. |
| **server/** | Separate app. Same as above. |
| **kpi-dashboard/backend/verticals/** | DC2_S verticals (customer configs, data). Commit if part of DC2S; ensure no secrets in CSVs. |
| **kpi-dashboard/backend/utils/** | Shared utilities. Commit if used by main app. |
| **kpi-dashboard/backend/templates/** | Flask templates. Commit if used. |
| **kpi-dashboard/backend/tests/** | Tests. Usually commit. |
| **kpi-dashboard/src/components/admin/** | Admin UI. Commit if part of feature set. |
| **kpi-dashboard/src/components/dc/** | DC UI. Commit if part of DC2S. |
| **kpi-dashboard/src/components/journey-visualizer/** | Journey UI. Commit if part of feature set. |
| **kpi-dashboard/src/components/onboarding/** | New onboarding (Step0–Step8, etc.). Commit if replacing deleted wizard. |
| **kpi-dashboard/src/components/settings/** | Settings UI. Commit if used. |
| **kpi-dashboard/src/components/wizard/** | Wizard UI. Commit if used. |
| **kpi-dashboard/config/** | Config files. Commit if no secrets. |
| **kpi-dashboard/verticals/** | Vertical data. Commit if no PII/secrets. |

**Action:** Decide which of these are part of `dc2s-implementation`. Add the rest to `.gitignore` or leave untracked for a later PR.

---

## 4. Untracked Docs (100+ .md files)

Many untracked `.md` files are implementation notes, fix reports, and test reports (e.g. `ACCOUNT_ID_MISMATCH_ANALYSIS.md`, `AUTH_FIXES_APPLIED.md`, `AWS_SHUTDOWN_CHECKLIST.md`, `RUN_ANALYSIS_FLOW.md`, `SIGNAL_CITATIONS_IMPLEMENTATION_PLAN.md`).

**Options:**

- **A) Commit a subset:** e.g. `README`-level and design docs (`RUN_ANALYSIS_FLOW.md`, `SIGNAL_CITATIONS_IMPLEMENTATION_PLAN.md`, `AWS_SHUTDOWN_CHECKLIST.md`, `DATA_CENTER_IMPLEMENTATION_PLAN.md`). Leave the rest untracked or in `docs/archive/`.
- **B) Commit all:** Repo becomes very doc-heavy; consider moving older ones to `docs/` or `archive/`.
- **C) Ignore most:** Add `kpi-dashboard/*_*.md` or a list of one-off reports to `.gitignore` and only track core docs.

**Action:** Choose A, B, or C and add only the chosen docs.

---

## 5. Deleted Files – Confirm Intent

These are **deleted** in your working tree (DC-specific and old onboarding):

- `kpi-dashboard/DC_FUNCTIONALITY_GAP_ANALYSIS.md`
- `kpi-dashboard/backend/alert_engine_dc.py`, `api_routes_dc.py`, `check_dc_data.py`, `config_dc.py`, `data_models_dc.py`, `delete_dc_data.py`, `generate_dc_seed_excel.py`, `health_calculator_dc.py`, `kpi_calculator_dc.py`, `kpi_definitions_dc.py`, `playbooks_dc.py`, `recommendation_engine_dc.py`, `seed_dc_data.py`, `upload_dc_seed_excel.py`, `utils_dc.py`, `verify_dc_data.py`
- `kpi-dashboard/backend/qdrant_historical_storage/.lock`, `qdrant_temporal_storage/.lock`
- `kpi-dashboard/src/components/onboarding/FieldMapperAI.tsx`, `OnboardingWizard.tsx`, `ProcessingProgress.tsx`, `SmartUploadZone.tsx`, `SuccessSummary.tsx`, `TemplatePreview.tsx`, `VerticalSelector.tsx`

**Action:** Confirm these deletions are intentional (DC consolidation + onboarding refactor). If yes, stage the deletions. If not, `git restore <file>` for any you want to keep.

---

## 6. Recommended .gitignore Additions

Add (or merge) the following so they are never committed:

**Repo root or `kpi-dashboard/.gitignore`:**

```gitignore
# Pre-commit cleanup
.DS_Store
*.log
frontend.log
*.pid
kpi_dashboard.db
*CREDENTIALS*.txt
*_CREDENTIALS*.txt
*.backup
*.bak
*.old
**/backups/
**/qdrant_temporal_storage_default/
**/test_csv_files/
**/test_qdrant/
product_rag_test_results_*.json
rag_test_results*.txt
test_score_calc.out
analyst.out
```

**kpi-dashboard/backend/.gitignore`** (if not already covered by root/kpi-dashboard):

```gitignore
instance/
*.sqlite3
*.db
DC2S_TEST_USER_CREDENTIALS.txt
E2E_UI_CREDENTIALS.txt
server.pid
backend.pid
*.backup
*.bak
*.old
backups/
qdrant_temporal_storage_default/
```

---

## 7. Suggested Commit Flow

1. **Update .gitignore** (Section 6) so credentials, DBs, logs, PIDs, and backup/test artifacts are ignored.
2. **Confirm no credentials or DBs are staged:**  
   `git status` and `git diff --cached` — ensure no `*CREDENTIALS*`, `*.db`, `*.pem`.
3. **Stage only what you want in this PR:**
   - All **modified** backend/frontend files that are part of DC2S implementation.
   - All **deleted** files you intend to remove (Section 5).
   - **New code:** e.g. `backend/scripts/audit_schema_alignment.py`, new onboarding components, `backend/verticals/`, `src/components/dc/`, etc., only if they belong in this branch.
   - **Docs:** Only the subset you chose (Section 4).
4. **Do not add** (leave untracked or ignored):  
   `client/`, `new-app/`, `server/` (unless they’re part of this repo), root `kpi_dashboard.db`, `frontend.log`, `.DS_Store`, any `*CREDENTIALS*.txt`, backup/junk files.
5. **Commit:**  
   `git add -A` **only after** .gitignore is updated and you’ve verified no sensitive or junk files are included. Prefer `git add` per path for clarity.
6. **Push:**  
   `git push origin dc2s-implementation` (or your remote name).

---

## 8. Quick Verification Commands

```bash
# 1. Ensure credentials are not staged
git status | grep -i credent
git diff --cached --name-only | grep -i credent

# 2. Ensure no .db or .pem staged
git diff --cached --name-only | grep -E '\.(db|pem|sqlite)$'

# 3. List what will be committed
git diff --cached --stat
```

---

*Generated as a pre-commit cleanup evaluation. Apply Section 6 and Section 7 before pushing to GitHub.*
