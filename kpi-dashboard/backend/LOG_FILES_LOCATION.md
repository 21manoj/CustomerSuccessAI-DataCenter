# Log Files Location

## Main Log Files

### 1. Backend Application Log
**Location:** `kpi-dashboard/backend/backend.log`
- **Size:** ~3.6MB (36,762 lines)
- **Content:** Main Flask application logs, API requests, database queries
- **View recent entries:**
  ```bash
  tail -100 backend.log
  ```
- **Search for errors:**
  ```bash
  grep -i "error\|exception\|traceback" backend.log | tail -50
  ```

### 2. Signal Analyst Log
**Location:** `kpi-dashboard/backend/logs/signal_analyst.log`
- **Size:** ~530KB (4,662 lines)
- **Content:** Signal analyst agent logs, RAG system logs
- **View recent entries:**
  ```bash
  tail -100 logs/signal_analyst.log
  ```

### 3. Error Log (Signal Analyst)
**Location:** `kpi-dashboard/backend/logs/signal_analyst_errors.log`
- **Size:** 0 bytes (currently empty)
- **Content:** Error-specific logs from signal analyst

### 4. API Costs Log
**Location:** `kpi-dashboard/backend/logs/api_costs.log`
- **Content:** API cost tracking logs

## Log Configuration

### Backend Log (`backend.log`)
- Configured in `app_v3_minimal.py` (lines 710-717)
- Uses `logging_config.py` for setup
- Default log level: `INFO`
- Can be changed via `LOG_LEVEL` environment variable
- Log file path can be changed via `LOG_FILE` environment variable

### Signal Analyst Logs
- Configured in `utils/logging_config.py`
- Uses structured JSON logging
- Logs directory: `kpi-dashboard/backend/logs/`

## Viewing Logs

### Quick Commands

```bash
# View last 50 lines of backend log
tail -50 backend.log

# View last 100 lines with errors
tail -100 backend.log | grep -i error

# Search for SQLAlchemy issues
grep -i "sqlalchemy\|import.*error" backend.log | tail -30

# View real-time logs (follow mode)
tail -f backend.log

# View logs from last hour
grep "$(date -v-1H +'%Y-%m-%d %H')" backend.log

# Count errors in log
grep -i "error\|exception" backend.log | wc -l
```

### Search for Specific Issues

```bash
# SQLAlchemy import errors
grep -i "sqlalchemy.*import\|import.*sqlalchemy" backend.log

# Import errors in general
grep -i "importerror\|modulenotfounderror" backend.log

# Traceback/stack traces
grep -A 20 "Traceback" backend.log

# All warnings
grep -i "warning" backend.log | tail -50
```

## Current Log Status

Based on recent log review:
- ✅ No SQLAlchemy import errors found
- ✅ No import errors in recent logs
- ✅ Application running normally
- ✅ All API endpoints responding correctly

## Console vs Log Files

**Note:** If you're seeing errors in the console but not in log files, they might be:
1. **Startup warnings** (printed to stdout/stderr before logging is initialized)
2. **Python warnings** (not logged, only printed)
3. **Deprecation warnings** (printed but not logged)

To capture console output:
```bash
# Run app and capture all output
python3 app_v3_minimal.py 2>&1 | tee console_output.log
```

## Log File Locations Summary

| Log File | Path | Purpose |
|----------|------|---------|
| Backend Log | `backend/backend.log` | Main application logs |
| Signal Analyst | `backend/logs/signal_analyst.log` | Signal analyst & RAG logs |
| Error Log | `backend/logs/signal_analyst_errors.log` | Error-specific logs |
| API Costs | `backend/logs/api_costs.log` | API cost tracking |

## Troubleshooting

If you see SQLAlchemy import errors in console:

1. **Check Python environment:**
   ```bash
   python3 -c "from sqlalchemy import text; print('OK')"
   ```

2. **Check installed packages:**
   ```bash
   pip3 list | grep -i sqlalchemy
   ```

3. **Check for circular imports:**
   - Look for import statements at module level
   - Check if models are imported before db is initialized

4. **Check console output directly:**
   - Errors might be printed before logging starts
   - Check the terminal/console where you started the app
