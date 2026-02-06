import { useState, useEffect } from 'react';
import { apiCall } from '../utils/api';

export interface PillarWeights {
  AI: number;
  CH: number;
  DV: number;
  EX: number;
  OS: number;
}

export interface KPIWeights {
  [pillar: string]: {
    [kpiCode: string]: number;
  };
}

export interface KPIDefinition {
  pillar: string;
  name: string;
  description?: string;
  unit: string;
  target: number;
  operator: '>' | '<' | '>=' | '<=' | '=';
  range: [number, number];
  thresholds?: {
    excellent: { min: number | null; max: number | null };
    good: { min: number | null; max: number | null };
    warning: { min: number | null; max: number | null };
    critical: { min: number | null; max: number | null };
  };
}

/** Source of weights shown in read-only Pillar and KPI Weight Management tab */
export type WeightsSource = 'bootstrap' | 'learned';

export interface CustomerConfig {
  customer_id: number;
  is_default: boolean;
  /** 'bootstrap' = from bootstrap config file; 'learned' = from Wizard C or user overrides */
  weights_source?: WeightsSource;
  /** ISO timestamp of last update for the displayed weights (bootstrap file or config) */
  weights_updated_at?: string | null;
  pillar_weights: PillarWeights;
  enabled_kpis: string[];
  kpi_definitions: { [kpiCode: string]: KPIDefinition };
  kpi_overrides: { [kpiCode: string]: Partial<KPIDefinition> };
  kpi_weights: KPIWeights;
  updated_at: string | null;
}

export function useCustomerConfig() {
  const [config, setConfig] = useState<CustomerConfig | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchConfig = async () => {
    setLoading(true);
    setError(null);
    
    try {
      const response = await apiCall('/api/dc2s/config/', {
        method: 'GET'
      });
      
      if (!response.ok) {
        // Handle 401 (unauthorized) - user needs to log in
        if (response.status === 401) {
          setError('Please log in to view configuration');
          // Set default config to prevent UI from breaking
          setConfig({
            customer_id: 0,
            is_default: true,
            weights_source: 'bootstrap',
            pillar_weights: { AI: 0.25, CH: 0.20, DV: 0.15, EX: 0.20, OS: 0.20 },
            enabled_kpis: [],
            kpi_definitions: {},
            kpi_overrides: {},
            kpi_weights: {},
            updated_at: null
          });
          return;
        }
        
        // Handle 404 or other errors gracefully
        if (response.status === 404) {
          // Config doesn't exist yet - use defaults
          setConfig({
            customer_id: 0,
            is_default: true,
            weights_source: 'bootstrap',
            pillar_weights: { AI: 0.25, CH: 0.20, DV: 0.15, EX: 0.20, OS: 0.20 },
            enabled_kpis: [],
            kpi_definitions: {},
            kpi_overrides: {},
            kpi_weights: {},
            updated_at: null
          });
          return;
        }
        
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.error || `Failed to load configuration (${response.status})`);
      }
      
      const data = await response.json();
      setConfig(data);
    } catch (err: any) {
      console.error('Error fetching config:', err);
      // Only set error if it's not a network error (network errors are handled gracefully)
      if (err.message && !err.message.includes('Failed to fetch')) {
        setError(err.message || 'Failed to load configuration');
      }
      // Always set default config on error to prevent UI from breaking
      setConfig({
        customer_id: 0,
        is_default: true,
        pillar_weights: { AI: 0.25, CH: 0.20, DV: 0.15, EX: 0.20, OS: 0.20 },
        enabled_kpis: [],
        kpi_definitions: {},
        kpi_overrides: {},
        kpi_weights: {},
        updated_at: null
      });
    } finally {
      setLoading(false);
    }
  };

  const updateConfig = async (updates: Partial<CustomerConfig>) => {
    try {
      const response = await apiCall('/api/dc2s/config/', {
        method: 'PUT',
        credentials: 'include',
        body: JSON.stringify(updates)
      });
      
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.error || 'Failed to update configuration');
      }
      
      await fetchConfig(); // Reload
      return { success: true };
    } catch (err: any) {
      return { 
        success: false, 
        error: err.message || 'Failed to update configuration' 
      };
    }
  };

  const updatePillarWeights = async (pillarWeights: PillarWeights) => {
    try {
      const response = await apiCall('/api/dc2s/config/pillar-weights', {
        method: 'PUT',
        credentials: 'include',
        body: JSON.stringify({ pillar_weights: pillarWeights })
      });
      
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.error || 'Failed to update pillar weights');
      }
      
      await fetchConfig();
      return { success: true };
    } catch (err: any) {
      return { 
        success: false, 
        error: err.message || 'Failed to update pillar weights' 
      };
    }
  };

  const addCustomKPI = async (kpiCode: string, definition: KPIDefinition) => {
    try {
      const response = await apiCall('/api/dc2s/config/custom-kpi', {
        method: 'POST',
        credentials: 'include',
        body: JSON.stringify({
          kpi_code: kpiCode,
          kpi_definition: definition
        })
      });
      
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.error || 'Failed to add custom KPI');
      }
      
      await fetchConfig();
      return { success: true };
    } catch (err: any) {
      return { 
        success: false, 
        error: err.message || 'Failed to add custom KPI' 
      };
    }
  };

  const deleteCustomKPI = async (kpiCode: string) => {
    try {
      const response = await apiCall(`/api/dc2s/config/custom-kpi/${kpiCode}`, {
        method: 'DELETE',
        credentials: 'include'
      });
      
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.error || 'Failed to delete custom KPI');
      }
      
      await fetchConfig();
      return { success: true };
    } catch (err: any) {
      return { 
        success: false, 
        error: err.message || 'Failed to delete custom KPI' 
      };
    }
  };

  useEffect(() => {
    fetchConfig();
  }, []);

  return {
    config,
    loading,
    error,
    refetch: fetchConfig,
    updateConfig,
    updatePillarWeights,
    addCustomKPI,
    deleteCustomKPI
  };
}
