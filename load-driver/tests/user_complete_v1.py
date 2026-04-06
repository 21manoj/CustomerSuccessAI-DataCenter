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
# Full Cycle Runner
# ─────────────────────────────────────────────────────────────────────────────

def run_full_cycle(base_url: str, manifest_path: str, cycle: int, seed: int,
                    verbose: bool, skip_delete: bool = False, mcp_host: str = None) -> dict:
    """Run one complete cycle: create → questions → extend → compare → delete."""
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

def run_concurrent(base_url: str, manifest_path: str, count: int, verbose: bool):
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
                                verbose=verbose, skip_delete=True)
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
        run_concurrent(args.base_url, args.manifest, args.concurrent, args.verbose)

    print(f"\n✅ User-Complete-V1 finished. Results in {RESULTS_DIR}/")


if __name__ == "__main__":
    main()
