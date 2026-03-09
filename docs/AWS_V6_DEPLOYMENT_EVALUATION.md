# AWS V6 Deployment Evaluation

## What We Did Before (from repo)

### Past AWS usage
- **Region:** `us-east-1`
- **Single EC2 host** ran V1 + V2 + V3:
  - Instance ID: `i-05d943311f6c90fdf`
  - Public IP (docs): `3.84.178.121`
  - Deploy scripts: `deploy-v2-aws.sh`, `deploy-v3-final.sh`, V5 to same box
- **Instance type** was not recorded in scripts; EC2 guide used **t2.micro** (1 vCPU, 1 GB) for *new* free-tier setups only.
- **Approximate past spend (from AWS_SHUTDOWN_CHECKLIST):**
  - EC2: ~$47 / period
  - ELB: ~$35
  - VPC (e.g. NAT): ~$29
  - ECS: ~$13
  - **Rough total:** ~$129/month when everything was on.

### Production resource intent (current repo)
From **docker-compose.production.yml**:

| Service            | Memory limit | Memory reservation | CPUs |
|--------------------|-------------|--------------------|------|
| **cspulse-platform** (Flask+React+Nginx) | 2 GB        | 1 GB               | 2.0  |
| **cspulse-postgres**                    | 512 MB      | 256 MB             | 1.0  |
| **Total containers**                    | **~2.5 GB** | **~1.25 GB**       | —    |

Architecture doc: platform image ~800 MB–1 GB, postgres ~100 MB.

---

## V6: Recommended server type, memory, and cost

### Assumptions for V6
- Same stack: **one EC2 (EC2-A)** running `docker-compose.production.yml` (cspulse-platform + cspulse-postgres).
- Optional second EC2 (EC2-B) for load-driver only when needed (can be smaller or stopped when not testing).
- V6 adds agents, memory, more APIs — slightly higher memory use than V5; production limits (2G + 0.5G) are a good target.

### EC2-A (platform) – single host for app + DB

Host must fit:
- Docker + OS overhead: ~500 MB–1 GB
- Platform container: **2 GB** limit (1 GB reserved)
- Postgres container: **512 MB** limit (256 MB reserved)  
→ **Recommended RAM: 4 GB** so containers + OS and spikes stay comfortable.

| Option        | Instance type | vCPUs | RAM  | Use case              | On-demand (us-east-1, ~monthly) |
|---------------|---------------|-------|------|------------------------|----------------------------------|
| **Minimum**   | t3.medium     | 2     | 4 GB | Dev / low traffic      | ~$30                             |
| **Recommended** | t3.large    | 2     | 8 GB | Production V6         | ~$60                             |
| **Comfortable** | t3.xlarge   | 4     | 16 GB| Higher traffic / RAG   | ~$120                            |

- **t2.medium** (2 vCPU, 4 GB): ~$34/month — ok for light production but 4 GB is tight for 2G+0.5G limits + OS.
- **t2.micro / t2.small**: 1–2 GB RAM — **not** suitable for V6 with current production compose (containers would be constrained or OOM).

### EC2-B (load testing, optional)
- Load-driver image ~250 MB, 3 containers; minimal CPU/memory when running.
- **t3.micro** or **t3.small** (1–2 GB) is enough; run only during test windows to save cost.

### Database: RDS vs same-host Postgres
- **Current:** Postgres in Docker on EC2-A (512 MB limit).
- **Upgrade:** For production resilience, move to **RDS** (e.g. db.t3.micro or db.t3.small). Adds ~$15–30/month but gives backups, patches, and frees EC2 memory.

---

## Cost snapshot (us-east-1, Linux, on-demand)

| Setup | EC2-A      | EC2-B (optional) | Est. monthly |
|-------|------------|-------------------|--------------|
| **Budget**   | t3.medium (4 GB)  | —                | **~$30**     |
| **Recommended** | t3.large (8 GB) | t3.micro when used | **~$60–65** |
| **With RDS** | t3.large + RDS db.t3.micro | — | **~$75–90**  |
| **With ELB + NAT** (like before) | t3.large | — | **~$60 + ~$35 ELB + ~$32 NAT ≈ $127** |

So:
- **Server type:** **t3.large** for EC2-A (8 GB RAM, 2 vCPU) matches the 2G+0.5G memory footprint and gives headroom for V6.
- **Memory footprint:** 2.5 GB reserved for containers; 4 GB host minimum, **8 GB recommended**.
- **Cost:** **~$60/month** for EC2-A only; **~$127/month** if you add ELB + NAT again (as in the old checklist).

---

## Summary

| Question | Answer |
|----------|--------|
| **What we used before?** | One EC2 (ID in checklist), type not specified; docs mentioned t2.micro for new free-tier; total AWS ~$129/mo with ELB + NAT + ECS. |
| **Server type for V6?** | **t3.large** (2 vCPU, 8 GB) for EC2-A. |
| **Memory footprint?** | Containers: 2 GB (platform) + 512 MB (postgres); host: **4 GB minimum, 8 GB recommended**. |
| **Cost?** | **~$60/month** (EC2-A only); **~$75–90** with RDS; **~$127** if you reintroduce ELB + NAT. |

---

## References in repo

- `kpi-dashboard/AWS_SHUTDOWN_CHECKLIST.md` — past costs, instance ID, what to turn off.
- `kpi-dashboard/EC2_DEPLOYMENT_GUIDE.md` — t2.micro free tier, security groups, Docker on EC2.
- `kpi-dashboard/QUICK_AWS_DEPLOYMENT.md` — App Runner / ECS cost ranges.
- `kpi-dashboard/docker-compose.production.yml` — 2G / 512M limits.
- `docs/ARCHITECTURE_CONTAINERS.md` — EC2-A vs EC2-B, container list.
