/**
 * Tests for KPI Filtering Logic
 * 
 * These tests ensure that product-level vs account-level KPI filtering
 * works correctly and doesn't regress.
 */

import {
  filterProductKPIs,
  filterAccountKPIs,
  isProductLevelKPI,
  isAccountLevelKPI,
  countProductKPIs,
  countAccountKPIs
} from './kpiFiltering';

import type { KPI } from './kpiFiltering';

describe('KPI Filtering Logic', () => {
  const mockKPIs: KPI[] = [
    // Account-level KPIs
    { kpi_id: 1, account_id: 1, product_id: null, kpi_parameter: 'Revenue', category: 'Business', data: '1000' },
    { kpi_id: 2, account_id: 1, product_id: undefined, kpi_parameter: 'Users', category: 'Product', data: '50' },
    { kpi_id: 3, account_id: 1, product_id: 0, kpi_parameter: 'Churn', category: 'Business', data: '5%' },
    
    // Product-level KPIs
    { kpi_id: 4, account_id: 1, product_id: 101, product_name: 'Core Platform', kpi_parameter: 'Activation', category: 'Product', data: '80%' },
    { kpi_id: 5, account_id: 1, product_id: 102, product_name: 'Mobile App', kpi_parameter: 'Activation', category: 'Product', data: '75%' },
    { kpi_id: 6, account_id: 1, product_id: 103, product_name: 'API Gateway', kpi_parameter: 'Activation', category: 'Product', data: '70%' },
  ];

  test('should correctly identify product-level KPIs', () => {
    const productKPIs = filterProductKPIs(mockKPIs);
    expect(productKPIs).toHaveLength(3);
    expect(productKPIs.map(k => k.kpi_id)).toEqual([4, 5, 6]);
    expect(productKPIs.every(k => k.product_id !== null && k.product_id !== undefined)).toBe(true);
  });

  test('should correctly identify account-level KPIs (null, undefined, and 0)', () => {
    const accountKPIs = filterAccountKPIs(mockKPIs);
    expect(accountKPIs).toHaveLength(3);
    expect(accountKPIs.map(k => k.kpi_id)).toEqual([1, 2, 3]);
    expect(accountKPIs.every(k => k.product_id === null || k.product_id === undefined || k.product_id === 0)).toBe(true);
  });

  test('should handle edge case: product_id = 0 (should be treated as account-level)', () => {
    const kpiWithZero: KPI = { kpi_id: 7, account_id: 1, product_id: 0, kpi_parameter: 'Test', category: 'Test', data: '0' };
    const productKPIs = filterProductKPIs([kpiWithZero]);
    const accountKPIs = filterAccountKPIs([kpiWithZero]);
    
    expect(productKPIs).toHaveLength(0);
    expect(accountKPIs).toHaveLength(1);
  });

  test('should handle empty array', () => {
    expect(filterProductKPIs([])).toEqual([]);
    expect(filterAccountKPIs([])).toEqual([]);
  });

  test('should handle mixed scenarios correctly', () => {
    const mixedKPIs: KPI[] = [
      { kpi_id: 1, account_id: 1, product_id: null, kpi_parameter: 'A', category: 'C', data: '1' },
      { kpi_id: 2, account_id: 1, product_id: undefined, kpi_parameter: 'B', category: 'C', data: '2' },
      { kpi_id: 3, account_id: 1, product_id: 100, kpi_parameter: 'C', category: 'C', data: '3' },
      { kpi_id: 4, account_id: 1, product_id: 200, kpi_parameter: 'D', category: 'C', data: '4' },
    ];

    const productKPIs = filterProductKPIs(mixedKPIs);
    const accountKPIs = filterAccountKPIs(mixedKPIs);

    expect(productKPIs).toHaveLength(2);
    expect(accountKPIs).toHaveLength(2);
    expect(productKPIs.map(k => k.kpi_id)).toEqual([3, 4]);
    expect(accountKPIs.map(k => k.kpi_id)).toEqual([1, 2]);
  });
});

