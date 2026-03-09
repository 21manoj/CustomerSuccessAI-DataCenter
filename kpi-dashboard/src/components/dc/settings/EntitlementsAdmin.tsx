/**
 * Entitlements Admin — Ring 1 Platform Component
 * ================================================
 * Manage subscription tiers and feature flags for the current customer.
 *
 * Backend API contract (entitlements.py):
 *   GET  /api/entitlements          → all features + enabled flags
 *   GET  /api/entitlements/tier     → { tier, features }
 *   PUT  /api/entitlements/tier     → { customer_id, tier }
 *   PUT  /api/entitlements/override → { customer_id, feature, enabled }
 *   GET  /api/entitlements/catalog  → full feature catalog
 *
 * Three tiers:
 *   starter       — 5 features   (dashboards, data upload, health scores, etc.)
 *   professional   — +8 features  (signal analyst, playbooks, PAOR loop, etc.)
 *   enterprise     — +8 features  (onboarding agent, auto-triggers, MCP, etc.)
 */

import React, { useState, useEffect, useCallback } from 'react';
import {
  Shield,
  CheckCircle,
  XCircle,
  RefreshCw,
  ArrowUp,
  Lock,
  Unlock,
  AlertCircle,
  Star,
  Zap,
  Crown,
  ToggleLeft,
  ToggleRight,
  Search,
  Info
} from 'lucide-react';
import { useSession } from '../../../contexts/SessionContext';

// ============================================================
// TYPES
// ============================================================

interface FeatureInfo {
  description: string;
  tier: string;
  enabled: boolean;
  overridden?: boolean;
}

interface TierData {
  tier: string;
  features: Record<string, boolean>;
}

interface CatalogEntry {
  description: string;
  tier: string;
}

interface Catalog {
  features: Record<string, CatalogEntry>;
  tiers: Record<string, { level: number; features: string[] }>;
}

type TierName = 'starter' | 'professional' | 'enterprise';

// ============================================================
// CONSTANTS
// ============================================================

const TIER_META: Record<TierName, { label: string; icon: React.ComponentType<{ className?: string }>; color: string; bgColor: string; borderColor: string; badgeColor: string; description: string }> = {
  starter: {
    label: 'Starter',
    icon: Star,
    color: 'text-gray-700',
    bgColor: 'bg-gray-50',
    borderColor: 'border-gray-300',
    badgeColor: 'bg-gray-100 text-gray-700',
    description: 'Core dashboards, data upload, health scores',
  },
  professional: {
    label: 'Professional',
    icon: Zap,
    color: 'text-blue-700',
    bgColor: 'bg-blue-50',
    borderColor: 'border-blue-300',
    badgeColor: 'bg-blue-100 text-blue-700',
    description: 'Signal Analyst, Playbooks, Agent Loop, Revenue Intelligence',
  },
  enterprise: {
    label: 'Enterprise',
    icon: Crown,
    color: 'text-purple-700',
    bgColor: 'bg-purple-50',
    borderColor: 'border-purple-300',
    badgeColor: 'bg-purple-100 text-purple-700',
    description: 'Onboarding Agent, Auto-triggers, MCP Connectors, Copilot',
  },
};

const TIER_ORDER: TierName[] = ['starter', 'professional', 'enterprise'];

// ============================================================
// MAIN COMPONENT
// ============================================================

const EntitlementsAdmin: React.FC = () => {
  const { session } = useSession();

  // State
  const [tierData, setTierData] = useState<TierData | null>(null);
  const [catalog, setCatalog] = useState<Catalog | null>(null);
  const [entitlements, setEntitlements] = useState<Record<string, FeatureInfo>>({});
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState<string | null>(null); // feature name being saved, or 'tier'
  const [toast, setToast] = useState<{ message: string; type: 'success' | 'error' } | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [filterTier, setFilterTier] = useState<'all' | TierName>('all');
  const [confirmTierChange, setConfirmTierChange] = useState<TierName | null>(null);

  // ── Helpers ──

  const showToast = useCallback((message: string, type: 'success' | 'error') => {
    setToast({ message, type });
    setTimeout(() => setToast(null), 4000);
  }, []);

  const getCustomerId = useCallback((): number => {
    return (session as any)?.customer_id || 1;
  }, [session]);

  // ── Data Fetching ──

  const fetchAll = useCallback(async () => {
    setLoading(true);
    try {
      const [tierResp, catalogResp, entResp] = await Promise.all([
        fetch('/api/entitlements/tier', { credentials: 'include' }),
        fetch('/api/entitlements/catalog', { credentials: 'include' }),
        fetch('/api/entitlements', { credentials: 'include' }),
      ]);

      if (tierResp.ok) {
        const td = await tierResp.json();
        setTierData({ tier: td.tier || 'starter', features: td.features || {} });
      }

      if (catalogResp.ok) {
        const cat = await catalogResp.json();
        setCatalog(cat);
      }

      if (entResp.ok) {
        const ent = await entResp.json();
        // Build feature map with override detection
        const entMap: Record<string, FeatureInfo> = {};
        const features = ent.entitlements || {};
        const overrides = ent.overrides || {};
        const catalogFeatures = catalog?.features || {};

        for (const [name, enabled] of Object.entries(features)) {
          entMap[name] = {
            description: (catalogFeatures as any)[name]?.description || name,
            tier: (catalogFeatures as any)[name]?.tier || 'starter',
            enabled: enabled as boolean,
            overridden: name in overrides,
          };
        }
        setEntitlements(entMap);
      }
    } catch (err) {
      console.error('Failed to fetch entitlements:', err);
      showToast('Failed to load entitlements', 'error');
    } finally {
      setLoading(false);
    }
  }, [showToast]);

  useEffect(() => {
    fetchAll();
  }, []);

  // Re-merge entitlements when catalog loads
  useEffect(() => {
    if (catalog && tierData) {
      // Rebuild entitlements with catalog descriptions
      const catFeatures = catalog.features || {};
      setEntitlements(prev => {
        const merged: Record<string, FeatureInfo> = {};
        for (const [name, info] of Object.entries(catFeatures)) {
          merged[name] = {
            description: info.description,
            tier: info.tier,
            enabled: prev[name]?.enabled ?? tierData.features[name] ?? false,
            overridden: prev[name]?.overridden ?? false,
          };
        }
        return merged;
      });
    }
  }, [catalog, tierData]);

  // ── Tier Change ──

  const handleTierChange = async (newTier: TierName) => {
    setConfirmTierChange(null);
    setSaving('tier');
    try {
      const resp = await fetch('/api/entitlements/tier', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ customer_id: getCustomerId(), tier: newTier }),
      });

      if (resp.ok) {
        showToast(`Tier changed to ${TIER_META[newTier].label}`, 'success');
        await fetchAll(); // Refresh all data
      } else {
        const err = await resp.json();
        showToast(err.error || 'Failed to change tier', 'error');
      }
    } catch (err) {
      showToast('Failed to change tier', 'error');
    } finally {
      setSaving(null);
    }
  };

  // ── Feature Override ──

  const handleToggleFeature = async (featureName: string, currentEnabled: boolean) => {
    setSaving(featureName);
    try {
      const resp = await fetch('/api/entitlements/override', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({
          customer_id: getCustomerId(),
          feature: featureName,
          enabled: !currentEnabled,
        }),
      });

      if (resp.ok) {
        // Update local state immediately
        setEntitlements(prev => ({
          ...prev,
          [featureName]: {
            ...prev[featureName],
            enabled: !currentEnabled,
            overridden: true,
          },
        }));
        showToast(
          `${featureName} ${!currentEnabled ? 'enabled' : 'disabled'}`,
          'success'
        );
      } else {
        const err = await resp.json();
        showToast(err.error || 'Failed to toggle feature', 'error');
      }
    } catch (err) {
      showToast('Failed to toggle feature', 'error');
    } finally {
      setSaving(null);
    }
  };

  // ── Filtering ──

  const filteredFeatures = Object.entries(entitlements).filter(([name, info]) => {
    if (filterTier !== 'all' && info.tier !== filterTier) return false;
    if (searchQuery) {
      const q = searchQuery.toLowerCase();
      return name.toLowerCase().includes(q) || info.description.toLowerCase().includes(q);
    }
    return true;
  });

  // Group by tier for display
  const featuresByTier: Record<TierName, [string, FeatureInfo][]> = {
    starter: [],
    professional: [],
    enterprise: [],
  };
  filteredFeatures.forEach(([name, info]) => {
    const t = info.tier as TierName;
    if (featuresByTier[t]) {
      featuresByTier[t].push([name, info]);
    }
  });

  const currentTier = (tierData?.tier || 'starter') as TierName;

  // ── Render ──

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <RefreshCw className="h-6 w-6 text-gray-400 animate-spin" />
        <span className="ml-2 text-gray-500">Loading entitlements...</span>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Toast */}
      {toast && (
        <div className={`fixed top-4 right-4 z-50 px-4 py-3 rounded-lg shadow-lg flex items-center space-x-2 transition-all duration-300 ${
          toast.type === 'success'
            ? 'bg-green-50 border border-green-200 text-green-800'
            : 'bg-red-50 border border-red-200 text-red-800'
        }`}>
          {toast.type === 'success' ? <CheckCircle className="h-4 w-4" /> : <AlertCircle className="h-4 w-4" />}
          <span className="text-sm font-medium">{toast.message}</span>
        </div>
      )}

      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-lg font-semibold text-gray-900">Entitlements & Feature Flags</h3>
          <p className="text-sm text-gray-500 mt-1">
            Manage subscription tier and per-feature overrides
          </p>
        </div>
        <button
          onClick={() => fetchAll()}
          disabled={loading}
          className="flex items-center px-3 py-2 text-sm text-gray-600 hover:text-gray-800 border border-gray-300 rounded-lg hover:bg-gray-50"
        >
          <RefreshCw className={`h-4 w-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
          Refresh
        </button>
      </div>

      {/* ── Tier Selector Cards ── */}
      <div>
        <h4 className="text-sm font-medium text-gray-700 mb-3">Current Subscription Tier</h4>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {TIER_ORDER.map(tier => {
            const meta = TIER_META[tier];
            const isActive = currentTier === tier;
            const TierIcon = meta.icon;

            return (
              <div
                key={tier}
                className={`relative rounded-lg border-2 p-4 transition-all ${
                  isActive
                    ? `${meta.borderColor} ${meta.bgColor} shadow-md`
                    : 'border-gray-200 bg-white hover:border-gray-300 hover:shadow-sm'
                }`}
              >
                {isActive && (
                  <div className="absolute -top-2.5 left-4">
                    <span className={`text-xs font-bold px-2 py-0.5 rounded-full ${meta.badgeColor}`}>
                      CURRENT
                    </span>
                  </div>
                )}

                <div className="flex items-center space-x-3 mb-2 mt-1">
                  <div className={`p-2 rounded-lg ${isActive ? meta.bgColor : 'bg-gray-100'}`}>
                    <TierIcon className={`h-5 w-5 ${isActive ? meta.color : 'text-gray-500'}`} />
                  </div>
                  <div>
                    <h5 className={`font-semibold ${isActive ? meta.color : 'text-gray-900'}`}>
                      {meta.label}
                    </h5>
                    <p className="text-xs text-gray-500">
                      {catalog?.tiers?.[tier]?.features?.length || '–'} features
                    </p>
                  </div>
                </div>

                <p className="text-xs text-gray-600 mb-3">{meta.description}</p>

                {!isActive && (
                  <button
                    onClick={() => setConfirmTierChange(tier)}
                    disabled={saving === 'tier'}
                    className={`w-full text-center text-sm font-medium py-2 rounded-lg transition-colors ${
                      TIER_ORDER.indexOf(tier) > TIER_ORDER.indexOf(currentTier)
                        ? 'bg-blue-600 text-white hover:bg-blue-700'
                        : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
                    } disabled:opacity-50`}
                  >
                    {saving === 'tier' ? (
                      <RefreshCw className="h-4 w-4 animate-spin mx-auto" />
                    ) : TIER_ORDER.indexOf(tier) > TIER_ORDER.indexOf(currentTier) ? (
                      <span className="flex items-center justify-center">
                        <ArrowUp className="h-3 w-3 mr-1" />
                        Upgrade
                      </span>
                    ) : (
                      'Downgrade'
                    )}
                  </button>
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* Tier Change Confirmation Modal */}
      {confirmTierChange && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl max-w-md w-full p-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-2">
              Confirm Tier Change
            </h3>
            <p className="text-sm text-gray-600 mb-4">
              {TIER_ORDER.indexOf(confirmTierChange) > TIER_ORDER.indexOf(currentTier) ? (
                <>
                  Upgrade from <strong>{TIER_META[currentTier].label}</strong> to{' '}
                  <strong>{TIER_META[confirmTierChange].label}</strong>?
                  This will unlock additional features.
                </>
              ) : (
                <>
                  Downgrade from <strong>{TIER_META[currentTier].label}</strong> to{' '}
                  <strong>{TIER_META[confirmTierChange].label}</strong>?
                  Some features will become unavailable.
                </>
              )}
            </p>
            <div className="flex justify-end space-x-3">
              <button
                onClick={() => setConfirmTierChange(null)}
                className="px-4 py-2 text-sm border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50"
              >
                Cancel
              </button>
              <button
                onClick={() => handleTierChange(confirmTierChange)}
                className={`px-4 py-2 text-sm rounded-lg text-white ${
                  TIER_ORDER.indexOf(confirmTierChange) > TIER_ORDER.indexOf(currentTier)
                    ? 'bg-blue-600 hover:bg-blue-700'
                    : 'bg-orange-600 hover:bg-orange-700'
                }`}
              >
                {TIER_ORDER.indexOf(confirmTierChange) > TIER_ORDER.indexOf(currentTier)
                  ? 'Confirm Upgrade'
                  : 'Confirm Downgrade'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ── Feature Catalog ── */}
      <div>
        <div className="flex items-center justify-between mb-3">
          <h4 className="text-sm font-medium text-gray-700">Feature Catalog</h4>
          <div className="flex items-center space-x-3">
            {/* Search */}
            <div className="relative">
              <Search className="h-4 w-4 absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
              <input
                type="text"
                value={searchQuery}
                onChange={e => setSearchQuery(e.target.value)}
                placeholder="Search features..."
                className="pl-9 pr-3 py-1.5 text-sm border border-gray-300 rounded-lg w-56"
              />
            </div>
            {/* Filter */}
            <select
              value={filterTier}
              onChange={e => setFilterTier(e.target.value as any)}
              className="text-sm border border-gray-300 rounded-lg px-3 py-1.5"
            >
              <option value="all">All Tiers</option>
              <option value="starter">Starter</option>
              <option value="professional">Professional</option>
              <option value="enterprise">Enterprise</option>
            </select>
          </div>
        </div>

        {/* Info banner */}
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-3 mb-4">
          <div className="flex items-start">
            <Info className="h-4 w-4 text-blue-600 mt-0.5 mr-2 shrink-0" />
            <p className="text-xs text-blue-700">
              Features are enabled by your subscription tier. Use the toggle to create per-feature overrides.
              Overridden features show an <span className="font-semibold">OVERRIDE</span> badge and persist across tier changes.
            </p>
          </div>
        </div>

        {/* Feature groups by tier */}
        {TIER_ORDER.map(tier => {
          const features = featuresByTier[tier];
          if (features.length === 0 && filterTier !== 'all') return null;
          if (features.length === 0) return null;

          const meta = TIER_META[tier];
          const TierIcon = meta.icon;
          const tierIncluded = TIER_ORDER.indexOf(tier) <= TIER_ORDER.indexOf(currentTier);

          return (
            <div key={tier} className="mb-6">
              {/* Tier section header */}
              <div className={`flex items-center space-x-2 mb-2 pb-2 border-b ${meta.borderColor}`}>
                <TierIcon className={`h-4 w-4 ${meta.color}`} />
                <span className={`text-sm font-semibold ${meta.color}`}>{meta.label}</span>
                <span className="text-xs text-gray-500">({features.length} features)</span>
                {tierIncluded ? (
                  <span className="text-xs px-2 py-0.5 rounded-full bg-green-100 text-green-700">
                    Included in your plan
                  </span>
                ) : (
                  <span className="text-xs px-2 py-0.5 rounded-full bg-gray-100 text-gray-500">
                    Requires {meta.label}
                  </span>
                )}
              </div>

              {/* Feature rows */}
              <div className="bg-white border border-gray-200 rounded-lg overflow-hidden">
                <table className="min-w-full divide-y divide-gray-200">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-4 py-2.5 text-left text-xs font-medium text-gray-500 uppercase w-1/4">Feature</th>
                      <th className="px-4 py-2.5 text-left text-xs font-medium text-gray-500 uppercase w-2/5">Description</th>
                      <th className="px-4 py-2.5 text-center text-xs font-medium text-gray-500 uppercase w-1/6">Status</th>
                      <th className="px-4 py-2.5 text-center text-xs font-medium text-gray-500 uppercase w-1/6">Override</th>
                    </tr>
                  </thead>
                  <tbody className="bg-white divide-y divide-gray-100">
                    {features.map(([name, info]) => {
                      const isSaving = saving === name;

                      return (
                        <tr key={name} className="hover:bg-gray-50">
                          <td className="px-4 py-3">
                            <div className="flex items-center space-x-2">
                              {info.enabled ? (
                                <Unlock className="h-3.5 w-3.5 text-green-500 shrink-0" />
                              ) : (
                                <Lock className="h-3.5 w-3.5 text-gray-400 shrink-0" />
                              )}
                              <span className="text-sm font-medium text-gray-900">{name}</span>
                            </div>
                            {info.overridden && (
                              <span className="ml-5 text-[10px] px-1.5 py-0.5 rounded bg-yellow-100 text-yellow-800 font-medium">
                                OVERRIDE
                              </span>
                            )}
                          </td>
                          <td className="px-4 py-3">
                            <span className="text-sm text-gray-600">{info.description}</span>
                          </td>
                          <td className="px-4 py-3 text-center">
                            <span className={`inline-flex px-2 py-0.5 text-xs rounded-full font-medium ${
                              info.enabled
                                ? 'bg-green-100 text-green-800'
                                : 'bg-gray-100 text-gray-600'
                            }`}>
                              {info.enabled ? 'Enabled' : 'Disabled'}
                            </span>
                          </td>
                          <td className="px-4 py-3 text-center">
                            <button
                              onClick={() => handleToggleFeature(name, info.enabled)}
                              disabled={isSaving}
                              className="inline-flex items-center justify-center transition-colors disabled:opacity-50"
                              title={info.enabled ? 'Disable this feature' : 'Enable this feature'}
                            >
                              {isSaving ? (
                                <RefreshCw className="h-5 w-5 text-gray-400 animate-spin" />
                              ) : info.enabled ? (
                                <ToggleRight className="h-6 w-6 text-green-500 hover:text-green-600" />
                              ) : (
                                <ToggleLeft className="h-6 w-6 text-gray-400 hover:text-gray-500" />
                              )}
                            </button>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>
          );
        })}

        {filteredFeatures.length === 0 && (
          <div className="text-center py-12 bg-white rounded-lg border border-gray-200">
            <Shield className="h-12 w-12 text-gray-300 mx-auto mb-3" />
            <p className="text-gray-500 text-sm">No features match your search</p>
          </div>
        )}
      </div>

      {/* ── Summary Stats ── */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="bg-white rounded-lg border border-gray-200 p-4">
          <p className="text-xs text-gray-500 uppercase font-medium">Total Features</p>
          <p className="text-2xl font-bold text-gray-900 mt-1">{Object.keys(entitlements).length}</p>
        </div>
        <div className="bg-white rounded-lg border border-gray-200 p-4">
          <p className="text-xs text-gray-500 uppercase font-medium">Enabled</p>
          <p className="text-2xl font-bold text-green-600 mt-1">
            {Object.values(entitlements).filter(f => f.enabled).length}
          </p>
        </div>
        <div className="bg-white rounded-lg border border-gray-200 p-4">
          <p className="text-xs text-gray-500 uppercase font-medium">Disabled</p>
          <p className="text-2xl font-bold text-gray-500 mt-1">
            {Object.values(entitlements).filter(f => !f.enabled).length}
          </p>
        </div>
        <div className="bg-white rounded-lg border border-gray-200 p-4">
          <p className="text-xs text-gray-500 uppercase font-medium">Overrides</p>
          <p className="text-2xl font-bold text-yellow-600 mt-1">
            {Object.values(entitlements).filter(f => f.overridden).length}
          </p>
        </div>
      </div>
    </div>
  );
};

export default EntitlementsAdmin;
