# Demo / Test Logins and Customer Data

## dc2s_super@test.com – invalid login / no pre-loaded data

- **DB data is not pre-loaded** for this user. The script only creates or updates the **user** (and optionally links DC2_S accounts to customer 5). Whether the dashboard shows data depends on whether **customer 5** has accounts in the DB (e.g. from onboarding, upload, or rehydration—see below).
- **If you get "Invalid email or password"** when logging in as `dc2s_super@test.com` with password `DC2_Super_2024!`, the user may be missing, have a wrong password hash, or `active=0`. Run this from the **backend** directory:
  ```bash
  python scripts/fix_dc2s_super_login.py
  ```
  That creates the user if missing, or resets the password and sets `active=1` using the same hashing as the app (`pbkdf2:sha256`). Then try logging in again with:
  - **Email:** `dc2s_super@test.com`
  - **Password:** `DC2_Super_2024!` (or set `DC2S_SUPER_PASSWORD` in `.env` before running the script)
- Alternatively, run the full setup (creates user and links DC2_S accounts to customer 5):
  ```bash
  python setup_dc2s_test_user.py
  ```

## Data loading: 02_Load* scripts vs current approach

**02_Load* scripts** (e.g. `02_load_customer19_data_SMART.py`) are **no longer the primary path** for loading data. Customer/account data can be loaded via:

- **Onboarding API** (config-aware onboarding creates customer, user, config, and can load CSVs from the provisioned directory)
- **Upload APIs** (Excel/CSV upload per customer)
- **Rehydration API** (`/api/rehydrate/import`)
- **Other import scripts** (e.g. `import_marketplace_accounts.py`, `import_customer_profile.py`)

So "which customer has data?" is whatever has been loaded through these flows, not only via 02_Load* scripts. Use `python scripts/list_users_and_customer_data.py` to see which users/customers have accounts in the DB.

## Why does demo@cspulse.ai show zero records?

The dashboard shows **accounts for the customer tied to your login**. If that customer has no rows in `accounts` (and no DC2S KPIs), you see zero records.

- **demo@cspulse.ai** is not created by any script in this repo; it was likely added manually or via onboarding.
- Its **customer_id** may point to a customer that was never loaded with data.
- So you get zero until either that customer gets data, or the user is pointed at a customer that already has data.

## See which logins have data

From the **backend** directory:

```bash
python scripts/list_users_and_customer_data.py
```

This lists every user (email, customer_id, customer name) and how many accounts/DC2S KPIs that customer has. Use it to see why a given login returns zero.

One-line summary:

```bash
python scripts/list_users_and_customer_data.py --csv
```

## Customer IDs that have 02_Load* scripts (legacy)

These customer IDs have a `02_load_customer*_SMART.py` script. You may have moved away from these; data can also come from onboarding, upload, or rehydration (see above). **Data appears only when loaded** (by any of those methods).

| Customer ID | Load script path (from repo root) |
|-------------|-----------------------------------|
| 5  | `kpi-dashboard/backend/verticals/customer5-dc2_s/scripts/02_load_customer5_data_SMART.py` |
| 7  | `.../customer7-dc2_s/scripts/02_load_customer7_data_SMART.py` |
| 9  | `.../customer9-dc2_s/scripts/02_load_customer9_data_SMART.py` |
| 10 | `.../customer10-dc2_s/scripts/02_load_customer10_data_SMART.py` |
| 11 | `.../customer11-dc2_s/scripts/02_load_customer11_data_SMART.py` |
| 12 | `.../customer12-dc2_s/scripts/02_load_customer12_data_SMART.py` |
| 13 | `.../customer13-dc2_s/scripts/02_load_customer13_data_SMART.py` |
| 14 | `.../customer14-dc2_s/scripts/02_load_customer14_data_SMART.py` |
| 15 | `.../customer15-dc2_s/scripts/02_load_customer15_data_SMART.py` |
| 17 | `.../customer17-dc2_s/scripts/02_load_customer17_data_SMART.py` |
| **19** | `.../customer19-dc2_s/scripts/02_load_customer19_data_SMART.py` |
| 23 | `.../customer23-dc2_s/scripts/02_load_customer23_data_SMART.py` |
| 33 | `.../customer33-dc2_s/scripts/02_load_customer33_data_SMART.py` |
| 35 | `.../customer35-dc2_s/scripts/02_load_customer35_data_SMART.py` |
| 102 | `.../customer102-dc2_s/scripts/02_load_customer102_data_SMART.py` |
| 273 | `.../customer273-dc2_s/scripts/02_load_customer273_data_SMART.py` |
| 274 | `.../customer274-dc2_s/scripts/02_load_customer274_data_SMART.py` |
| 999 | `.../customer999-dc2_s/scripts/02_load_customer999_data_SMART.py` |

## Pre-configured logins (after you run the right scripts)

None of these create data by themselves; the **customer** must have data loaded first.

| Email | Password | Customer ID | How created | Has data if |
|-------|----------|------------|-------------|-------------|
| **admin@example.com** | admin123 | Demo Company (varies) | `seed_all_data.py` | Only if you add accounts for that customer (e.g. upload or another seed). |
| **dc2s_super@test.com** | DC2_Super_2024! | **5** | `setup_dc2s_test_user.py` or `scripts/fix_dc2s_super_login.py` | Only if customer 5 has accounts (onboarding/upload/rehydration or legacy 02_Load*). **If login fails**, run `python scripts/fix_dc2s_super_login.py`. |
| **test_19@cspulse.test** | (test fixture) | 19 | test seed | Yes, if you ran `02_load_customer19_data_SMART.py`. |
| **admin@dc2s-demo.example.com** | (you set on onboarding) | 19 | Onboarding API (example payload) | Yes, if onboarding was run for customer 19 and `02_load_customer19_data_SMART.py` was run. |

So in practice, the logins that are **already wired in code** to a customer that has a load script are:

- **dc2s_super@test.com** → customer **5** (run customer 5 load script, then this login has data).
- **test_19@cspulse.test** → customer **19** (run customer 19 load script for tests).
- Any user you create via onboarding for e.g. customer **19** (run customer 19 load script).

## How to fix demo@cspulse.ai (two options)

### Option A: Give that user’s customer some data

1. Run `python scripts/list_users_and_customer_data.py` and note **customer_id** for `demo@cspulse.ai`.
2. If that customer has a load script (e.g. customer 19 → `verticals/customer19-dc2_s/scripts/02_load_customer19_data_SMART.py`), run it from **backend**:
   ```bash
   cd verticals/customer19-dc2_s/scripts && python 02_load_customer19_data_SMART.py
   ```
3. Reload the app and log in again with demo@cspulse.ai; the dashboard should show data.

### Option B: Point demo@cspulse.ai at a customer that already has data

1. Run the list script and pick a **customer_id** that already has accounts (e.g. 19 after loading customer 19).
2. Update the user in the DB (replace `19` with the chosen customer_id):
   ```sql
   UPDATE users SET customer_id = 19 WHERE email = 'demo@cspulse.ai';
   ```
   Or use a one-off script with Flask-SQLAlchemy and the `User` model.
3. Log in again with demo@cspulse.ai; the dashboard will show that customer’s data.

## Quick Data Center demo (customer 19)

1. Load customer 19 data (from repo root):
   ```bash
   cd kpi-dashboard/backend/verticals/customer19-dc2_s/scripts
   python 02_load_customer19_data_SMART.py
   ```
2. Ensure a user exists for customer 19 and you know the password:
   - Either create one via onboarding (e.g. email `admin@dc2s-demo.example.com`, customer_id 19), or
   - Create/update a user in the DB with `customer_id = 19` and set a password (e.g. with `setup_dc2s_test_user.py` logic but for customer 19 and your desired email/password).
3. Log in with that email; you should see customer 19’s accounts and data.
