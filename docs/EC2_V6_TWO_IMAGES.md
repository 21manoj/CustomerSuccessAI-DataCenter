# EC2 V6: Run Only Two Images (Platform + Postgres)

Use this after provisioning the t3.large with `./scripts/provision-ec2-v6.sh`. Load driver runs from your laptop.

## What runs where

| Where | What |
|-------|------|
| **EC2 (t3.large)** | `cspulse-platform` (Flask + React + Nginx) + `cspulse-postgres` |
| **Your laptop** | Load driver (point `CS_PULSE_BASE_URL` at EC2 public IP or CloudFront URL) |

## Deployment pattern: Build → Push → Pull → Run

We use a **registry-based** flow (no building on EC2, no S3 tarballs):

- **Local:** `docker build` → `docker push` → **ECR** or **Docker Hub**
- **EC2:** `docker pull` → `docker run` (via `docker compose`)

See **[DEPLOYMENT_PATTERN_REGISTRY.md](DEPLOYMENT_PATTERN_REGISTRY.md)** for full steps (build/push from laptop, pull/run on EC2 using `docker-compose.ec2-registry.yml`).

---

## After provisioning

1. **SSH in**
   ```bash
   ssh -i cspulse-v6-key.pem ec2-user@<PUBLIC_IP>
   ```

2. **Get images from the registry** (recommended): set `REGISTRY` in `~/cspulse/.env` (e.g. `REGISTRY=YOUR_ACCOUNT.dkr.ecr.us-east-1.amazonaws.com` or your Docker Hub username), copy `docker-compose.ec2-registry.yml` to `~/cspulse`, log in to the registry on EC2, then:
   ```bash
   cd ~/cspulse
   sudo docker compose -f docker-compose.ec2-registry.yml pull
   sudo docker compose -f docker-compose.ec2-registry.yml up -d
   ```

   **Alternative — load from S3:** if images were uploaded as tarballs, load and run with pre-loaded image names:
   ```bash
   aws s3 cp s3://YOUR_BUCKET/containers/cspulse-platform.tar.gz /tmp/
   aws s3 cp s3://YOUR_BUCKET/containers/cspulse-postgres.tar.gz /tmp/
   gunzip -c /tmp/cspulse-platform.tar.gz | sudo docker load
   gunzip -c /tmp/cspulse-postgres.tar.gz | sudo docker load
   ```
   Then use `docker-compose.ec2-from-s3.yml` and start with `docker compose -f docker-compose.ec2-from-s3.yml up -d`.

3. **Create `.env`** in `~/cspulse` (copy from your repo or use the example and fill in secrets):
   ```bash
   cd ~/cspulse
   # Copy from laptop: scp -i cspulse-v6-key.pem kpi-dashboard/.env ec2-user@<IP>:~/cspulse/
   # Or edit .env.example and save as .env with real POSTGRES_PASSWORD, SECRET_KEY, OPENAI_API_KEY, ANTHROPIC_API_KEY
   ```
   **To update only API keys later** (without overwriting POSTGRES_PASSWORD/SECRET_KEY): see [EC2_UPDATE_API_KEYS.md](EC2_UPDATE_API_KEYS.md) and run `./scripts/update-ec2-api-keys.sh <EC2_IP>`.

4. **Copy the EC2 compose file** to `~/cspulse`:
   - **Registry flow:** `docker-compose.ec2-registry.yml` (set `REGISTRY` in `.env` and run `docker compose pull` then `up -d`).
   - **S3/pre-loaded flow:** `docker-compose.ec2-from-s3.yml`.
   ```bash
   # From laptop:
   scp -i cspulse-v6-key.pem kpi-dashboard/docker-compose.ec2-registry.yml ec2-user@<IP>:~/cspulse/
   # or docker-compose.ec2-from-s3.yml if using S3 tarballs
   ```

5. **Start the two containers**
   ```bash
   cd ~/cspulse
   # Registry: docker compose -f docker-compose.ec2-registry.yml pull && docker compose -f docker-compose.ec2-registry.yml up -d
   # S3:       docker compose -f docker-compose.ec2-from-s3.yml up -d
   docker compose -f docker-compose.ec2-registry.yml ps
   ```

6. **Check**
   - From EC2: `curl -s http://localhost/api/health`
   - From laptop: `curl -s http://<PUBLIC_IP>/api/health`

## SSL (zero-cost option): CloudFront

**Use CloudFront instead of an Application Load Balancer** for SSL in front of EC2:

- **Cost:** **$0–~$5/month** for demo-level traffic. Free tier includes 1 TB data transfer out and 10M requests/month for 12 months; EC2 → CloudFront is free.
- **ACM:** Certificates are **$0** when used with CloudFront (or ALB).
- **ALB alternative:** ALB is ~$24–35/month; CloudFront is the zero / low-cost option.

**Quick setup (default CloudFront URL):**

```bash
# Origin must be EC2 public DNS (CloudFront does not accept an IP). Default uses current EC2 DNS.
./scripts/create-cloudfront-for-ec2.sh
```

This creates a distribution with origin `http://ec2-3-81-222-159.compute-1.amazonaws.com` (override with `ORIGIN_HOST`), viewer redirect HTTP→HTTPS, and forwards cookies/headers so the app works. Use **https://&lt;distribution-domain&gt;.cloudfront.net** once the distribution is deployed (5–10 min).

**Current distribution (if already created):** `https://d2oqfugrb2ltg9.cloudfront.net` (Id: E2I8B0C6RDAOGT). Origins point to EC2 public DNS. If the instance gets a new IP after stop/start, run `./scripts/update-cloudfront-origin.sh [INSTANCE_ID]` (or set `ORIGIN_HOST=ec2-xx-xx-xx-xx.compute-1.amazonaws.com`) to update both origins. Rehydration script updates CloudFront automatically unless `SKIP_CLOUDFRONT_UPDATE=1`. After enabling HTTPS, set `SESSION_COOKIE_SECURE=true` on EC2 (remove `SESSION_COOKIE_SECURE=false` from `~/cspulse/.env`).

**MCP server over HTTPS:** The same distribution has a second origin (EC2 port 8001) and a path-based behavior for `/mcp*`. Use **https://d2oqfugrb2ltg9.cloudfront.net/mcp** for the MCP server (streamable-http). Direct EC2 remains **http://&lt;EC2_IP&gt;:8001/mcp** if needed.

**Custom domain + ACM (optional):**

1. Request an **ACM certificate** for your domain (e.g. `www.auctusai.ai` or `*.auctusai.ai`) in **us-east-1** (required for CloudFront).
2. Update the distribution: add **Aliases** (CNAME) and **ACMCertificateArn** (e.g. via AWS Console or `aws cloudfront update-distribution`).
3. **DNS:** Add a CNAME for your subdomain pointing to the CloudFront domain (e.g. `d2oqfugrb2ltg9.cloudfront.net`).

Then use **https://your-domain** as `CS_PULSE_BASE_URL` when running the load driver from your laptop.

See **docs/V6_DEPLOYMENT_CONFIRMATIONS.md** for more detail on SSL and subpath (/CSPulseV6).
