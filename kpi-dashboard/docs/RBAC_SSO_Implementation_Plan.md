# CS Pulse Platform: RBAC & SSO Implementation Plan

**Version**: 1.0
**Date**: March 22, 2026
**Status**: Planning
**Author**: Engineering Team

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Current Authentication & Authorization Audit](#2-current-authentication--authorization-audit)
3. [RBAC Design](#3-rbac-design)
4. [SSO/SAML Implementation Plan](#4-ssosaml-implementation-plan)
5. [Admin Configuration Guide](#5-admin-configuration-guide)
6. [Migration Plan](#6-migration-plan)
7. [Timeline & Milestones](#7-timeline--milestones)
8. [Security Considerations](#8-security-considerations)

---

## 1. Executive Summary

CS Pulse currently uses session-based email/password authentication with a flat role model (`admin`, `user`, `contractor`). As the platform moves toward enterprise customers, we need:

- **Fine-grained RBAC** to control which personas (CRO, CFO, CEO, VP CS, Sales, CSM, CS Ops) see which dashboards, data, and tools.
- **SSO/SAML** for enterprise identity provider integration (Okta, Azure AD, OneLogin, Google Workspace).
- **SCIM provisioning** to automate user lifecycle (create/deactivate/update) from the customer's IdP.
- **Tier-based entitlements** to gate features by subscription level (Starter, Professional, Enterprise).

The implementation spans three phases over approximately 7 weeks:
- Phase 1: OAuth 2.0 social login (Google, Microsoft) -- 2 weeks
- Phase 2: SAML 2.0 enterprise SSO -- 3 weeks
- Phase 3: SCIM auto-provisioning -- 2 weeks

RBAC and permission infrastructure ships in parallel with Phase 1.

---

## 2. Current Authentication & Authorization Audit

### 2.1 What Exists Today

#### Session Authentication
- **Flask-Login** with server-side sessions stored via Flask-Session.
- Login endpoint: `POST /api/login` (email + password, bcrypt hash via werkzeug).
- Global auth middleware in `auth_middleware.py` runs `before_request` on all `/api/*` routes.
- Whitelisted public endpoints: `/api/login`, `/api/register`, `/api/health`, `/api/onboarding/*`, `/api/integrations/webhook`.
- Idle timeout: 2 hours of inactivity triggers automatic logout.
- Password hashing: `werkzeug.security.generate_password_hash` / `check_password_hash`.

#### User Model (`models.py`, `users` table)
| Column | Type | Purpose |
|--------|------|---------|
| `user_id` | Integer PK | Internal ID |
| `customer_id` | FK -> customers | Tenant scoping |
| `email` | String (unique) | Login credential |
| `password_hash` | String(128) | bcrypt hash |
| `role` | String(50) | `admin`, `user`, `contractor` |
| `active` | Boolean | Account deactivation flag |
| `allowed_account_ids` | JSON | Account-level restriction (NULL = all) |
| `allowed_customer_ids` | JSON | Multi-customer access (Test Runner) |
| `expires_at` | DateTime | Contractor expiry |
| `is_contractor` | Boolean | Contractor flag |
| `last_login` | DateTime | Last login timestamp |
| `uuid` | String(60) | UUID migration column |

#### API Keys (`customer_api_keys` table)
- Prefix: `csp_*`, stored as SHA-256 hash.
- Scopes: `read`, `write`, `admin`, `ingest`, `export` (JSON array).
- Account-level restriction via `allowed_account_ids`.
- Partner tier support via `partner_tier` column.
- Expiry and last-used tracking.
- Created/managed via Super Admin Console (`contractor_access_api.py`).

#### Super Admin
- `super_admin_required` decorator in `admin_ui_api.py` and `contractor_access_api.py`.
- Checks `user.role in ('super_admin', 'admin')` via session `user_id`.
- Super Admin Console endpoints: `/api/admin-ui/*` (customer CRUD, user management, license management, config overrides).

#### Activity Logging
- `ActivityLog` model tracks action_type, action_category, resource_type, resource_id, IP, user agent.
- Used by contractor access API and admin actions.

#### Tenant Isolation
- `get_current_customer_id()` in `auth_middleware.py` enforces tenant scoping.
- Admin users can override customer scope via `X-Customer-ID` header.
- Non-admin users are locked to their `customer_id` -- header override is rejected.

### 2.2 Gaps and Risks

| Gap | Risk Level | Description |
|-----|-----------|-------------|
| No SSO/SAML | **Critical** | Enterprise buyers require IdP integration. Blocks deals. |
| Flat role model | **High** | Only 3 roles. Cannot differentiate CRO (revenue data) from CSM (account data) from CS Ops (config). No way to restrict dashboard access by persona. |
| No dashboard-level access control | **High** | All 7 persona dashboards visible to all authenticated users. A CSM can see the CFO financial dashboard. |
| No feature entitlements by tier | **Medium** | All customers get all features. No way to gate Context Graph, ROI Engine, or Wizard B to Enterprise tier. |
| Password-only auth | **Medium** | No MFA support. Single factor for all users. |
| Duplicated `super_admin_required` | **Low** | Decorator defined in both `admin_ui_api.py` and `contractor_access_api.py`. Should be centralized. |
| No SCIM | **Medium** | Manual user provisioning. Enterprise IT teams expect automated lifecycle management. |
| Session storage | **Low** | Flask-Session in DB. Works but not horizontally scalable. JWT consideration for API clients. |
| `X-Customer-ID` header in unauthenticated path | **Medium** | Fallback path allows unauthenticated requests with `X-Customer-ID` for onboarding. Acceptable for bootstrapping but needs tightening. |

---

## 3. RBAC Design

### 3.1 Role Hierarchy

```
Super Admin (CS Pulse internal, customer_id=1)
  |
  +-- Customer Admin (per-tenant admin, manages their org)
  |     |
  |     +-- Manager (VP CS, CRO, CFO, CEO -- executive visibility)
  |     |     |
  |     |     +-- CSM (account-level operator)
  |     |     |
  |     |     +-- Read-Only (viewer, no actions)
  |     |
  |     +-- CS Ops (config & operations, not executive dashboards)
  |
  +-- Partner (external partner, scoped to P4 pillar + assigned accounts)
```

**Role definitions:**

| Role | Code | Scope | Description |
|------|------|-------|-------------|
| Super Admin | `super_admin` | Platform-wide | CS Pulse internal staff. Full access to all customers, config, admin console. |
| Customer Admin | `customer_admin` | Own customer | Manages users, roles, SSO config, feature settings for their organization. |
| Manager | `manager` | Own customer | Executive persona. Sees all dashboards (CRO, CFO, CEO, VP CS). Read-only on config. |
| CSM | `csm` | Assigned accounts | Operational persona. CSM dashboard, playbooks, actions. Scoped to `allowed_account_ids`. |
| CS Ops | `cs_ops` | Own customer | Configuration persona. Manages KPI weights, thresholds, integrations. No executive dashboards. |
| Read-Only | `read_only` | Own customer | View-only access. Can see dashboards but cannot trigger playbooks or modify anything. |
| Partner | `partner` | Assigned accounts | External partner users. Limited to P4 pillar data and partner portal. |

### 3.2 Permission Matrix

#### Dashboard Access

| Dashboard | Super Admin | Customer Admin | Manager | CSM | CS Ops | Read-Only | Partner |
|-----------|:-----------:|:--------------:|:-------:|:---:|:------:|:---------:|:-------:|
| CRO Dashboard | Y | Y | Y | - | - | Y | - |
| CFO Dashboard | Y | Y | Y | - | - | Y | - |
| CEO Dashboard | Y | Y | Y | - | - | Y | - |
| VP CS Dashboard | Y | Y | Y | - | - | Y | - |
| Sales Dashboard | Y | Y | Y | - | - | Y | - |
| CSM Dashboard | Y | Y | Y | Y | - | Y | - |
| CS Ops Dashboard | Y | Y | - | - | Y | Y | - |
| Partner Portal | Y | Y | - | - | - | - | Y |
| Admin Console | Y | Y* | - | - | - | - | - |

*Customer Admin sees only their own customer in the Admin Console.

#### Tool/Action Permissions

| Action | Super Admin | Customer Admin | Manager | CSM | CS Ops | Read-Only | Partner |
|--------|:-----------:|:--------------:|:-------:|:---:|:------:|:---------:|:-------:|
| Run playbooks | Y | Y | - | Y | - | - | - |
| Trigger Wizards A/B/C | Y | Y | - | - | Y | - | - |
| Configure KPI weights | Y | Y | - | - | Y | - | - |
| Configure health thresholds | Y | Y | - | - | Y | - | - |
| Manage integrations | Y | Y | - | - | Y | - | - |
| Upload CSV data | Y | Y | - | - | Y | - | - |
| Export data | Y | Y | Y | Y | Y | - | - |
| View health scores | Y | Y | Y | Y | Y | Y | Y* |
| View context graph | Y | Y | Y | Y | Y | Y | - |
| View ROI reports | Y | Y | Y | - | - | Y | - |
| Create/manage users | Y | Y | - | - | - | - | - |
| Create/manage API keys | Y | Y | - | - | Y | - | - |
| Manage feature toggles | Y | - | - | - | - | - | - |
| Manage SSO config | Y | Y | - | - | - | - | - |

*Partner sees only P4 pillar health for assigned accounts.

#### Data Scoping

| Role | Account Visibility | Customer Visibility |
|------|--------------------|---------------------|
| Super Admin | All accounts, all customers | All customers |
| Customer Admin | All accounts in own customer | Own customer only |
| Manager | All accounts in own customer | Own customer only |
| CSM | Only `allowed_account_ids` (or all if NULL) | Own customer only |
| CS Ops | All accounts in own customer | Own customer only |
| Read-Only | All accounts in own customer (or scoped) | Own customer only |
| Partner | Only `allowed_account_ids` | Own customer only |

### 3.3 Account-Level Scoping

The existing `allowed_account_ids` JSON column on the User model already supports account restriction. The RBAC layer formalizes this:

- **CSM role**: When a Customer Admin assigns the CSM role, they also assign specific accounts. `allowed_account_ids = [101, 102, 103]`.
- **Partner role**: Always requires explicit `allowed_account_ids`. NULL is not permitted.
- **All other roles**: `allowed_account_ids = NULL` (unrestricted within customer).
- **Enforcement point**: Existing `User.has_account_access(account_id)` method is already implemented. Must be called in every account-scoped API handler (many are missing this check today).

### 3.4 Feature Entitlements by Tier

| Feature | Starter | Professional | Enterprise |
|---------|:-------:|:------------:|:----------:|
| Health scores (5 pillars) | Y | Y | Y |
| CSM Dashboard + Playbooks | Y | Y | Y |
| Executive Dashboards (CRO, CFO, CEO) | - | Y | Y |
| Context Graph | - | Y | Y |
| ROI Engine | - | - | Y |
| Wizard B (Pattern Analysis) | - | - | Y |
| Wizard C (Weight Calibration) | - | Y | Y |
| SAML SSO | - | - | Y |
| SCIM Provisioning | - | - | Y |
| OAuth (Google/Microsoft) | - | Y | Y |
| Partner Portal | - | - | Y |
| Custom KPI weights | - | Y | Y |
| API access | 1 key | 5 keys | Unlimited |
| Max users | 5 | 25 | Unlimited |
| Max accounts | 10 | 50 | Unlimited |

**Implementation**: Add a `tier` column (`starter`, `professional`, `enterprise`) to the `customers` table. The entitlement check runs as middleware, gating API routes and frontend navigation by tier.

### 3.5 DB Schema Changes for RBAC

```sql
-- 1. New permissions table (static reference data)
CREATE TABLE permissions (
    id SERIAL PRIMARY KEY,
    code VARCHAR(100) UNIQUE NOT NULL,       -- e.g. 'dashboard:cro:view'
    category VARCHAR(50) NOT NULL,            -- 'dashboard', 'action', 'data', 'admin'
    description TEXT
);

-- 2. Role-permission mapping
CREATE TABLE role_permissions (
    id SERIAL PRIMARY KEY,
    role VARCHAR(50) NOT NULL,                -- 'customer_admin', 'csm', etc.
    permission_id INTEGER REFERENCES permissions(id),
    UNIQUE(role, permission_id)
);

-- 3. Customer tier (add column to existing customers table)
ALTER TABLE customers ADD COLUMN tier VARCHAR(20) DEFAULT 'professional';

-- 4. Update users.role to use new role codes
-- (migration script handles mapping: 'admin' -> 'customer_admin', 'user' -> 'csm')

-- 5. User-account assignments (replaces JSON column with proper join table)
CREATE TABLE user_account_assignments (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(user_id) ON DELETE CASCADE,
    account_id INTEGER REFERENCES accounts(account_id) ON DELETE CASCADE,
    assigned_at TIMESTAMP DEFAULT NOW(),
    assigned_by INTEGER REFERENCES users(user_id),
    UNIQUE(user_id, account_id)
);
```

### 3.6 Permission Code Naming Convention

```
{category}:{resource}:{action}

Examples:
  dashboard:cro:view
  dashboard:csm:view
  action:playbook:execute
  action:wizard:trigger
  config:kpi_weights:write
  config:health_thresholds:write
  data:accounts:read
  data:accounts:export
  admin:users:manage
  admin:sso:configure
  admin:api_keys:manage
```

---

## 4. SSO/SAML Implementation Plan

### 4.1 Phase 1: OAuth 2.0 (Google, Microsoft) -- 2 Weeks

**Goal**: Allow users to log in via Google Workspace or Microsoft 365 accounts, linked to their CS Pulse user record.

#### Week 1: Backend OAuth Flow

**Library**: `Authlib` (MIT license, supports OAuth 2.0 + OpenID Connect + SAML)

```
pip install authlib
```

**New endpoints:**
| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/auth/oauth/google/login` | GET | Redirect to Google consent screen |
| `/api/auth/oauth/google/callback` | GET | Handle Google callback, create/link session |
| `/api/auth/oauth/microsoft/login` | GET | Redirect to Microsoft consent screen |
| `/api/auth/oauth/microsoft/callback` | GET | Handle Microsoft callback |
| `/api/auth/oauth/link` | POST | Link OAuth identity to existing user |
| `/api/auth/oauth/unlink` | POST | Remove OAuth link from user |

**DB schema changes:**
```sql
CREATE TABLE user_oauth_links (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(user_id) ON DELETE CASCADE,
    provider VARCHAR(50) NOT NULL,           -- 'google', 'microsoft'
    provider_user_id VARCHAR(255) NOT NULL,  -- sub claim from OIDC
    provider_email VARCHAR(255) NOT NULL,
    provider_name VARCHAR(255),
    access_token_encrypted TEXT,             -- for future API calls
    refresh_token_encrypted TEXT,
    token_expires_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    last_login_at TIMESTAMP,
    UNIQUE(provider, provider_user_id),
    UNIQUE(provider, user_id)
);

-- Customer-level OAuth configuration
ALTER TABLE customer_configs ADD COLUMN oauth_providers JSON DEFAULT '[]';
-- Example: ["google", "microsoft"]
ALTER TABLE customer_configs ADD COLUMN oauth_auto_provision BOOLEAN DEFAULT FALSE;
-- If true, auto-create user on first OAuth login if email domain matches
ALTER TABLE customer_configs ADD COLUMN allowed_email_domains JSON DEFAULT '[]';
-- Example: ["acme.com", "acme.io"]
```

**OAuth login flow:**
1. User clicks "Sign in with Google" on login page.
2. Frontend redirects to `/api/auth/oauth/google/login`.
3. Backend generates OAuth state token, stores in session, redirects to Google.
4. Google authenticates user, redirects back to `/api/auth/oauth/google/callback`.
5. Backend validates state, exchanges code for tokens, extracts email from ID token.
6. Lookup `user_oauth_links` by provider + provider_user_id:
   - **Found**: Log in the linked user, update `last_login_at`.
   - **Not found, but email matches existing user**: Auto-link if `oauth_auto_provision` is enabled and email domain is allowed. Otherwise prompt to link.
   - **Not found, no matching user**: If `oauth_auto_provision` is enabled, create new user with default role (`read_only`). Otherwise reject with "Contact your admin."
7. Create Flask-Login session, redirect to dashboard.

#### Week 2: Frontend + Testing

- Login page: Add "Sign in with Google" and "Sign in with Microsoft" buttons.
- Account settings: "Linked Accounts" section showing connected OAuth providers.
- Customer Admin settings: Enable/disable OAuth providers, configure allowed domains.
- Error handling: Domain mismatch, provider down, token expired.
- Integration tests with mock OAuth providers.

**Dependencies:**
- Google Cloud Console: OAuth 2.0 client ID + secret (Web application type).
- Azure AD: App registration with redirect URI.
- Environment variables: `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `MICROSOFT_CLIENT_ID`, `MICROSOFT_CLIENT_SECRET`.

### 4.2 Phase 2: SAML 2.0 (Okta, Azure AD, OneLogin) -- 3 Weeks

**Goal**: Enterprise customers can configure their IdP for SAML-based SSO. CS Pulse acts as the Service Provider (SP).

**Library**: `python3-saml` (OneLogin's library) or `Authlib` SAML module.

```
pip install python3-saml
```

#### Week 3: SAML Core Infrastructure

**New endpoints:**
| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/auth/saml/{customer_slug}/metadata` | GET | SP metadata XML for IdP configuration |
| `/api/auth/saml/{customer_slug}/login` | GET | Initiate SAML AuthnRequest (SP-initiated) |
| `/api/auth/saml/{customer_slug}/acs` | POST | Assertion Consumer Service (handle IdP response) |
| `/api/auth/saml/{customer_slug}/sls` | GET/POST | Single Logout Service |
| `/api/admin-ui/customers/{cid}/saml` | GET/PUT | SAML config management (admin) |

**`customer_slug`**: A URL-safe identifier for each customer (e.g., `acme-corp`). Added as a column on the `customers` table.

**DB schema changes:**
```sql
-- SAML configuration per customer
CREATE TABLE customer_saml_configs (
    id SERIAL PRIMARY KEY,
    customer_id INTEGER REFERENCES customers(customer_id) UNIQUE,
    enabled BOOLEAN DEFAULT FALSE,

    -- IdP metadata
    idp_entity_id VARCHAR(500),
    idp_sso_url VARCHAR(500),               -- IdP login URL
    idp_slo_url VARCHAR(500),               -- IdP logout URL (optional)
    idp_x509_cert TEXT,                      -- IdP signing certificate

    -- SP settings
    sp_entity_id VARCHAR(500),              -- auto-generated: https://cspulse.ai/saml/{slug}

    -- Attribute mapping
    attribute_map JSON DEFAULT '{
        "email": "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/emailaddress",
        "first_name": "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/givenname",
        "last_name": "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/surname",
        "role": "cspulse_role",
        "groups": "http://schemas.xmlsoap.org/claims/Group"
    }',

    -- Group-to-role mapping
    group_role_map JSON DEFAULT '{}',
    -- Example: {"CS Admins": "customer_admin", "CS Managers": "manager", "CSM Team": "csm"}

    -- Policy
    auto_provision BOOLEAN DEFAULT TRUE,     -- Create user on first SAML login
    default_role VARCHAR(50) DEFAULT 'read_only',
    force_sso BOOLEAN DEFAULT FALSE,         -- Disable password login when SSO is active

    -- Metadata
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    last_tested_at TIMESTAMP,
    setup_status VARCHAR(20) DEFAULT 'pending'  -- pending, testing, active, error
);

-- Add slug to customers table
ALTER TABLE customers ADD COLUMN slug VARCHAR(100) UNIQUE;
```

**SAML login flow:**
1. User navigates to `https://cspulse.ai/login/acme-corp` (or clicks "SSO Login").
2. Frontend calls `/api/auth/saml/acme-corp/login`.
3. Backend loads `customer_saml_configs` for the slug, builds SAML AuthnRequest, redirects to IdP.
4. User authenticates at IdP (Okta, Azure AD, etc.).
5. IdP POSTs SAML Response to `/api/auth/saml/acme-corp/acs`.
6. Backend validates signature, decrypts assertion, extracts attributes.
7. Maps attributes to user fields via `attribute_map`.
8. Maps groups to roles via `group_role_map`.
9. Find-or-create user, create Flask-Login session, redirect to dashboard.

#### Week 4: Admin Configuration UI

- Customer Admin settings page for SAML:
  - Upload IdP metadata XML (auto-parse entity ID, SSO URL, certificate).
  - Download SP metadata XML for pasting into IdP.
  - Configure attribute mapping with visual field mapper.
  - Configure group-to-role mapping.
  - Test connection button (initiates test SAML flow, validates round-trip).
  - Force SSO toggle (disables password login for this customer).

#### Week 5: Testing & Hardening

- Test with Okta developer account.
- Test with Azure AD (free tier).
- Test with OneLogin sandbox.
- Test IdP-initiated SSO flow (user starts from IdP portal).
- Test SLO (Single Logout) -- user logs out at IdP, invalidate CS Pulse session.
- Test edge cases: expired certificate, clock skew, replay attacks.
- Test `force_sso` mode: password login returns error directing to SSO.

### 4.3 Phase 3: SCIM Provisioning -- 2 Weeks

**Goal**: Automate user lifecycle (create, update, deactivate, group sync) from customer's IdP via SCIM 2.0.

**Library**: Build lightweight SCIM endpoint (no heavy framework needed; SCIM is a REST API spec).

#### Week 6: SCIM Core

**New endpoints (SCIM 2.0 spec):**
| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/scim/v2/{customer_slug}/Users` | GET | List users |
| `/scim/v2/{customer_slug}/Users` | POST | Create user |
| `/scim/v2/{customer_slug}/Users/{id}` | GET | Get user |
| `/scim/v2/{customer_slug}/Users/{id}` | PUT | Replace user |
| `/scim/v2/{customer_slug}/Users/{id}` | PATCH | Update user |
| `/scim/v2/{customer_slug}/Users/{id}` | DELETE | Deactivate user |
| `/scim/v2/{customer_slug}/Groups` | GET | List groups/roles |
| `/scim/v2/{customer_slug}/Groups` | POST | Create group mapping |
| `/scim/v2/{customer_slug}/Groups/{id}` | PATCH | Update group members |
| `/scim/v2/{customer_slug}/ServiceProviderConfig` | GET | SCIM capabilities |
| `/scim/v2/{customer_slug}/Schemas` | GET | User/Group schemas |

**Authentication**: SCIM endpoints use Bearer token authentication. Each customer gets a SCIM API token (stored in `customer_saml_configs` or a new `customer_scim_configs` table).

**DB schema changes:**
```sql
CREATE TABLE customer_scim_configs (
    id SERIAL PRIMARY KEY,
    customer_id INTEGER REFERENCES customers(customer_id) UNIQUE,
    enabled BOOLEAN DEFAULT FALSE,
    bearer_token_hash VARCHAR(64) NOT NULL,  -- SHA-256 of SCIM bearer token
    token_prefix VARCHAR(20),                 -- For display: "scim_acme_..."
    default_role VARCHAR(50) DEFAULT 'read_only',
    auto_activate BOOLEAN DEFAULT TRUE,
    sync_groups BOOLEAN DEFAULT TRUE,
    group_role_map JSON DEFAULT '{}',
    last_sync_at TIMESTAMP,
    total_synced_users INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Track SCIM-provisioned users
ALTER TABLE users ADD COLUMN scim_external_id VARCHAR(255);
ALTER TABLE users ADD COLUMN provisioned_by VARCHAR(20); -- 'manual', 'oauth', 'saml', 'scim'
```

#### Week 7: Testing & IdP Integration Guides

- Okta SCIM provisioning setup guide.
- Azure AD SCIM provisioning setup guide.
- Test incremental sync (user added in Okta appears in CS Pulse).
- Test deprovisioning (user deactivated in Okta, `active=false` in CS Pulse).
- Test group membership changes (user moved from "CSM Team" to "Managers" in Okta, role updates).
- Rate limiting on SCIM endpoints (IdPs can be aggressive with full syncs).

### 4.4 Dependency Summary

| Component | Library | License | Purpose |
|-----------|---------|---------|---------|
| OAuth 2.0 + OIDC | `authlib>=1.3` | BSD | Google/Microsoft login |
| SAML 2.0 | `python3-saml>=1.16` | MIT | Enterprise SSO |
| XML parsing | `lxml` | BSD | SAML metadata/assertion parsing |
| Crypto | `cryptography` | BSD/Apache | Token encryption, certificate validation |

**Infrastructure dependencies:**
- HTTPS required for all OAuth/SAML callbacks (already in place via CloudFront).
- DNS: Need per-customer SAML endpoints (`cspulse.ai/saml/{slug}`).
- Secrets management: OAuth client secrets, SAML signing key (currently using env vars; consider AWS Secrets Manager for production).

---

## 5. Admin Configuration Guide

### 5.1 Super Admin: Configuring RBAC for a Customer

**Step 1: Set customer tier**
```
Admin Console > Customers > [Customer] > License & Billing
  Tier: [Starter | Professional | Enterprise]
```
Tier controls which features and max user/account limits are enforced.

**Step 2: Enable SSO for the customer** (Enterprise tier only)
```
Admin Console > Customers > [Customer] > Authentication
  OAuth Providers: [x] Google  [x] Microsoft
  SAML: [Enable]
    - Upload IdP metadata XML
    - Configure attribute mapping
    - Configure group-to-role mapping
    - Test connection
  Force SSO: [ ] (check to disable password login)
```

**Step 3: Verify user roles**
```
Admin Console > Customers > [Customer] > Users
  - View all users with current roles
  - Override role if needed (e.g., promote user to customer_admin)
  - View SCIM-provisioned users (marked with "SCIM" badge)
```

**Step 4: Enable SCIM** (Enterprise tier only)
```
Admin Console > Customers > [Customer] > Provisioning
  SCIM: [Enable]
  - Generate SCIM bearer token (shown once, copy to IdP)
  - SCIM Base URL: https://cspulse.ai/scim/v2/{slug}/
  - Configure default role for new SCIM users
  - Configure group-to-role mapping
```

### 5.2 Customer Admin: Managing Their Own Users/Roles

Customer Admins access a simplified user management interface:

**Settings > Team Management:**
- Invite users by email (sends invitation link).
- Assign roles from allowed set: Manager, CSM, CS Ops, Read-Only.
- Assign accounts to CSM-role users (multi-select from account list).
- Deactivate/reactivate users.
- View login activity and last-active timestamps.

**Settings > Authentication:**
- View SSO configuration status (read-only for SAML config; Customer Admin sees but does not edit IdP metadata).
- Toggle OAuth providers (Google/Microsoft) if enabled by tier.
- View allowed email domains.
- Set default role for new SSO/SCIM users.
- Configure group-to-role mapping (which IdP groups map to which CS Pulse roles).

**Settings > API Keys:**
- Create API keys with scoped permissions (read, write, ingest, export).
- Assign API keys to specific accounts (for partner integrations).
- Revoke API keys.
- View usage logs.

### 5.3 Testing SSO Integration

**Pre-flight checklist:**

1. **Verify metadata exchange:**
   - Download SP metadata XML from CS Pulse.
   - Upload to IdP (Okta/Azure AD/OneLogin).
   - Upload IdP metadata XML to CS Pulse.
   - Verify entity IDs, ACS URL, SLO URL are correct.

2. **Test SP-initiated SSO:**
   - Navigate to `https://cspulse.ai/login/{slug}`.
   - Click "Sign in with SSO".
   - Verify redirect to IdP, authenticate, redirect back.
   - Verify user is created/matched correctly.
   - Verify role is assigned based on group mapping.

3. **Test IdP-initiated SSO:**
   - Log in to IdP portal (e.g., Okta dashboard).
   - Click CS Pulse tile.
   - Verify redirect and session creation.

4. **Test SLO (Single Logout):**
   - Log out from CS Pulse, verify session invalidated at IdP.
   - Log out from IdP, verify CS Pulse session invalidated.

5. **Test SCIM sync:**
   - Create user in IdP, verify appears in CS Pulse within 60 seconds.
   - Update user name/email in IdP, verify updates propagate.
   - Deactivate user in IdP, verify `active=false` in CS Pulse.
   - Change group membership, verify role updates.

6. **Test force-SSO mode:**
   - Enable "Force SSO" in customer settings.
   - Attempt password login, verify it is rejected with SSO redirect.
   - Verify Super Admin can still bypass with password (emergency access).

### 5.4 Troubleshooting Guide

| Symptom | Likely Cause | Resolution |
|---------|-------------|------------|
| SAML login redirects but returns "Invalid Response" | Clock skew between SP and IdP | Verify NTP sync. `python3-saml` allows configurable clock tolerance (default 120s). Increase if needed. |
| User created with wrong role | Group-to-role mapping mismatch | Check `group_role_map` in SAML config. Verify group claim name matches IdP attribute. |
| "User not found" after SAML login | `auto_provision` is disabled and user does not exist | Enable auto-provision or manually create the user first. |
| OAuth callback returns "state mismatch" | Session expired between redirect and callback | User took too long at IdP. Retry login. Check session cookie domain matches callback URL. |
| SCIM creates duplicate users | Email mismatch between SCIM `externalId` and existing user | Use `scim_external_id` for matching. Run dedup script if duplicates exist. |
| "SSO required" but admin locked out | `force_sso` enabled and IdP is down | Super Admin can access via `/api/login` with `?bypass_sso=1` flag (requires `super_admin` role). |
| SAML assertion signature invalid | Certificate rotated at IdP | Upload new IdP certificate. Support multiple active certificates during rotation window. |

---

## 6. Migration Plan

### 6.1 Migrating Existing Users to New Role Model

**Phase A: Schema migration (zero downtime)**

1. Add new columns to `users` table:
   ```sql
   ALTER TABLE users ADD COLUMN new_role VARCHAR(50);
   ALTER TABLE users ADD COLUMN provisioned_by VARCHAR(20) DEFAULT 'manual';
   ALTER TABLE users ADD COLUMN scim_external_id VARCHAR(255);
   ```
2. Add `tier` column to `customers` table:
   ```sql
   ALTER TABLE customers ADD COLUMN tier VARCHAR(20) DEFAULT 'professional';
   ALTER TABLE customers ADD COLUMN slug VARCHAR(100);
   ```
3. Create `permissions`, `role_permissions`, `user_oauth_links`, `customer_saml_configs`, `customer_scim_configs` tables.

**Phase B: Data migration**

Map existing roles to new roles:

| Old `role` | New `new_role` | Logic |
|-----------|---------------|-------|
| `admin` (customer_id = 1) | `super_admin` | CS Pulse internal admin |
| `admin` (customer_id != 1) | `customer_admin` | Customer's own admin |
| `user` | `csm` | Default operational role |
| `contractor` | `read_only` | Contractors become read-only; review case by case |
| NULL | `read_only` | Unset roles default to read-only |

Migration script:
```sql
UPDATE users SET new_role = CASE
    WHEN role = 'admin' AND customer_id = 1 THEN 'super_admin'
    WHEN role = 'admin' AND customer_id != 1 THEN 'customer_admin'
    WHEN role = 'user' THEN 'csm'
    WHEN role = 'contractor' THEN 'read_only'
    ELSE 'read_only'
END;
```

Generate customer slugs:
```sql
UPDATE customers SET slug = LOWER(REPLACE(REPLACE(name, ' ', '-'), '.', ''));
```

**Phase C: Code cutover**

1. Update `auth_middleware.py` to read from `new_role` column.
2. Update `super_admin_required` to check `new_role = 'super_admin'`.
3. Add permission-checking middleware that loads role permissions from DB.
4. Deploy behind feature flag: `FEATURE_RBAC_V2=true`.
5. Test in staging with all 7 persona dashboards.

**Phase D: Cleanup**

1. After validation period (2 weeks), rename columns:
   ```sql
   ALTER TABLE users RENAME COLUMN role TO role_legacy;
   ALTER TABLE users RENAME COLUMN new_role TO role;
   ```
2. Remove feature flag, remove legacy code paths.

### 6.2 Backward Compatibility

- **API keys**: No change. Existing API keys continue to work with their current scopes.
- **Flask-Login sessions**: No change. Existing sessions remain valid through the migration.
- **`X-Customer-ID` header**: Continues to work for admin users and onboarding endpoints.
- **Frontend**: Dashboard routing stays the same. The permission check happens at the API layer, not the route layer. Frontend adds navigation filtering (hide menu items the user cannot access) but API enforcement is the source of truth.
- **MCP server**: No auth changes. MCP tools are unauthenticated (run server-side). Customer scoping stays via `customer_id` parameter.
- **Load driver**: Uses API keys with `admin` scope. No changes needed.

---

## 7. Timeline & Milestones

```
Week 0  (Prep)       RBAC schema design finalized, permissions seeded
                      DB migration scripts written and tested in staging
                      +-------------------------------------------------+

Week 1               OAuth 2.0 backend (Google + Microsoft)
Week 2               OAuth 2.0 frontend + integration tests
                      RBAC permission middleware deployed (feature-flagged)
                      +-------------------------------------------------+
                      MILESTONE: OAuth login working, RBAC enforced

Week 3               SAML 2.0 core (SP metadata, AuthnRequest, ACS)
Week 4               SAML admin UI (config, attribute mapping, test flow)
Week 5               SAML testing with Okta, Azure AD, OneLogin
                      +-------------------------------------------------+
                      MILESTONE: Enterprise SSO working with 3 IdPs

Week 6               SCIM 2.0 endpoints (Users, Groups, ServiceProviderConfig)
Week 7               SCIM testing, IdP integration guides, monitoring
                      +-------------------------------------------------+
                      MILESTONE: Full SSO + SCIM stack complete

Week 8  (Buffer)     Role migration for existing customers
                      Documentation, runbooks, support training
                      Feature flag removal, GA release
```

**Key milestones:**

| Milestone | Target | Deliverable |
|-----------|--------|-------------|
| M1: RBAC + OAuth GA | End of Week 2 | Role-based dashboard access, Google/Microsoft login |
| M2: SAML SSO GA | End of Week 5 | Enterprise SSO with Okta/Azure AD/OneLogin |
| M3: SCIM GA | End of Week 7 | Automated user provisioning from IdP |
| M4: Migration complete | End of Week 8 | All existing users migrated, legacy code removed |

---

## 8. Security Considerations

### 8.1 Session Management

- **Current**: Flask-Session with server-side session store (PostgreSQL). 2-hour idle timeout.
- **Post-SSO**: Sessions tied to SSO assertions. Session lifetime should not exceed SAML assertion validity (typically 8 hours).
- **Session invalidation**: When a user is deactivated (via SCIM or admin), all active sessions for that user must be invalidated immediately. Implement a `session_invalidation` check in `before_request` that queries `users.active` on every request (or cache with 60-second TTL).
- **Concurrent sessions**: Consider limiting to 3 concurrent sessions per user. Track active sessions in a `user_sessions` table.

### 8.2 Token Expiry

- **API keys**: Already support `expires_at`. Enforce expiry check on every API key authentication.
- **OAuth tokens**: Store `access_token` and `refresh_token` encrypted. Refresh tokens have 90-day expiry (Google) or configurable (Microsoft). Do not store access tokens longer than needed.
- **SAML assertions**: Validate `NotBefore` and `NotOnOrAfter` conditions. Reject replayed assertions (track assertion IDs in a short-lived cache).
- **SCIM bearer tokens**: No expiry by default but support rotation. Customer Admin can regenerate token (invalidates old one).

### 8.3 MFA Readiness

CS Pulse does not implement MFA directly. Instead, MFA is delegated to the IdP:

- **SSO customers**: MFA enforced at IdP level (Okta, Azure AD). CS Pulse trusts the SAML assertion's `AuthnContextClassRef` to verify MFA was used.
- **Password-only customers**: Recommend enabling OAuth (Google/Microsoft), which provides MFA via the provider. Future consideration: TOTP-based MFA for password login (library: `pyotp`).
- **API keys**: MFA not applicable. API keys are machine credentials. Protect with IP allowlisting (future feature).

### 8.4 Audit Logging Requirements

The existing `ActivityLog` model provides the foundation. Extend for auth events:

| Event | Log Fields | Retention |
|-------|-----------|-----------|
| Login (password) | user_id, IP, user_agent, success/failure | 90 days |
| Login (OAuth) | user_id, provider, IP, success/failure | 90 days |
| Login (SAML) | user_id, IdP entity_id, IP, assertion_id | 90 days |
| Logout | user_id, method (manual/idle/slo) | 90 days |
| Role change | user_id, old_role, new_role, changed_by | 1 year |
| User provisioned (SCIM) | user_id, external_id, action (create/update/deactivate) | 1 year |
| SSO config change | customer_id, field_changed, changed_by | 1 year |
| API key created/revoked | key_prefix, scopes, created_by | 1 year |
| Permission denied | user_id, endpoint, required_permission, IP | 90 days |
| Failed login (brute force) | email, IP, failure_count | 30 days |

**Rate limiting**: After 5 failed login attempts within 15 minutes, lock the account for 30 minutes. Log all failed attempts. Alert Super Admin if >20 failed attempts from a single IP in 1 hour.

### 8.5 Data Encryption

- **At rest**: Password hashes (bcrypt), API key hashes (SHA-256), OAuth/SAML tokens (AES-256 via `cryptography.fernet`). SAML IdP certificates stored as PEM text.
- **In transit**: TLS 1.2+ enforced via CloudFront. SAML assertions are signed and optionally encrypted.
- **Secrets**: OAuth client secrets and SAML SP signing key stored in environment variables. Migration to AWS Secrets Manager recommended for production.

### 8.6 Cross-Tenant Isolation

- RBAC does not change the tenant isolation model. `customer_id` scoping remains the primary isolation boundary.
- SAML endpoints are customer-scoped by slug. A SAML assertion for `acme-corp` cannot authenticate a user in `beta-inc`.
- SCIM tokens are customer-scoped. A SCIM token for customer A cannot provision users in customer B.
- Super Admin cross-tenant access continues to work via `X-Customer-ID` header override (admin role only).

### 8.7 Compliance Considerations

- **SOC 2**: Audit logging, session management, and access control satisfy Trust Services Criteria CC6.1-CC6.3.
- **GDPR**: SCIM deprovisioning supports "right to erasure" workflow. User deactivation can be extended to data deletion on request.
- **HIPAA**: If applicable, enforce session timeout <= 15 minutes, require MFA via IdP, enable audit logging for all PHI access.

---

## Appendix A: File Impact Map

| File | Change Type | Description |
|------|------------|-------------|
| `backend/models.py` | Modify | Add `new_role`, `scim_external_id`, `provisioned_by` to User; add new tables |
| `backend/auth_middleware.py` | Modify | Add permission-checking middleware, RBAC enforcement |
| `backend/auth_decorators.py` | Modify | Add `permission_required(perm_code)` decorator |
| `backend/admin_ui_api.py` | Modify | Add SAML config endpoints, SCIM config endpoints |
| `backend/contractor_access_api.py` | Minor | Centralize `super_admin_required` |
| `backend/auth_oauth.py` | **New** | OAuth 2.0 login/callback handlers |
| `backend/auth_saml.py` | **New** | SAML 2.0 SP handlers |
| `backend/scim_api.py` | **New** | SCIM 2.0 provisioning endpoints |
| `backend/rbac.py` | **New** | Permission loading, role checking, tier enforcement |
| `src/components/Login.tsx` | Modify | Add OAuth/SSO buttons, customer slug login |
| `src/components/settings/TeamManagement.tsx` | **New** | Customer Admin user/role management UI |
| `src/components/settings/SSOSettings.tsx` | **New** | SAML configuration UI |
| `backend/migrations/add_rbac_tables.py` | **New** | DB migration script |

## Appendix B: Permission Seed Data

Default permissions for each role (loaded via migration):

**`super_admin`**: All permissions (wildcard).

**`customer_admin`**: All permissions within own customer except `admin:feature_toggles:manage`.

**`manager`**: `dashboard:cro:view`, `dashboard:cfo:view`, `dashboard:ceo:view`, `dashboard:vpcs:view`, `dashboard:sales:view`, `dashboard:csm:view`, `data:accounts:read`, `data:accounts:export`, `data:roi:view`, `data:context_graph:view`.

**`csm`**: `dashboard:csm:view`, `action:playbook:execute`, `data:accounts:read` (scoped to assigned accounts).

**`cs_ops`**: `dashboard:csops:view`, `action:wizard:trigger`, `config:kpi_weights:write`, `config:health_thresholds:write`, `config:integrations:manage`, `data:accounts:read`, `admin:api_keys:manage`.

**`read_only`**: `dashboard:*:view` (all dashboards, view only), `data:accounts:read`.

**`partner`**: `dashboard:partner:view`, `data:accounts:read` (scoped), `data:p4:view`.
