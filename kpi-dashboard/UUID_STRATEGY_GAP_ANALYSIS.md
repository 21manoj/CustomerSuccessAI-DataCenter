# UUID Strategy Gap Analysis

**Reference:** `CUSTOMER_ID_STRATEGY.md` (UUID + Display ID recommendation)  
**Context:** CS Pulse / KPI Dashboard codebase (customer_id usage, onboarding, account range, directories).

This document evaluates the strategy doc against the **actual codebase** and lists **gaps** that must be addressed before or during a UUID migration.

---

## 1. Account ID range formula (critical)

**Strategy doc:** Does not mention account IDs.

**Codebase:** Account IDs are **derived from integer customer_id**:

- **Formula:** `account_id = customer_id * 1000 + offset` (e.g. customer 19 → 19001–19999).
- **Used in:** `onboarding_api_v2_config_aware.py` (`calculate_account_id_range`, account creation at complete, process-data validation), `provision_dc_customer.py` (template placeholders use `10000 + customer_id * 1000` in some places), CSV validation, synthetic data generators, tests.

**Gap:** With UUID as `customer_id` you cannot compute `customer_id * 1000`. You must either:

- **A)** Keep an **internal integer** (e.g. `legacy_id` or `internal_id`) used **only** for this formula and for directory naming, and never expose it as the tenant identifier; or  
- **B)** Change the model: account IDs become UUIDs or a separate scheme (e.g. per-customer sequence, or global sequence); CSV validation and all consumers of the “account range” must be updated.

The strategy doc’s migration section renames to `customer_id` (UUID) and keeps `legacy_id` (integer) “for reference” but does not say that **account_id range and directory paths** must continue to use that integer. Without that, onboarding and provisioning break.

---

## 2. Directory and file layout

**Strategy doc:** No mention of filesystem paths.

**Codebase:** Customer-scoped paths depend on **integer customer_id**:

- **Pattern:** `verticals/customer{customer_id}-{vertical_slug}` (e.g. `customer19-dc2_s`).
- **Used in:** `get_customer_directory(customer_id, vertical_slug)`, `provision_customer(customer_id=..., vertical_slug=...)`, process-data (load CSVs from that dir), embedding scripts, Wizard A/B/C paths (e.g. `customer_dir / "journey" / "wizard_c" / "outputs"`).

**Gap:** With UUID as the only customer identifier:

- Paths like `customer_a1b2c3d4-e5f6-7890-abcd-ef1234567890-dc2_s` are long and awkward.
- **Options:** (1) Keep a **short internal integer** for paths only (e.g. `customer19-dc2_s` from `legacy_id` or `internal_id`). (2) Use **display_id** in paths (e.g. `customer_CS-019-dc2_s`) and ensure display_id is stable and unique. (3) Use UUID in paths and update every caller to use the new path format.

The strategy doc does not define how `get_customer_directory` and `provision_customer` should resolve the “directory key” (integer vs UUID vs display_id).

---

## 3. Onboarding flow (complete + process-data)

**Strategy doc:** Migration describes Customer table only; no onboarding behavior.

**Codebase:**

- **Complete** creates `Customer`, optionally with explicit integer `customer_id`; then provisions directory `customer{customer_id}-{vertical}`, creates User, CustomerConfig, and Account rows with `account_id = customer_id * 1000 + 1..N`.
- **Process-data** takes `customer_id` (integer) in the request, loads CSVs from `get_customer_directory(customer_id)`, validates account_id in CSVs against `calculate_account_id_range(customer_id)`, and writes to `accounts` / `dc2s_kpis` / etc. with that `customer_id`.

**Gap:** The strategy does not specify:

- Whether **onboarding complete** should accept UUID or display_id (or both) when creating a customer.
- Whether **process-data** and **status** endpoints accept UUID/display_id and how they resolve to the directory and account range (e.g. via internal integer).
- Who allocates **display_id** (complete vs a separate service) and whether it’s generated before or after directory provisioning.

---

## 4. Registration vs onboarding (two entry points)

**Strategy doc:** Describes a single Customer creation flow with UUID + display_id.

**Codebase:** Two independent paths create customers:

- **Registration** (`/api/register`): Creates Customer (no explicit ID) → DB assigns integer `customer_id`; creates User, CustomerConfig, playbook triggers. No onboarding step.
- **Onboarding complete** (`/api/onboarding/complete`): Creates Customer (optional explicit integer ID or DB-assigned), provisions directory, creates User, Config, Accounts. No registration step.

**Gap:** Both paths must be updated to:

- Create Customer with **UUID** (and optionally assign **display_id** at creation).
- Ensure **display_id** is allocated in a single, consistent way (e.g. shared `DisplayIDGenerator` or DB sequence) so registration and onboarding don’t conflict or produce duplicate display_ids.
- Decide whether registration also provisions a directory (currently it does not); if not, the “directory key” (integer vs UUID vs display_id) still matters when the same tenant later goes through onboarding.

---

## 5. Per-vertical “namespace” for display_id

**Strategy doc:** Single global display_id sequence (e.g. CS-001, CS-002). Vertical is a column; “get all SaaS customers” is done by filtering on `vertical`.

**Your requirement (from earlier):** “Keep SaaS and DataCenter (or any new vertical) in **separate namespace**” so there’s no ID collision and namespaces are clear.

**Gap:** The doc’s design gives **one** namespace for display_id (all verticals share CS-001, CS-002, …). It does **not** give:

- **Separate namespaces per vertical**, e.g.:
  - **SaaS:** CS-SAAS-001, CS-SAAS-002  
  - **DataCenter:** CS-DC-001, CS-DC-002  
  or separate sequences per vertical so that “SaaS” and “DC” never share the same numeric space.
- If the requirement is “SaaS and DC in separate namespaces,” the strategy should either:
  - Define **per-vertical display_id** (prefix or separate sequence), or  
  - Explicitly state that “namespace” is **only** the `vertical` column (logical filter), not a separate ID space, and that display_id is global.

---

## 6. Foreign keys and schema scope

**Strategy doc:** Migration adds `customer_uuid` and `display_id` to Customer, then renames to make UUID the PK and `legacy_id` the old integer. It does not list all dependent tables.

**Codebase:** Many tables reference `customers.customer_id` (integer):

- **CustomerConfig**, **Account**, **User**, **Product**, **KPIUpload**, **KPI**, **HealthTrend**, **ReferenceRange**, **KPITimeSeries**, **PlaybookTrigger**, **PlaybookExecution**, **PlaybookReport**, **FeatureFlag**, **QueryAudit**, **ActivityLog**, **CustomerWorkflowConfig**, **AccountNote**, **AccountSnapshot**, **QualitativeSignal**, **DC2SKPI**, etc.

**Gap:** Migration must:

- Change **every** `customer_id` FK column (and index) from `Integer` to `String(36)` (or equivalent for UUID) in all these tables, **or**
- Keep **integer** FKs and introduce a **stable internal id** (e.g. `customers.internal_id` or `legacy_id`) that remains the target of FKs, while `customer_id` (UUID) is the public/API identifier. The strategy doc’s “legacy_id for reference” suggests the latter, but it does not clearly say “all FKs continue to point to legacy_id / internal_id” and “customer_id UUID is for API and external use only.” Without that, the scope of migration (all child tables and all code that joins on customer_id) is understated.

---

## 7. API and auth

**Strategy doc:** Suggests APIs accept either UUID or display_id (e.g. `GET /api/customers/CS-001` or `GET /api/customers/{uuid}`). No mention of auth or session.

**Codebase:**

- **Auth:** `get_current_customer_id()` returns **integer** (from `current_user.customer_id` or `X-Customer-ID` header). Used everywhere for tenant isolation.
- **APIs:** Many endpoints use `get_current_customer_id()` or take `customer_id` in body/path (e.g. process-data, status, config, accounts list). They assume integer.

**Gap:** The strategy should cover:

- **Session / token:** Store UUID (or display_id) in session/JWT and resolve to internal id where needed for DB/directory, or store internal id and keep APIs backward compatible.
- **X-Customer-ID:** Whether it remains integer during transition or becomes UUID/display_id; and how middleware resolves to the row (and optionally to internal id for directory/account range).
- **Backward compatibility:** During migration, whether APIs accept **both** integer and UUID/display_id and how lookup works (`get_customer_by_any_id`-style).

---

## 8. CSV and upload validation

**Strategy doc:** No mention of CSV validation or uploads.

**Codebase:** Onboarding validates that **account_id** in CSVs falls in the range `(customer_id * 1000 + 1)` to `(customer_id * 1000 + 999)`. Process-data loads CSVs and sets `customer_id` on accounts and KPI rows.

**Gap:** With UUID:

- Validation logic cannot use `customer_id * 1000` unless an **internal integer** is defined and used for this check.
- If account_id scheme changes (e.g. UUID or free-form per customer), validation rules and CSV templates must be redesigned and documented.

---

## 9. Qdrant and external systems

**Strategy doc:** No mention of external or search services.

**Codebase:** Qdrant collection names (or payloads) use customer scope, e.g. `kpi_dashboard_vectors_customer_{customer_id}`. If `customer_id` becomes a 36-char UUID, collection names or keys may need to change (and backfill/rebuild considered).

**Gap:** Document impact on:

- Qdrant collection naming and any customer_id in payloads.
- Other systems that store or index by customer_id (e.g. caches, analytics). Decide whether they use UUID, display_id, or internal id.

---

## 10. Display_id generation and concurrency

**Strategy doc:** `DisplayIDGenerator.generate(session)` does `max(display_id)` + 1 and returns the next value. Retry on `IntegrityError` is mentioned, but the shown code does not **reserve** the value (e.g. by inserting a row or locking a sequence) before returning.

**Gap:** Under concurrent creation (e.g. two requests at once), both can get the same “next” display_id and one will fail on unique constraint. The strategy should specify a **safe** allocation method: e.g. DB sequence, `SELECT ... FOR UPDATE` on a sequence table, or allocate-on-insert (e.g. trigger or application insert with retry). The current “max + 1” pattern is racy unless the insert is done in the same transaction with a lock.

---

## 11. Provision script and template formula

**Codebase:** `provision_dc_customer.py` uses `10000 + customer_id * 1000` for **account_id_start** in templates (e.g. 29000 for customer 19). Onboarding complete uses `customer_id * 1000 + 1` (19001–19010 for customer 19). There is an existing inconsistency in the codebase; UUID migration should not reinforce it.

**Gap:** Strategy should state:

- Whether **provision** and **onboarding** will share a single formula and, if so, which one.
- How **provision** gets the “directory key” and “account_id_start” when customer is identified by UUID (e.g. from internal_id or from a new rule). Template placeholders like `{ACCOUNT_ID_START}` must be defined in terms of UUID-based customer (e.g. via internal_id).

---

## Summary table

| Area | Strategy doc | Codebase reality | Gap |
|------|--------------|-------------------|-----|
| Account ID range | Not mentioned | `account_id = customer_id * 1000 + offset` everywhere | Need internal integer or new account_id scheme |
| Directory paths | Not mentioned | `customer{customer_id}-{vertical}` | Need key for paths (internal id / display_id / UUID) |
| Onboarding complete/process-data | Not mentioned | Integer customer_id end-to-end | Define how UUID/display_id is used and how range/dir are resolved |
| Registration vs onboarding | Single flow | Two creation paths | Both must assign UUID + display_id consistently |
| Per-vertical namespace | Single display_id sequence | Requirement for SaaS vs DC separation | Clarify: global display_id + vertical column vs per-vertical display_id |
| FKs and schema | Customer table only | 20+ tables with customer_id FK | Migrate all FKs or keep integer internal id for FKs |
| Auth and API | GET by UUID or display_id | get_current_customer_id() returns int; APIs use int | Session/header and resolution for UUID/display_id/int |
| CSV validation | Not mentioned | Validates account_id in range(customer_id*1000+1, 999) | Need internal id for formula or new validation |
| Qdrant / external | Not mentioned | Collection names use customer_id | Impact on collection names and payloads |
| Display_id concurrency | max+1 with retry | Race under concurrent create | Safe allocation (sequence / lock / allocate-on-insert) |
| Provision vs complete formula | N/A | 10000+cid*1000 vs cid*1000+1 | Unify and define for UUID-based customer |

---

**Conclusion:** The UUID + Display ID direction is compatible with the codebase only if the **gaps above** are addressed. The largest are: (1) **account_id formula and directory layout** (need an internal integer or a new scheme), (2) **full FK and schema migration** (or clear “internal_id for FKs, UUID for API”), (3) **onboarding and registration** both using UUID/display_id and a single place that knows the “directory key” and “account range,” and (4) **per-vertical namespace** for display_id if you want SaaS and DataCenter in separate ID spaces.
