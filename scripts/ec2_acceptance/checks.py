"""Executive dashboard acceptance checks (CFO / CRO / VPCS)."""

from __future__ import annotations

from .http_client import AcceptanceClient


def verify_cfo_phases(client: AcceptanceClient) -> bool:
    cfo = client.get_json("/api/executive/cfo-dashboard")
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

    js = client.fetch_main_js()
    if js:
        phase_markers = [
            ("Phase 0/2 metric guide", "How to read CFO metrics"),
            ("Phase 2 pre-proof", "ROI tiles are Power-of-1 estimates until playbooks close"),
            ("Phase 1 graph strip", "Revenue intelligence (context graph)"),
            ("Phase 3 efficiency panel", "CS Efficiency"),
        ]
        phase3_bundle_checks = [
            ("Phase 3 modeled badge", lambda s: "Modeled" in s and "Po1" in s),
            ("Phase 3 growth_bar from API", lambda s: s.count("growth_bar") >= 2),
        ]
        print("\n--- UI bundle markers ---")
        ok = client.check_js_markers(js, phase_markers, fail_labels=lambda l: "Phase 3" in l or "Phase 4" in l) and ok
        for label, check in phase3_bundle_checks:
            if check(js):
                print(f"  {label}: OK")
            else:
                print(f"  {label}: MISSING")
                ok = False

    print("\n--- Phase 5: proof path ---")
    proof = cfo.get("proof_data") or {}
    print(f"  proof executions_total={proof.get('executions_total')} realized_roi={proof.get('realized_roi')}")
    if proof.get("total_cost", 0) > 0:
        print("  Golden proof path: data present")
    else:
        print("  Golden proof path: pre-proof (expected on demo tenant)")

    return ok


def verify_cfo_phase1(client: AcceptanceClient) -> bool:
    login_resp = client.get_json("/api/health")
    print(f"HEALTH: {login_resp.get('status', login_resp)}")

    cro = client.get_json("/api/executive/cro-dashboard")
    cfo = client.get_json("/api/executive/cfo-dashboard")

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

    js = client.fetch_main_js()
    if js:
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
        for marker in ("Modeled cost of inaction", "How to read CFO metrics"):
            if marker in js:
                print(f"UI bundle: contains Phase 0/2 '{marker}' ✓")
            else:
                print(f"UI bundle: MISSING '{marker}'")
                ok = False
        if "ROI tiles are Power-of-1 estimates until playbooks close" in js:
            print("UI bundle: Phase 2 pre-proof banner ✓")
        else:
            print("UI bundle: Phase 2 banner not in bundle (rebuild frontend if expected)")

    return ok


def verify_cro_phases(client: AcceptanceClient) -> bool:
    ok = True
    cro = client.get_json("/api/executive/cro-dashboard")
    cfo = client.get_json("/api/executive/cfo-dashboard")

    print("--- Phase 1: CRO/CFO context-graph $ parity ---")
    for field in ("revenue_at_risk", "revenue_protected", "expansion_pipeline"):
        cv, cc = cro.get(field), cfo.get(field)
        match = cv == cc
        print(f"  {field}: CRO={cv} CFO={cc} {'OK' if match else 'MISMATCH'}")
        if not match:
            ok = False

    print("\n--- Phase 3: period_meta API ---")
    cro_q3 = client.get_json("/api/executive/cro-dashboard?period=Q3")
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

    js = client.fetch_main_js()
    if js:
        markers = [
            ("Phase 0 metric guide", "How to read CRO metrics"),
            ("Phase 1 graph strip", "Revenue intelligence (context graph)"),
            ("Phase 2 pre-proof", "Playbook ROI is estimated until attributions close"),
            ("Phase 0 ARR exposure", "ARR exposure"),
        ]
        print("\n--- UI bundle markers ---")
        ok = client.check_js_markers(js, markers) and ok

    proof = cro.get("proof_data") or {}
    print("\n--- Phase 5: proof path ---")
    print(f"  executions_total={proof.get('executions_total')} realized_roi={proof.get('realized_roi')}")

    return ok


def verify_vpcs_phases(client: AcceptanceClient) -> bool:
    ok = True

    print("--- Phase 3: team-capacity capacity_planning ---")
    cap = client.get_json("/api/v1/team-capacity")
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
    roi = client.get_json("/api/outcome-roi/portfolio-summary")
    cfo = client.get_json("/api/executive/cfo-dashboard")
    for field in ("revenue_at_risk", "revenue_protected", "expansion_pipeline"):
        rv, cv = roi.get(field), cfo.get(field)
        match = rv == cv
        print(f"  {field}: portfolio={rv} cfo={cv} {'OK' if match else 'MISMATCH'}")
        if not match:
            ok = False

    print("\n--- Phase 3: renewals API ---")
    ren = client.get_json("/api/v1/renewals?days=90")
    print(f"  renewals count: {len(ren.get('renewals') or [])}")

    js = client.fetch_main_js()
    if js:
        markers = [
            ("Phase 0 metric guide", "How to read VP CS metrics"),
            ("Phase 1 graph strip", "Revenue intelligence (context graph)"),
            ("Phase 2 pre-proof", "Playbook success is logged"),
            ("Phase 3 capacity", "Capacity planning & allocation"),
            ("Phase 3 performers", "Top performers"),
        ]
        print("\n--- UI bundle markers ---")
        ok = client.check_js_markers(js, markers) and ok
    else:
        print("  FAIL: main.js hash not found")
        ok = False

    return ok
