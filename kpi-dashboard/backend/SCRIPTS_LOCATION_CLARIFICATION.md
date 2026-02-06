# Scripts Location Clarification

## 📁 Current Structure

### Template Directory Structure:
```
verticals/_template/
├── scripts/                    ← Data loading scripts (02_load, 03_embed, etc.)
│   ├── 02_load_customer9_data_SMART.py
│   ├── 03_embed_customer9_OPENAI.py
│   └── ...
└── journey/
    └── scripts/                ← Journey-related scripts (if any)
```

### Expected Customer Directory Structure:
```
verticals/customer19-dc2_s/
├── scripts/                    ← Should contain data loading scripts
│   ├── 02_load_customer19_data_SMART.py
│   ├── 03_embed_customer19_OPENAI.py
│   └── ...
└── journey/
    ├── wizard_a/
    ├── wizard_b/
    ├── wizard_c/
    └── scripts/                ← Journey scripts (if copied from template)
```

## 🔍 Code Expectations

The `process-data` endpoint expects scripts at:
```python
load_script = customer_dir / "scripts" / f"02_load_customer{customer_id}_data_SMART.py"
embed_script = customer_dir / "scripts" / f"03_embed_customer{customer_id}_OPENAI.py"
```

**Location:** `verticals/customer19-dc2_s/scripts/`

**NOT:** `verticals/customer19-dc2_s/journey/scripts/`

## ❓ Question

You asked: "scripts are in verticals/customer19-dc2_s/journey/scripts, correct?"

**Answer:** ❌ **NO** - Scripts should be in `verticals/customer19-dc2_s/scripts/`

However, the template has BOTH:
1. `_template/scripts/` - Data loading scripts (what we need)
2. `_template/journey/scripts/` - Journey scripts (if any)

## 🔧 Current Issue

Customer 19 directory structure:
```
verticals/customer19-dc2_s/
├── data/
└── DEMO_MANIFEST.md
```

**Missing:**
- ❌ `scripts/` directory
- ❌ `journey/` directory

This confirms that the provision script didn't copy files correctly (0 files copied).

## ✅ Solution

After fixing the provision script path issue, scripts should be at:
- **Primary location:** `verticals/customer19-dc2_s/scripts/`
- **Journey scripts (if any):** `verticals/customer19-dc2_s/journey/scripts/`

The `process-data` endpoint looks for scripts in the **primary location** (`scripts/`), not in `journey/scripts/`.
