/**
 * KPI Filtering Utilities
 * 
 * Provides type-safe utilities for filtering product-level vs account-level KPIs.
 * These functions use explicit null/undefined checks to prevent flaky behavior.
 */

export interface KPI {
  kpi_id: number;
  account_id: number;
  product_id?: number | null;
  product_name?: string | null;
  kpi_parameter: string;
  category: string;
  data: string;
  [key: string]: any; // Allow additional properties
}

/**
 * Check if a KPI is product-level
 * Uses explicit null/undefined checks to prevent type coercion issues
 * 
 * @param kpi - KPI object to check
 * @returns true if KPI is product-level, false otherwise
 */
export const isProductLevelKPI = (kpi: KPI): boolean => {
  return kpi.product_id !== null && kpi.product_id !== undefined;
};

/**
 * Check if a KPI is account-level
 * Uses explicit null/undefined checks to prevent type coercion issues
 * 
 * @param kpi - KPI object to check
 * @returns true if KPI is account-level, false otherwise
 */
export const isAccountLevelKPI = (kpi: KPI): boolean => {
  return kpi.product_id === null || kpi.product_id === undefined;
};

/**
 * Filter product-level KPIs from an array
 * 
 * @param kpis - Array of KPIs to filter
 * @returns Array of product-level KPIs
 */
export const filterProductKPIs = (kpis: KPI[]): KPI[] => {
  return kpis.filter(isProductLevelKPI);
};

/**
 * Filter account-level KPIs from an array
 * 
 * @param kpis - Array of KPIs to filter
 * @returns Array of account-level KPIs
 */
export const filterAccountKPIs = (kpis: KPI[]): KPI[] => {
  return kpis.filter(isAccountLevelKPI);
};

/**
 * Count product-level KPIs
 * 
 * @param kpis - Array of KPIs to count
 * @returns Number of product-level KPIs
 */
export const countProductKPIs = (kpis: KPI[]): number => {
  return kpis.filter(isProductLevelKPI).length;
};

/**
 * Count account-level KPIs
 * 
 * @param kpis - Array of KPIs to count
 * @returns Number of account-level KPIs
 */
export const countAccountKPIs = (kpis: KPI[]): number => {
  return kpis.filter(isAccountLevelKPI).length;
};

