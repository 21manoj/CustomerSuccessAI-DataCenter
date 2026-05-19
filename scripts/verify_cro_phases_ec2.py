#!/usr/bin/env python3
"""Post-deploy verification: CRO Phases 0–5 (customer 334 on EC2)."""

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
    cro = json.loads(get("/api/executive/cro-dashboard").read().decode())
    cfo = json.loads(get("/api/executive/cfo-dashboard").read().decode())

    print("--- Phase 1: CRO/CFO context-graph $ parity ---")
    for field in ("revenue_at_risk", "revenue_protected", "expansion_pipeline"):
        cv, cc = cro.get(field), cfo.get(field)
        match = cv == cc
        print(f"  {field}: CRO={cv} CFO={cc} {'OK' if match else 'MISMATCH'}")
        if not match:
            ok = False

    print("\n--- Phase 3: period_meta API ---")
    cro_q3 = json.loads(get("/api/executive/cro-dashboard?period=Q3").read().decode())
    pm = cro_q3.get("period_meta") or {}
    print(f"  period echo: {cro_q3.get('period')}")
    print(f"  period_meta.filter_mode: {pm.get('filter_mode')}")
    if pm.get("filter_mode") != "client_side":
        print("  FAIL: expected client_side filter_mode")
        ok = False
    else:
        print("  Phase 3 API: period_meta OK")

    print(f"  arr_exposure: {cro.get('arr_exposure')}")
    print(f"  context_graph_provenance: {'yes' if cro.get('context_graph_provenance') else 'no'}")

    html = opener.open(f"{BASE}/", timeout=30).read().decode()
    m = re.search(r"/static/js/main\.([a-f0-9]+)\.js", html)
    if m:
        js = opener.open(f"{BASE}/static/js/main.{m.group(1)}.js", timeout=60).read().decode(
            errors="ignore"
        )
        markers = [
            ("Phase 0 metric guide", "How to read CRO metrics"),
            ("Phase 1 graph strip", "Revenue intelligence (context graph)"),
            ("Phase 2 pre-proof", "Playbook ROI is estimated until attributions close"),
            ("Phase 0 ARR exposure", "ARR exposure"),
        ]
        print("\n--- UI bundle markers ---")
        for label, needle in markers:
            if needle in js:
                print(f"  {label}: OK")
            else:
                print(f"  {label}: MISSING ({needle})")
                ok = False

    proof = cro.get("proof_data") or {}
    print("\n--- Phase 5: proof path ---")
    print(f"  executions_total={proof.get('executions_total')} realized_roi={proof.get('realized_roi')}")

    print("\n" + ("PASS" if ok else "FAIL"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
