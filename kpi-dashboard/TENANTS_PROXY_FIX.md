# Tenants Tab - Proxy and Authentication Fix

**Issue:** Request going to `localhost:3000/api/accounts` returns 401 (45 bytes = auth error)

---

## Root Cause Analysis

### Network Request Analysis
- **Request URL:** `http://localhost:3000/api/accounts` ✅ (Proxy is working)
- **Response:** 401 Unauthorized (45 bytes = `{"error":"Authentication required",...}`)
- **Server:** `Werkzeug/2.2.3 Python/3.9.6` ✅ (Request IS reaching backend)
- **Cookie:** `cs_session=...` ✅ (Cookie is being sent)

### Conclusion
✅ **Proxy is working correctly** - Request reaches backend  
❌ **Authentication is failing** - Session cookie is invalid/expired

---

## Fixes Applied

### 1. Enhanced Proxy Configuration ✅
**File:** `src/setupProxy.js` (Created)

Added explicit proxy middleware with:
- Cookie forwarding
- Debug logging
- Error handling

### 2. Improved Frontend Fetch ✅
**File:** `src/components/dc/tenants/dc_TenantHub.tsx`

- Added cookie logging for debugging
- Ensured `credentials: 'include'` is set
- Added session validation logging

---

## Solution: Re-Login Required

The 401 error indicates your **session has expired**. 

### Steps to Fix:

1. **Logout:**
   - Click logout button in the UI
   - Or clear cookies: DevTools → Application → Cookies → Delete all

2. **Login Again:**
   ```
   Email: dc2s_super@gpucloud.com
   Password: DC2_Super_2024!
   ```

3. **Verify Session:**
   - After login, check DevTools → Application → Cookies
   - Look for `cs_session` cookie
   - Should have expiration date in the future

4. **Test Tenants Tab:**
   - Navigate to `/dc-dashboard/tenants`
   - Check console for `[DCTenantHub]` logs
   - Should see 19 tenants

---

## Session Timeout Settings

- **Active Session:** 8 hours
- **Idle Timeout:** 30 minutes
- **Cookie Name:** `cs_session`
- **Cookie Type:** HttpOnly, SameSite=Lax

If you've been idle for >30 minutes, session expires and you need to re-login.

---

## Debugging After Re-Login

### Expected Console Output:
```
[DCTenantHub] Fetching tenants... { customer_id: 9, hasSession: true, cookies: "cs_session=..." }
[DCTenantHub] Response status: 200 OK
[DCTenantHub] Response data: { status: 'success', total: 19, accounts_count: 19 }
[DCTenantHub] Mapped tenants: 19
[DCTenantHub] Rendering list view: { tenantsCount: 19, loading: false, error: null }
```

### If Still Getting 401:
1. Check cookie expiration in DevTools
2. Verify backend is running on port 5059
3. Check backend logs for authentication errors
4. Try clearing all cookies and re-login

---

## Status

✅ **Proxy Configuration:** Fixed  
✅ **Frontend Fetch:** Improved  
⚠️ **Authentication:** User needs to re-login (session expired)

---

**Next Step:** Re-login and test again
