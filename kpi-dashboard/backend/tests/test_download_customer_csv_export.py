#!/usr/bin/env python3
"""Unit tests for download_customer_csv export enrichment helpers."""

import os
import sys
import types
from types import SimpleNamespace
from unittest.mock import patch

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BACKEND_DIR)
sys.path.insert(0, os.path.join(BACKEND_DIR, 'mcp_server'))


def _install_fastmcp_stub():
    if 'fastmcp' in sys.modules:
        return

    class _Tool:
        def __init__(self, fn):
            self.fn = fn

        def __call__(self, *args, **kwargs):
            return self.fn(*args, **kwargs)

    class _FastMCP:
        def __init__(self, *a, **kw):
            pass

        def tool(self, fn=None, **opts):
            if fn is None:
                return lambda f: _Tool(f)
            return _Tool(fn)

        def resource(self, *a, **kw):
            def deco(f):
                return f
            return deco

        def prompt(self, *a, **kw):
            def deco(f):
                return f
            return deco

    fm = types.ModuleType('fastmcp')
    fm.FastMCP = _FastMCP
    sys.modules['fastmcp'] = fm

    fm_exc = types.ModuleType('fastmcp.exceptions')

    class _ToolError(Exception):
        pass

    fm_exc.ToolError = _ToolError
    sys.modules['fastmcp.exceptions'] = fm_exc


_install_fastmcp_stub()

from mcp_server.cs_pulse_onboarding import (  # noqa: E402
    _build_kpi_catalog_lookup,
    _confidence_export_value,
    _enrich_signal_export_row,
    _signal_id_lookup_keys,
    _stakeholder_name_from_signal,
)


class TestKpiCatalogLookup:
    @patch('mcp_server.cs_pulse_onboarding._resolve_customer_vertical', return_value='saas_premium')
    def test_saas_kpi_name_and_unit_from_catalog(self, _mock_vertical):
        customer = SimpleNamespace(customer_id=336, vertical='saas_premium')
        lookup = _build_kpi_catalog_lookup(customer)
        assert lookup['P1-KPI1']['kpi_name'] == 'Daily Active Users (DAU) Rate'
        assert lookup['P1-KPI1']['unit'] == 'percentage'
        assert lookup['P1-KPI1']['pillar'] == 'P1'


class TestSignalExportHelpers:
    def test_signal_id_strips_customer_prefix_for_node_lookup(self):
        keys = _signal_id_lookup_keys(336, 336001, 'c336_narrative_sig_336001_1')
        assert (336001, 'c336_narrative_sig_336001_1') in keys
        assert (336001, 'narrative_sig_336001_1') in keys

    def test_stakeholder_name_from_roles_json(self):
        sig = SimpleNamespace(stakeholder_roles=[{'role': 'champion', 'name': 'Alex Chen'}])
        assert _stakeholder_name_from_signal(sig) == 'Alex Chen'

    def test_confidence_scalar_and_dict(self):
        assert _confidence_export_value(0.85) == '0.85'
        assert _confidence_export_value({'overall': 0.9, 'sentiment': 0.7}) == '0.9'

    def test_enrich_signal_from_context_node_and_edges(self):
        signal = SimpleNamespace(
            signal_id='c336_narrative_sig_336001_1',
            account_id=336001,
            cg_node_id=101,
            stakeholder_roles=None,
            stakeholder_title='VP Ops',
            source_type=None,
            confidence=None,
        )
        node = SimpleNamespace(
            node_id=101,
            node_type='SIGNAL',
            source_event_id='narrative_sig_336001_1',
            source_platform='csv_import',
            properties={'signal_ref': 'narrative_sig_336001_1'},
            confidence=0.82,
            revenue_impact=None,
        )
        target = SimpleNamespace(
            node_id=202,
            source_event_id='dec_336001_1',
            properties={},
            source_ref=None,
        )
        edge = SimpleNamespace(
            edge_id=1,
            from_node_id=101,
            to_node_id=202,
            confidence=0.8,
            revenue_impact=150000,
        )
        sig_ref_to_node = {(336001, 'narrative_sig_336001_1'): node}
        node_by_id = {101: node, 202: target}
        outgoing = {101: [edge]}

        row = _enrich_signal_export_row(
            signal, 336, sig_ref_to_node, node_by_id, outgoing,
        )
        assert row['source_platform'] == 'csv_import'
        assert row['causal_chain_ref'] == 'dec_336001_1'
        assert row['confidence'] == '0.82'
        assert row['revenue_impact'] == 150000.0
