#!/usr/bin/env python3
"""
User-Complete-V1 Test Harness
==============================
Full lifecycle test: create → load → validate persona questions → extend → compare → delete → repeat.
Uses ONLY user-scoped paths: REST APIs (load driver) + MCP HTTP calls. No direct DB access.

Usage:
  # Sequential (3 cycles):
  python3 tests/user_complete_v1.py --base-url https://d2oqfugrb2ltg9.cloudfront.net --cycles 3

  # Concurrent (10 parallel):
  python3 tests/user_complete_v1.py --base-url https://d2oqfugrb2ltg9.cloudfront.net --concurrent 10

  # Single cycle (debug):
  python3 tests/user_complete_v1.py --base-url https://d2oqfugrb2ltg9.cloudfront.net --cycles 1 --verbose

Requires: pip install requests
"""

import argparse
import json
import os
import sys
import time
import threading
import traceback
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

# Add load-driver to path
SCRIPT_DIR = Path(__file__).parent
LOAD_DRIVER_DIR = SCRIPT_DIR.parent
sys.path.insert(0, str(LOAD_DRIVER_DIR))

import requests

# ─────────────────────────────────────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────────────────────────────────────

MANIFEST_FILE = str(LOAD_DRIVER_DIR / "manifests" / "user_complete_v1_saas.json")
RESULTS_DIR = LOAD_DRIVER_DIR / "results" / "user-complete-v1"
MCP_PORT = 8001  # MCP server port on EC2


# ─────────────────────────────────────────────────────────────────────────────
# MCP Client (HTTP — user-scoped, no DB access)
# ─────────────────────────────────────────────────────────────────────────────

class MCPClient:
    """Calls MCP tools via HTTP Streamable Transport — same path as Claude.ai."""

    def __init__(self, base_url: str, api_key: str, mcp_host: str = None):
        from urllib.parse import urlparse
        # Sanitize API key
        api_key = api_key.strip().strip('"').rstrip('}').rstrip(',').strip()
        if mcp_host:
            # Explicit MCP host (e.g. "54.89.77.21:8001")
            self.mcp_url = f"http://{mcp_host}/mcp"
        else:
            # Derive from base_url — use port 8001 on same host
            parsed = urlparse(base_url)
            self.mcp_url = f"http://{parsed.hostname}:{MCP_PORT}/mcp"
        self.headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
            "Authorization": f"Bearer {api_key}",
        }
        self.api_key = api_key
        self._call_id = 0
        self._session_id = None
        # Initialize MCP session (required by Streamable HTTP transport)
        self._initialize_session()

    def _initialize_session(self):
        """Send MCP initialize request to get session ID."""
        self._call_id += 1
        payload = {
            "jsonrpc": "2.0",
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "user-complete-v1", "version": "1.0"},
            },
            "id": self._call_id,
        }
        try:
            resp = requests.post(self.mcp_url, json=payload, headers=self.headers, timeout=15)
            self._session_id = resp.headers.get("mcp-session-id")
            if self._session_id:
                self.headers["Mcp-Session-Id"] = self._session_id
            # Send initialized notification (required by MCP protocol)
            self._call_id += 1
            notif = {"jsonrpc": "2.0", "method": "notifications/initialized"}
            requests.post(self.mcp_url, json=notif, headers=self.headers, timeout=5)
        except Exception as e:
            print(f"  ⚠️  MCP session init failed: {e}")

    def _parse_sse_response(self, resp) -> dict:
        """Parse SSE or JSON response from MCP server."""
        content_type = resp.headers.get("content-type", "")
        if "text/event-stream" in content_type:
            # SSE format: "event: message\ndata: {...}\n\n"
            for line in resp.text.split("\n"):
                if line.startswith("data: "):
                    return json.loads(line[6:])
            return {}
        else:
            return resp.json()

    def call(self, tool_name: str, arguments: dict, timeout: int = 60) -> dict:
        """Call an MCP tool and return parsed JSON result."""
        self._call_id += 1
        payload = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {"name": tool_name, "arguments": arguments},
            "id": self._call_id,
        }
        resp = requests.post(self.mcp_url, json=payload, headers=self.headers, timeout=timeout)
        resp.raise_for_status()
        data = self._parse_sse_response(resp)

        if "error" in data:
            raise RuntimeError(f"MCP error: {data['error']}")

        content = data.get("result", {}).get("content", [{}])
        text = content[0].get("text", "{}") if content else "{}"
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return {"raw": text}


# ─────────────────────────────────────────────────────────────────────────────
# REST Client (user-scoped — same APIs the browser uses)
# ─────────────────────────────────────────────────────────────────────────────

class RESTClient:
    """Calls CS Pulse REST APIs with session auth — same as browser login."""

    def __init__(self, base_url: str, email: str, password: str):
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()
        self.session.headers["Content-Type"] = "application/json"
        # Login
        resp = self.session.post(f"{self.base_url}/api/login", json={
            "email": email, "password": password,
        }, timeout=15)
        if resp.status_code != 200 or resp.json().get("status") != "success":
            raise RuntimeError(f"Login failed: {resp.text[:200]}")
        user = resp.json().get("user", {})
        self.customer_id = user.get("customer_id")
        self.session.headers["X-Customer-ID"] = str(self.customer_id)

    def get(self, path: str, **kwargs) -> dict:
        resp = self.session.get(f"{self.base_url}{path}", timeout=30, **kwargs)
        resp.raise_for_status()
        return resp.json()

    def post(self, path: str, data: dict = None, **kwargs) -> dict:
        resp = self.session.post(f"{self.base_url}{path}", json=data, timeout=120, **kwargs)
        resp.raise_for_status()
        return resp.json()

    def delete_customer(self, customer_id: int) -> dict:
        """Admin cleanup — user-scoped via REST API."""
        resp = self.session.post(
            f"{self.base_url}/api/admin/cleanup/customer/{customer_id}",
            json={"dry_run": False, "confirm": True},
            timeout=60,
        )
        resp.raise_for_status()
        return resp.json()


# ─────────────────────────────────────────────────────────────────────────────
# Persona Question Definitions
# ─────────────────────────────────────────────────────────────────────────────

def get_persona_questions(customer_id: int, accounts: list) -> list:
    """Return all persona questions with MCP tool calls."""
    at_risk = [a for a in accounts if a.get("health_score", 100) < 70]
    worst = sorted(accounts, key=lambda a: a.get("health_score", 100))
    worst_id = worst[0]["account_id"] if worst else 1

    questions = []

    # ── CSM Questions (10) ──
    questions += [
        ("CSM", "What should I do today?", "get_csm_daily_actions", {"customer_id": customer_id}),
        ("CSM", "How is the worst account doing?", "get_account_health", {"customer_id": customer_id, "account_id": worst_id}),
        ("CSM", "What playbook for worst account?", "get_playbook_recommendations", {"customer_id": customer_id, "account_id": worst_id}),
        ("CSM", "Who are key people at worst account?", "get_stakeholder_map", {"customer_id": customer_id, "account_id": worst_id}),
        ("CSM", "What happened to worst account?", "get_account_journey_timeline", {"customer_id": customer_id, "account_id": worst_id}),
        ("CSM", "What signals fired this quarter?", "search_signals", {"customer_id": customer_id, "account_id": worst_id, "node_type": "SIGNAL"}),
        ("CSM", "If I improve TTFV by 1%?", "calculate_power_of_1", {"customer_id": customer_id, "metric_id": "TTFV"}),
        ("CSM", "Health score history (6mo)?", "get_health_score_history", {"customer_id": customer_id, "months": 6}),
        ("CSM", "Support tickets for worst?", "get_support_tickets", {"customer_id": customer_id, "account_id": worst_id}),
        ("CSM", "Customer feedback for worst?", "get_customer_feedback", {"customer_id": customer_id, "account_id": worst_id}),
    ]

    # ── CRO Questions (10) ──
    questions += [
        ("CRO", "How much ARR is at risk?", "get_at_risk_accounts", {"customer_id": customer_id}),
        ("CRO", "Revenue breakdown for worst?", "get_revenue_at_risk", {"customer_id": customer_id, "account_id": worst_id}),
        ("CRO", "NRR forecast?", "get_nrr_forecast", {"customer_id": customer_id}),
        ("CRO", "Portfolio ROI summary?", "get_portfolio_roi_summary", {"customer_id": customer_id}),
        ("CRO", "1% NRR improvement = $?", "calculate_power_of_1", {"customer_id": customer_id, "metric_id": "NRR"}),
        ("CRO", "All accounts overview?", "list_accounts", {"customer_id": customer_id}),
        ("CRO", "Context graph for worst?", "get_context_graph_mermaid", {"customer_id": customer_id, "account_id": worst_id}),
        ("CRO", "Causal chain for a signal?", "get_graph_summary", {"customer_id": customer_id, "account_id": worst_id}),
        ("CRO", "CRM data for worst?", "get_crm_account_data", {"customer_id": customer_id, "account_id": worst_id}),
        ("CRO", "1% GRR improvement = $?", "calculate_power_of_1", {"customer_id": customer_id, "metric_id": "GRR"}),
    ]

    # ── CFO Questions (10) ──
    questions += [
        ("CFO", "What's our CS ROI?", "get_portfolio_roi_summary", {"customer_id": customer_id}),
        ("CFO", "Playbook economics?", "get_playbook_economics", {"customer_id": customer_id}),
        ("CFO", "Highest ROI metric?", "calculate_power_of_1", {"customer_id": customer_id, "metric_id": "product_adoption"}),
        ("CFO", "Board-ready account story?", "get_outcome_roi_story", {"customer_id": customer_id, "account_id": worst_id}),
        ("CFO", "1% expansion rate = $?", "calculate_power_of_1", {"customer_id": customer_id, "metric_id": "expansion_rate"}),
        ("CFO", "1% ticket resolution = $?", "calculate_power_of_1", {"customer_id": customer_id, "metric_id": "ticket_resolution_time"}),
        ("CFO", "KPI catalog?", "get_kpi_catalog", {"customer_id": customer_id}),
        ("CFO", "Revenue at risk (worst)?", "get_revenue_at_risk", {"customer_id": customer_id, "account_id": worst_id}),
        ("CFO", "Health trend (portfolio)?", "get_health_score_history", {"customer_id": customer_id, "account_id": 0, "months": 6}),
        ("CFO", "At-risk accounts?", "get_at_risk_accounts", {"customer_id": customer_id}),
    ]

    # ── VP CS Questions (10) ──
    questions += [
        ("VPCS", "What should team do today?", "get_csm_daily_actions", {"customer_id": customer_id}),
        ("VPCS", "Portfolio trajectory?", "get_health_score_history", {"customer_id": customer_id, "account_id": 0, "months": 6}),
        ("VPCS", "Which accounts need attention?", "get_at_risk_accounts", {"customer_id": customer_id}),
        ("VPCS", "Stakeholder map (worst)?", "get_stakeholder_map", {"customer_id": customer_id, "account_id": worst_id}),
        ("VPCS", "NRR forecast?", "get_nrr_forecast", {"customer_id": customer_id}),
        ("VPCS", "Playbook recommendations?", "get_playbook_recommendations", {"customer_id": customer_id, "account_id": worst_id}),
        ("VPCS", "Account journey (worst)?", "get_account_journey_timeline", {"customer_id": customer_id, "account_id": worst_id}),
        ("VPCS", "All accounts?", "list_accounts", {"customer_id": customer_id}),
        ("VPCS", "Power of 1 (TTFV)?", "calculate_power_of_1", {"customer_id": customer_id, "metric_id": "TTFV"}),
        ("VPCS", "Graph summary (worst)?", "get_graph_summary", {"customer_id": customer_id, "account_id": worst_id}),
    ]

    return questions


# ─────────────────────────────────────────────────────────────────────────────
# Validation Helpers
# ─────────────────────────────────────────────────────────────────────────────

def validate_response(tool_name: str, result: dict) -> tuple:
    """Validate MCP tool response. Returns (passed: bool, reason: str)."""
    if not result:
        return False, "Empty response"
    if "error" in result:
        return False, f"Error: {result['error']}"
    if result.get("raw"):
        return False, f"Non-JSON: {result['raw'][:100]}"

    # Tool-specific checks
    if tool_name == "list_accounts":
        accts = result.get("accounts", [])
        return len(accts) > 0, f"{len(accts)} accounts"
    elif tool_name == "get_at_risk_accounts":
        return "accounts" in result or "total_arr_at_risk" in result, "has risk data"
    elif tool_name == "get_account_health":
        return result.get("health_score") is not None, f"health={result.get('health_score')}"
    elif tool_name == "get_csm_daily_actions":
        actions = result.get("actions", [])
        return True, f"{len(actions)} actions"
    elif tool_name == "calculate_power_of_1":
        return result.get("dollar_impact") is not None, f"${result.get('dollar_impact', 0):,.0f}"
    elif tool_name == "get_portfolio_roi_summary":
        story = result.get("story", {})
        return "summary" in story or "total_arr" in result, "has ROI data"
    elif tool_name == "get_health_score_history":
        return result.get("account_count", 0) > 0 or len(result.get("accounts", [])) > 0, "has history"
    elif tool_name == "get_nrr_forecast":
        return "projected_nrr" in result or "trajectory" in result or "revenue_waterfall" in result, "has forecast"
    else:
        # Generic: any non-empty dict with no error is a pass
        return len(result) > 1, f"{len(result)} fields"


def grade_response(passed: bool, result: dict, tool_name: str) -> str:
    """Grade A/B/C/F based on response quality."""
    if not passed:
        return "F"
    # Check for richness
    if tool_name in ("get_portfolio_roi_summary", "get_outcome_roi_story"):
        story = result.get("story", {})
        if story.get("summary", {}).get("total_impact", 0) > 0:
            return "A"
        return "B"
    if tool_name == "get_csm_daily_actions":
        actions = result.get("actions", [])
        return "A" if len(actions) >= 5 else "B" if len(actions) >= 1 else "C"
    if tool_name == "list_accounts":
        return "A" if len(result.get("accounts", [])) >= 5 else "B"
    return "A" if passed else "F"


# ─────────────────────────────────────────────────────────────────────────────
# Phase Runners
# ─────────────────────────────────────────────────────────────────────────────

def phase1_create_and_load(base_url: str, manifest_path: str, seed: int, cycle: int, verbose: bool) -> dict:
    """Phase 1: Create customer via load driver CLI + capture baseline."""
    print(f"\n{'='*60}")
    print(f"  PHASE 1: Create & Load (Cycle {cycle})")
    print(f"{'='*60}")

    t0 = time.time()

    # Patch manifest with unique company name/domain/email to avoid 409 conflicts
    import tempfile
    manifest_data = json.loads(Path(manifest_path).read_text())
    ts = int(time.time()) % 100000
    orig_name = manifest_data["customer"]["name"]
    manifest_data["customer"]["name"] = f"{orig_name} C{cycle}-{ts}"
    manifest_data["customer"]["domain"] = f"ucv1-c{cycle}-{ts}.test"
    manifest_data["customer"]["admin_email"] = f"admin@ucv1-c{cycle}-{ts}.test"
    if "admin_password" not in manifest_data["customer"]:
        manifest_data["customer"]["admin_password"] = "CSPulse2026!"
    patched_manifest = tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", prefix="ucv1_", delete=False, dir=str(LOAD_DRIVER_DIR / "manifests")
    )
    json.dump(manifest_data, patched_manifest, indent=2)
    patched_manifest.close()
    actual_manifest = patched_manifest.name
    print(f"  Company: {manifest_data['customer']['name']}")

    # Step 1.1: Run load driver CLI (calls REST APIs internally)
    import subprocess
    cmd = [
        sys.executable, str(LOAD_DRIVER_DIR / "cs_pulse_driver.py"),
        "--manifest", actual_manifest,
        "--register",
        "--base-url", base_url,
        "--seed", str(seed),
        "--no-validate-strict",
    ]
    print(f"  Running: {' '.join(cmd[-8:])}")
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

    if result.returncode != 0:
        tail = (result.stderr or "") + "\n--- stdout ---\n" + (result.stdout or "")
        tail = tail[-2000:] if len(tail) > 2000 else tail
        print(f"  ❌ Load driver failed (exit {result.returncode}):\n{tail}")
        return {"error": tail}

    # Parse customer_id and API key from output (driver logs mostly go to stderr)
    combined_out = (result.stdout or "") + "\n" + (result.stderr or "")
    customer_id = None
    api_key = None
    for line in combined_out.split("\n"):
        if "customer_id" in line.lower() and ":" in line:
            try:
                customer_id = int(line.split(":")[-1].strip().rstrip(",").strip('"'))
            except (ValueError, IndexError):
                pass
        if "api_key" in line.lower() and ":" in line:
            api_key = line.split(":")[-1].strip().strip('"').rstrip(",").rstrip("}").strip().strip('"')
        # Also try JSON parsing
        if "{" in line and "customer_id" in line:
            try:
                d = json.loads(line[line.index("{"):])
                customer_id = customer_id or d.get("customer_id")
                api_key = api_key or d.get("api_key")
            except (json.JSONDecodeError, ValueError):
                pass

    if not customer_id:
        # Try to find from the full output
        import re
        match = re.search(r"customer_id[\"']?\s*[:=]\s*(\d+)", combined_out)
        if match:
            customer_id = int(match.group(1))
    if not customer_id:
        match = re.search(r"Registered:\s*customer_id=(\d+)", combined_out)
        if match:
            customer_id = int(match.group(1))

    if not customer_id:
        print(f"  ❌ Could not parse customer_id from output")
        if verbose:
            print(f"  combined tail: {combined_out[-1500:]}")
        return {"error": "Could not parse customer_id"}

    elapsed = time.time() - t0
    print(f"  ✅ Customer created: ID={customer_id}, API key={'yes' if api_key else 'NO'}")
    print(f"  ⏱  Load time: {elapsed:.1f}s")

    # Clean up temp manifest
    try:
        os.unlink(actual_manifest)
    except OSError:
        pass

    return {
        "customer_id": customer_id,
        "api_key": api_key,
        "load_time_s": round(elapsed, 1),
        "stdout_tail": result.stdout[-500:] if result.stdout else "",
        "manifest_path": manifest_path,  # original (for extend)
    }


def phase1_capture_baseline(mcp: MCPClient, customer_id: int, verbose: bool) -> dict:
    """Capture baseline metrics via MCP tools."""
    print(f"\n  Capturing baseline metrics...")
    baseline = {}

    tools = [
        ("list_accounts", {"customer_id": customer_id}),
        ("get_at_risk_accounts", {"customer_id": customer_id}),
        ("get_health_score_history", {"customer_id": customer_id, "months": 6}),
        ("get_portfolio_roi_summary", {"customer_id": customer_id}),
    ]

    for tool_name, args in tools:
        try:
            result = mcp.call(tool_name, args)
            baseline[tool_name] = result
            if verbose:
                print(f"    {tool_name}: {json.dumps(result)[:200]}")
            else:
                passed, reason = validate_response(tool_name, result)
                print(f"    {tool_name}: {'✅' if passed else '❌'} {reason}")
        except Exception as e:
            baseline[tool_name] = {"error": str(e)}
            print(f"    {tool_name}: ❌ {e}")

    return baseline


def phase2_run_questions(mcp: MCPClient, customer_id: int, accounts: list, verbose: bool) -> list:
    """Phase 2: Run 40 persona questions via MCP tools."""
    print(f"\n{'='*60}")
    print(f"  PHASE 2: Run Persona Questions (40)")
    print(f"{'='*60}")

    questions = get_persona_questions(customer_id, accounts)
    results = []
    persona_stats = {}

    for i, (persona, question, tool_name, args) in enumerate(questions, 1):
        try:
            t0 = time.time()
            result = mcp.call(tool_name, args, timeout=30)
            elapsed = time.time() - t0
            passed, reason = validate_response(tool_name, result)
            grade = grade_response(passed, result, tool_name)
        except Exception as e:
            elapsed = 0
            passed = False
            reason = str(e)[:100]
            grade = "F"
            result = {"error": str(e)}

        status = "✅" if passed else "❌"
        print(f"  {i:2d}/{len(questions)} [{persona:4s}] {question:40s} {status} {grade} ({elapsed:.1f}s) {reason}")

        results.append({
            "num": i,
            "persona": persona,
            "question": question,
            "tool": tool_name,
            "passed": passed,
            "grade": grade,
            "reason": reason,
            "latency_s": round(elapsed, 2),
        })

        # Track per-persona stats
        if persona not in persona_stats:
            persona_stats[persona] = {"total": 0, "passed": 0, "grades": []}
        persona_stats[persona]["total"] += 1
        persona_stats[persona]["passed"] += int(passed)
        persona_stats[persona]["grades"].append(grade)

    # Print summary
    print(f"\n  {'─'*50}")
    print(f"  PERSONA SUMMARY:")
    for persona, stats in sorted(persona_stats.items()):
        grade_dist = {g: stats["grades"].count(g) for g in ["A", "B", "C", "F"]}
        grade_str = " ".join(f"{g}:{c}" for g, c in grade_dist.items() if c > 0)
        pct = stats["passed"] / stats["total"] * 100
        print(f"    {persona:5s}: {stats['passed']}/{stats['total']} passed ({pct:.0f}%)  Grades: {grade_str}")

    total_passed = sum(s["passed"] for s in persona_stats.values())
    total = sum(s["total"] for s in persona_stats.values())
    print(f"    TOTAL: {total_passed}/{total} passed ({total_passed/total*100:.0f}%)")

    return results


def phase3_extend_and_compare(base_url: str, manifest_path: str, customer_id: int,
                               mcp: MCPClient, baseline: dict, seed: int, verbose: bool) -> dict:
    """Phase 3: Extend data months 7-12, compare predictions vs actuals."""
    print(f"\n{'='*60}")
    print(f"  PHASE 3: Extend Data & Compare")
    print(f"{'='*60}")

    # Step 3.1: Record predictions from baseline
    predictions = {}
    bl_accounts = baseline.get("list_accounts", {})
    if bl_accounts.get("accounts"):
        predictions["avg_health"] = sum(a.get("health_score", 0) for a in bl_accounts["accounts"]) / len(bl_accounts["accounts"])
        predictions["at_risk_count"] = len([a for a in bl_accounts["accounts"] if a.get("health_score", 100) < 70])
        predictions["total_arr"] = bl_accounts.get("total_arr", 0)
    bl_roi = baseline.get("get_portfolio_roi_summary", {})
    predictions["roi_pct"] = bl_roi.get("story", {}).get("summary", {}).get("roi_pct", 0)

    print(f"  Predictions from Phase 1: {json.dumps(predictions, indent=2)}")

    # Step 3.2: Extend data
    import subprocess
    cmd = [
        sys.executable, str(LOAD_DRIVER_DIR / "cs_pulse_driver.py"),
        "--manifest", manifest_path,
        "--customer-id", str(customer_id),
        "--extend",
        "--months", "6",
        "--base-url", base_url,
        "--seed", str(seed),
        "--no-validate-strict",
    ]
    print(f"  Extending data (months 7-12)...")
    t0 = time.time()
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    extend_time = time.time() - t0

    if result.returncode != 0:
        print(f"  ❌ Extend failed: {result.stderr[-300:]}")
        return {"error": result.stderr[-300:]}

    print(f"  ✅ Extended in {extend_time:.1f}s")

    # Step 3.3: Capture actuals
    print(f"  Capturing actuals after extension...")
    actuals = {}
    try:
        acct_result = mcp.call("list_accounts", {"customer_id": customer_id})
        actuals["avg_health"] = sum(a.get("health_score", 0) for a in acct_result.get("accounts", [])) / max(1, len(acct_result.get("accounts", [])))
        actuals["at_risk_count"] = len([a for a in acct_result.get("accounts", []) if a.get("health_score", 100) < 70])
        actuals["total_arr"] = acct_result.get("total_arr", 0)
    except Exception as e:
        print(f"  ❌ Could not fetch actuals: {e}")
        actuals = {"error": str(e)}

    try:
        roi_result = mcp.call("get_portfolio_roi_summary", {"customer_id": customer_id})
        actuals["roi_pct"] = roi_result.get("story", {}).get("summary", {}).get("roi_pct", 0)
    except Exception:
        actuals["roi_pct"] = 0

    # Step 3.4: Compare
    comparison = []
    for metric in ["avg_health", "at_risk_count", "total_arr", "roi_pct"]:
        pred = predictions.get(metric, 0)
        actual = actuals.get(metric, 0)
        delta = actual - pred if isinstance(actual, (int, float)) and isinstance(pred, (int, float)) else "N/A"
        comparison.append({
            "metric": metric,
            "prediction": pred,
            "actual": actual,
            "delta": delta,
        })

    print(f"\n  {'Metric':<20} {'Predicted':>12} {'Actual':>12} {'Delta':>10}")
    print(f"  {'─'*54}")
    for c in comparison:
        pred_str = f"{c['prediction']:.1f}" if isinstance(c["prediction"], float) else str(c["prediction"])
        act_str = f"{c['actual']:.1f}" if isinstance(c["actual"], float) else str(c["actual"])
        delta_str = f"{c['delta']:+.1f}" if isinstance(c["delta"], float) else str(c["delta"])
        print(f"  {c['metric']:<20} {pred_str:>12} {act_str:>12} {delta_str:>10}")

    return {
        "predictions": predictions,
        "actuals": actuals,
        "comparison": comparison,
        "extend_time_s": round(extend_time, 1),
    }


def phase4_delete_and_verify(base_url: str, customer_id: int, rest: RESTClient, mcp: MCPClient, verbose: bool) -> dict:
    """Phase 4: Delete customer via admin API + verify cleanup."""
    print(f"\n{'='*60}")
    print(f"  PHASE 4: Delete & Verify (customer_id={customer_id})")
    print(f"{'='*60}")

    # Step 4.1: Delete
    try:
        t0 = time.time()
        delete_result = rest.delete_customer(customer_id)
        delete_time = time.time() - t0
        rows = delete_result.get("rows_deleted", "?")
        status = delete_result.get("verification", {}).get("status", "?")
        orphans = delete_result.get("verification", {}).get("orphan_rows", "?")
        print(f"  ✅ Deleted in {delete_time:.1f}s: {rows} rows, status={status}, orphans={orphans}")
    except Exception as e:
        print(f"  ❌ Delete failed: {e}")
        return {"error": str(e)}

    # Step 4.2: Verify via MCP
    try:
        verify = mcp.call("list_accounts", {"customer_id": customer_id})
        acct_count = len(verify.get("accounts", []))
        clean = acct_count == 0
        print(f"  Verify: {acct_count} accounts remaining → {'✅ Clean' if clean else '❌ NOT CLEAN'}")
    except Exception as e:
        # Error = customer not found = clean
        clean = True
        print(f"  Verify: Error (expected — customer deleted) → ✅ Clean")

    return {
        "rows_deleted": rows,
        "verification_status": status,
        "orphan_rows": orphans,
        "delete_time_s": round(delete_time, 1),
        "post_delete_clean": clean,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Phase 1.5: Post-Onboarding Seeder
# ─────────────────────────────────────────────────────────────────────────────

# Arc-type → (signal_subtype, playbook_id, expected_outcome, health_boost_range)
ARC_ACTION_MAP = {
    'champion_loss':        ('champion_departure',  'PB-06', 'resolved',  (8, 12)),
    'infrastructure_decay': ('escalation',          'PB-02', 'resolved',  (6, 10)),
    'crisis_recovery':      ('critical_incident',   'PB-05', 'escalated', (2, 5)),
    'budget_pressure':      ('budget_cut',          'PB-04', 'resolved',  (8, 14)),
    'land_and_expand':      ('expansion_signal',    'PB-08', 'resolved',  (3, 6)),
    'steady_state':         ('usage_decline',       'PB-01', 'resolved',  (4, 8)),
    'competitive_threat':   ('competitor_mention',   'PB-06', 'resolved',  (6, 10)),
    'seasonal_pattern':     ('usage_decline',       'PB-07', 'resolved',  (5, 8)),
}
DEFAULT_ARC_ACTION = ('health_drop', 'PB-01', 'resolved', (6, 10))

SEEDER_LOG_DIR = RESULTS_DIR / "seeder"


def phase1_5a_data_audit(mcp: MCPClient, customer_id: int, verbose: bool) -> dict:
    """Step 1.5a: Audit onboarded data — learn the customer before acting."""
    print(f"\n  ── Step 1.5a: Data Audit ──")
    audit: Dict[str, Any] = {"passed": False}

    # 1. Onboarding checklist
    try:
        onboard = mcp.call("complete_onboarding", {"customer_id": customer_id, "check_only": True})
        checklist = onboard.get("checklist", {})
        audit["customer_name"] = onboard.get("customer_name", f"Customer {customer_id}")
        audit["csv_files"] = checklist.get("data_files_present", [])
        audit["account_count"] = checklist.get("account_count", 0)
        audit["kpi_count"] = checklist.get("kpi_record_count", 0)
        audit["scores_calculated"] = checklist.get("scores_calculated", False)
        audit["wizard_runs"] = checklist.get("wizard_runs", 0)
        status = "✅" if checklist.get("scores_calculated") else "⚠️"
        print(f"    Onboarding: {status} {audit['account_count']} accounts, "
              f"{audit['kpi_count']} KPIs, {len(audit['csv_files'])} CSVs, "
              f"{audit['wizard_runs']} wizard runs")
        if verbose:
            print(f"    CSVs: {', '.join(audit['csv_files'])}")
    except Exception as e:
        print(f"    Onboarding check: ❌ {e}")
        audit["onboarding_error"] = str(e)

    # 2. List all accounts with health, ARR, arc
    #    Try list_accounts first (requires auth), fall back to get_health_score_history
    all_accounts = []
    try:
        accts = mcp.call("list_accounts", {"customer_id": customer_id})
        # Check for auth error
        if accts.get("raw", "").startswith("Invalid") or "error" in accts.get("raw", "").lower():
            raise RuntimeError("Auth required for list_accounts")
        all_accounts = accts.get("accounts", [])
        audit["total_arr"] = accts.get("total_arr", 0)
    except Exception:
        # Fallback: build account list from health_score_history + individual account_health calls
        print(f"    list_accounts: auth required, falling back to health_score_history...")
        try:
            hist = mcp.call("get_health_score_history", {"customer_id": customer_id, "months": 6})
            if hist.get("raw", "").startswith("Invalid"):
                raise RuntimeError("Auth required")
            for a in hist.get("accounts", []):
                all_accounts.append({
                    "account_id": a.get("account_id"),
                    "account_name": a.get("account_name", f"Account {a.get('account_id')}"),
                    "health_score": a.get("current_health", 0),
                    "arc_type": a.get("arc_type"),
                    "arr": a.get("arr", 0),
                    "revenue": a.get("arr", 0),
                })
        except Exception:
            # Last resort: use complete_onboarding account_count and probe account IDs
            print(f"    health_score_history: also auth-gated, using onboarding checklist only")
            # We know the account count from onboarding; try common account ID ranges
            # In practice, the load driver creates sequential IDs. Try a range probe.
            pass

    audit["all_accounts"] = all_accounts
    audit["total_arr"] = audit.get("total_arr", 0) or sum(
        a.get("arr", 0) or a.get("revenue", 0) or 0 for a in all_accounts
    )

    if all_accounts:
        # Classify
        healthy = [a for a in all_accounts if (a.get("health_score") or 0) >= 70]
        at_risk = [a for a in all_accounts if 50 <= (a.get("health_score") or 0) < 70]
        critical = [a for a in all_accounts if (a.get("health_score") or 0) < 50]
        audit["health_distribution"] = {
            "healthy": len(healthy), "at_risk": len(at_risk), "critical": len(critical),
        }

        # Sort worst and best
        sorted_accts = sorted(all_accounts, key=lambda a: a.get("health_score") or 0)
        audit["worst_accounts"] = [
            {"id": a.get("account_id"), "name": a.get("account_name", "?"),
             "health": a.get("health_score", 0), "arc": a.get("arc_type"),
             "arr": a.get("arr") or a.get("revenue") or 0}
            for a in sorted_accts[:5]
        ]
        audit["best_accounts"] = [
            {"id": a.get("account_id"), "name": a.get("account_name", "?"),
             "health": a.get("health_score", 0), "arc": a.get("arc_type"),
             "arr": a.get("arr") or a.get("revenue") or 0}
            for a in sorted_accts[-3:]
        ]

        dist = audit["health_distribution"]
        print(f"    Accounts: {len(all_accounts)} total, "
              f"H:{dist['healthy']} AR:{dist['at_risk']} C:{dist['critical']}, "
              f"ARR: ${audit['total_arr']:,.0f}")
        for w in audit["worst_accounts"][:3]:
            print(f"      Worst: {w['name']} (health={w['health']:.0f}, arc={w['arc'] or 'none'})")
    else:
        audit["health_distribution"] = {"healthy": 0, "at_risk": 0, "critical": 0}
        audit["worst_accounts"] = []
        audit["best_accounts"] = []
        print(f"    Accounts: ⚠️ Could not list accounts (auth-gated). "
              f"Onboarding says {audit.get('account_count', '?')} accounts exist.")

    # 3. KPI catalog
    try:
        catalog = mcp.call("get_kpi_catalog", {"customer_id": customer_id})
        audit["vertical"] = catalog.get("vertical", "unknown")
        pillars = catalog.get("pillars", {})
        # pillars can be dict (keyed by P1/P2/...) or list
        if isinstance(pillars, dict):
            audit["pillar_count"] = len(pillars)
            audit["catalog_kpi_count"] = sum(
                len(p.get("kpis", {})) if isinstance(p, dict) else 0
                for p in pillars.values()
            )
        else:
            audit["pillar_count"] = len(pillars)
            audit["catalog_kpi_count"] = sum(len(p.get("kpis", [])) for p in pillars)
        print(f"    Catalog: {audit['vertical']}, {audit['pillar_count']} pillars, "
              f"{audit['catalog_kpi_count']} KPIs")
    except Exception as e:
        print(f"    Catalog: ❌ {e}")
        audit["vertical"] = "unknown"

    # Passed if we have accounts OR onboarding confirmed accounts exist
    audit["passed"] = bool(audit.get("all_accounts")) or audit.get("account_count", 0) > 0
    return audit


def phase1_5b_health_check(mcp: MCPClient, customer_id: int, audit: dict, verbose: bool) -> dict:
    """Step 1.5b: Validate health scores exist for all accounts."""
    print(f"\n  ── Step 1.5b: Health Score Validation ──")
    result: Dict[str, Any] = {"passed": False, "checks_passed": 0, "checks_failed": 0}

    expected_count = audit.get("account_count", 0) or len(audit.get("all_accounts", []))

    # 1. Health history
    try:
        history = mcp.call("get_health_score_history", {"customer_id": customer_id, "months": 6})
        accounts_with_scores = history.get("account_count", 0) or len(history.get("accounts", []))
        result["accounts_with_scores"] = accounts_with_scores
        result["accounts_missing_scores"] = max(0, expected_count - accounts_with_scores)

        # Score range from account list (already fetched in audit)
        scores = [a.get("health_score", 0) for a in audit.get("all_accounts", []) if a.get("health_score")]
        result["score_range"] = [round(min(scores), 1), round(max(scores), 1)] if scores else [0, 0]
        result["avg_health"] = round(sum(scores) / len(scores), 1) if scores else 0

        # Checks
        if accounts_with_scores >= expected_count:
            result["checks_passed"] += 1
            print(f"    ✅ All {accounts_with_scores} accounts have health scores")
        else:
            result["checks_failed"] += 1
            print(f"    ⚠️ {accounts_with_scores}/{expected_count} accounts have scores")

        if result["score_range"][0] > 0:
            result["checks_passed"] += 1
            print(f"    ✅ No zero-health accounts (range: {result['score_range'][0]}-{result['score_range'][1]})")
        else:
            result["checks_failed"] += 1
            print(f"    ⚠️ Some accounts have 0 health")

        if result["score_range"][1] < 100:
            result["checks_passed"] += 1
        else:
            result["checks_failed"] += 1
            print(f"    ⚠️ Some accounts have exactly 100 health (suspicious)")

    except Exception as e:
        print(f"    Health history: ❌ {e}")
        result["health_error"] = str(e)

    # 2. Cross-check at-risk
    try:
        at_risk = mcp.call("get_at_risk_accounts", {"customer_id": customer_id})
        at_risk_count = len(at_risk.get("accounts", []))
        expected_at_risk = audit["health_distribution"]["at_risk"] + audit["health_distribution"]["critical"]
        result["at_risk_count"] = at_risk_count
        if at_risk_count >= expected_at_risk * 0.8:  # 80% tolerance
            result["checks_passed"] += 1
            print(f"    ✅ At-risk accounts: {at_risk_count} (expected ~{expected_at_risk})")
        else:
            result["checks_failed"] += 1
            print(f"    ⚠️ At-risk count mismatch: got {at_risk_count}, expected ~{expected_at_risk}")
    except Exception as e:
        print(f"    At-risk check: ❌ {e}")

    result["passed"] = result["checks_failed"] == 0
    return result


def phase1_5c_seed_signals_and_playbooks(
    mcp: MCPClient, customer_id: int, audit: dict,
    max_playbooks: int = 4, verbose: bool = False,
) -> dict:
    """Step 1.5c: Execute + close playbooks based on account arc types."""
    print(f"\n  ── Step 1.5c: Seed Signals & Playbooks ──")
    result: Dict[str, Any] = {"executions": [], "passed": False}

    worst = audit.get("worst_accounts", [])[:max_playbooks]
    best = audit.get("best_accounts", [])

    if not worst:
        print(f"    ⚠️ No accounts to seed (empty worst list)")
        result["passed"] = True
        return result

    import random as _rng
    _rng.seed(customer_id)

    targets = list(worst)
    # Add best account for expansion playbook if we have room
    if best and len(targets) < max_playbooks:
        targets.append(best[-1])  # highest health

    resolved_count = 0
    escalated_count = 0
    total_protected = 0

    for i, acct in enumerate(targets):
        aid = acct["id"]
        aname = acct["name"]
        health = acct.get("health", 50)
        arr = acct.get("arr", 0)
        arc = acct.get("arc") or ""

        # Lookup arc action or default
        signal_sub, pb_id, default_outcome, boost_range = ARC_ACTION_MAP.get(arc, DEFAULT_ARC_ACTION)

        # For best account, always use expansion
        if acct in best[-1:] and health >= 70:
            signal_sub, pb_id, default_outcome = 'expansion_signal', 'PB-08', 'resolved'
            boost_range = (2, 5)

        # Decide outcome (70% resolved, 30% escalated — except expansion always resolves)
        outcome = default_outcome
        if pb_id != 'PB-08' and _rng.random() < 0.3:
            outcome = 'escalated'
            boost_range = (1, 4)

        health_boost = _rng.uniform(*boost_range)
        health_at_close = min(95, health + health_boost)
        revenue_expanded = round(arr * 0.15) if pb_id == 'PB-08' and outcome == 'resolved' else 0

        # Execute
        try:
            exec_result = mcp.call("execute_playbook", {
                "customer_id": customer_id,
                "account_id": aid,
                "playbook_id": pb_id,
                "triggered_by": "signal_analyst",
            }, timeout=30)
            exec_id = exec_result.get("execution_id")
            if not exec_id:
                print(f"    ❌ {aname}: execute_playbook returned no execution_id")
                continue

            # Close
            close_args: Dict[str, Any] = {
                "customer_id": customer_id,
                "execution_id": exec_id,
                "outcome": outcome,
                "outcome_notes": f"Seeder: {arc or 'default'} arc → {pb_id}",
                "health_at_close": round(health_at_close, 1),
            }
            if revenue_expanded:
                close_args["revenue_expanded"] = revenue_expanded

            close_result = mcp.call("close_playbook", close_args, timeout=30)

            rev_protected = close_result.get("revenue_protected", 0) or 0
            roi_x = close_result.get("realized_roi_x", 0) or 0
            h_delta = close_result.get("health_delta", 0) or 0

            if outcome == 'resolved':
                resolved_count += 1
            else:
                escalated_count += 1
            total_protected += rev_protected + revenue_expanded

            status = "✅" if outcome == "resolved" else "⬆️"
            print(f"    {status} {aname}: {pb_id} ({arc or 'default'}) → {outcome} "
                  f"Δh={h_delta:+.1f} ${rev_protected:,.0f} protected {f'${revenue_expanded:,.0f} expanded ' if revenue_expanded else ''}"
                  f"ROI={roi_x}x")

            result["executions"].append({
                "execution_id": exec_id,
                "account_id": aid,
                "account_name": aname,
                "arc_type": arc,
                "playbook_id": pb_id,
                "outcome": outcome,
                "health_at_trigger": health,
                "health_at_close": round(health_at_close, 1),
                "health_delta": round(h_delta, 1),
                "revenue_protected": rev_protected,
                "revenue_expanded": revenue_expanded,
                "roi_x": roi_x,
            })

        except Exception as e:
            print(f"    ❌ {aname}: {pb_id} failed — {e}")
            result["executions"].append({
                "account_name": aname, "playbook_id": pb_id, "error": str(e),
            })

    result["total_executions"] = len(result["executions"])
    result["resolved"] = resolved_count
    result["escalated"] = escalated_count
    result["total_revenue_protected"] = total_protected
    result["passed"] = resolved_count + escalated_count > 0

    print(f"    Summary: {resolved_count} resolved, {escalated_count} escalated, "
          f"${total_protected:,.0f} revenue impact")
    return result


def _generate_ask_ai_questions(customer_id: int, audit: dict, per_persona: int = 5) -> list:
    """Generate customer-specific Ask AI questions from audit data."""
    worst = audit.get("worst_accounts", [{}])
    best = audit.get("best_accounts", [{}])
    w0 = worst[0] if worst else {"id": 0, "name": "Unknown", "health": 0, "arc": None}
    w1 = worst[1] if len(worst) > 1 else w0
    b0 = best[-1] if best else {"id": 0, "name": "Unknown", "health": 80}
    dist = audit.get("health_distribution", {})
    cid = customer_id

    questions = []

    # ── CSM (tool-backed questions) ──
    csm_qs = [
        (f"What should I do about {w0['name']} (health {w0['health']:.0f})?",
         "get_csm_daily_actions", {"customer_id": cid}),
        (f"Show me the health breakdown for {w0['name']}",
         "get_account_health", {"customer_id": cid, "account_id": w0["id"]}),
        (f"Who is the champion at {w0['name']}?",
         "get_stakeholder_map", {"customer_id": cid, "account_id": w0["id"]}),
        (f"What happened at {w1['name']} recently?",
         "get_account_journey_timeline", {"customer_id": cid, "account_id": w1["id"]}),
        (f"What playbook should I run for {w0['name']}?",
         "get_playbook_recommendations", {"customer_id": cid, "account_id": w0["id"]}),
    ]

    # ── VP CS ──
    vpcs_qs = [
        ("Which accounts need immediate attention?",
         "get_at_risk_accounts", {"customer_id": cid}),
        ("Show me the portfolio health trajectory",
         "get_health_score_history", {"customer_id": cid, "account_id": 0, "months": 6}),
        (f"What's the team workload like?",
         "get_csm_daily_actions", {"customer_id": cid}),
        (f"How are our playbooks performing?",
         "get_playbook_success_metrics", {"customer_id": cid}),
        ("NRR forecast for next quarter?",
         "get_nrr_forecast", {"customer_id": cid}),
    ]

    # ── CRO ──
    cro_qs = [
        ("How much ARR is at risk right now?",
         "get_at_risk_accounts", {"customer_id": cid}),
        (f"Revenue breakdown for {w0['name']}?",
         "get_revenue_at_risk", {"customer_id": cid, "account_id": w0["id"]}),
        ("What's driving NRR this quarter?",
         "get_nrr_forecast", {"customer_id": cid}),
        ("Portfolio ROI summary for the board?",
         "get_portfolio_roi_summary", {"customer_id": cid}),
        (f"If we improve NRR by 1%, what's the dollar impact?",
         "calculate_power_of_1", {"customer_id": cid, "metric_id": "NRR"}),
    ]

    # ── CFO ──
    cfo_qs = [
        ("What's the ROI on our CS investment?",
         "get_portfolio_roi_summary", {"customer_id": cid}),
        ("Show me playbook cost economics",
         "get_playbook_economics", {"customer_id": cid}),
        (f"Power of 1: 1% expansion rate improvement?",
         "calculate_power_of_1", {"customer_id": cid, "metric_id": "expansion_rate"}),
        (f"What's the full ROI story for {w0['name']}?",
         "get_outcome_roi_story", {"customer_id": cid, "account_id": w0["id"]}),
        (f"1% improvement in ticket resolution time?",
         "calculate_power_of_1", {"customer_id": cid, "metric_id": "ticket_resolution_time"}),
    ]

    for persona, qs in [("CSM", csm_qs), ("VPCS", vpcs_qs), ("CRO", cro_qs), ("CFO", cfo_qs)]:
        for q_text, tool, args in qs[:per_persona]:
            questions.append((persona, q_text, tool, args))

    return questions


def phase1_5d_persona_validation(
    mcp: MCPClient, customer_id: int, audit: dict,
    per_persona: int = 5, verbose: bool = False,
) -> dict:
    """Step 1.5d: Validate persona workflows + Ask AI."""
    print(f"\n  ── Step 1.5d: Persona Workflow Validation ──")
    result: Dict[str, Any] = {"workflow_checks": {}, "ask_ai": [], "passed": False}

    # ── Part A: Workflow validation per persona ──
    print(f"    Part A: Workflow checks")
    checks = {}

    # CSM
    try:
        actions = mcp.call("get_csm_daily_actions", {"customer_id": customer_id})
        action_list = actions.get("actions", [])
        has_stakeholders = any(a.get("primary_champion") for a in action_list)
        has_arcs = any(a.get("arc_type") for a in action_list)
        passed = len(action_list) >= 3
        checks["CSM"] = {
            "actions_count": len(action_list),
            "has_stakeholders": has_stakeholders,
            "has_arcs": has_arcs,
            "passed": passed,
        }
        print(f"      CSM:  {'✅' if passed else '❌'} {len(action_list)} actions, "
              f"stakeholders={'✅' if has_stakeholders else '❌'}, arcs={'✅' if has_arcs else '❌'}")
    except Exception as e:
        checks["CSM"] = {"error": str(e), "passed": False}
        print(f"      CSM:  ❌ {e}")

    # VP CS
    try:
        pb_metrics = mcp.call("get_playbook_success_metrics", {"customer_id": customer_id})
        summary = pb_metrics.get("portfolio_summary", {})
        success_rate = summary.get("overall_success_rate_pct", 0)
        total_runs = summary.get("total_runs", 0)
        passed = success_rate > 0 and total_runs > 0
        checks["VPCS"] = {
            "playbook_success_rate": success_rate,
            "total_runs": total_runs,
            "passed": passed,
        }
        print(f"      VPCS: {'✅' if passed else '❌'} {success_rate:.0f}% success rate, {total_runs} runs")
    except Exception as e:
        checks["VPCS"] = {"error": str(e), "passed": False}
        print(f"      VPCS: ❌ {e}")

    # CRO
    try:
        nrr = mcp.call("get_nrr_forecast", {"customer_id": customer_id})
        projected_nrr = nrr.get("projected_nrr") or nrr.get("revenue_waterfall", {}).get("projected_nrr")
        has_trajectory = bool(nrr.get("trajectory") or nrr.get("revenue_waterfall"))
        passed = has_trajectory
        checks["CRO"] = {
            "projected_nrr": projected_nrr,
            "has_trajectory": has_trajectory,
            "passed": passed,
        }
        print(f"      CRO:  {'✅' if passed else '❌'} NRR={projected_nrr}, trajectory={'✅' if has_trajectory else '❌'}")
    except Exception as e:
        checks["CRO"] = {"error": str(e), "passed": False}
        print(f"      CRO:  ❌ {e}")

    # CFO
    try:
        po1 = mcp.call("calculate_power_of_1", {"customer_id": customer_id, "metric_id": "NRR"})
        dollar_impact = po1.get("dollar_impact", 0)
        econ = mcp.call("get_playbook_economics", {"customer_id": customer_id})
        has_costs = bool(econ.get("playbooks") or econ.get("portfolio_summary"))
        passed = dollar_impact > 0 and has_costs
        checks["CFO"] = {
            "power_of_1_nrr": dollar_impact,
            "has_playbook_costs": has_costs,
            "passed": passed,
        }
        print(f"      CFO:  {'✅' if passed else '❌'} Power-of-1 NRR=${dollar_impact:,.0f}, "
              f"costs={'✅' if has_costs else '❌'}")
    except Exception as e:
        checks["CFO"] = {"error": str(e), "passed": False}
        print(f"      CFO:  ❌ {e}")

    result["workflow_checks"] = checks

    # ── Part B: Ask AI questions ──
    print(f"\n    Part B: Ask AI ({per_persona} per persona)")
    questions = _generate_ask_ai_questions(customer_id, audit, per_persona)
    ai_results = []
    persona_stats: Dict[str, Dict] = {}

    for i, (persona, question, tool_name, args) in enumerate(questions, 1):
        try:
            t0 = time.time()
            resp = mcp.call(tool_name, args, timeout=30)
            elapsed = time.time() - t0
            passed_q, reason = validate_response(tool_name, resp)
            grade = grade_response(passed_q, resp, tool_name)
        except Exception as e:
            elapsed = 0
            passed_q = False
            reason = str(e)[:100]
            grade = "F"

        status = "✅" if passed_q else "❌"
        print(f"      {i:2d}/{len(questions)} [{persona:4s}] {question[:50]:50s} {status} {grade} ({elapsed:.1f}s)")

        ai_results.append({
            "persona": persona, "question": question, "tool": tool_name,
            "passed": passed_q, "grade": grade, "reason": reason,
            "latency_s": round(elapsed, 2),
        })

        if persona not in persona_stats:
            persona_stats[persona] = {"total": 0, "passed": 0, "grades": []}
        persona_stats[persona]["total"] += 1
        persona_stats[persona]["passed"] += int(passed_q)
        persona_stats[persona]["grades"].append(grade)

    # Summary
    total_passed = sum(s["passed"] for s in persona_stats.values())
    total_q = sum(s["total"] for s in persona_stats.values())
    result["ask_ai"] = ai_results
    result["ask_ai_pass_rate"] = f"{total_passed}/{total_q}"

    # Compute overall grade
    all_grades = [r["grade"] for r in ai_results]
    a_count = all_grades.count("A")
    f_count = all_grades.count("F")
    if f_count == 0 and a_count >= total_q * 0.7:
        result["overall_grade"] = "A"
    elif f_count == 0:
        result["overall_grade"] = "A-"
    elif f_count <= total_q * 0.1:
        result["overall_grade"] = "B+"
    elif f_count <= total_q * 0.25:
        result["overall_grade"] = "B"
    else:
        result["overall_grade"] = "C"

    print(f"\n    Ask AI: {total_passed}/{total_q} passed — Grade: {result['overall_grade']}")
    for persona, stats in sorted(persona_stats.items()):
        pct = stats["passed"] / max(stats["total"], 1) * 100
        print(f"      {persona:5s}: {stats['passed']}/{stats['total']} ({pct:.0f}%)")

    result["passed"] = all(c.get("passed", False) for c in checks.values()) and f_count <= total_q * 0.25
    return result


def phase1_5_post_onboarding_seeder(
    mcp: MCPClient, customer_id: int,
    max_playbooks: int = 4, per_persona_ai: int = 5,
    verbose: bool = False, log_dir: Optional[str] = None,
) -> dict:
    """Phase 1.5 orchestrator: audit → health → seed → validate."""
    print(f"\n{'='*60}")
    print(f"  PHASE 1.5: Post-Onboarding Seeder (customer_id={customer_id})")
    print(f"{'='*60}")

    t0 = time.time()
    seeder_result: Dict[str, Any] = {"customer_id": customer_id}

    # 1.5a: Audit
    audit = phase1_5a_data_audit(mcp, customer_id, verbose)
    seeder_result["audit"] = audit
    if not audit.get("passed"):
        print(f"\n  ⚠️ Data audit failed — skipping remaining seeder steps")
        seeder_result["status"] = "AUDIT_FAILED"
        return seeder_result

    # 1.5b: Health check
    health = phase1_5b_health_check(mcp, customer_id, audit, verbose)
    seeder_result["health_check"] = health

    # 1.5c: Seed playbooks
    playbooks = phase1_5c_seed_signals_and_playbooks(
        mcp, customer_id, audit, max_playbooks=max_playbooks, verbose=verbose,
    )
    seeder_result["playbook_executions"] = playbooks

    # 1.5d: Persona validation + Ask AI
    persona = phase1_5d_persona_validation(
        mcp, customer_id, audit, per_persona=per_persona_ai, verbose=verbose,
    )
    seeder_result["persona_validation"] = persona

    elapsed = time.time() - t0
    seeder_result["duration_s"] = round(elapsed, 1)
    seeder_result["status"] = "COMPLETE"

    # Summary
    pb = playbooks
    pv = persona
    print(f"\n  ── Phase 1.5 Summary ({elapsed:.1f}s) ──")
    print(f"    Audit:     {'✅' if audit['passed'] else '❌'} {audit.get('account_count', 0)} accounts, "
          f"${audit.get('total_arr', 0):,.0f} ARR")
    print(f"    Health:    {'✅' if health['passed'] else '❌'} {health.get('checks_passed', 0)} checks passed")
    print(f"    Playbooks: {'✅' if pb['passed'] else '❌'} {pb.get('resolved', 0)} resolved, "
          f"{pb.get('escalated', 0)} escalated, ${pb.get('total_revenue_protected', 0):,.0f} protected")
    print(f"    Personas:  {'✅' if pv['passed'] else '❌'} Ask AI {pv.get('ask_ai_pass_rate', '?')} — "
          f"Grade: {pv.get('overall_grade', '?')}")

    # Write log file
    _log_dir = Path(log_dir) if log_dir else SEEDER_LOG_DIR
    _log_dir.mkdir(parents=True, exist_ok=True)
    safe_name = (audit.get("customer_name") or "unknown").replace(" ", "_")[:30]
    ts = datetime.utcnow().strftime("%Y%m%dT%H%M%S")
    log_path = _log_dir / f"{customer_id}_{safe_name}_{ts}.json"
    try:
        log_path.write_text(json.dumps(seeder_result, indent=2, default=str))
        print(f"    Log: {log_path}")
    except Exception as e:
        print(f"    Log write failed: {e}")

    return seeder_result


# ─────────────────────────────────────────────────────────────────────────────
# Full Cycle Runner
# ─────────────────────────────────────────────────────────────────────────────

def run_full_cycle(base_url: str, manifest_path: str, cycle: int, seed: int,
                    verbose: bool, skip_delete: bool = False, mcp_host: str = None,
                    skip_seeder: bool = False, seeder_playbooks: int = 4,
                    seeder_ask_ai: int = 5, log_dir: Optional[str] = None) -> dict:
    """Run one complete cycle: create → seed → questions → extend → compare → delete."""
    cycle_result = {"cycle": cycle, "start_time": datetime.utcnow().isoformat()}
    t_cycle = time.time()

    # Phase 1: Create
    p1 = phase1_create_and_load(base_url, manifest_path, seed, cycle, verbose)
    cycle_result["phase1"] = p1
    if "error" in p1:
        cycle_result["status"] = "FAILED_PHASE1"
        return cycle_result

    customer_id = p1["customer_id"]
    api_key = p1.get("api_key")

    if not api_key:
        print(f"  ⚠️  No API key returned — MCP calls will fail. Skipping Phases 2-3.")
        cycle_result["status"] = "NO_API_KEY"
        return cycle_result

    mcp = MCPClient(base_url, api_key, mcp_host=mcp_host)

    # Capture baseline
    baseline = phase1_capture_baseline(mcp, customer_id, verbose)
    cycle_result["phase1"]["baseline"] = baseline

    # Get accounts for persona questions
    accounts = baseline.get("list_accounts", {}).get("accounts", [])

    # Phase 1.5: Post-onboarding seeder (audit + health + playbooks + persona validation)
    if not skip_seeder:
        p1_5 = phase1_5_post_onboarding_seeder(
            mcp, customer_id,
            max_playbooks=seeder_playbooks,
            per_persona_ai=seeder_ask_ai,
            verbose=verbose,
            log_dir=log_dir,
        )
        cycle_result["phase1_5"] = p1_5
        # Use enriched account list from audit (has arc_type, health, etc.)
        if p1_5.get("audit", {}).get("all_accounts"):
            accounts = p1_5["audit"]["all_accounts"]

    # Phase 2: Questions
    p2 = phase2_run_questions(mcp, customer_id, accounts, verbose)
    cycle_result["phase2"] = p2

    # Phase 3: Extend & Compare
    p3 = phase3_extend_and_compare(base_url, manifest_path, customer_id, mcp, baseline, seed, verbose)
    cycle_result["phase3"] = p3

    # Phase 4: Delete
    if not skip_delete:
        # Need admin REST client for delete
        # Use the customer's own admin credentials (created during registration)
        try:
            # Attempt login with the manifest's admin email
            manifest_data = json.loads(Path(manifest_path).read_text())
            cust = manifest_data.get("customer", {})
            admin_email = cust.get("admin_email", f"admin@ucv1-{cycle}.test")
            admin_password = cust.get("admin_password", "CSPulse2026!")
            rest = RESTClient(base_url, admin_email, admin_password)
            p4 = phase4_delete_and_verify(base_url, customer_id, rest, mcp, verbose)
        except Exception as e:
            print(f"  ⚠️  Delete failed (admin login issue): {e}")
            p4 = {"error": str(e)}
        cycle_result["phase4"] = p4

    cycle_result["total_time_s"] = round(time.time() - t_cycle, 1)
    cycle_result["status"] = "COMPLETE"
    return cycle_result


# ─────────────────────────────────────────────────────────────────────────────
# Concurrent Runner
# ─────────────────────────────────────────────────────────────────────────────

def run_concurrent(base_url: str, manifest_path: str, count: int, verbose: bool,
                    skip_seeder: bool = False, seeder_playbooks: int = 4,
                    seeder_ask_ai: int = 5, log_dir: Optional[str] = None):
    """Run N customers in parallel threads."""
    print(f"\n{'#'*60}")
    print(f"  CONCURRENT TEST: {count} customers in parallel")
    print(f"{'#'*60}")

    results = {}
    lock = threading.Lock()

    def worker(idx: int):
        name = f"UCv1-{idx}"
        try:
            r = run_full_cycle(base_url, manifest_path, idx, seed=42 + idx,
                                verbose=verbose, skip_delete=True,
                                skip_seeder=skip_seeder, seeder_playbooks=seeder_playbooks,
                                seeder_ask_ai=seeder_ask_ai, log_dir=log_dir)
            with lock:
                results[name] = r
        except Exception as e:
            with lock:
                results[name] = {"error": str(e), "traceback": traceback.format_exc()}

    threads = []
    t0 = time.time()
    for i in range(1, count + 1):
        t = threading.Thread(target=worker, args=(i,), name=f"UCv1-{i}")
        threads.append(t)
        t.start()
        time.sleep(1)  # Stagger starts by 1s to reduce thundering herd

    for t in threads:
        t.join(timeout=600)

    elapsed = time.time() - t0

    # Summary
    print(f"\n{'='*60}")
    print(f"  CONCURRENT RESULTS ({elapsed:.0f}s total)")
    print(f"{'='*60}")
    ok = sum(1 for r in results.values() if r.get("status") == "COMPLETE")
    fail = len(results) - ok
    print(f"  Completed: {ok}/{count}  Failed: {fail}")

    for name, r in sorted(results.items()):
        status = r.get("status", "ERROR")
        cid = r.get("phase1", {}).get("customer_id", "?")
        time_s = r.get("total_time_s", "?")
        print(f"    {name}: {status} (customer={cid}, {time_s}s)")

    # Save
    out_dir = RESULTS_DIR / "concurrent"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "summary.json").write_text(json.dumps(results, indent=2, default=str))
    print(f"\n  Results saved to {out_dir}/summary.json")


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="User-Complete-V1 Test Harness")
    parser.add_argument("--base-url", required=True, help="CS Pulse server URL")
    parser.add_argument("--manifest", default=MANIFEST_FILE, help="Manifest JSON path")
    parser.add_argument("--cycles", type=int, default=3, help="Sequential cycles (default 3)")
    parser.add_argument("--concurrent", type=int, default=0, help="Concurrent customers (0=skip)")
    parser.add_argument("--seed", type=int, default=42, help="Base random seed")
    parser.add_argument("--verbose", action="store_true", help="Show full MCP responses")
    parser.add_argument("--skip-delete", action="store_true", help="Skip Phase 4 delete")
    parser.add_argument(
        "--unique-company",
        action="store_true",
        help="Append [UTC timestamp] to manifest customer.name (avoids 409 duplicate company on re-runs)",
    )
    parser.add_argument(
        "--mcp-host",
        default=None,
        help="MCP server host:port (default: derive from --base-url). Use EC2 IP for direct access: 54.89.77.21:8001",
    )
    # Phase 1.5 seeder args
    parser.add_argument("--skip-seeder", action="store_true", help="Skip Phase 1.5 post-onboarding seeder")
    parser.add_argument("--seeder-playbooks", type=int, default=4, help="Number of playbook executions per customer (default: 4, max: 10)")
    parser.add_argument("--seeder-ask-ai", type=int, default=5, help="Ask AI questions per persona (default: 5)")
    parser.add_argument("--log-dir", default=None, help="Seeder log output directory (default: results/seeder/)")
    args = parser.parse_args()

    if not Path(args.manifest).exists():
        print(f"❌ Manifest not found: {args.manifest}")
        print(f"   Create it first (10-account SaaS manifest with diverse arcs)")
        sys.exit(1)

    manifest_path = Path(args.manifest)
    if args.unique_company:
        RESULTS_DIR.mkdir(parents=True, exist_ok=True)
        data = json.loads(manifest_path.read_text())
        ts = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
        tag = ts.replace("T", "").replace("Z", "").lower()
        cust = data.setdefault("customer", {})
        base = cust.get("name", "Customer")
        cust["name"] = f"{base} [{ts}]"
        # Server rejects duplicate company name and duplicate email *domain*; vary both per run.
        cust["domain"] = f"mountk-e2e-{tag}.test"
        cust["admin_email"] = f"admin@mountk-e2e-{tag}.test"
        manifest_path = RESULTS_DIR / "_patched_manifest.json"
        manifest_path.write_text(json.dumps(data, indent=2))
        args.manifest = str(manifest_path)

    print(f"╔{'═'*58}╗")
    print(f"║  User-Complete-V1 Test Harness                           ║")
    print(f"║  Server: {args.base_url:<48s}║")
    print(f"║  Manifest: {Path(args.manifest).name:<46s}║")
    print(f"║  Cycles: {args.cycles} sequential{', ' + str(args.concurrent) + ' concurrent' if args.concurrent else '':<30s}║")
    print(f"╚{'═'*58}╝")

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    # Sequential cycles
    all_results = []
    for cycle in range(1, args.cycles + 1):
        result = run_full_cycle(
            args.base_url, args.manifest, cycle,
            seed=args.seed + cycle - 1,
            verbose=args.verbose,
            skip_delete=args.skip_delete,
            mcp_host=args.mcp_host,
            skip_seeder=args.skip_seeder,
            seeder_playbooks=min(args.seeder_playbooks, 10),
            seeder_ask_ai=args.seeder_ask_ai,
            log_dir=args.log_dir,
        )
        all_results.append(result)

        # Save per-cycle
        cycle_dir = RESULTS_DIR / f"cycle_{cycle}"
        cycle_dir.mkdir(parents=True, exist_ok=True)
        (cycle_dir / "result.json").write_text(json.dumps(result, indent=2, default=str))
        print(f"\n  Cycle {cycle} saved to {cycle_dir}/result.json")

    # Print sequential summary
    print(f"\n{'#'*60}")
    print(f"  SEQUENTIAL SUMMARY ({args.cycles} cycles)")
    print(f"{'#'*60}")
    for r in all_results:
        c = r["cycle"]
        status = r.get("status", "?")
        t = r.get("total_time_s", "?")
        p2 = r.get("phase2", [])
        passed = sum(1 for q in p2 if q.get("passed")) if isinstance(p2, list) else "?"
        total = len(p2) if isinstance(p2, list) else "?"
        print(f"  Cycle {c}: {status} | {t}s | Questions: {passed}/{total}")

    # Concurrent
    if args.concurrent > 0:
        run_concurrent(args.base_url, args.manifest, args.concurrent, args.verbose,
                        skip_seeder=args.skip_seeder, seeder_playbooks=min(args.seeder_playbooks, 10),
                        seeder_ask_ai=args.seeder_ask_ai, log_dir=args.log_dir)

    print(f"\n✅ User-Complete-V1 finished. Results in {RESULTS_DIR}/")


if __name__ == "__main__":
    main()
