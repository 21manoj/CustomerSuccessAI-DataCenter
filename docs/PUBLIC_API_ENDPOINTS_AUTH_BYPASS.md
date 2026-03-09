# Public API Endpoints (Authentication Bypass)

All API routes that **skip authentication** are defined in one place:  
**`kpi-dashboard/backend/auth_middleware.py`** in the list **`PUBLIC_ENDPOINTS`**.

Any path that **exactly matches** or **starts with** one of these prefixes is allowed without login.

---

## Count: **16 base paths** (plus everything under them)

Because the check is `request.path == public_path or request.path.startswith(public_path + '/')`, each entry below effectively makes that path **and all subpaths** public (e.g. `/api/onboarding/templates` makes `/api/onboarding/templates/foo` public too).

---

## Full list (as in code)

| # | Path | Purpose | Production concern? |
|---|------|--------|----------------------|
| 1 | `/api/login` | User login | No — must be public. |
| 2 | `/api/register` | User registration | No — must be public. |
| 3 | `/api/health` | Health check (load balancer, monitoring) | No — must be public. |
| 4 | `/api/upload/health` | Upload service health | No — fine to be public. |
| 5 | `/api/forgot-password` | Password reset request | No — must be public. |
| 6 | `/api/reset-password` | Password reset with token | No — must be public. |
| 7 | `/api/onboarding/complete` | Onboarding completion | Review — only if onboarding is used before login. |
| 8 | `/api/onboarding/provision` | Customer provisioning | Same as above. |
| 9 | `/api/onboarding/upload` | Onboarding file upload | Same as above. |
| 10 | `/api/onboarding/process-data` | Onboarding data processing | Same as above. |
| 11 | `/api/onboarding/register-journey-api` | Journey API registration | Same as above. |
| 12 | `/api/onboarding/processing-status` | Onboarding status | Same as above. |
| 13 | `/api/onboarding/templates` | Onboarding template download | Same as above. |
| 14 | `/api/onboarding/validate-csv` | CSV validation | Same as above. |
| 15 | `/api/test-runner` | Test runner / load driver UI (scenario listing, etc.) | **Yes — relaxed for dev.** Gate by API key or IP in production, or remove from public list. |
| 16 | `/api/admin/uuid-backfill` | Admin UUID backfill | **Yes — comment in code: "should be gated by API key in production, public for dev".** Must be restricted (e.g. API key or admin-only) before production. |

---

## Summary

- **Total base paths that bypass auth:** **16** (and any subpath under them).
- **Legitimately public (auth, health, password reset):** 6 (login, register, health, upload/health, forgot-password, reset-password).
- **Onboarding (public by design for new customers):** 8 — keep public only if your flow requires unauthenticated onboarding; otherwise consider gating.
- **Dev-relaxed — should be restricted in production:** **2**
  - `/api/test-runner` (and subpaths)
  - `/api/admin/uuid-backfill` (and subpaths)

---

## What to do before production

1. **Remove or gate the two dev-relaxed endpoints from the public list:**
   - **`/api/test-runner`** — Either remove from `PUBLIC_ENDPOINTS` (and require login or API key) or add a separate check (e.g. API key header or IP allowlist) in the middleware or in the test-runner blueprint.
   - **`/api/admin/uuid-backfill`** — Remove from `PUBLIC_ENDPOINTS` and protect with admin auth or API key (e.g. `X-Admin-Key` or similar).

2. **Onboarding:** If new customers never hit onboarding before logging in, consider moving onboarding endpoints behind auth or a one-time token; otherwise leave as-is and rely on rate limiting and input validation.

3. **Optional:** Add rate limiting for public endpoints (login, register, forgot-password, onboarding) to reduce abuse.

4. **No other files** define a separate “public” list; the single source of truth is `auth_middleware.PUBLIC_ENDPOINTS`. Changing that list is enough to lock down or open paths globally.
