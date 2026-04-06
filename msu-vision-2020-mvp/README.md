# MSU Vision 2020

Django app for alumni–foundation coordination: **needs**, **projects** (milestones / timeline), **funding** (pools, contributions, expenses), **events**, **governance** thresholds, and persona-aware dashboards.

See [`msu_vision_2020_architecture_v1.2.md`](./msu_vision_2020_architecture_v1.2.md) for the full architecture and product narrative.

---

## Prerequisites

- **Python 3.9+** (Django 4.2 locally; **3.11** matches the production `Dockerfile`)
- **Git** and **pip**; virtualenv recommended

Optional: **Docker**; **AWS CLI + EB CLI** only for deploy.

---

## Local setup (co-developers)

```bash
git clone git@github.com:21manoj/MSU2020.git
cd MSU2020

python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

pip install -r requirements.txt

cp .env.example .env
# Edit .env — set SECRET_KEY for any shared/staging use

python manage.py migrate
python manage.py load_demo_data
python manage.py runserver
```

Open **http://127.0.0.1:8000/accounts/login/**

- **`demo`** / **`demo`**, or **Sign in as demo** when `DEBUG=True`
- Other seeded users: **`demo123`** (see `load_demo_data` output: `hod_hostel`, `donor_anita`, `gov_meera`, …)

---

## Environment variables

| Variable | Purpose |
|----------|--------|
| `DEBUG` | `True` locally; `False` in production |
| `SECRET_KEY` | **Required** in production |
| `ALLOWED_HOSTS` | Comma-separated hosts |
| `CSRF_TRUSTED_ORIGINS` | HTTPS origins if applicable |
| `DATABASE_URL` | Optional; default SQLite (`db.sqlite3`) |
| `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` | Optional Google login |
| `GOVERNANCE_THRESHOLD_*_USD` | Governance routing thresholds |

**Never commit `.env`** (see `.gitignore`).

---

## Docker (optional)

```bash
docker build -t msu-vision-2020 .
docker run --rm -p 8000:8000 --env-file .env msu-vision-2020
```

---

## Django apps

| App | Role |
|-----|------|
| `apps.core` | Shared utilities |
| `apps.stakeholders` | Profiles, personas, registration |
| `apps.needs` | Needs lifecycle |
| `apps.projects` | Projects, milestones, timeline |
| `apps.funding` | Pools, contributions, expenses |
| `apps.events` | Events |
| `apps.dashboard` | Home, rollup, governance queue |

---

## Tests

```bash
source .venv/bin/activate
python manage.py test
```

---

## Deploy (Elastic Beanstalk)

Requires **AWS credentials** and EB config (`.elasticbeanstalk/` — not committed by default). From this directory:

```bash
eb deploy
```

GitHub write access alone does **not** deploy; grant AWS or CI separately.

---

## Deploy alongside CS Pulse (same EC2 / Docker)

This repo copy is wired into **CS Pulse** compose files under `kpi-dashboard/`:

- **URL path:** `https://<your-cloudfront-domain>/msu2020/` (nginx in `cspulse-platform` proxies to the `msu-vision` container).
- **Image:** `cspulse-msu-vision:latest` in the same ECR registry as CS Pulse (built by `.github/workflows/cspulse-ecr-build-push.yml`).
- **Persistent data:** SQLite file in Docker volume `msu_vision_data` → `/data/db.sqlite3`.

### 1. EC2 `~/cspulse/.env` (or your compose `.env`)

Set at least:

| Variable | Example / notes |
|----------|------------------|
| `MSU_VISION_SECRET_KEY` | Same value as EB `SECRET_KEY` if you want existing sessions to stay valid; otherwise generate a new secret. |
| `MSU_VISION_ALLOWED_HOSTS` | `d2oqfugrb2ltg9.cloudfront.net,localhost,127.0.0.1` plus any custom domain. |
| `MSU_VISION_CSRF_TRUSTED_ORIGINS` | `https://d2oqfugrb2ltg9.cloudfront.net` (and `https://your-custom-domain` if used). |
| `MSU_VISION_GOOGLE_CLIENT_ID` / `MSU_VISION_GOOGLE_CLIENT_SECRET` | If Google login is enabled; update **Google Cloud Console** redirect URIs to use `/msu2020/...`. |

### 2. Pull images and restart

From `kpi-dashboard/` on the EC2 host (registry deploy):

```bash
docker compose -f docker-compose.ec2-registry.yml pull
docker compose -f docker-compose.ec2-registry.yml up -d
```

Or build on the box: `docker compose -f docker-compose.ec2-build.yml build && docker compose -f docker-compose.ec2-build.yml up -d`.

### 3. Migrate SQLite from Elastic Beanstalk (optional)

Before terminating the EB environment, copy `db.sqlite3` from the old instance into the new volume (paths may vary), or export data and re-seed with `load_demo_data`.

### 4. Decommission EB

When `https://…/msu2020/` is verified, delete the **Elastic Beanstalk** environment `msu-vision-mvp-prod` and release its **Elastic IP** to stop the extra EC2 and IPv4 charges.

---

## Collaboration

- **GitHub:** Settings → Collaborators for push/PRs.
- **AWS:** IAM or CI for `eb deploy`.

## License

Add a `LICENSE` file if needed.
