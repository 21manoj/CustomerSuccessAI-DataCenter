#!/usr/bin/env python3
"""
Step 9 — Portfolio Model + Synergy Engine
============================================
PE multi-company play: models a portfolio of companies, each running
the Power of 1 program, and calculates cross-portfolio synergies.

Synergy types:
  - Shared playbook learnings (reduced ramp time for co #2, #3, …)
  - Shared resource pools (fractional CSM/SE across portfolio)
  - Vendor leverage (volume discounts on tools/licenses)
  - Cross-sell / land-and-expand across portfolio companies
  - Benchmarking lift (portfolio-wide best practice diffusion)

Data model relies on:
  - Portfolio / PortfolioMembership (models.py)
  - Power of 1 metrics per company
  - Resource capacity model for shared pools
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from enum import Enum
import math

from power_of_1_model import (
    POWER_OF_1_METRICS, calculate_portfolio_impact, calculate_portfolio_impact_multi_lever,
    INVESTMENT_SUMMARY,
)
from resource_capacity_model import (
    ROLE_RATES, CSRole, check_capacity, get_resource_pool_summary,
)


# ============================================================
# SYNERGY TYPES
# ============================================================

class SynergyType(Enum):
    SHARED_PLAYBOOKS = "shared_playbooks"
    SHARED_RESOURCES = "shared_resources"
    VENDOR_LEVERAGE = "vendor_leverage"
    CROSS_SELL = "cross_sell"
    BENCHMARKING = "benchmarking"


@dataclass
class SynergyFactor:
    """A single synergy factor with its multiplier and dollar impact."""
    synergy_type: SynergyType
    description: str
    multiplier: float  # 1.0 = no synergy, 1.15 = 15% lift
    dollar_impact: float = 0
    applies_from_company_n: int = 2  # Synergy kicks in from company #N


# ============================================================
# SYNERGY PARAMETERS
# ============================================================

# These are the synergy curves — each additional portfolio company
# contributes diminishing but still positive synergy
SYNERGY_CURVE = {
    SynergyType.SHARED_PLAYBOOKS: {
        'base_lift_pct': 12.0,    # First additional co gets 12% lift
        'decay_rate': 0.70,       # Each subsequent co gets 70% of prior
        'max_companies': 15,
        'description': 'Playbook learnings transfer across portfolio companies',
    },
    SynergyType.SHARED_RESOURCES: {
        'base_lift_pct': 18.0,    # Shared CSM/SE pool saves 18%
        'decay_rate': 0.80,
        'max_companies': 15,
        'description': 'Fractional CSM/SE resources shared across companies',
    },
    SynergyType.VENDOR_LEVERAGE: {
        'base_lift_pct': 8.0,     # Volume discount on tooling
        'decay_rate': 0.65,
        'max_companies': 10,
        'description': 'Volume discounts on CS platform licenses',
    },
    SynergyType.CROSS_SELL: {
        'base_lift_pct': 5.0,     # Land-and-expand across portfolio
        'decay_rate': 0.60,
        'max_companies': 10,
        'description': 'Cross-sell opportunities across portfolio companies',
    },
    SynergyType.BENCHMARKING: {
        'base_lift_pct': 10.0,    # Best practice diffusion
        'decay_rate': 0.75,
        'max_companies': 20,
        'description': 'Portfolio-wide benchmarking drives best practice adoption',
    },
}


# ============================================================
# PORTFOLIO COMPANY MODEL
# ============================================================

@dataclass
class PortfolioCompany:
    """A company in the PE portfolio."""
    company_id: str
    company_name: str
    arr: float
    improvement_pct: float = 1.0  # Power of 1 target
    maturity_level: str = 'emerging'  # 'emerging', 'growth', 'mature'
    vertical: str = 'general'


@dataclass
class CompanyResult:
    """Power of 1 result for a single portfolio company."""
    company_id: str
    company_name: str
    arr: float
    standalone_impact: float
    synergy_impact: float
    total_impact: float
    standalone_investment: float
    synergy_adjusted_investment: float
    standalone_roi: float
    synergy_roi: float
    synergies_applied: List[SynergyFactor]


@dataclass
class PortfolioResult:
    """Full portfolio-level analysis."""
    portfolio_name: str
    company_count: int
    total_arr: float
    companies: List[CompanyResult]
    standalone_total_impact: float
    synergy_total_impact: float
    portfolio_total_impact: float
    standalone_total_investment: float
    synergy_adjusted_investment: float
    standalone_roi: float
    portfolio_roi: float
    synergy_uplift_pct: float
    synergy_breakdown: Dict[str, float]  # synergy_type → total $
    payback_months: float


# ============================================================
# SYNERGY CALCULATION
# ============================================================

def calculate_synergy_multiplier(
    synergy_type: SynergyType,
    company_index: int,
) -> float:
    """
    Calculate the synergy multiplier for the Nth company in the portfolio.

    Company index 0 = first company (no synergy)
    Company index 1 = second company (full base synergy)
    Company index N = diminishing returns via decay curve

    Returns a multiplier >= 1.0
    """
    if company_index < 1:
        return 1.0  # First company gets no synergy

    curve = SYNERGY_CURVE.get(synergy_type)
    if not curve:
        return 1.0

    if company_index >= curve['max_companies']:
        company_index = curve['max_companies'] - 1

    # Geometric decay: base * decay^(n-1)
    lift_pct = curve['base_lift_pct'] * (curve['decay_rate'] ** (company_index - 1))

    return 1.0 + (lift_pct / 100.0)


def calculate_company_synergies(
    company_index: int,
    standalone_impact: float,
    standalone_investment: float,
) -> Tuple[List[SynergyFactor], float, float]:
    """
    Calculate all synergies for a company at a given portfolio position.

    Returns:
        (synergy_factors, total_synergy_impact, adjusted_investment)
    """
    synergy_factors = []
    total_impact_lift = 0
    total_cost_reduction = 0

    for synergy_type, curve in SYNERGY_CURVE.items():
        multiplier = calculate_synergy_multiplier(synergy_type, company_index)

        if multiplier <= 1.0:
            continue

        if synergy_type in (SynergyType.SHARED_RESOURCES, SynergyType.VENDOR_LEVERAGE):
            # These reduce cost
            cost_reduction = standalone_investment * (multiplier - 1.0)
            total_cost_reduction += cost_reduction
            synergy_factors.append(SynergyFactor(
                synergy_type=synergy_type,
                description=curve['description'],
                multiplier=round(multiplier, 4),
                dollar_impact=round(cost_reduction, 2),
                applies_from_company_n=2,
            ))
        else:
            # These increase impact
            impact_lift = standalone_impact * (multiplier - 1.0)
            total_impact_lift += impact_lift
            synergy_factors.append(SynergyFactor(
                synergy_type=synergy_type,
                description=curve['description'],
                multiplier=round(multiplier, 4),
                dollar_impact=round(impact_lift, 2),
                applies_from_company_n=2,
            ))

    adjusted_investment = max(0, standalone_investment - total_cost_reduction)
    return synergy_factors, total_impact_lift, adjusted_investment


# ============================================================
# PORTFOLIO-LEVEL ANALYSIS
# ============================================================

def analyze_portfolio(
    portfolio_name: str,
    companies: List[PortfolioCompany],
) -> PortfolioResult:
    """
    Run a full portfolio analysis with synergy calculations.

    Companies should be ordered by priority (most mature first)
    since synergy accrues based on position.
    """
    company_results = []
    standalone_total_impact = 0
    synergy_total_impact = 0
    standalone_total_investment = 0
    synergy_adjusted_total_investment = 0
    synergy_breakdown: Dict[str, float] = {}

    for idx, company in enumerate(companies):
        # Run Power of 1 for this company in isolation
        po1 = calculate_portfolio_impact(company.improvement_pct, company.arr)
        standalone_impact = po1['totals']['total_impact']
        standalone_investment = po1['totals']['investment']
        standalone_roi = po1['totals']['roi']

        # Calculate synergies based on portfolio position
        synergies, impact_lift, adj_investment = calculate_company_synergies(
            idx, standalone_impact, standalone_investment
        )

        total_impact = standalone_impact + impact_lift

        # Synergy-adjusted ROI
        synergy_roi = round(
            (total_impact - adj_investment) / adj_investment, 2
        ) if adj_investment > 0 else 0

        # Accumulate
        standalone_total_impact += standalone_impact
        synergy_total_impact += impact_lift
        standalone_total_investment += standalone_investment
        synergy_adjusted_total_investment += adj_investment

        for sf in synergies:
            key = sf.synergy_type.value
            synergy_breakdown[key] = synergy_breakdown.get(key, 0) + sf.dollar_impact

        company_results.append(CompanyResult(
            company_id=company.company_id,
            company_name=company.company_name,
            arr=company.arr,
            standalone_impact=round(standalone_impact, 2),
            synergy_impact=round(impact_lift, 2),
            total_impact=round(total_impact, 2),
            standalone_investment=round(standalone_investment, 2),
            synergy_adjusted_investment=round(adj_investment, 2),
            standalone_roi=standalone_roi,
            synergy_roi=synergy_roi,
            synergies_applied=synergies,
        ))

    portfolio_total_impact = standalone_total_impact + synergy_total_impact

    standalone_roi = round(
        (standalone_total_impact - standalone_total_investment) / standalone_total_investment, 2
    ) if standalone_total_investment > 0 else 0

    portfolio_roi = round(
        (portfolio_total_impact - synergy_adjusted_total_investment)
        / synergy_adjusted_total_investment, 2
    ) if synergy_adjusted_total_investment > 0 else 0

    synergy_uplift_pct = round(
        (synergy_total_impact / standalone_total_impact) * 100, 1
    ) if standalone_total_impact > 0 else 0

    payback_months = round(
        synergy_adjusted_total_investment / (portfolio_total_impact / 12), 1
    ) if portfolio_total_impact > 0 else 0

    total_arr = sum(c.arr for c in companies)

    return PortfolioResult(
        portfolio_name=portfolio_name,
        company_count=len(companies),
        total_arr=round(total_arr, 2),
        companies=company_results,
        standalone_total_impact=round(standalone_total_impact, 2),
        synergy_total_impact=round(synergy_total_impact, 2),
        portfolio_total_impact=round(portfolio_total_impact, 2),
        standalone_total_investment=round(standalone_total_investment, 2),
        synergy_adjusted_investment=round(synergy_adjusted_total_investment, 2),
        standalone_roi=standalone_roi,
        portfolio_roi=portfolio_roi,
        synergy_uplift_pct=synergy_uplift_pct,
        synergy_breakdown={k: round(v, 2) for k, v in synergy_breakdown.items()},
        payback_months=payback_months,
    )


def analyze_portfolio_multi_lever(
    portfolio_name: str,
    companies: List[PortfolioCompany],
    improvement_by_metric: Dict[str, float],
) -> PortfolioResult:
    """
    Run portfolio analysis when each of the 6 Power of 1 levers has its own improvement %.
    Same synergy logic as analyze_portfolio; per-company impact uses multi-lever calc.
    """
    company_results = []
    standalone_total_impact = 0
    synergy_total_impact = 0
    standalone_total_investment = 0
    synergy_adjusted_total_investment = 0
    synergy_breakdown: Dict[str, float] = {}

    for idx, company in enumerate(companies):
        po1 = calculate_portfolio_impact_multi_lever(improvement_by_metric, company.arr)
        standalone_impact = po1["totals"]["total_impact"]
        standalone_investment = po1["totals"]["investment"]
        standalone_roi = po1["totals"]["roi"]

        synergies, impact_lift, adj_investment = calculate_company_synergies(
            idx, standalone_impact, standalone_investment
        )

        total_impact = standalone_impact + impact_lift
        synergy_roi = round(
            (total_impact - adj_investment) / adj_investment, 2
        ) if adj_investment > 0 else 0

        standalone_total_impact += standalone_impact
        synergy_total_impact += impact_lift
        standalone_total_investment += standalone_investment
        synergy_adjusted_total_investment += adj_investment

        for sf in synergies:
            key = sf.synergy_type.value
            synergy_breakdown[key] = synergy_breakdown.get(key, 0) + sf.dollar_impact

        company_results.append(CompanyResult(
            company_id=company.company_id,
            company_name=company.company_name,
            arr=company.arr,
            standalone_impact=round(standalone_impact, 2),
            synergy_impact=round(impact_lift, 2),
            total_impact=round(total_impact, 2),
            standalone_investment=round(standalone_investment, 2),
            synergy_adjusted_investment=round(adj_investment, 2),
            standalone_roi=standalone_roi,
            synergy_roi=synergy_roi,
            synergies_applied=synergies,
        ))

    portfolio_total_impact = standalone_total_impact + synergy_total_impact

    standalone_roi = round(
        (standalone_total_impact - standalone_total_investment) / standalone_total_investment, 2
    ) if standalone_total_investment > 0 else 0

    portfolio_roi = round(
        (portfolio_total_impact - synergy_adjusted_total_investment)
        / synergy_adjusted_total_investment, 2
    ) if synergy_adjusted_total_investment > 0 else 0

    synergy_uplift_pct = round(
        (synergy_total_impact / standalone_total_impact) * 100, 1
    ) if standalone_total_impact > 0 else 0

    payback_months = round(
        synergy_adjusted_total_investment / (portfolio_total_impact / 12), 1
    ) if portfolio_total_impact > 0 else 0

    total_arr = sum(c.arr for c in companies)

    return PortfolioResult(
        portfolio_name=portfolio_name,
        company_count=len(companies),
        total_arr=round(total_arr, 2),
        companies=company_results,
        standalone_total_impact=round(standalone_total_impact, 2),
        synergy_total_impact=round(synergy_total_impact, 2),
        portfolio_total_impact=round(portfolio_total_impact, 2),
        standalone_total_investment=round(standalone_total_investment, 2),
        synergy_adjusted_investment=round(synergy_adjusted_total_investment, 2),
        standalone_roi=standalone_roi,
        portfolio_roi=portfolio_roi,
        synergy_uplift_pct=synergy_uplift_pct,
        synergy_breakdown={k: round(v, 2) for k, v in synergy_breakdown.items()},
        payback_months=payback_months,
    )


# ============================================================
# PRESET PORTFOLIO SCENARIOS
# ============================================================

EXAMPLE_PORTFOLIOS = {
    'pe_3_company': {
        'name': 'PE 3-Company Portfolio',
        'companies': [
            PortfolioCompany('co-1', 'MidMarket SaaS Co', 15_000_000, 2.0, 'growth', 'saas'),
            PortfolioCompany('co-2', 'Enterprise Platform', 40_000_000, 1.0, 'mature', 'platform'),
            PortfolioCompany('co-3', 'Growth Startup', 5_000_000, 3.0, 'emerging', 'saas'),
        ],
    },
    'pe_5_company': {
        'name': 'PE 5-Company Platform',
        'companies': [
            PortfolioCompany('co-1', 'Anchor Enterprise', 80_000_000, 1.0, 'mature', 'enterprise'),
            PortfolioCompany('co-2', 'Mid-Market A', 20_000_000, 2.0, 'growth', 'saas'),
            PortfolioCompany('co-3', 'Mid-Market B', 18_000_000, 2.0, 'growth', 'saas'),
            PortfolioCompany('co-4', 'Vertical Player', 12_000_000, 2.5, 'growth', 'vertical'),
            PortfolioCompany('co-5', 'Early Stage', 4_000_000, 4.0, 'emerging', 'saas'),
        ],
    },
    'data_center': {
        'name': 'Data Center Portfolio',
        'companies': [
            PortfolioCompany('dc-1', 'Tier 1 Hyperscaler', 120_000_000, 1.0, 'mature', 'data_center'),
            PortfolioCompany('dc-2', 'Regional DC Provider', 30_000_000, 2.0, 'growth', 'data_center'),
            PortfolioCompany('dc-3', 'Edge Computing Co', 8_000_000, 3.0, 'emerging', 'data_center'),
        ],
    },
}


def run_preset_portfolio(preset_name: str) -> Optional[PortfolioResult]:
    """Run analysis on a preset portfolio scenario."""
    preset = EXAMPLE_PORTFOLIOS.get(preset_name)
    if not preset:
        return None
    return analyze_portfolio(preset['name'], preset['companies'])


# ============================================================
# SERIALIZATION
# ============================================================

def portfolio_result_to_dict(r: PortfolioResult) -> Dict:
    """Serialize a PortfolioResult for API response."""
    return {
        'portfolio_name': r.portfolio_name,
        'company_count': r.company_count,
        'total_arr': r.total_arr,
        'standalone_total_impact': r.standalone_total_impact,
        'synergy_total_impact': r.synergy_total_impact,
        'portfolio_total_impact': r.portfolio_total_impact,
        'standalone_total_investment': r.standalone_total_investment,
        'synergy_adjusted_investment': r.synergy_adjusted_investment,
        'standalone_roi': r.standalone_roi,
        'portfolio_roi': r.portfolio_roi,
        'synergy_uplift_pct': r.synergy_uplift_pct,
        'synergy_breakdown': r.synergy_breakdown,
        'payback_months': r.payback_months,
        'companies': [
            {
                'company_id': c.company_id,
                'company_name': c.company_name,
                'arr': c.arr,
                'standalone_impact': c.standalone_impact,
                'synergy_impact': c.synergy_impact,
                'total_impact': c.total_impact,
                'standalone_investment': c.standalone_investment,
                'synergy_adjusted_investment': c.synergy_adjusted_investment,
                'standalone_roi': c.standalone_roi,
                'synergy_roi': c.synergy_roi,
                'synergies': [
                    {
                        'type': s.synergy_type.value,
                        'description': s.description,
                        'multiplier': s.multiplier,
                        'dollar_impact': s.dollar_impact,
                    }
                    for s in c.synergies_applied
                ],
            }
            for c in r.companies
        ],
    }
