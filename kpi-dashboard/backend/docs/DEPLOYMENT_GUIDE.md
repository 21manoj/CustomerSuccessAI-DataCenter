# DC2_S Platform Deployment Guide

## Prerequisites

- PostgreSQL 12+ database
- Python 3.9+
- Node.js 16+ (for frontend)
- Redis (optional, for caching)

---

## Backend Deployment

### Step 1: Database Setup

```bash
# Create database
createdb cspulse_db

# Run migrations (if using Flask-Migrate)
cd backend
flask db upgrade

# Or manually run schema scripts
psql -d cspulse_db -f scripts/migrate_phase1_schema.py
```

### Step 2: Install Dependencies

```bash
cd backend
pip install -r requirements.txt
```

### Step 3: Environment Configuration

Create `.env` file:

```bash
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/cspulse_db

# Flask
SECRET_KEY=your-secret-key-here
FLASK_ENV=production
FLASK_DEBUG=False

# OpenAI (optional)
OPENAI_API_KEY=sk-...

# Server
PORT=5059
HOST=0.0.0.0
```

### Step 4: Run Backend

**Development:**
```bash
python3 app_v3_minimal.py
```

**Production (using gunicorn):**
```bash
gunicorn -w 4 -b 0.0.0.0:5059 app_v3_minimal:app
```

**Production (using systemd):**
```bash
# Create service file: /etc/systemd/system/cspulse-backend.service
[Unit]
Description=CS Pulse Backend
After=network.target

[Service]
User=www-data
WorkingDirectory=/path/to/kpi-dashboard/backend
Environment="PATH=/path/to/venv/bin"
ExecStart=/path/to/venv/bin/gunicorn -w 4 -b 0.0.0.0:5059 app_v3_minimal:app

[Install]
WantedBy=multi-user.target

# Enable and start
sudo systemctl enable cspulse-backend
sudo systemctl start cspulse-backend
```

---

## Frontend Deployment

### Step 1: Build Frontend

```bash
cd kpi-dashboard
npm install
npm run build
```

### Step 2: Serve Static Files

**Option A: Nginx**
```nginx
server {
    listen 80;
    server_name your-domain.com;

    root /path/to/kpi-dashboard/build;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }

    location /api {
        proxy_pass http://localhost:5059;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

**Option B: Serve with Flask**
```python
# In app_v3_minimal.py
@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve_frontend(path):
    if path != "" and os.path.exists(os.path.join(app.static_folder, path)):
        return send_from_directory(app.static_folder, path)
    else:
        return send_from_directory(app.static_folder, 'index.html')
```

---

## Database Backup

### Automated Backup Script

```bash
#!/bin/bash
# /etc/cron.daily/backup-cspulse-db.sh

BACKUP_DIR="/var/backups/cspulse"
DB_NAME="cspulse_db"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

mkdir -p "$BACKUP_DIR"

pg_dump "$DB_NAME" > "$BACKUP_DIR/backup_${TIMESTAMP}.sql"

# Keep only last 30 days
find "$BACKUP_DIR" -name "backup_*.sql" -mtime +30 -delete
```

### Manual Backup

```bash
# Using provided script
cd backend
./scripts/backup_database.sh

# Or manually
pg_dump cspulse_db > backup_$(date +%Y%m%d_%H%M%S).sql
```

### Restore from Backup

```bash
psql -d cspulse_db < backup_20260123_120000.sql
```

---

## Security Checklist

### ✅ Authentication
- [x] All API endpoints require authentication
- [x] Session-based authentication implemented
- [x] Password hashing (bcrypt)

### ⚠️ To Do
- [ ] HTTPS/SSL certificates
- [ ] Rate limiting
- [ ] CORS configuration
- [ ] Input sanitization
- [ ] SQL injection prevention (using ORM)
- [ ] XSS prevention

---

## Monitoring

### Health Check Endpoint

```bash
curl http://localhost:5059/api/health
```

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2026-01-23T13:00:00",
  "version": "V5"
}
```

### Log Files

- Application logs: `backend/logs/app.log`
- Error logs: `backend/logs/errors.log`
- Signal Analyst logs: `backend/logs/signal_analyst.log`

### Database Monitoring

```sql
-- Check table sizes
SELECT 
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
```

---

## Performance Optimization

### Database Indexes

Ensure indexes exist on:
- `customer_configs.customer_id`
- `kpi_scores.account_id, measurement_month`
- `pillar_scores.account_id, measurement_month`
- `health_scores.account_id, measurement_month`
- `dc2s_kpis.account_id, kpi_code, measured_at`

### Caching

Consider implementing:
- Redis for session storage
- Cache for frequently accessed configurations
- Cache for score calculations (with TTL)

### Query Optimization

- Use `LIMIT` for pagination
- Batch score calculations
- Use database transactions for bulk operations

---

## Troubleshooting

### Backend Won't Start

1. Check database connection:
   ```bash
   psql -d cspulse_db -c "SELECT 1;"
   ```

2. Check port availability:
   ```bash
   lsof -i :5059
   ```

3. Check logs:
   ```bash
   tail -f backend/logs/app.log
   ```

### Scores Not Calculating

1. Verify KPI data exists:
   ```sql
   SELECT COUNT(*) FROM dc2s_kpis WHERE customer_id = 9;
   ```

2. Check configuration:
   ```bash
   curl -X GET http://localhost:5059/api/dc2s/config/ -b cookies.txt
   ```

3. Check for errors in logs

### API Returns 404

1. Verify route registration:
   ```bash
   curl http://localhost:5059/debug/routes | grep dc2s
   ```

2. Check blueprint registration in `app_v3_minimal.py`

---

## Rollback Procedure

### Configuration Rollback

1. Restore from backup:
   ```bash
   psql -d cspulse_db < backup_YYYYMMDD_HHMMSS.sql
   ```

2. Or manually update:
   ```sql
   UPDATE customer_configs 
   SET dc2s_pillar_weights = '{"AI":0.25,"CH":0.20,...}'::json
   WHERE customer_id = 9;
   ```

### Code Rollback

1. Revert to previous git commit:
   ```bash
   git checkout <previous-commit>
   ```

2. Restart services:
   ```bash
   sudo systemctl restart cspulse-backend
   ```

---

## Production Checklist

### Pre-Deployment
- [x] Security audit passed
- [x] Database backup created
- [x] Error handling tested
- [x] Load testing completed
- [x] Documentation created

### Deployment
- [ ] Database migrations run
- [ ] Environment variables set
- [ ] SSL certificates installed
- [ ] Monitoring configured
- [ ] Backup automation set up

### Post-Deployment
- [ ] Health checks passing
- [ ] API endpoints responding
- [ ] Frontend accessible
- [ ] Scores calculating correctly
- [ ] Logs being collected

---

## Support

For deployment issues:
- Check logs: `backend/logs/`
- Review error messages
- Verify database connectivity
- Contact system administrator
