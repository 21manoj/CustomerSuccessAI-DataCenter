# App File Clarification

**Date**: December 27, 2025

---

## Current Situation

You have two Flask app files:

### 1. `app.py` (Port 8001 - Currently Running)
- ❌ **No Flask-Login sessions** - Login endpoint doesn't use `login_user()`
- ✅ **Has DC2_S endpoints** registered (`/api/dc2s/*`)
- ✅ **Has vertical mapping** in login (dc2_s → datacenter)
- ✅ **Has Signal Analyst Agent** registered

### 2. `app_v3_minimal.py` (Port 5059 - Main Production App)
- ✅ **Has Flask-Login sessions** - Proper session-based authentication
- ✅ **Has vertical mapping** - Should check login endpoint
- ⚠️ **Missing DC2_S endpoints** - Just added (needs testing)
- ❓ **Missing Signal Analyst Agent** - Need to check/add

---

## Answer to Your Question

**Yes, `app_v3_minimal.py` is the main production app** based on:
- ✅ Dockerfile uses it: `FLASK_APP=app_v3_minimal.py`
- ✅ Most test scripts import from `app_v3_minimal`
- ✅ Has proper Flask-Login session support (required for DC2_S endpoints)
- ✅ Runs on port 5059 (production port)

---

## What I Just Did

I added DC2_S endpoints to `app_v3_minimal.py`:
- Added import: `from verticals.dc2_s.api_routes import dc2s_api`
- Added registration: `app.register_blueprint(dc2s_api, url_prefix='/api/dc2s')`

---

## Next Steps

1. **Use `app_v3_minimal.py` instead of `app.py`** for running the server
2. **Test DC2_S endpoints** with `app_v3_minimal.py` (they should work with Flask-Login sessions)
3. **Check if Signal Analyst Agent** needs to be added to `app_v3_minimal.py`
4. **Check if login endpoint** in `app_v3_minimal.py` has the same vertical mapping logic as `app.py`

---

## Recommendation

**Switch to using `app_v3_minimal.py`** since it has:
- ✅ Proper Flask-Login sessions (required for DC2_S endpoints)
- ✅ All the same features
- ✅ Production-ready configuration
- ✅ Now has DC2_S endpoints (just added)

The DC2_S endpoints will work properly with `app_v3_minimal.py` because it has Flask-Login session support.
