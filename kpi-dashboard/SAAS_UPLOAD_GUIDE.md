# SaaS Data Upload Guide

## Important: No Server Restarts Required! 🚀

This is a **true SaaS system** designed to run 24/7 without downtime. Data uploads do **NOT** require server restarts.

## How It Works

### 1. **Database-Driven Design**
- All data stored in SQLite database
- Backend reads from database dynamically
- New data immediately available
- **No restart needed** for new data

### 2. **Hot Reload Capability**
- Flask development mode (with reloader) auto-reloads code changes
- Database changes are picked up automatically
- Frontend served as static files (no restart needed)

### 3. **When Restarts ARE Needed**

Only restart containers when:
- ❌ Backend code changes (`*.py` files modified)
- ❌ Frontend code changes (`*.tsx`, `*.ts` files modified)
- ❌ Configuration changes (`docker-compose.yml`, nginx config)
- ❌ Dependencies updated (`requirements.txt`, `package.json`)

Do **NOT** restart for:
- ✅ Database-only operations (insert, update, delete)
- ✅ New data uploads via UI or API
- ✅ New customer registrations
- ✅ New accounts or KPIs created
- ✅ Playbook executions
- ✅ Reports generated

## Uploading Data for a New Customer

### Method 1: Via UI (No Script Needed)
1. **Register customer** via `/register` page
2. **Login** with new credentials
3. **Upload data** via Data Integration tab
4. **Done!** - Data immediately available

### Method 2: Via Script (For Bulk Data)
1. **Create upload script** (see `backend/upload_company_b_data.py` as example)
2. **Run script locally** to populate local database
3. **Copy database to AWS** (if needed):
   ```bash
   scp -i key.pem instance/kpi_dashboard.db ec2-user@server:/path/to/db
   ```
4. **That's it!** - No backend restart needed

## What Happened With My Earlier Restarts

I incorrectly restarted the backend during our troubleshooting session. This was:
- ❌ **Not green space required** for new data
- ✅ **Only needed** because we were testing code changes
- ⚠️ **Should NOT** be done for regular data uploads

## Best Practices for SaaS Operations

### ✅ Do This:
```bash
# Upload data via API or UI
curl -X POST /api/upload -F file=@data.csv

# EMAIL verification - data is immediately accessible
curl /api/accounts

# Update settings via UI
# Data persists in database without restart
```

### ❌ Don't Do This for Data Uploads:
```bash
# Unnecessary - only restart for code changes
docker restart backend
docker restart frontend

# Unnecessary - database changes are immediate
service nginx restart
```

## Architecture Benefits

### Why No Restarts Are Needed

1. **Separated Concerns**:
   - **Database**: Persistent storage (always on)
   - **Backend**: Stateless API (queries DB on each request)
   - **Frontend**: Static files (cached by browser)

2. **Dynamic Data Access**:
   - Every API call queries database
   - New data immediately in results
   - No caching of data structure

3. **Stateless Design**:
   - No in-memory data structures
   - Everything comes from database
   - New transactions = new data accessible

## Summary

**For Data Uploads**: ✅ **Just upload** - it's immediately available  
**For Code Changes**: ⚠️ **Restart needed** - backend/frontend must reload

The system is designed for true SaaS operation: **add data, not restart services!**
