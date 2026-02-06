# Proxy Debugging

**Issue:** `/api/login` returns 404 when accessed through frontend proxy, but works when accessed directly.

**Findings:**
1. Backend route exists at `/api/login` (line 466 in app_v3_minimal.py)
2. Direct curl to `http://localhost:5059/api/login` works (200 OK)
3. Proxy request to `http://localhost:3000/api/login` returns 404
4. Response headers show both Express (React dev server) and Werkzeug (Flask)
5. 404 response format matches Flask's error handler

**Solution:** Using simple `proxy` field in `package.json` instead of `setupProxy.js`.

**Current Configuration:**
- `package.json`: `"proxy": "http://localhost:5059"`
- `setupProxy.js`: DELETED (was causing conflicts)

**Next Steps:**
Test login after clearing browser cache.
