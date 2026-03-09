# Updating API Keys on EC2 (Without Breaking the DB)

When you need to set or rotate **OPENAI_API_KEY** and **ANTHROPIC_API_KEY** on the EC2 instance, **do not overwrite the entire `.env`** file. The EC2 `.env` was created when the stack was first run; **POSTGRES_PASSWORD** and **SECRET_KEY** were set at that time and Postgres was initialized with them. Replacing `.env` with a copy from your laptop can change those values and cause **password authentication failed for user "cspulse"** and platform restart loops.

## Recommended: Use the script

From your laptop (repo root), with a `.env` that contains your API keys (e.g. `kpi-dashboard/.env`):

```bash
./scripts/update-ec2-api-keys.sh <EC2_IP>
# or
CSPULSE_EC2_HOST=3.81.222.159 ./scripts/update-ec2-api-keys.sh
```

The script:

- Reads **OPENAI_API_KEY** and **ANTHROPIC_API_KEY** from your local `kpi-dashboard/.env` (or `kpi-dashboard/backend/.env`).
- Updates **only** those two variables in `~/cspulse/.env` on EC2; **POSTGRES_PASSWORD** and **SECRET_KEY** are left unchanged.
- Restarts only the **platform** container (not Postgres), so the database is untouched.
- Creates a timestamped backup of `.env` on EC2 before changing it (e.g. `.env.bak.20260308223700`).

**Prerequisites:** SSH key `cspulse-v6-key.pem` in the repo root, and EC2 host reachable (IP or `CSPULSE_EC2_HOST`).

## Manual method (if you prefer)

1. SSH to EC2 and go to the app dir:
   ```bash
   ssh -i cspulse-v6-key.pem ec2-user@<EC2_IP>
   cd ~/cspulse
   ```

2. Back up `.env`:
   ```bash
   cp .env .env.bak.$(date +%Y%m%d%H%M%S)
   ```

3. Edit `.env` and change **only** the two lines:
   - `OPENAI_API_KEY=...`
   - `ANTHROPIC_API_KEY=...`  
   Do **not** change `POSTGRES_PASSWORD` or `SECRET_KEY`.

4. Restart only the platform:
   ```bash
   sudo docker compose -f docker-compose.ec2-from-s3.yml up -d --force-recreate cs-pulse
   ```

5. Check health:
   ```bash
   curl -s http://localhost/api/health
   ```

## If you already overwrote `.env` and the platform is crashing

Restore **POSTGRES_PASSWORD** and **SECRET_KEY** to the values the running Postgres was initialized with. On EC2 you may have a backup (e.g. `.env.bak.*`); if not, you must reset Postgres (remove the postgres volume and start again, which loses DB data) or recover the original values from wherever they were first generated. After fixing, restart the platform only:

```bash
sudo docker compose -f docker-compose.ec2-from-s3.yml up -d --force-recreate cs-pulse
```
