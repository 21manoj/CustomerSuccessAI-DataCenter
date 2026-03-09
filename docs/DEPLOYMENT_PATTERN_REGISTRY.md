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
   cd kpi-dashboard
   docker buildx build --platform linux/amd64 -f Dockerfile.cspulse -t YOUR_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/cspulse-platform:latest --load .
   docker buildx build --platform linux/amd64 -f docker/postgres/Dockerfile -t YOUR_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/cspulse-postgres:latest --load ./docker/postgres
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
   cd kpi-dashboard
   docker buildx build --platform linux/amd64 -f Dockerfile.cspulse -t YOUR_DOCKERHUB_USER/cspulse-platform:latest --load .
   docker buildx build --platform linux/amd64 -f docker/postgres/Dockerfile -t YOUR_DOCKERHUB_USER/cspulse-postgres:latest --load ./docker/postgres
   ```

3. **Push:**

   ```bash
   docker push YOUR_DOCKERHUB_USER/cspulse-platform:latest
   docker push YOUR_DOCKERHUB_USER/cspulse-postgres:latest
   ```

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

## Summary

| Step   | Where      | Action |
|--------|------------|--------|
| Build  | Local      | `docker build` (use `buildx --platform linux/amd64` on Apple Silicon) |
| Push   | Local      | `docker push` to ECR or Docker Hub |
| Pull   | EC2        | `docker compose pull` (images from registry) |
| Run    | EC2        | `docker compose up -d` |

See **EC2_V6_TWO_IMAGES.md** for EC2 setup (SSH, `.env`, CloudFront). Use **docker-compose.ec2-registry.yml** on EC2 so image names come from the `REGISTRY` (and optional tag) in `.env`.
