/**
 * useContextGraphToggle — Custom hook for checking context graph feature status.
 *
 * Fetches the toggle once and caches the result. Returns active state + sub-toggles.
 */

import { useState, useEffect } from 'react';
import { fetchContextGraphToggle } from '../utils/contextGraphApi';
import type { ContextGraphSubToggles } from '../types/contextGraph';

interface ContextGraphToggleState {
  active: boolean;
  subToggles: ContextGraphSubToggles;
  loading: boolean;
  error: string | null;
}

const DEFAULT_SUB_TOGGLES: ContextGraphSubToggles = {
  story_arcs: false,
  signal_edges: false,
  stakeholder_tracking: false,
  decision_lifecycle: false,
  outcome_economics: false,
  industry_benchmarks: false,
};

// Module-level cache so we don't re-fetch every mount
let cachedResult: { active: boolean; subToggles: ContextGraphSubToggles } | null = null;

export function useContextGraphToggle(): ContextGraphToggleState {
  const [state, setState] = useState<ContextGraphToggleState>({
    active: cachedResult?.active ?? false,
    subToggles: cachedResult?.subToggles ?? DEFAULT_SUB_TOGGLES,
    loading: cachedResult === null,
    error: null,
  });

  useEffect(() => {
    if (cachedResult) return; // Already fetched

    let cancelled = false;

    fetchContextGraphToggle()
      .then((data) => {
        if (cancelled) return;
        const result = {
          active: data.active,
          subToggles: data.sub_toggles || DEFAULT_SUB_TOGGLES,
        };
        cachedResult = result;
        setState({ ...result, loading: false, error: null });
      })
      .catch((err) => {
        if (cancelled) return;
        // Graceful fallback: if toggle endpoint fails, assume disabled
        setState({
          active: false,
          subToggles: DEFAULT_SUB_TOGGLES,
          loading: false,
          error: err.message,
        });
      });

    return () => { cancelled = true; };
  }, []);

  return state;
}

/** Force refetch (e.g. after settings change) */
export function invalidateToggleCache(): void {
  cachedResult = null;
}
