# CS Pulse Architecture — Container Checklist

## Target Architecture

```
EC2-A (Platform)                         EC2-B (Load Testing)
┌────────────────────────┐              ┌──────────────────┐
│ docker-compose          │              │ load-driver      │
│ ┌────────────────────┐ │   HTTPS      │ 19 .py, 10 deps  │
│ │ cspulse-platform   │ │◄────────────►│ ~250MB image     │
│ │ Flask+React+Nginx  │ │              └──────────────────┘
│ │ ~800MB-1GB         │ │
│ └────────────────────┘ │
│ ┌────────────────────┐ │
│ │ cspulse-postgres   │ │
│ │ 39 tables, seeds   │ │
│ │ ~100MB             │ │
│ └────────────────────┘ │
└────────────────────────┘
```

## EC2-A (Platform) — ✅ All containers present

| Container           | Compose file                    | Image / build              | Status |
|---------------------|----------------------------------|----------------------------|--------|
| **cspulse-platform**| `kpi-dashboard/docker-compose.cspulse.yml` | `Dockerfile.cspulse` (Flask+React+Nginx) | ✅ |
| **cspulse-postgres**| same                             | `docker/postgres/Dockerfile` | ✅ |

**Run on EC2-A:**
```bash
cd kpi-dashboard
docker compose -f docker-compose.cspulse.yml up -d --build
```

---

## EC2-B (Load Testing) — ✅ Present; use standalone compose for remote target

| Item        | Location | Status |
|------------|----------|--------|
| Load driver code | `load-driver/` (19 .py, scenarios, client, driver) | ✅ |
| Dockerfile | `load-driver/Dockerfile` | ✅ |
| Dependencies | `load-driver/requirements.txt` (requests, faker, pandas, click, etc.) | ✅ |
| Compose (same-host) | `docker-compose.loaddriver.yml` (depends on `cs-pulse` + network `cspulse`) | ✅ For same host |
| Compose (EC2-B only) | `docker-compose.loaddriver-standalone.yml` | ✅ For EC2-B → HTTPS to EC2-A |

**Run on EC2-B (standalone, target EC2-A via HTTPS):**
```bash
export CS_PULSE_BASE_URL=https://<ec2-a-host-or-alb>
docker compose -f docker-compose.loaddriver-standalone.yml up -d --build
# Or run a single customer: docker compose -f docker-compose.loaddriver-standalone.yml up -d load-driver-customer-1
```

**Run on same host as platform (e.g. dev):**
```bash
# After platform is up and network cspulse exists
docker network create cspulse  # if not already
docker compose -f docker-compose.loaddriver.yml up -d
```

---

## Summary

- **EC2-A:** You have both required containers (`cspulse-platform`, `cspulse-postgres`) in `kpi-dashboard/docker-compose.cspulse.yml`.
- **EC2-B:** You have the load-driver app, Dockerfile, and deps; use `docker-compose.loaddriver-standalone.yml` on EC2-B with `CS_PULSE_BASE_URL=https://...` pointing at EC2-A.
