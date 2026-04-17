#!/usr/bin/env python3
"""
Tests for Onboarding Wizard Enhancement + NRR Dashboard.

Verifies:
  1. Onboarding wizard has guided checklist, column schema, post-processing summary
  2. NRR Dashboard exists with all 5 sections
  3. NRR route registered in App.tsx
  4. Backend NRR forecast endpoint exists

Run: python3 -m pytest tests/test_onboarding_nrr_ui.py -v
"""

import ast
import os
import sys
import pytest

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KPI_DIR = os.path.dirname(BACKEND_DIR)
sys.path.insert(0, BACKEND_DIR)


# ============================================================
# Onboarding Wizard Enhancement Tests
# ============================================================

class TestOnboardingWizard:
    @pytest.fixture(autouse=True)
    def load_source(self):
        path = os.path.join(KPI_DIR, 'src', 'components', 'onboarding', 'OnboardingWizard.tsx')
        with open(path) as f:
            self.source = f.read()

    def test_file_def_has_source_field(self):
        assert "source: string" in self.source or "source:" in self.source

    def test_file_def_has_required_cols(self):
        assert "requiredCols:" in self.source

    def test_file_def_has_optional_cols(self):
        assert "optionalCols:" in self.source

    def test_step1_has_checklist(self):
        assert "What you'll need" in self.source

    def test_step1_shows_source_hints(self):
        assert "Salesforce Account object" in self.source
        assert "BI tool" in self.source

    def test_step1_shows_4_required(self):
        # Should show 4 required files, not "2"
        assert 'text-teal-400">4' in self.source

    def test_step2_has_column_preview(self):
        assert "Columns" in self.source
        assert "expandedSchema" in self.source

    def test_step2_shows_required_columns(self):
        assert "Required:" in self.source

    def test_step3_has_skip_guidance(self):
        assert "When to add these" in self.source
        assert "Month 2-3" in self.source

    def test_step3_mentions_settings(self):
        assert "Settings" in self.source
        assert "Data Integration" in self.source

    def test_step4_has_processing_summary(self):
        assert "Processing Summary" in self.source
        assert "accounts_loaded" in self.source
        assert "health_scores_computed" in self.source

    def test_step4_has_next_steps(self):
        assert "Next Steps" in self.source
        assert "Executive Dashboard" in self.source
        assert "CSM Cockpit" in self.source
        assert "Ask AI" in self.source

    def test_step4_shows_context_graph_nodes(self):
        assert "context_graph_nodes" in self.source

    def test_accounts_csv_columns(self):
        assert "'account_name'" in self.source
        assert "'revenue'" in self.source

    def test_outcomes_csv_columns(self):
        assert "'outcome_type'" in self.source
        assert "'revenue_impact'" in self.source


# ============================================================
# NRR Dashboard Tests
# ============================================================

class TestNRRDashboard:
    @pytest.fixture(autouse=True)
    def load_source(self):
        path = os.path.join(KPI_DIR, 'src', 'components', 'dashboard', 'NRRDashboard.tsx')
        with open(path) as f:
            self.source = f.read()

    def test_file_exists(self):
        assert len(self.source) > 100

    def test_has_summary_cards(self):
        assert "Current NRR" in self.source
        assert "Projected NRR" in self.source
        assert "ARR Protected" in self.source
        assert "Renewal Risk" in self.source

    def test_has_trajectory_chart(self):
        assert "NRR Trajectory" in self.source
        assert "AreaChart" in self.source
        assert "Without CS Pulse" in self.source
        assert "With Interventions" in self.source

    def test_has_revenue_waterfall(self):
        assert "Revenue Waterfall" in self.source
        assert "BarChart" in self.source
        assert "Expected" in self.source
        assert "Protectable" in self.source
        assert "Expandable" in self.source

    def test_has_account_attribution_table(self):
        assert "Account Attribution" in self.source
        assert "sortField" in self.source
        assert "sortAsc" in self.source

    def test_has_filter_buttons(self):
        assert "'all'" in self.source
        assert "'at_risk'" in self.source
        assert "'expansion'" in self.source

    def test_has_scenario_simulator(self):
        assert "Scenario Simulator" in self.source
        assert "scenarioPct" in self.source
        assert 'type="range"' in self.source

    def test_fetches_nrr_forecast(self):
        assert "/api/revenue-intelligence/nrr-forecast" in self.source

    def test_has_renewal_risk_overlay(self):
        assert "Upcoming Renewals at Risk" in self.source
        assert "days_until" in self.source

    def test_uses_recharts(self):
        assert "ResponsiveContainer" in self.source
        assert "CartesianGrid" in self.source
        assert "Tooltip" in self.source

    def test_has_loading_state(self):
        assert "Loading NRR forecast" in self.source
        assert "Loader2" in self.source

    def test_has_error_state(self):
        assert "NRR Forecast Unavailable" in self.source

    def test_nrr_color_coding(self):
        assert "nrrColor" in self.source
        assert ">= 110" in self.source or "pct >= 110" in self.source

    def test_100_reference_line(self):
        assert "ReferenceLine" in self.source
        assert "y={100}" in self.source


# ============================================================
# App.tsx Route Tests
# ============================================================

class TestNRRRoute:
    @pytest.fixture(autouse=True)
    def load_source(self):
        path = os.path.join(KPI_DIR, 'src', 'App.tsx')
        with open(path) as f:
            self.source = f.read()

    def test_nrr_dashboard_imported(self):
        assert "import NRRDashboard" in self.source

    def test_nrr_route_exists(self):
        assert '"/nrr"' in self.source

    def test_nrr_dashboard_route_exists(self):
        assert '"/nrr-dashboard"' in self.source

    def test_nrr_behind_entitlement_guard(self):
        # NRR should require revenue_intelligence entitlement
        idx = self.source.index('"/nrr"')
        context = self.source[max(0, idx - 100):idx + 100]
        assert "revenue_intelligence" in context


# ============================================================
# Backend NRR Endpoint Tests
# ============================================================

class TestNRRBackendEndpoint:
    def test_nrr_forecast_endpoint_exists(self):
        path = os.path.join(BACKEND_DIR, 'revenue_intelligence_api.py')
        with open(path) as f:
            source = f.read()
        assert "/api/revenue-intelligence/nrr-forecast" in source

    def test_revenue_intelligence_api_parses(self):
        path = os.path.join(BACKEND_DIR, 'revenue_intelligence_api.py')
        with open(path) as f:
            ast.parse(f.read())


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
