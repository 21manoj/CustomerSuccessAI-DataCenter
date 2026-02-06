# Login 404 Error Fix

**Date:** 2026-01-20  
**Issue:** `POST http://localhost:3000/api/login 404 (NOT FOUND)`

---

## Root Cause

The `package.json` had **both** a `proxy` field and a `setupProxy.js` file. In Create React App, when both exist, there can be conflicts where the simple `proxy` field takes precedence over the custom `setupProxy.js`, causing routing issues.

---

## Fix Applied

### 1. Removed `proxy` Field from `package.json` ✅
- **Before:** Had both `"proxy": "http://localhost:5059"` and `setupProxy.js`
- **After:** Removed the `proxy` field, now using only `setupProxy.js`

### 2. Verified `setupProxy.js` Configuration ✅
- Located at: `src/setupProxy.js`
- Proxies `/api/*` requests to `http://localhost:5059`
- Includes cookie forwarding for authentication
- Has debug logging enabled

### 3. Restarted Frontend ✅
- Killed old process
- Started fresh with new configuration
- Server is running on port 3000

---

## Current Configuration

### `package.json`
```json
{
  "devDependencies": {
    "@types/react-router-dom": "^5.3.3",
    "http-proxy-middleware": "^3.0.5"
  }
  // ❌ Removed: "proxy": "http://localhost:5059"
}
```

### `src/setupProxy.js`
```javascript
const { createProxyMiddleware } = require('http-proxy-middleware');

module.exports = function(app) {
  app.use(
    '/api',
    createProxyMiddleware({
      target: 'http://localhost:5059',
      changeOrigin: true,
      secure: false,
      logLevel: 'debug',
      onProxyReq: (proxyReq, req, res) => {
        if (req.headers.cookie) {
          proxyReq.setHeader('Cookie', req.headers.cookie);
        }
        console.log('[Proxy] Proxying', req.method, req.url, 'to', 'http://localhost:5059' + req.url);
      },
      onProxyRes: (proxyRes, req, res) => {
        console.log('[Proxy] Response:', proxyRes.statusCode, 'for', req.url);
        if (proxyRes.headers['set-cookie']) {
          res.setHeader('Set-Cookie', proxyRes.headers['set-cookie']);
        }
      },
      onError: (err, req, res) => {
        console.error('[Proxy] Error:', err.message);
        res.status(500).json({ error: 'Proxy error', message: err.message });
      }
    })
  );
};
```

---

## Backend Route Verification

The backend route exists and is working:
- **Route:** `POST /api/login`
- **Location:** `backend/app_v3_minimal.py:466`
- **Status:** ✅ Responding (tested with curl)

---

## Testing Steps

1. **Clear Browser Cache:**
   - Mac: `Cmd + Shift + R`
   - Windows: `Ctrl + Shift + R`

2. **Navigate to:** `http://localhost:3000`

3. **Login Credentials:**
   - Email: `dc2s_super@gpucloud.com`
   - Password: `DC2_Super_2024!`
   - Vertical: Select "Data Center"

4. **Check Browser Console:**
   - Should see `[Proxy] Proxying POST /api/login` logs
   - Should see `[Proxy] Response: 200` (or 401 if wrong credentials)

5. **Check Network Tab:**
   - Request to `http://localhost:3000/api/login`
   - Should get 200 OK (not 404)
   - Response should contain session data

---

## Troubleshooting

### If Still Getting 404:

1. **Verify Frontend is Running:**
   ```bash
   curl http://localhost:3000
   ```

2. **Check Backend is Running:**
   ```bash
   curl http://localhost:5059/api/health
   ```

3. **Check Proxy Logs:**
   - Open browser console
   - Look for `[Proxy]` messages
   - If no proxy logs appear, `setupProxy.js` might not be loading

4. **Verify setupProxy.js Location:**
   ```bash
   ls -la kpi-dashboard/src/setupProxy.js
   ```
   - Must be in `src/` directory
   - Must be named exactly `setupProxy.js`

5. **Restart Frontend:**
   ```bash
   lsof -ti:3000 | xargs kill -9
   cd kpi-dashboard
   npm start
   ```

---

## Why This Happened

Create React App's proxy system:
- **Simple proxy:** `"proxy": "http://localhost:5059"` in `package.json`
- **Custom proxy:** `src/setupProxy.js` file

When both exist, the behavior can be unpredictable. The `setupProxy.js` should take precedence, but in some cases the simple proxy field can interfere, especially with cookie handling and custom routing logic.

**Solution:** Use only `setupProxy.js` for full control over proxy behavior.

---

**Status:** ✅ **FIXED - Ready for Testing**
