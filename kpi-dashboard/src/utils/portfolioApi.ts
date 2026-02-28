/**
 * Portfolio API utility functions.
 * All calls go to real backend endpoints — no mock data.
 */
import { apiCall } from './api';

// ─── Types ───────────────────────────────────────────

export interface SynergyBreakdown {
  type: string;
  description: string;
  multiplier: number;
  dollar_impact: number;
}

export interface CompanyResult {
  company_id: string;
  company_name: string;
  arr: number;
  standalone_impact: number;
  synergy_impact: number;
  total_impact: number;
  standalone_investment: number;
  synergy_adjusted_investment: number;
  standalone_roi: number;
  synergy_roi: number;
  synergies: SynergyBreakdown[];
}

export interface PortfolioResult {
  portfolio_id: number;
  portfolio_name: string;
  company_count: number;
  total_arr: number;
  standalone_total_impact: number;
  synergy_total_impact: number;
  portfolio_total_impact: number;
  standalone_total_investment: number;
  synergy_adjusted_investment: number;
  standalone_roi: number;
  portfolio_roi: number;
  synergy_uplift_pct: number;
  synergy_breakdown: Record<string, number>;
  payback_months: number;
  companies: CompanyResult[];
  improvement_pct: number;
  investment_summary: InvestmentSummary;
  cost_inputs: CostInputs;
}

export interface PortfolioSummary {
  portfolio_id: number;
  portfolio_name: string;
  portfolio_type: string;
  description: string | null;
  total_aum: number | null;
  enabled: boolean;
  company_count: number;
  total_arr: number;
}

export interface PortfolioCompanyInfo {
  customer_id: number;
  customer_name: string;
  arr: number;
  account_count: number;
  vertical: string | null;
  status: string;
  role: string;
  acquisition_date: string | null;
  synergies_identified: number;
  synergies_realized: number;
  synergy_value: number;
}

export interface SliderPoint {
  improvement_pct: number;
  company_count: number;
  total_arr: number;
  standalone_impact: number;
  synergy_impact: number;
  portfolio_total_impact: number;
  standalone_roi: number;
  portfolio_roi: number;
  synergy_uplift_pct: number;
  investment: number;
  payback_months: number;
}

export interface MetricCurvePoint {
  improvement_pct: number;
  total_impact: number;
  roi: number;
  display_name: string;
}

export interface SliderData {
  portfolio_id: number;
  portfolio_name: string;
  slider_points: SliderPoint[];
  per_metric_curves: Record<string, MetricCurvePoint[]>;
  investment_summary: InvestmentSummary;
}

export interface CostInputs {
  total_investment?: number;
  cs_initiatives?: number;
  platform_cost?: number;
}

export interface InvestmentSummary {
  total_investment: number;
  cs_initiatives: number;
  platform_cost: number;
  total_hours: number;
  total_fte: number;
}

export interface SynergyOverride {
  base_lift_pct: number;
  decay_rate: number;
}

export interface PortfolioConfig {
  portfolio_id: number;
  cost_inputs: CostInputs;
  role_rate_overrides: Record<string, number>;
  synergy_overrides: Record<string, SynergyOverride>;
  default_improvement_pct: number;
  resource_pool: {
    roles: Array<{
      role: string;
      display_name: string;
      annual_hours: number;
      fte: number;
      hourly_rate: number;
      annual_cost: number;
      description: string;
    }>;
    totals: {
      total_hours: number;
      total_fte: number;
      total_annual_cost: number;
    };
  };
}

export interface ScalingCurvePoint {
  improvement_pct: number;
  standalone_impact?: number;
  synergy_impact?: number;
  portfolio_total_impact?: number;
  portfolio_roi?: number;
  synergy_uplift_pct?: number;
  total_impact?: number;
  roi?: number;
  investment?: number;
}

export interface PortfolioScalingCurves {
  portfolio_id: number;
  company_curves: Record<string, {
    customer_name: string;
    arr: number;
    curves: ScalingCurvePoint[];
  }>;
  portfolio_curves: ScalingCurvePoint[];
}

// ─── API Functions ───────────────────────────────────

async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const err = await response.json().catch(() => ({ error: `HTTP ${response.status}` }));
    throw new Error(err.error || `Request failed with status ${response.status}`);
  }
  return response.json();
}

/** List all portfolios for the current user */
export async function listPortfolios(): Promise<{ portfolios: PortfolioSummary[]; count: number }> {
  const res = await apiCall('/api/portfolio');
  return handleResponse(res);
}

/** List customers available to add to a portfolio (Power of 1 / revenue_intelligence enabled, with accounts) */
export async function getAvailableCustomersForPortfolio(): Promise<{
  customers: Array<{ customer_id: number; customer_name: string }>;
}> {
  const res = await apiCall('/api/portfolio/available-customers');
  return handleResponse(res);
}

/** Create a new portfolio */
export async function createPortfolio(data: {
  portfolio_name: string;
  portfolio_type?: string;
  description?: string;
  total_aum?: number;
  investment_thesis?: string;
  cost_inputs?: CostInputs;
  companies?: Array<{ customer_id: number; vertical?: string; status?: string }>;
}): Promise<{ portfolio_id: number; portfolio: PortfolioSummary }> {
  const res = await apiCall('/api/portfolio', {
    method: 'POST',
    body: JSON.stringify(data),
  });
  return handleResponse(res);
}

/** Get portfolio detail with companies */
export async function getPortfolio(portfolioId: number): Promise<PortfolioSummary & {
  companies: PortfolioCompanyInfo[];
  company_count: number;
  total_arr: number;
  config: Record<string, unknown>;
}> {
  const res = await apiCall(`/api/portfolio/${portfolioId}`);
  return handleResponse(res);
}

/** Update portfolio */
export async function updatePortfolio(portfolioId: number, data: Record<string, unknown>): Promise<{ message: string }> {
  const res = await apiCall(`/api/portfolio/${portfolioId}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  });
  return handleResponse(res);
}

/** Delete portfolio */
export async function deletePortfolio(portfolioId: number): Promise<{ message: string }> {
  const res = await apiCall(`/api/portfolio/${portfolioId}`, { method: 'DELETE' });
  return handleResponse(res);
}

/** List companies in a portfolio */
export async function listPortfolioCompanies(portfolioId: number): Promise<{
  companies: PortfolioCompanyInfo[];
  count: number;
  total_arr: number;
}> {
  const res = await apiCall(`/api/portfolio/${portfolioId}/companies`);
  return handleResponse(res);
}

/** Add a company to a portfolio */
export async function addPortfolioCompany(portfolioId: number, data: {
  customer_id: number;
  vertical?: string;
  status?: string;
  role?: string;
}): Promise<{ message: string }> {
  const res = await apiCall(`/api/portfolio/${portfolioId}/companies`, {
    method: 'POST',
    body: JSON.stringify(data),
  });
  return handleResponse(res);
}

/** Remove a company from a portfolio */
export async function removePortfolioCompany(portfolioId: number, customerId: number): Promise<{ message: string }> {
  const res = await apiCall(`/api/portfolio/${portfolioId}/companies/${customerId}`, {
    method: 'DELETE',
  });
  return handleResponse(res);
}

/** Get combined Power of 1 + Synergy impact for all companies */
export async function getPortfolioImpact(portfolioId: number, improvementPct = 1.0): Promise<PortfolioResult> {
  const res = await apiCall(`/api/portfolio/${portfolioId}/impact?improvement_pct=${improvementPct}`);
  return handleResponse(res);
}

/** What-if slider: get impact across 0.5%-6% improvement range (single slider; legacy) */
export async function getSliderData(portfolioId: number): Promise<SliderData> {
  const res = await apiCall(`/api/portfolio/${portfolioId}/power-of-1-slider`);
  return handleResponse(res);
}

/** 6-lever impact: each of the 6 Power of 1 levers has its own improvement % */
export interface PowerOf1LeverImpact {
  improvement_pct: number;
  baseline?: number;
  new_value?: number;
  unit?: string;
  total_impact: number;
  investment: number;
  roi: number;
  display_name: string;
}

export type PowerOf1ImpactResult = PortfolioResult & {
  improvement_by_metric: Record<string, number>;
  per_metric_impacts: Record<string, PowerOf1LeverImpact>;
};

const POWER_OF_1_LEVER_IDS = [
  'TTFV', 'NRR', 'GRR', 'ticket_resolution_time', 'product_adoption', 'expansion_rate',
];

export async function getPowerOf1Impact(
  portfolioId: number,
  leverPcts: Record<string, number>
): Promise<PowerOf1ImpactResult> {
  const params = new URLSearchParams();
  POWER_OF_1_LEVER_IDS.forEach(id => {
    const v = leverPcts[id] ?? 1.0;
    params.set(id, String(v));
  });
  const res = await apiCall(`/api/portfolio/${portfolioId}/power-of-1-impact?${params.toString()}`);
  return handleResponse(res);
}

/** Non-linear scaling curves per company + combined */
export async function getScalingCurves(portfolioId: number): Promise<PortfolioScalingCurves> {
  const res = await apiCall(`/api/portfolio/${portfolioId}/scaling-curves`);
  return handleResponse(res);
}

/** Get portfolio configuration */
export async function getPortfolioConfig(portfolioId: number): Promise<PortfolioConfig> {
  const res = await apiCall(`/api/portfolio/${portfolioId}/config`);
  return handleResponse(res);
}

/** Update portfolio configuration */
export async function updatePortfolioConfig(portfolioId: number, data: {
  cost_inputs?: CostInputs;
  role_rate_overrides?: Record<string, number>;
  synergy_overrides?: Record<string, SynergyOverride>;
  default_improvement_pct?: number;
}): Promise<{ message: string }> {
  const res = await apiCall(`/api/portfolio/${portfolioId}/config`, {
    method: 'PUT',
    body: JSON.stringify(data),
  });
  return handleResponse(res);
}
