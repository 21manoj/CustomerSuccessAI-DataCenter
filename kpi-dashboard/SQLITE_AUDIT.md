# SQLite Database Usage Audit

**Date**: December 18, 2025  
**Status**: ✅ Main Production Apps Use PostgreSQL  
**Action Required**: Update utility scripts and Dockerfiles

---

## Summary

✅ **GOOD NEWS**: The main production applications (`app_v3_minimal.py` and `app.py`) are correctly using PostgreSQL.

⚠️ **ISSUES FOUND**: Several utility scripts, Dockerfiles, and non-production app files still reference SQLite.

---

## Production Apps Status

### ✅ Using PostgreSQL (Correct)

1. **`app_v3_minimal.py`** - Main production app
   - ✅ Uses PostgreSQL via `DATABASE_URL`
   - ✅ Raises error if `DATABASE_URL` not set
   - ✅ No SQLite fallback

2. **`app.py`** - Alternative app file
   - ✅ Uses PostgreSQL via `DATABASE_URL`
   - ✅ Validates PostgreSQL connection string
   - ✅ Raises error if not PostgreSQL

3. **`config.py`** - Configuration
   - ✅ Base `Config` class requires PostgreSQL
   - ✅ `DevelopmentConfig` requires PostgreSQL
   - ✅ `ProductionConfig` requires PostgreSQL
   - ⚠️ `TestingConfig` uses SQLite in-memory (OK for tests)

---

## Issues Found

### ⚠️ Non-Production App Files (Not Critical)

1. **`app_v3_simple.py`**
   - Uses SQLite as fallback
   - Not used in production (based on Dockerfile using `app_v3_minimal.py`)
   - **Recommendation**: Update to use PostgreSQL or mark as deprecated

2. **`app_minimal.py`**
   - Uses SQLite hardcoded
   - Not used in production
   - **Recommendation**: Update to use PostgreSQL or mark as deprecated

### ⚠️ Dockerfiles (Critical for Deployment)

1. **`Dockerfile.production`**
   - Line 29: `ENV SQLALCHEMY_DATABASE_URI=sqlite:///instance/kpi_dashboard.db`
   - **CRITICAL**: This will override DATABASE_URL if not set
   - **Action Required**: Remove or update to require DATABASE_URL

2. **`Dockerfile.aws`**
   - Line 30: `ENV SQLALCHEMY_DATABASE_URI=sqlite:///instance/kpi_dashboard.db`
   - **CRITICAL**: This will override DATABASE_URL if not set
   - **Action Required**: Remove or update to require DATABASE_URL

### ⚠️ Utility Scripts (Not Critical for Runtime)

Many utility scripts use SQLite as fallback when `DATABASE_URL` is not set. These are OK for local development scripts but should ideally use PostgreSQL:

**Seed Scripts:**
- `seed_all_data.py`
- `seed_59_kpis_per_account.py`
- `seed_improved_health_data*.py`
- `generate_25_accounts_seed_data.py`

**Migration/Setup Scripts:**
- `setup_dc2s_vertical.py` (uses `app.py` which is OK)
- `reset_syntara_password.py`
- `fix_duplicate_uploads.py`
- `migrate_add_openai_key.py`
- `fix_admin_user_after_restore.py`

**Test/Diagnostic Scripts:**
- `verify_admin_login.py`
- `find_36_accounts_user.py`
- `check_openai_key_db.py`
- `validate_openai_key_support.py`
- Various `test_*.py` scripts

**Other Scripts:**
- `build_syntara_knowledge_base.py`
- `upload_company_b_data.py`
- `clear_stale_sessions.py`
- `create_db_minimal.py`
- `comprehensive_e2e_test.py`

---

## Recommendations

### High Priority (Production Impact)

1. **Update Dockerfiles**
   - Remove SQLite default from `Dockerfile.production`
   - Remove SQLite default from `Dockerfile.aws`
   - Ensure these require `DATABASE_URL` environment variable

### Medium Priority (Development Experience)

2. **Update Utility Scripts**
   - Update seed scripts to require `DATABASE_URL`
   - Update migration scripts to require `DATABASE_URL`
   - Add warnings if SQLite is used

### Low Priority (Legacy Files)

3. **Deprecate or Update Legacy App Files**
   - Mark `app_v3_simple.py` as deprecated
   - Mark `app_minimal.py` as deprecated
   - Or update them to use PostgreSQL

### OK to Keep (By Design)

4. **Test Files**
   - SQLite in-memory is fine for unit tests
   - No changes needed

---

## Testing

To verify PostgreSQL is being used:

1. **Check main app startup logs:**
   ```
   ✅ Using PostgreSQL database: postgresql://...
   ```

2. **Verify environment variable:**
   ```bash
   echo $DATABASE_URL
   # Should show PostgreSQL connection string
   ```

3. **Database connection check:**
   ```python
   from app_v3_minimal import app
   with app.app_context():
       print(app.config['SQLALCHEMY_DATABASE_URI'])
       # Should show postgresql://...
   ```

---

## Files to Update

### Critical (Production)
- [ ] `Dockerfile.production` - Remove SQLite default
- [ ] `Dockerfile.aws` - Remove SQLite default

### Optional (Development)
- [ ] Utility scripts - Update to require DATABASE_URL
- [ ] Legacy app files - Mark deprecated or update

---

## Status

✅ **Production apps are safe** - Both `app_v3_minimal.py` and `app.py` correctly use PostgreSQL.

⚠️ **Dockerfiles need updating** - They have SQLite defaults that could cause issues in production deployments if `DATABASE_URL` is not set.

✅ **Utility scripts are acceptable** - They're not used in production, but should ideally use PostgreSQL for consistency.
