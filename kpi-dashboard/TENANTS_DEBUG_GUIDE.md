# Tenants Tab Debugging Guide

**Issue:** Tenants not showing in UI despite 19 accounts in database

---

## Database Verification ✅

- **Total Accounts:** 19 accounts for Customer 9
- **All accounts have:** Valid IDs, names, and revenue values
- **Endpoint Logic:** Should return all 19 accounts for `dc2_s` vertical users

---

## Frontend Debugging Added

### Console Logging
Added detailed console logging to `dc_TenantHub.tsx`:
- `[DCTenantHub] Fetching tenants...` - When fetch starts
- `[DCTenantHub] Response status:` - HTTP status code
- `[DCTenantHub] Response data:` - Response payload
- `[DCTenantHub] Mapped tenants:` - Number of tenants after mapping
- `[DCTenantHub] Rendering list view:` - Component render state

### Error Handling
- Better error messages displayed in UI
- Retry button when error occurs
- Shows customer ID in tenant count

---

## Debugging Steps

### 1. Check Browser Console
Open DevTools → Console tab and look for:
```
[DCTenantHub] Fetching tenants... { customer_id: 9 }
[DCTenantHub] Response status: 200 OK
[DCTenantHub] Response data: { status: 'success', total: 19, accounts_count: 19 }
[DCTenantHub] Mapped tenants: 19
[DCTenantHub] Rendering list view: { tenantsCount: 19, loading: false, error: null }
```

### 2. Check Network Tab
- Open DevTools → Network tab
- Filter by `/api/accounts`
- Click on the request
- Check:
  - **Status:** Should be 200 (not 401)
  - **Response:** Should show `{"status": "success", "accounts": [...], "total": 19}`
  - **Headers:** Should include session cookie

### 3. Check Session
- Open DevTools → Application → Cookies
- Look for `cs_session` cookie
- If missing → Session expired, need to re-login

### 4. Common Issues

#### Issue: 401 Unauthorized
**Cause:** Session expired or not authenticated
**Solution:** 
1. Logout and login again
2. Clear cookies and refresh
3. Check backend logs for authentication errors

#### Issue: Empty Response
**Cause:** Endpoint returning empty array
**Solution:**
- Check backend logs for errors
- Verify customer_id in session matches database
- Check vertical filtering logic

#### Issue: Data Not Rendering
**Cause:** Frontend mapping issue or component not updating
**Solution:**
- Check console for JavaScript errors
- Verify `tenants` state is being set
- Check if `TenantList_dc` component is receiving props

---

## Expected Behavior

### When Working Correctly:
1. **Loading State:** Shows spinner while fetching
2. **Success State:** Shows "19 tenants found" and list of tenants
3. **Error State:** Shows error message with retry button
4. **Empty State:** Shows "No Tenants Found" message

### Console Output (Success):
```
[DCTenantHub] Fetching tenants... { customer_id: 9 }
[DCTenantHub] Response status: 200 OK
[DCTenantHub] Response data: { status: 'success', total: 19, accounts_count: 19 }
[DCTenantHub] Mapped tenants: 19
[DCTenantHub] Rendering list view: { tenantsCount: 19, loading: false, error: null, hasSession: true }
```

---

## Next Steps

1. **Refresh Browser** - Clear cache and reload
2. **Check Console** - Look for the debug messages above
3. **Check Network Tab** - Verify API response
4. **Re-login if needed** - Session may have expired

---

**Status:** Debugging logs added, ready for user testing
