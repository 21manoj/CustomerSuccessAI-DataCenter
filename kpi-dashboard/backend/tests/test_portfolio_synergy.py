#!/usr/bin/env python3
"""
Test Suite 4 — Portfolio Model + Synergy Engine
=================================================
Tests: PE multi-company model, 5 synergy types, diminishing-return
curves, preset portfolio scenarios, serialization.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest


# ============================================================
# MODULE IMPORT TESTS
# ============================================================

class TestImports:
    def test_portfolio_engine_imports(self):
        from portfolio_synergy_engine import (
            SynergyType, SynergyFactor, PortfolioCompany, CompanyResult,
            PortfolioResult, SYNERGY_CURVE, EXAMPLE_PORTFOLIOS,
            calculate_synergy_multiplier, analyze_portfolio,
            run_preset_portfolio, portfolio_result_to_dict,
        )


# ============================================================
# SYNERGY TYPE TESTS
# ============================================================

class TestSynergyTypes:
    def test_five_synergy_types_defined(self):
        from portfolio_synergy_engine import SynergyType
        types = list(SynergyType)
        assert len(types) == 5
        expected = {
            'shared_playbooks', 'shared_resources', 'vendor_leverage',
            'cross_sell', 'benchmarking',
        }
        assert {t.value for t in types} == expected

    def test_synergy_curves_defined(self):
        from portfolio_synergy_engine import SYNERGY_CURVE, SynergyType
        for st in SynergyType:
            assert st in SYNERGY_CURVE, f"Missing curve for {st}"
            curve = SYNERGY_CURVE[st]
            assert 'base_lift_pct' in curve
            assert 'decay_rate' in curve
            assert 'max_companies' in curve
            assert curve['base_lift_pct'] > 0
            assert 0 < curve['decay_rate'] <= 1.0


# ============================================================
# SYNERGY MULTIPLIER TESTS
# ============================================================

class TestSynergyMultiplier:
    def test_first_company_no_synergy(self):
        from portfolio_synergy_engine import calculate_synergy_multiplier, SynergyType
        for st in SynergyType:
            mult = calculate_synergy_multiplier(st, 0)
            assert mult == 1.0, f"First company should get no synergy for {st}"

    def test_second_company_gets_synergy(self):
        from portfolio_synergy_engine import calculate_synergy_multiplier, SynergyType
        for st in SynergyType:
            mult = calculate_synergy_multiplier(st, 1)
            assert mult > 1.0, f"Second company should get synergy for {st}"

    def test_diminishing_returns(self):
        """Each additional company should get less synergy than the previous."""
        from portfolio_synergy_engine import calculate_synergy_multiplier, SynergyType

        for st in SynergyType:
            multipliers = [calculate_synergy_multiplier(st, i) for i in range(1, 8)]
            for i in range(1, len(multipliers)):
                assert multipliers[i] <= multipliers[i-1], \
                    f"Synergy should diminish: {st} company {i+2} > company {i+1}"

    def test_multiplier_bounded(self):
        """Synergy multiplier should never exceed 1 + base_lift/100."""
        from portfolio_synergy_engine import (
            calculate_synergy_multiplier, SynergyType, SYNERGY_CURVE,
        )
        for st in SynergyType:
            max_mult = 1.0 + SYNERGY_CURVE[st]['base_lift_pct'] / 100.0
            for i in range(1, 20):
                mult = calculate_synergy_multiplier(st, i)
                assert mult <= max_mult + 0.001, \
                    f"Multiplier {mult} exceeds max {max_mult} for {st} at company {i+1}"

    def test_max_companies_cap(self):
        """Companies beyond max should still get some (capped) synergy."""
        from portfolio_synergy_engine import calculate_synergy_multiplier, SynergyType
        for st in SynergyType:
            mult_at_max = calculate_synergy_multiplier(st, 50)
            assert mult_at_max >= 1.0


# ============================================================
# PORTFOLIO ANALYSIS TESTS
# ============================================================

class TestPortfolioAnalysis:
    def test_single_company_portfolio(self):
        from portfolio_synergy_engine import (
            PortfolioCompany, analyze_portfolio,
        )
        companies = [
            PortfolioCompany('co-1', 'Test Co', 10_000_000, 1.0),
        ]
        result = analyze_portfolio('Test Portfolio', companies)
        assert result.company_count == 1
        assert result.standalone_total_impact > 0
        assert result.synergy_total_impact == 0, "Single company should have no synergy"
        assert result.portfolio_total_impact == result.standalone_total_impact

    def test_multi_company_synergy_uplift(self):
        """Multiple companies should show synergy uplift."""
        from portfolio_synergy_engine import PortfolioCompany, analyze_portfolio

        companies = [
            PortfolioCompany('co-1', 'Company A', 20_000_000, 2.0),
            PortfolioCompany('co-2', 'Company B', 15_000_000, 2.0),
            PortfolioCompany('co-3', 'Company C', 10_000_000, 2.0),
        ]
        result = analyze_portfolio('3-Co Portfolio', companies)

        assert result.company_count == 3
        assert result.synergy_total_impact > 0, "Multi-company should have synergy"
        assert result.portfolio_total_impact > result.standalone_total_impact
        assert result.synergy_uplift_pct > 0

    def test_portfolio_roi_improves_with_synergy(self):
        """Portfolio ROI should be higher than standalone ROI."""
        from portfolio_synergy_engine import PortfolioCompany, analyze_portfolio

        companies = [
            PortfolioCompany('co-1', 'Co A', 30_000_000, 2.0),
            PortfolioCompany('co-2', 'Co B', 20_000_000, 2.0),
        ]
        result = analyze_portfolio('Test', companies)
        assert result.portfolio_roi >= result.standalone_roi

    def test_total_arr_summed_correctly(self):
        from portfolio_synergy_engine import PortfolioCompany, analyze_portfolio
        companies = [
            PortfolioCompany('co-1', 'A', 10_000_000, 1.0),
            PortfolioCompany('co-2', 'B', 20_000_000, 1.0),
        ]
        result = analyze_portfolio('Test', companies)
        assert result.total_arr == 30_000_000

    def test_payback_months_positive(self):
        from portfolio_synergy_engine import PortfolioCompany, analyze_portfolio
        companies = [
            PortfolioCompany('co-1', 'A', 15_000_000, 2.0),
        ]
        result = analyze_portfolio('Test', companies)
        assert result.payback_months > 0

    def test_synergy_breakdown_keys(self):
        """Synergy breakdown should contain the synergy types that applied."""
        from portfolio_synergy_engine import PortfolioCompany, analyze_portfolio

        companies = [
            PortfolioCompany('co-1', 'A', 20_000_000, 2.0),
            PortfolioCompany('co-2', 'B', 15_000_000, 2.0),
        ]
        result = analyze_portfolio('Test', companies)
        assert isinstance(result.synergy_breakdown, dict)
        assert len(result.synergy_breakdown) > 0


# ============================================================
# PRESET PORTFOLIO TESTS
# ============================================================

class TestPresetPortfolios:
    def test_all_presets_defined(self):
        from portfolio_synergy_engine import EXAMPLE_PORTFOLIOS
        assert 'pe_3_company' in EXAMPLE_PORTFOLIOS
        assert 'pe_5_company' in EXAMPLE_PORTFOLIOS
        assert 'data_center' in EXAMPLE_PORTFOLIOS

    def test_pe_3_company_preset(self):
        from portfolio_synergy_engine import run_preset_portfolio
        result = run_preset_portfolio('pe_3_company')
        assert result is not None
        assert result.company_count == 3
        assert result.portfolio_total_impact > 0

    def test_pe_5_company_preset(self):
        from portfolio_synergy_engine import run_preset_portfolio
        result = run_preset_portfolio('pe_5_company')
        assert result is not None
        assert result.company_count == 5
        assert result.synergy_uplift_pct > 0

    def test_data_center_preset(self):
        from portfolio_synergy_engine import run_preset_portfolio
        result = run_preset_portfolio('data_center')
        assert result is not None
        assert result.company_count == 3

    def test_invalid_preset_returns_none(self):
        from portfolio_synergy_engine import run_preset_portfolio
        result = run_preset_portfolio('nonexistent')
        assert result is None

    def test_more_companies_more_synergy(self):
        """5-company portfolio should have higher absolute synergy than 3-company."""
        from portfolio_synergy_engine import run_preset_portfolio
        r3 = run_preset_portfolio('pe_3_company')
        r5 = run_preset_portfolio('pe_5_company')
        # More companies → more absolute synergy dollars
        assert r5.synergy_total_impact > r3.synergy_total_impact


# ============================================================
# SERIALIZATION TESTS
# ============================================================

class TestSerialization:
    def test_portfolio_result_to_dict(self):
        from portfolio_synergy_engine import (
            run_preset_portfolio, portfolio_result_to_dict,
        )
        result = run_preset_portfolio('pe_3_company')
        d = portfolio_result_to_dict(result)

        assert 'portfolio_name' in d
        assert 'company_count' in d
        assert 'total_arr' in d
        assert 'standalone_total_impact' in d
        assert 'synergy_total_impact' in d
        assert 'portfolio_roi' in d
        assert 'companies' in d
        assert len(d['companies']) == 3

    def test_company_synergies_in_dict(self):
        from portfolio_synergy_engine import (
            run_preset_portfolio, portfolio_result_to_dict,
        )
        result = run_preset_portfolio('pe_3_company')
        d = portfolio_result_to_dict(result)

        # Second company should have synergies
        co2 = d['companies'][1]
        assert 'synergies' in co2
        assert len(co2['synergies']) > 0
        for s in co2['synergies']:
            assert 'type' in s
            assert 'multiplier' in s
            assert 'dollar_impact' in s


# ============================================================
# COMPANY-LEVEL DETAIL TESTS
# ============================================================

class TestCompanyLevel:
    def test_first_company_no_synergy_impact(self):
        from portfolio_synergy_engine import run_preset_portfolio
        result = run_preset_portfolio('pe_3_company')
        first = result.companies[0]
        assert first.synergy_impact == 0
        assert first.standalone_impact == first.total_impact

    def test_second_company_has_synergy(self):
        from portfolio_synergy_engine import run_preset_portfolio
        result = run_preset_portfolio('pe_3_company')
        second = result.companies[1]
        assert second.synergy_impact > 0
        assert second.total_impact > second.standalone_impact

    def test_synergy_adjusted_investment_lower(self):
        """Shared resources should reduce investment for later companies."""
        from portfolio_synergy_engine import run_preset_portfolio
        result = run_preset_portfolio('pe_3_company')
        second = result.companies[1]
        assert second.synergy_adjusted_investment <= second.standalone_investment


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
