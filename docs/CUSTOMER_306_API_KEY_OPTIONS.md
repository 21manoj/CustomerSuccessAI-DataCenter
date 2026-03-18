# Customer 306 — Authentication Wall (API Key)

When a customer is created via the MCP tool **create_customer()**, the platform generates an **API key** and returns it **once** in the tool result. That key is required for subsequent MCP intelligence tools (list_accounts, get_account_health, etc.) when using HTTP/Bearer auth. If the key was not saved when customer 306 was created, the client hits an authentication wall.

---

## Three ways to move forward

### Option 1 — You have the API key

- **If** the key was saved when customer 306 was created:
  - Configure it in the MCP connection (e.g. **Authorization: Bearer &lt;api_key&gt;**).
  - The key format is `csp_read_...` or `csp_write_...`.
- No platform changes needed.

---

### Option 2 — Regenerate the key

- **If** the key was lost:
  - **Admin UI:** Use CS Pulse Admin UI → select customer 306 → API Keys → create a new key. Save the key when shown (it is only shown once).
  - **API:** `POST /api/admin-ui/customers/306/api-keys` (requires super_admin or admin for customer 306), body: `{"name": "Regenerated key", "scopes": ["read", "write"]}`. Response includes the new key once.
- **Blocker:** The deployed app may show *"Admin UI API not fully available (cannot import name 'CustomerApiKey' from 'models')"*. In that case the **customer_api_keys** table and **CustomerApiKey** model must be added and deployed before regeneration works (see **Enabling API key support** below).

---

### Option 3 — Create a fresh test customer (recommended for testing)

- **No key retrieval needed.** Use the MCP onboarding flow to create a **new** tenant with demo data:
  1. Call **create_customer(name, domain, vertical, admin_email, admin_name)** with a new company name and domain (e.g. `name="Test Corp"`, `domain="testcorp-demo.com"`, `vertical="dc2_s"`).
  2. The tool returns **api_key** in the result — **save it immediately** (it is shown only once).
  3. Use that key in the MCP connection for all subsequent intelligence tools.
  4. Optionally call **upload_csv**, **process_data**, **complete_onboarding**, etc., to load demo data.

This is the cleanest way to test the full platform without depending on an old key for customer 306.

---

## Enabling API key support (for Option 2)

If the Admin UI / API key APIs are not available because **CustomerApiKey** is missing:

1. **Add the table** (if not present): run the migration that creates **customer_api_keys** (e.g. `migrate_admin_ui_saas_premium.py` Step 7, or equivalent SQL).
2. **Add the model:** define **CustomerApiKey** in `kpi-dashboard/backend/models.py` to match the table (id, customer_id, created_by, key_prefix, key_hash, name, scopes, is_active, expires_at, last_used_at, last_used_ip, created_at, and optionally allowed_account_ids, partner_tier).
3. **Deploy** and restart the platform. Then Option 2 (Admin UI or POST to create a key for customer 306) will work.

---

## Summary

| Option | When to use | Requirement |
|--------|-------------|-------------|
| **1. Use existing key** | Key was saved at create time | Configure Bearer token in MCP connection. |
| **2. Regenerate key** | Key lost; need to keep using customer 306 | CustomerApiKey model + customer_api_keys table deployed; then Admin UI or POST to create key. |
| **3. Fresh test customer** | Easiest path; no key retrieval | Call create_customer(); save **api_key** from the response; use it in MCP connection. |

For the fastest path to test the full platform, use **Option 3** and save the new key from the **create_customer()** result.
