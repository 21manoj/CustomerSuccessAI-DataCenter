# EC2 stop/restart and recreate to save money

Yes, you can shut down when not needed and bring the app back later. Here’s effort and cost.

## Two ways to “turn off”

| | **Stop** (recommended for short breaks) | **Terminate** (for long idle) |
|--|----------------------------------------|-------------------------------|
| **Effort to bring back** | Low: start instance, wait ~1–2 min, app is still there | Higher: new instance + redeploy (or launch from AMI) |
| **Data** | Preserved (EBS + Postgres on disk) | Lost unless you have backup/restore or AMI |
| **Cost while “off”** | EBS only (~\$3–5/month for 30 GB gp3) | \$0 (no instance, no volume if terminated) |
| **Public IP** | **Changes** after stop/start (unless you use an Elastic IP) | New instance = new IP (or new Elastic IP) |

---

## 1. Stop and start (easiest)

**Shutdown:**  
AWS Console → EC2 → Instances → select instance → **Instance state → Stop instance**.  
Or: `aws ec2 stop-instances --instance-ids i-xxxxx`

**Bring back:**  
Instance state → **Start instance**.  
Or: `aws ec2 start-instances --instance-ids i-xxxxx`

**Rehydrate from ECR (start instance + pull images + run all containers):**  
`./scripts/rehydrate-ec2-ecr.sh [INSTANCE_ID]`  
Uses ECR only (no S3). Starts the instance if stopped, copies compose files, logs in to ECR (using your local AWS CLI), pulls platform + postgres + load-driver, and runs them. Optional: set `CSPULSE_EC2_INSTANCE_ID` or pass the instance ID; otherwise the script finds one by tag `Name=cspulse-v6`.

- Same instance, same disk, same Postgres data.
- **Caveat:** Public IP changes after start. If you use **CloudFront**, update the distribution’s **origin** to the new EC2 public DNS (e.g. `ec2-<new-ip>.compute-1.amazonaws.com`). If you use **Elastic IP** and reattach it after start, IP stays the same and CloudFront needs no change.

**Effort:** 1–2 minutes. Saves: no compute charge while stopped (~\$60/month for t3.large → ~\$0 compute; you still pay EBS).

---

## 2. Terminate and recreate when needed (maximum savings)

**“Images on S3”** = your **container images** (e.g. `cspulse-platform.tar.gz`, `cspulse-postgres.tar.gz`). They let you **reinstall the app** on a **new** EC2; they do **not** preserve DB or instance state by themselves.

**If you terminate:**

- Instance and (by default) root volume are gone.
- To run again you either:
  - **A) Launch a new instance** with `scripts/provision-ec2-v6.sh`, then on the new box: copy `.env` and compose, pull/load images from S3, start containers. You get a **fresh Postgres** unless you **restore from a backup** (see below).
  - **B) Create an AMI** before terminating: EC2 → Create image. Later, launch a **new** instance from that AMI so it comes back with OS + Docker + data as of the snapshot. Then start the instance and start containers (or add user-data to do it). Effort: one-time AMI creation; recreating is “launch from AMI + start.”

**Effort (terminate + recreate without AMI):**

1. Before terminate: optional but recommended — **back up Postgres** and put the dump in S3 (see below).
2. Terminate instance (Console or `aws ec2 terminate-instances`).
3. When needed: run `./scripts/provision-ec2-v6.sh` (or use the same script/pattern).
4. SSH to new instance; copy your `.env` and `docker-compose.ec2-from-s3.yml` (or equivalent) into `~/cspulse`.
5. Pull images from S3, load, start containers (as in docs/EC2_V6_TWO_IMAGES.md).
6. If you saved a DB backup: restore it into Postgres.
7. If using CloudFront: update distribution origin to the **new** EC2 public DNS.

**Effort (with AMI):** Create image once; later “launch from AMI → start instance → start Docker” (and optionally a small script). No manual restore if the AMI had the DB volume.

**Cost:** While terminated you pay **\$0** for that instance and its default root volume. You only pay for S3 (backups, image tarballs) and, if you use it, EBS snapshots/AMIs (small).

---

## Quick DB backup before stop/terminate

On the EC2 box (or from a host that can reach Postgres):

```bash
# From EC2, with postgres container running (adjust container name if needed)
docker exec cs-pulse-postgres pg_dump -U postgres -d kpi_dashboard -Fc -f /tmp/db.dump
# Copy out and upload to S3, e.g.:
docker cp cs-pulse-postgres:/tmp/db.dump ./db.dump
aws s3 cp db.dump s3://YOUR_BUCKET/backups/cspulse-db-$(date +%Y%m%d).dump
```

Restore on a new instance after Postgres is running:

```bash
docker exec -i cs-pulse-postgres pg_restore -U postgres -d kpi_dashboard -c -Fc < db.dump
# (or copy db.dump into container first, then pg_restore from inside)
```

---

## Summary

| Goal | Action | Saves money? |
|------|--------|--------------|
| Pause for a few days/weeks, same data | **Stop** instance | Yes (no compute; pay EBS only) |
| Idle for months, don’t care about state | **Terminate**; recreate later from provision script + S3 images | Yes (no EC2/EBS; pay S3/snapshots only) |
| Idle for months, want same state back | **AMI** before terminate; later **launch from AMI** | Yes; slightly more setup (AMI creation + possibly Elastic IP for CloudFront) |

So: **shutdown/restart is low effort**; **recreating from S3 images is doable** and saves the most when you fully terminate, but you need either a **DB backup/restore** or an **AMI** if you want your current data back.
