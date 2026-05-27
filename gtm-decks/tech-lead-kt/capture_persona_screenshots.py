#!/usr/bin/env python3
"""Capture authenticated persona dashboard screenshots for the tech-lead KT doc.

Logs into the live EC2 deployment as cust 334 super-admin, navigates to each
persona dashboard, takes a top-of-fold screenshot. Output: screenshots/persona_<name>.png

Run from gtm-decks/tech-lead-kt:
    python3 capture_persona_screenshots.py
"""
from pathlib import Path
from playwright.sync_api import sync_playwright

BASE = "http://3.94.106.197"
EMAIL = "dc2s_super@test.com"
PASSWORD = "DC2_Super_2024!"
OUT_DIR = Path(__file__).parent / "screenshots"
OUT_DIR.mkdir(exist_ok=True)

# (persona name, dashboard URL, wait seconds for late-loading tiles)
DASHBOARDS = [
    ("cro",    f"{BASE}/cro-dashboard",  8),
    ("cfo",    f"{BASE}/cfo-dashboard",  8),
    ("ceo",    f"{BASE}/ceo-dashboard",  6),
    ("vpcs",   f"{BASE}/vpcs-dashboard", 6),
    ("csm",    f"{BASE}/saas-dashboard/csm", 6),
    ("outcome_roi", f"{BASE}/outcome-roi", 6),
]


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(viewport={"width": 1440, "height": 900})
        page = ctx.new_page()

        # ── Log in
        page.goto(f"{BASE}/login", wait_until="networkidle")
        page.wait_for_timeout(1500)

        # Switch to Password tab (default is Magic Link)
        try:
            page.get_by_role("button", name="Password").click(timeout=3000)
        except Exception:
            pass
        page.wait_for_timeout(500)

        page.fill('input[type="email"]', EMAIL)
        page.fill('input[type="password"]', PASSWORD)
        page.get_by_role("button", name="Sign In").click()
        page.wait_for_timeout(4000)
        print(f"  logged in → {page.url}")

        # ── Capture each persona
        for name, url, wait_s in DASHBOARDS:
            print(f"capturing {name}: {url}")
            page.goto(url, wait_until="networkidle", timeout=30000)
            page.wait_for_timeout(wait_s * 1000)
            out = OUT_DIR / f"persona_{name}.png"
            page.screenshot(path=str(out), full_page=False)  # top-of-fold only
            print(f"  → {out} ({out.stat().st_size:,} bytes)")

            # Also capture full-page for CRO + CFO (the two most demo-critical)
            if name in ("cro", "cfo"):
                out_full = OUT_DIR / f"persona_{name}_fullpage.png"
                page.screenshot(path=str(out_full), full_page=True)
                print(f"  → {out_full} ({out_full.stat().st_size:,} bytes)")

        browser.close()
    print("done.")


if __name__ == "__main__":
    main()
