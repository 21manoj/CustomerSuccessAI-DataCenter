#!/usr/bin/env python3
"""Post-deploy verification: CFO Phases 0–5 (customer 334 on EC2)."""

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

    cfo = json.loads(get("/api/executive/cfo-dashboard").read().decode())
    ok = True

    print("--- Phase 3: ROI scaling + efficiency ---")
    scaling = cfo.get("roi_scaling") or {}
    projs = scaling.get("projections") or []
    has_growth = any(p.get("growth_bar", 0) > 0 for p in projs)
    has_roi = any(p.get("roi", 0) > 0 for p in projs)
    print(f"  projections: {[p.get('roi') for p in projs]}")
    print(f"  growth_bar: {[p.get('growth_bar') for p in projs]}")
    print(f"  efficiency.available: {(cfo.get('efficiency') or {}).get('available')}")
    if not has_roi:
        print("  WARN: all scaling roi are 0")
    if not has_growth and has_roi:
        print("  FAIL: roi > 0 but growth_bar all 0")
        ok = False
    if has_roi and has_growth:
        print("  Phase 3 API: scaling + bars OK")

    eff = cfo.get("efficiency") or {}
    if eff.get("available"):
        print(f"  efficiency source={eff.get('source')} score={eff.get('efficiency_score')}")
    else:
        print("  WARN: efficiency block not available (may be OK pre-proof)")

    html = opener.open(f"{BASE}/", timeout=30).read().decode()
    m = re.search(r"/static/js/main\.([a-f0-9]+)\.js", html)
    if m:
        js = opener.open(f"{BASE}/static/js/main.{m.group(1)}.js", timeout=60).read().decode(
            errors="ignore"
        )
        phase_markers = [
            ("Phase 0/2 metric guide", "How to read CFO metrics"),
            ("Phase 2 pre-proof", "ROI tiles are Power-of-1 estimates until playbooks close"),
            ("Phase 1 graph strip", "Revenue intelligence (context graph)"),
            ("Phase 3 efficiency panel", "CS Efficiency"),
            ("Phase 3 modeled badge", "Modeled · Po1"),
            ("Phase 3 growth_bar from API", "growth_bar: s.growth_bar"),
        ]
        print("\n--- UI bundle markers ---")
        for label, needle in phase_markers:
            if needle in js:
                print(f"  {label}: OK")
            else:
                print(f"  {label}: MISSING ({needle})")
                if "Phase 3" in label or "Phase 4" in label:
                    ok = False

    print("\n--- Phase 5: proof path ---")
    proof = cfo.get("proof_data") or {}
    print(f"  proof executions_total={proof.get('executions_total')} realized_roi={proof.get('realized_roi')}")
    if proof.get("total_cost", 0) > 0:
        print("  Golden proof path: data present")
    else:
        print("  Golden proof path: pre-proof (expected on demo tenant)")

    print("\n" + ("PASS" if ok else "FAIL"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
