# Deployment Pattern: Build → Push → Pull → Run

We follow this flow for CS Pulse:

- **Local machine:** `docker build` → `docker push` → **ECR** or **Docker Hub**
- **EC2:** `docker pull` → `docker run` (via `docker compose`)

No building on EC2 and no S3 tarballs for images. The registry is the single source of truth.

---

## 1. Local: Build and push

### Using AWS ECR

1. **Create ECR repositories** (once per account/region):

   ```bash
   aws ecr create-repository --repository-name cspulse-platform --region us-east-1
   aws ecr create-repository --repository-name cspulse-postgres --region us-east-1
   ```

2. **Log in to ECR:**

   ```bash
   aws ecr get-login-password --region us-east-1 | \
     docker login --username AWS --password-stdin YOUR_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com
   ```

3. **Build for linux/amd64** (required if your laptop is Apple Silicon; EC2 is amd64):

   ```bash
   # Build from project root (includes load-driver in image)
   cd CustomerSuccessAI-DataCenter
   docker buildx build --platform linux/amd64 -f kpi-dashboard/Dockerfile.cspulse -t YOUR_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/cspulse-platform:latest --load .
   docker buildx build --platform linux/amd64 -f kpi-dashboard/docker/postgres/Dockerfile -t YOUR_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/cspulse-postgres:latest --load kpi-dashboard/docker/postgres
   ```

   On x86_64 you can use plain `docker build` and tag as above.

4. **Push:**

   ```bash
   docker push YOUR_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/cspulse-platform:latest
   docker push YOUR_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/cspulse-postgres:latest
   ```

### Using Docker Hub

1. **Log in:** `docker login`

2. **Build and tag** (use your Docker Hub username):

   ```bash
   # Build from project root (includes load-driver in image)
   cd CustomerSuccessAI-DataCenter
   docker buildx build --platform linux/amd64 -f kpi-dashboard/Dockerfile.cspulse -t YOUR_DOCKERHUB_USER/cspulse-platform:latest --load .
   docker buildx build --platform linux/amd64 -f kpi-dashboard/docker/postgres/Dockerfile -t YOUR_DOCKERHUB_USER/cspulse-postgres:latest --load kpi-dashboard/docker/postgres
   ```

3. **Push:**

   ```bash
   docker push YOUR_DOCKERHUB_USER/cspulse-platform:latest
   docker push YOUR_DOCKERHUB_USER/cspulse-postgres:latest
   ```

### GitHub Actions (native `linux/amd64`, recommended for EC2)

Use the workflow **`.github/workflows/cspulse-ecr-build-push.yml`**. It runs on **`ubuntu-latest`** (real x86_64), so you avoid slow **QEMU/`amd64` emulation on Apple Silicon**.

1. Add repository **secrets**: `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY` (IAM user or role with **ECR push** permissions to `cspulse-platform`, `cspulse-postgres`, `cspulse-load-driver`).
2. **Push to `main`** (with changes under `kpi-dashboard/` or `load-driver/`) or run **Actions → CS Pulse — ECR build (amd64) → Run workflow** (optional **`no_cache`** for a full rebuild).

**After images are in ECR:** either run `./scripts/rehydrate-ec2-ecr.sh` from your laptop (pull + compose on EC2), or **build on EC2 from git** (`kpi-dashboard/docker-compose.ec2-build.yml`, `scripts/ec2-git-pull-rebuild.sh`). A **CI rehydrate over SSH** job was removed from the workflow for now (restore from git history if you want it back).

---

## 2. EC2: Pull and run

1. **Set the registry in `~/cspulse/.env`:**

   - **ECR:**  
     `REGISTRY=YOUR_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com`  
     (EC2 instance role or IAM user must have `ecr:GetDownloadUrlForLayer`, `ecr:BatchGetImage`.)

   - **Docker Hub:**  
     `REGISTRY=YOUR_DOCKERHUB_USER`  
     (For private images, run `docker login` on EC2 or use a token.)

2. **Log in to the registry on EC2** (if required):

   - **ECR:**
     ```bash
     aws ecr get-login-password --region us-east-1 | sudo docker login --username AWS --password-stdin YOUR_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com
     ```
   - **Docker Hub (private):** `sudo docker login`

3. **Use the registry compose file and start:**

   ```bash
   cd ~/cspulse
   sudo docker compose -f docker-compose.ec2-registry.yml pull
   sudo docker compose -f docker-compose.ec2-registry.yml up -d
   ```

4. **Check:**

   ```bash
   sudo docker compose -f docker-compose.ec2-registry.yml ps
   curl -s http://localhost/api/health
   ```

---

## Second platform on same EC2 (shared Postgres)

For extra app capacity or **load tests against a second endpoint** without a second database:

1. **Compose:** `kpi-dashboard/docker-compose.ec2-platform-replica.yml` defines **`cs-pulse-b`** (`cspulse-platform-b`) with the same image, env, and **named volumes** as `cs-pulse`, and the same `DATABASE_URL` to `postgres`.
2. **Ports:** Host **`9080` → HTTP**, **`9443` → HTTPS**, **`8002` → MCP** (primary stays `80` / `443` / `8001`).
3. **Deploy:** `scripts/rehydrate-ec2-ecr.sh` copies this file and runs compose with **three** `-f` files (registry + load-driver + replica).
4. **Load tester (from your machine):**  
   `BASE_URL=http://<EC2_PUBLIC_IP>:9080`
5. **Security group:** Allow inbound **TCP 9080** (and **9443** / **8002** if you use them) from your IP or test runners.
6. **From another container** on `cspulse-net`: `http://cspulse-platform-b:5059` (same pattern as `cspulse-platform:5059` for the load-driver image).

### Restart on EC2 (pick up compose env changes, e.g. `FEATURE_CONTEXT_GRAPH`)

Run **on the EC2 instance** from `~/cspulse` (same three compose files as `scripts/rehydrate-ec2-ecr.sh`). `docker restart` does **not** reload environment variables from YAML — use **`up -d --force-recreate`** when you changed `environment:` in compose or `.env` values referenced there.

**Second platform only** (`cspulse-platform-b`, port 9080):

```bash
cd ~/cspulse
sudo docker compose -f docker-compose.ec2-registry.yml -f docker-compose.ec2-loaddriver.yml -f docker-compose.ec2-platform-replica.yml up -d --force-recreate cs-pulse-b
```

**Primary platform only** (`cspulse-platform`, ports 80/443/8001):

```bash
cd ~/cspulse
sudo docker compose -f docker-compose.ec2-registry.yml -f docker-compose.ec2-loaddriver.yml -f docker-compose.ec2-platform-replica.yml up -d --force-recreate cs-pulse
```

**Full stack** (pull new images + recreate all defined services):

```bash
cd ~/cspulse
sudo docker compose -f docker-compose.ec2-registry.yml -f docker-compose.ec2-loaddriver.yml -f docker-compose.ec2-platform-replica.yml pull
sudo docker compose -f docker-compose.ec2-registry.yml -f docker-compose.ec2-loaddriver.yml -f docker-compose.ec2-platform-replica.yml up -d
```

---

## Summary

| Step   | Where      | Action |
|--------|------------|--------|
| Build  | Local **or** **GitHub Actions** (`ubuntu-latest`) | `docker build` / `buildx` — on Apple Silicon use **CI** or `buildx --platform linux/amd64` |
| Push   | Local or CI | `docker push` to ECR |
| Pull   | EC2        | `docker compose pull` (images from registry) |
| Run    | EC2        | `docker compose up -d` |

See **EC2_V6_TWO_IMAGES.md** for EC2 setup (SSH, `.env`, CloudFront). Use **docker-compose.ec2-registry.yml** on EC2 so image names come from the `REGISTRY` (and optional tag) in `.env`.
