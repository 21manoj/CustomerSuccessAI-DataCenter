#!/usr/bin/env python3
"""Post-deploy verification: VPCS Phases 0–5 (customer 334 on EC2)."""

import json
import re
import sys
import urllib.error
import urllib.request
import http.cookiejar

BASE = "http://3.94.106.197"
EMAIL = "dc2s_super@test.com"
PASSWORD = "DC2_Super_2024!"
CUST = 334


def main() -> int:
    cj = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
    login_body = json.dumps({"email": EMAIL, "password": PASSWORD}).encode()
    req = urllib.request.Request(
        f"{BASE}/api/login",
        data=login_body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        opener.open(req, timeout=30)
    except urllib.error.HTTPError as e:
        print(f"LOGIN FAIL: {e.code}")
        return 1

    def get(path: str):
        return opener.open(
            urllib.request.Request(
                f"{BASE}{path}",
                headers={"X-Customer-ID": str(CUST)},
            ),
            timeout=120,
        )

    ok = True

    print("--- Phase 3: team-capacity capacity_planning ---")
    cap = json.loads(get("/api/v1/team-capacity").read().decode())
    planning = cap.get("capacity_planning") or {}
    uncovered = cap.get("uncovered_at_risk")
    print(f"  csm_count: {cap.get('csm_count')}")
    print(f"  recommended_csm: {planning.get('recommended_csm_count')}")
    print(f"  top_performers: {len(planning.get('top_performers') or [])}")
    print(f"  uncovered_at_risk: {len(uncovered or [])}")
    if not planning.get("recommended_csm_count"):
        print("  FAIL: missing capacity_planning.recommended_csm_count")
        ok = False
    else:
        print("  capacity_planning OK")

    print("\n--- Phase 1: portfolio-summary graph $ ---")
    roi = json.loads(get("/api/outcome-roi/portfolio-summary").read().decode())
    cfo = json.loads(get("/api/executive/cfo-dashboard").read().decode())
    for field in ("revenue_at_risk", "revenue_protected", "expansion_pipeline"):
        rv, cv = roi.get(field), cfo.get(field)
        match = rv == cv
        print(f"  {field}: portfolio={rv} cfo={cv} {'OK' if match else 'MISMATCH'}")
        if not match:
            ok = False

    print("\n--- Phase 3: renewals API ---")
    ren = json.loads(get("/api/v1/renewals?days=90").read().decode())
    print(f"  renewals count: {len(ren.get('renewals') or [])}")

    html = opener.open(f"{BASE}/", timeout=30).read().decode()
    m = re.search(r"/static/js/main\.([a-f0-9]+)\.js", html)
    if m:
        js = opener.open(f"{BASE}/static/js/main.{m.group(1)}.js", timeout=60).read().decode(
            errors="ignore"
        )
        markers = [
            ("Phase 0 metric guide", "How to read VP CS metrics"),
            ("Phase 1 graph strip", "Revenue intelligence (context graph)"),
            ("Phase 2 pre-proof", "Playbook success is logged"),
            ("Phase 3 capacity", "Capacity planning & allocation"),
            ("Phase 3 performers", "critical → expansion"),
        ]
        print("\n--- UI bundle markers ---")
        for label, needle in markers:
            hit = needle in js
            print(f"  {label}: {'OK' if hit else 'MISSING'}")
            if not hit:
                ok = False
    else:
        print("  FAIL: main.js hash not found")
        ok = False

    print("\n" + ("PASS" if ok else "FAIL"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
