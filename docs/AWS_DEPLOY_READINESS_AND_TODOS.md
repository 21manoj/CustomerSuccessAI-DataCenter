# AWS Deploy Readiness & Pre–Image TODOs

## Are we ready to deploy on AWS?

**Summary:** You have the three image definitions and production compose in place. You are **almost ready**. Complete the TODOs below (especially security and env handling) before building and pushing new images to ECR and deploying.

| Area | Status | Notes |
|------|--------|--------|
| **Image 1: CS Pulse platform** | ✅ Dockerfile exists | `kpi-dashboard/Dockerfile.cspulse` — single image (Flask + React + Nginx). |
| **Image 2: PostgreSQL** | ✅ Dockerfile exists | `kpi-dashboard/docker/postgres/Dockerfile` — Postgres 16 Alpine + init scripts. |
| **Image 3: Load driver** | ✅ Dockerfile exists | `load-driver/Dockerfile` — run locally or on AWS later. |
| **Production compose** | ✅ Exists | `docker-compose.production.yml` — platform + postgres, resource limits, healthchecks. |
| **Secrets in images** | ⚠️ Verify | Ensure no `.env` or real API keys in build context; use env at runtime only. |
| **Production hardening** | ⚠️ TODO | DEBUG off, SECRET_KEY from env, optional subpath/SSL config. |
| **ECR / tagging** | 📋 TODO | Decide repo names and tags before first push. |

---

## The three Docker images (mapping)

| # | Purpose | Dockerfile | Image name (suggested for ECR) | Run |
|---|--------|------------|----------------------------------|-----|
| 1 | **CS Pulse platform** (Flask + React + Nginx) | `kpi-dashboard/Dockerfile.cspulse` | e.g. `cspulse-platform` or `kpi-dashboard-platform` | On EC2 (or ECS) via `docker-compose.production.yml` |
| 2 | **PostgreSQL DB** | `kpi-dashboard/docker/postgres/Dockerfile` | e.g. `cspulse-postgres` or `kpi-dashboard-postgres` | On same EC2 via same compose (or RDS instead of container) |
| 3 | **Load driver** | `load-driver/Dockerfile` | e.g. `cspulse-load-driver` | **Locally on your laptop** (point at V6 URL); optional: run on AWS later (e.g. EC2-B) |

Only **images 1 and 2** are required on AWS for the V6 app. Image 3 is for load testing from the laptop (or from AWS when you choose).

---

## TODOs before creating new Docker images

Do these on your side before building and pushing the three images (e.g. to ECR).

### Security & config

- [x] **TODO 1 – Keep secrets out of images** ✅  
  - **Done:** `.dockerignore` excludes `.env`, `.env.*`, `backend/.env`, `backend/.env.*` so they are never copied into the build context.  
  - All secrets are provided at **runtime** via env or AWS SSM/Secrets Manager (see `docs/PRODUCTION_ENV_TEMPLATE.md`).

- [x] **TODO 2 – Production DEBUG off** ✅  
  - **Done:** In `app_v3_minimal.py`, `DEBUG` is set from `FLASK_DEBUG` env (default `'false'`). Production must **not** set `FLASK_DEBUG=true` (documented in compose and production template).

- [x] **TODO 3 – SECRET_KEY in production** ✅  
  - **Done:** `docker-compose.production.yml` requires `SECRET_KEY` from env. `config.ProductionConfig` validates SECRET_KEY at startup (min 32 chars); no default secret in production code.

- [x] **TODO 4 – .env.example safe** ✅  
  - **Done:** `kpi-dashboard/backend/.env.example` uses placeholders only; no real API keys or secrets.

### Build & image hygiene

- [x] **TODO 5 – .dockerignore** ✅  
  - **Done:** `.dockerignore` excludes env files and secrets; does not exclude files required by `Dockerfile.cspulse` (backend, frontend, nginx, entrypoint).

- [x] **TODO 6 – Postgres image default password** ✅  
  - **Done:** Postgres Dockerfile documents that production must override `POSTGRES_PASSWORD`; `docker-compose.production.yml` and `docs/PRODUCTION_ENV_TEMPLATE.md` state never use default on AWS.

- [x] **TODO 7 – Load driver image** ✅  
  - **Done:** Load driver Dockerfile documents that `CS_PULSE_BASE_URL` (and any keys) are set at run time only; no secrets in image.

### Optional before first AWS deploy (subpath / SSL)

- [ ] **TODO 8 – Subpath /CSPulseV6 (if using www.auctusai.ai/CSPulseV6)**  
  - Only if you deploy under a subpath: set React `homepage` and `Router` `basename` to `/CSPulseV6`, add nginx config for `/CSPulseV6/` and `/CSPulseV6/api/`, and set backend cookie path if needed.  
  - Can be done in a follow-up change; not required to build the three images.

- [ ] **TODO 9 – SSL (ACM + ALB or CloudFront)**  
  - No image changes required. After images are built, configure ACM, ALB or CloudFront, and DNS.  
  - Document in your runbook how to attach the certificate and point the domain at the load balancer or distribution.

### ECR and tagging

- [x] **TODO 10 – ECR repo names and tags** ✅  
  - **Suggested ECR repo names:** `cspulse-platform`, `cspulse-postgres`, `cspulse-load-driver` (or `kpi-dashboard-platform`, etc.).  
  - **Tag strategy:** e.g. `latest`, `v6`, or date `YYYYMMDD`.  
  - **Build and push commands** (replace `AWS_ACCOUNT_ID` and `AWS_REGION`; run from repo root):

```bash
# 1) Platform image (from kpi-dashboard directory)
cd kpi-dashboard
docker build -f Dockerfile.cspulse -t cspulse-platform:latest .
docker tag cspulse-platform:latest AWS_ACCOUNT_ID.dkr.ecr.AWS_REGION.amazonaws.com/cspulse-platform:latest
aws ecr get-login-password --region AWS_REGION | docker login --username AWS --password-stdin AWS_ACCOUNT_ID.dkr.ecr.AWS_REGION.amazonaws.com
docker push AWS_ACCOUNT_ID.dkr.ecr.AWS_REGION.amazonaws.com/cspulse-platform:latest

# 2) Postgres image (from kpi-dashboard)
docker build -f docker/postgres/Dockerfile -t cspulse-postgres:latest ./docker/postgres
docker tag cspulse-postgres:latest AWS_ACCOUNT_ID.dkr.ecr.AWS_REGION.amazonaws.com/cspulse-postgres:latest
docker push AWS_ACCOUNT_ID.dkr.ecr.AWS_REGION.amazonaws.com/cspulse-postgres:latest

# 3) Load driver image (from load-driver directory)
cd ../load-driver
docker build -t cspulse-load-driver:latest .
docker tag cspulse-load-driver:latest AWS_ACCOUNT_ID.dkr.ecr.AWS_REGION.amazonaws.com/cspulse-load-driver:latest
docker push AWS_ACCOUNT_ID.dkr.ecr.AWS_REGION.amazonaws.com/cspulse-load-driver:latest
```

Create ECR repos first if needed: `aws ecr create-repository --repository-name cspulse-platform` (and same for `cspulse-postgres`, `cspulse-load-driver`).

### Verification before push

- [ ] **TODO 11 – Local build test**  
  - From repo root (or `kpi-dashboard`):  
    - Build platform: `docker compose -f docker-compose.production.yml build cs-pulse` (or equivalent using `Dockerfile.cspulse`).  
    - Build postgres: `docker compose -f docker-compose.production.yml build postgres`.  
  - From `load-driver`: build load driver image.  
  - Run `docker compose -f docker-compose.production.yml up -d` (without pushing) and confirm platform health and DB connectivity; then run load driver locally with `CS_PULSE_BASE_URL=http://localhost:80` (or the appropriate URL) to verify it can drive scenarios.

- [x] **TODO 12 – Production env template** ✅  
  - **Done:** See **`docs/PRODUCTION_ENV_TEMPLATE.md`** for every variable required by `docker-compose.production.yml` (POSTGRES_PASSWORD, OPENAI_API_KEY, ANTHROPIC_API_KEY, SECRET_KEY, GUNICORN_*, etc.) and how to set them in AWS (env file, SSM, or Secrets Manager).

---

## Checklist summary

| # | TODO | Status | Blocks image build? |
|---|------|--------|----------------------|
| 1 | Secrets not in images (.dockerignore, runtime env) | ✅ Done | Yes — do before build. |
| 2 | DEBUG off in production | ✅ Done | Yes — do before build. |
| 3 | SECRET_KEY from env in production | ✅ Done | Yes — do before build. |
| 4 | .env.example placeholders only | ✅ Done | Yes — do before build. |
| 5 | .dockerignore complete | ✅ Done | Yes — do before build. |
| 6 | Postgres password override doc | ✅ Done | No — document before deploy. |
| 7 | Load driver env-only config | ✅ Done | No — confirm before run. |
| 8 | Subpath /CSPulseV6 | Optional | No — optional, can be later. |
| 9 | SSL (ACM + ALB/CloudFront) | Optional | No — after images, infra only. |
| 10 | ECR repo names and tags | ✅ Done (doc) | Yes — before push. |
| 11 | Local build and smoke test | Pending | Yes — before push. |
| 12 | Production env template / runbook | ✅ Done | No — before first AWS deploy. |

After TODOs 1–5, 10, and 11 are done, you can build and tag the three images and push them to ECR. Then run through 6, 7, 12 (and optionally 8, 9) for a safe, documented AWS deploy.
