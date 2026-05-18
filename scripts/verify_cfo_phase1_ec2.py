#!/usr/bin/env python3
"""Post-deploy verification: CFO Phase 0–2 (customer 334 on EC2)."""

import json
import sys
import urllib.error
import urllib.parse
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
        r = opener.open(req, timeout=30)
        login = json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        print(f"LOGIN FAIL: {e.code} {e.read().decode()[:300]}")
        return 1

    print(f"LOGIN OK customer_id={login.get('customer_id')} tier={login.get('subscription_tier')}")

    def get(path: str):
        return opener.open(
            urllib.request.Request(
                f"{BASE}{path}",
                headers={"X-Customer-ID": str(CUST)},
            ),
            timeout=120,
        )

    health = json.loads(get("/api/health").read().decode())
    print(f"HEALTH: {health.get('status', health)}")

    cro = json.loads(get("/api/executive/cro-dashboard").read().decode())
    cfo = json.loads(get("/api/executive/cfo-dashboard").read().decode())

    cro_risk = cro.get("revenue_at_risk")
    cro_prot = cro.get("revenue_protected")
    cro_exp = cro.get("expansion_pipeline")

    cfo_risk = cfo.get("revenue_at_risk")
    cfo_prot = cfo.get("revenue_protected")
    cfo_exp = cfo.get("expansion_pipeline")
    prov = cfo.get("context_graph_provenance") or {}

    print("\n--- Context graph $ (CRO vs CFO must match) ---")
    print(f"  CRO  at_risk={cro_risk:,.0f}  protected={cro_prot:,.0f}  expansion={cro_exp:,.0f}")
    print(f"  CFO  at_risk={cfo_risk:,.0f}  protected={cfo_prot:,.0f}  expansion={cfo_exp:,.0f}")
    print(f"  OUTCOME nodes: {prov.get('outcome_node_count')}")
    samples = (prov.get("revenue_at_risk") or {}).get("sample_nodes") or []
    print(f"  Sample at-risk OUTCOMEs: {len(samples)}")

    ok = True
    if cro_risk != cfo_risk:
        print("  FAIL: revenue_at_risk mismatch CRO vs CFO")
        ok = False
    if cro_prot != cfo_prot:
        print("  FAIL: revenue_protected mismatch CRO vs CFO")
        ok = False
    if cro_exp != cfo_exp:
        print("  FAIL: expansion_pipeline mismatch CRO vs CFO")
        ok = False
    if not cfo_exp and cfo_exp != 0:
        print("  FAIL: expansion_pipeline missing on CFO")
        ok = False
    if prov.get("outcome_node_count", 0) < 1:
        print("  WARN: no outcome nodes in provenance")

    # Frontend bundle marker
    html = opener.open(f"{BASE}/", timeout=30).read().decode()
    if "main." in html:
        import re

        m = re.search(r"/static/js/main\.([a-f0-9]+)\.js", html)
        if m:
            js = opener.open(f"{BASE}/static/js/main.{m.group(1)}.js", timeout=60).read().decode(
                errors="ignore"
            )
            if "Revenue intelligence (context graph)" in js:
                print("\nUI bundle: contains Phase 1 panel title string ✓")
            else:
                print("\nUI bundle: MISSING 'Revenue intelligence (context graph)' in main.js")
                ok = False
            if "Confirmed revenue at risk" in js:
                print("UI bundle: contains 'Confirmed revenue at risk' ✓")
            else:
                print("UI bundle: MISSING confirmed at risk label")
                ok = False
            phase2_markers = [
                "Modeled cost of inaction",
                "How to read CFO metrics",
            ]
            for marker in phase2_markers:
                if marker in js:
                    print(f"UI bundle: contains Phase 0/2 '{marker}' ✓")
                else:
                    print(f"UI bundle: MISSING '{marker}'")
                    ok = False
            # Phase 2 strings ship when frontend is rebuilt with latest CFODashboard.tsx
            if "ROI tiles are Power-of-1 estimates until playbooks close" in js:
                print("UI bundle: Phase 2 pre-proof banner ✓")
            else:
                print("UI bundle: Phase 2 banner not in bundle (rebuild frontend if expected)")

    print("\n" + ("PASS" if ok else "FAIL"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
