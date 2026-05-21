# EC2 acceptance (step 7)

Repeatable post-deploy checks: **HTTP dashboard acceptance** + optional **persona grading** in Docker.

## Quick start

```bash
cp scripts/.env.acceptance.example scripts/.env.acceptance
# Edit base URL, credentials, ANTHROPIC_API_KEY

chmod +x scripts/run_acceptance_ec2.sh
./scripts/run_acceptance_ec2.sh
```

## Environment

| Variable | Default | Purpose |
|----------|---------|---------|
| `CS_PULSE_BASE_URL` | `http://3.94.106.197` | Target host |
| `CS_PULSE_EMAIL` / `CS_PULSE_PASSWORD` | dc2s super user | Login |
| `ACCEPTANCE_CUSTOMER_ID` | `334` | Tenant for APIs + grading |
| `ACCEPTANCE_SUITE` | `all` | `cfo`, `cro`, `vpcs`, `cfo-phase1`, or `all` |
| `ACCEPTANCE_RUN_PERSONA` | `0` | Set `1` to run Ask AI grading in container |
| `ACCEPTANCE_PERSONA_SHOTS` | `3` | Shots per question |
| `ACCEPTANCE_PERSONAS` | `cro,cfo,vpcs` | Subset of personas |
| `ACCEPTANCE_MIN_GRADE_NUMERIC` | `0` | e.g. `3.7` to fail below A− |
| `ACCEPTANCE_SEED_VPCS` | `0` | Set `1` to run `seed_vpcs_demo_334.py` first |
| `CSPULSE_CONTAINER` | auto-detect | Docker container name |

## HTTP-only (no Anthropic cost)

```bash
ACCEPTANCE_SKIP_HTTP=0 ./scripts/run_acceptance_ec2.sh
# or
python3 scripts/verify_executive_phases_ec2.py --suite cro,vpcs
```

Legacy entry points still work: `verify_cfo_phases_ec2.py`, etc.

## Full step 7 (HTTP + persona)

```bash
export ACCEPTANCE_RUN_PERSONA=1
export ANTHROPIC_API_KEY=sk-ant-...
./scripts/run_acceptance_ec2.sh
```

Requires a **rebuilt platform image** that includes `tests/persona_grading/` (see root `.dockerignore` exceptions).
