# CS Pulse Deployment — FDE 1-Pager

Distilled from `CSPulse_FDE_Playbook.docx` §3 + §5.6–§5.7. For the FDE on the ground; not a substitute for the full playbook.

## Two deploy paths — pick deliberately

| When | Script | What it does | Time |
|---|---|---|---|
| Day-to-day. EC2 must match `main` bit-for-bit. | `./scripts/deploy-ec2-git-pull.sh` | Pulls `main` on EC2, rebuilds image locally on the host, recreates containers. | ~5–10 min |
| CI already pushed image to ECR; deploy a specific tag. | `./scripts/rehydrate-ec2-ecr.sh <INSTANCE_ID>` | Pulls from ECR, recreates containers. **Honors `PLATFORM_TAG` on EC2 — see footgun #1.** | ~1–2 min |

Both scripts are idempotent and self-healing (env-file repair, magic-link reissue, `SESSION_COOKIE_SECURE` for direct-HTTP).

## The 3-step post-deploy ritual

1. **Bundle-hash test** — `curl -s http://<EC2>/ | grep -oE 'main\.[a-f0-9]+\.js'`. If unchanged from prior deploy, your code is NOT running (footgun #1 below).
2. **Acceptance harness** — `./scripts/run_acceptance_ec2.sh`. Runs `verify_executive_phases_ec2.py` against CFO/CRO/VPCS suites. Optional persona grading via `ACCEPTANCE_RUN_PERSONA=1` (~$3–5, ~5 min).
3. **Cold-start probe** — register a new tenant with `load-driver --register`, walk `list_customers` + `get_at_risk_accounts` + `get_csm_daily_actions` + `get_portfolio_nrr_forecast_v3` via MCP. Open all 5 dashboards. Any 500 means schema/model drift slipped through.

## Top 5 footguns

1. **PLATFORM_TAG promotion gap.** `rehydrate-ec2-ecr.sh` pulls but doesn't promote — EC2's `~/cspulse/.env` pins `PLATFORM_TAG=<old-tag>`. Fix: edit `.env` to `PLATFORM_TAG=latest` + re-rehydrate, OR promote the new build to the pinned tag in ECR. **Bundle hash unchanged after rehydrate is the tell.**
2. **Empty `MCP_SERVER_API_KEY` on EC2.** Symptom: HTTP transport accepts Bearer tokens, but every MCP tool call returns "Invalid or revoked API key." Diagnostic: `grep -c MCP_SERVER_API_KEY ~/cspulse/.env` on EC2 (must be ≥1). Fix: append the key + `docker compose up -d --no-deps --force-recreate cs-pulse`.
3. **CI concurrency cancellation.** Workflow has `cancel-in-progress: true`. Two merges within ~15s → older build is killed; end state is still correct (newer run's image contains all prior commits). Don't chase cancelled runs — verify against `main` HEAD.
4. **EC2 HTTP 000 during rehydrate.** Docker-compose recreate drops the listener for 30–90s. Normal. Worry only if >5 min unresponsive, OR HTTP 200 with unchanged bundle hash (that's #1, not connectivity).
5. **`gh pr merge --delete-branch` failing on worktree locks.** Merge itself completed on GitHub; local cleanup tripped. Fix: `gh api -X DELETE repos/<owner>/<repo>/git/refs/heads/<branch>` + `git branch -D` from a detached HEAD.

## Rollback — under 60 seconds

Every promoted tag stays in ECR. Flip `PLATFORM_TAG` on EC2 to a known-good tag, re-run `rehydrate-ec2-ecr.sh`. Do not delete prior tags — that's your only safety net.

## Sign-off gate (use before handover)

- [ ] `./scripts/run_acceptance_ec2.sh` exits 0 (HTTP suites pass)
- [ ] Persona grading run with `ACCEPTANCE_MIN_GRADE_NUMERIC=3.7` (A-) passes for all 5 personas
- [ ] Bundle hash on EC2 matches what `main` HEAD's CI pushed
- [ ] Cold-start probe (new tenant + every MCP tool + all 5 dashboards) is clean
- [ ] CHANGELOG.md in the customer overlay reflects every change in this deploy

## What you DON'T do during a deploy

- **Don't** `docker cp` files into a running container. That pattern has burned us before — every fix goes through one of the two deploy scripts.
- **Don't** skip `git pull` before `deploy-ec2-git-pull.sh`. The script does the pull on the EC2 side, but if your laptop is on stale main you'll be confused about what was deployed.
- **Don't** edit `signal_engine/`, `outcome_roi_engine.py`, `predictor/`, or `wizards/` — base dev owns these. FDE changes go in `verticals/customer{N}-{vertical}/` overlays.
- **Don't** promise the customer features that require base-dev work (new MCP tool, schema change, new vertical, prompt edit). File a request; do not promise a date.

---

*Companion: `CSPulse_FDE_Playbook.docx` §3 + §5.6 + §5.7. For incident response, also see Common Gotchas (§3.5).*
