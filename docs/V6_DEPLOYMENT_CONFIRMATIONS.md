# V6 Deployment Confirmations

## 1. Load driver from your laptop → V6 instance ✅ **Confirmed**

**Yes.** Run the load driver on your laptop and point it at the V6 instance over HTTPS.

- On your laptop (no need for EC2-B):
  ```bash
  cd <repo>/CustomerSuccessAI-DataCenter
  export CS_PULSE_BASE_URL=https://www.auctusai.ai/CSPulseV6
  docker compose -f docker-compose.loaddriver-standalone.yml up -d
  # Or run without Docker: pip install -r load-driver/requirements.txt && python load-driver/driver.py --base-url https://www.auctusai.ai/CSPulseV6 --scenarios 1,2a,... --customers 1,2,3
  ```
- Ensure the V6 instance allows HTTPS from your IP (security group / firewall) and that the load driver can resolve `www.auctusai.ai` to your EC2 (or ALB).

**No issues** with driving test scenarios from the laptop to V6.

---

## 2. SSL under www.auctusai.ai/CSPulseV6 ✅ **Confirmed (with config changes)**

**Yes**, you can run V6 with SSL at **https://www.auctusai.ai/CSPulseV6**. Your registered domain is assumed to be **auctusai.ai** (if it’s different, substitute it below).

**What you need:**

| Item | What to do |
|------|------------|
| **SSL certificate** | Use AWS Certificate Manager (ACM) for `www.auctusai.ai` (or `*.auctusai.ai`). Attach to ALB or CloudFront in front of the instance. |
| **DNS** | Point `www.auctusai.ai` to the ALB (or EC2 if no ALB). Optionally a CNAME for `CSPulseV6` if you want a subdomain instead of path. |
| **App under subpath /CSPulseV6** | The app is currently built for root `/`. To serve at `/CSPulseV6` you need the following. |

**Required app/config changes for /CSPulseV6:**

1. **React (frontend)**  
   - Set base path so assets and router use `/CSPulseV6`:
     - In `package.json`: `"homepage": "/CSPulseV6"` (or `"https://www.auctusai.ai/CSPulseV6"`).
     - In `App.tsx`: `<Router basename="/CSPulseV6">` (or equivalent if you switch to `createBrowserRouter`).
   - Rebuild the frontend so all asset paths and client-side routes are under `/CSPulseV6`.

2. **Nginx (in container)**  
   - Serve the app and API under the subpath, e.g.:
     - `location /CSPulseV6/` → serve React build (root adjusted so files are under `/CSPulseV6`).
     - `location /CSPulseV6/api/` → `proxy_pass http://127.0.0.1:5059/api/` (strip or preserve prefix as needed).
   - Ensure `try_files` for the SPA fallback uses `/CSPulseV6/index.html`.

3. **Backend (Flask)**  
   - If the app uses redirects or cookie paths, set `APPLICATION_ROOT` or `SESSION_COOKIE_PATH` to `/CSPulseV6` so cookies and redirects stay under the same path. CORS and API paths are usually fine as long as the browser sends requests to `https://www.auctusai.ai/CSPulseV6/api/...`.

4. **Load driver and bookmarks**  
   - Use base URL: `https://www.auctusai.ai/CSPulseV6` (no trailing slash for the base). All API calls will go to `https://www.auctusai.ai/CSPulseV6/api/...`.

**Summary:** No fundamental issue with SSL or subpath. Plan for the above changes and test locally (e.g. `https://localhost/CSPulseV6`) before going live.

### Extra cost for SSL: ACM + ALB or CloudFront

| Component | Cost |
|-----------|------|
| **ACM (SSL certificate)** | **$0** — No charge when used with ALB, CloudFront, or other supported AWS services. |
| **ALB (Application Load Balancer)** | **~\$18–35/month** (us-east-1): ~\$0.025/hr (~\$18.40/month) plus LCU usage (~\$0.008 per LCU-hour). Light demo traffic often adds ~\$5–15 in LCUs → **~\$24–35 total**. Your earlier bill had ELB ~\$35. |
| **CloudFront** (alternative to ALB) | **$0–~\$5/month** for demo-level traffic: free tier includes 1 TB data transfer out and 10M requests/month for 12 months; data from EC2 → CloudFront is free. After free tier, pay-as-you-go is ~\$0.085/GB and ~\$0.0075 per 10k requests. For a few demos, often **$0** (free tier) or a few dollars. |

**Summary:** ACM adds **no** extra cost. The extra cost is the **ALB** (~**\$24–35/month**) or **CloudFront** (~**\$0–5/month** for light use). So **SSL in front of the instance costs about \$0 (CloudFront free tier) to ~\$35 (ALB)** depending on which you use.

---

## 3. Same instance for Claude.ai demo via agents ✅ **Confirmed**

**Yes.** You can use the same V6 instance for demos run via Claude.ai (or any agent) that call your APIs.

- The agent (or browser) will call the same base URL: `https://www.auctusai.ai/CSPulseV6` (and `/CSPulseV6/api/...`).
- Ensure:
  - **HTTPS** is working and the certificate is valid so agents/browsers don’t reject the connection.
  - **CORS**: If the demo runs in a browser (e.g. from Claude’s side), your backend must allow the origin that serves the demo (or use a broad policy for demo only). If the agent calls the API server-to-server, CORS is not an issue.
  - **Auth**: If your APIs require login or API keys, the agent needs the same (e.g. session cookie, bearer token, or API key in headers).

**No issues** with using the same V6 instance for both load testing (from laptop) and Claude.ai-driven demos, as long as the above are set.

---

## 4. Storage cost after teardown – use **S3** (you mentioned “S4”; S3 is the right service)

**Yes.** After you spin down EC2, storing data in **Amazon S3** is much cheaper than leaving instances running.

**Rough S3 storage cost (us-east-1):**

| Storage class | Typical use | $/GB/month (approx) | 10 GB | 50 GB |
|---------------|-------------|----------------------|-------|-------|
| **S3 Standard** | Frequent access | ~$0.023 | ~$0.23 | ~$1.15 |
| **S3 Standard-IA** | Infrequent access | ~$0.0125 | ~$0.13 | ~$0.63 |
| **S3 Glacier Instant** | Archive, instant retrieval | Lower | — | — |

- **EC2** (e.g. t3.large): ~\$60/month even if idle.
- **S3**: A few GB (DB dumps, Docker image tarballs, configs) is on the order of **\$0.20–1/month** for Standard.

**What to put in S3 when you tear down:**

- **Database backup**: `pg_dump` (or your backup format) of the V6 Postgres DB → upload to S3. Restore to a new RDS or EC2 Postgres when you bring V6 back.
- **App/artifacts**: Configs, env templates, any uploaded files or vertical data you care about → S3 (or a tarball in S3).
- **Docker images**: Either keep in ECR (small monthly storage cost) or save as tarballs to S3 if you prefer not to rely on ECR.

**Recommendation:** Before stopping the instance, run a DB backup and upload it (and any critical files) to an S3 bucket. Then terminate/stop the EC2. When you need to run demos again, launch a new instance (or start the stopped one), restore from S3, and redeploy. Storage in S3 for tens of GB is typically **well under \$2/month**, so **yes, it’s much cheaper than keeping EC2 running**.

---

## Quick reference

| Question | Answer |
|----------|--------|
| Load driver from laptop to V6? | ✅ Yes. Set `CS_PULSE_BASE_URL=https://www.auctusai.ai/CSPulseV6` and run load driver locally. |
| SSL at www.auctusai.ai/CSPulseV6? | ✅ Yes. Need: ACM cert, DNS, and app changes (homepage, Router basename, nginx subpath, cookie path if used). |
| Same instance for Claude.ai demo? | ✅ Yes. Same URL; ensure HTTPS, CORS (if browser), and auth for the agent. |
| Storage after teardown (S3)? | ✅ Yes. Use S3 (not “S4”); cost is much lower than EC2 (e.g. &lt;\$2/month for tens of GB). Back up DB and key files to S3 before tearing down. |
