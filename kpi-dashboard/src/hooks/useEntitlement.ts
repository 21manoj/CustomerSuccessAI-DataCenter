/**
 * useEntitlement — Tier-based feature gating hook
 * =================================================
 *
 * Mirrors the backend FEATURE_CATALOG from entitlements.py.
 * Uses the tier + entitlements stored in SessionContext
 * (populated at login from the backend).
 *
 * Usage:
 *   const { allowed, tier, requiredTier } = useEntitlement('signal_analyst');
 *   const { check, tier } = useEntitlements();
 *   if (check('playbook_triggers')) { ... }
 */

import { useSession, type Tier } from '../contexts/SessionContext';

// ---------------------------------------------------------------------------
// Feature catalog — must stay in sync with backend entitlements.py
// ---------------------------------------------------------------------------
const FEATURE_CATALOG: Record<string, { tier: Tier; description: string }> = {
  // Starter
  dashboards:           { tier: 'starter',      description: 'Core KPI dashboards and health scores' },
  data_upload:          { tier: 'starter',      description: 'CSV/Excel data upload and validation' },
  health_scores:        { tier: 'starter',      description: 'Pillar-based health score calculation' },
  journey_generation:   { tier: 'starter',      description: 'Customer journey visualization' },
  reports_basic:        { tier: 'starter',      description: 'Basic RACI and status reports' },

  // Professional
  signal_analyst:       { tier: 'professional', description: 'AI Signal Analyst (churn/expansion prediction)' },
  agent_loop:           { tier: 'professional', description: 'Agentic reasoning loop (6-step PAOR)' },
  playbook_triggers:    { tier: 'professional', description: 'Manual playbook triggering and execution' },
  power_of_1:           { tier: 'professional', description: 'Power of 1 financial impact calculator' },
  decision_matrix:      { tier: 'professional', description: 'AI-powered decision matrix' },
  approval_queue:       { tier: 'professional', description: 'Human-in-the-loop approval workflow' },
  journey_visualizer:   { tier: 'professional', description: 'Journey Visualizer (Wizard A/B analysis)' },
  rag_queries:          { tier: 'professional', description: 'RAG-powered natural language queries' },

  // Enterprise
  test_runner_advanced: { tier: 'enterprise',   description: 'Test Runner advanced options' },
  revenue_intelligence: { tier: 'enterprise',   description: 'Revenue intelligence and portfolio analysis' },
  portfolio_synergy:    { tier: 'enterprise',   description: 'PE portfolio synergy modeling (Power of 1 CEO)' },
  onboarding_agent:     { tier: 'enterprise',   description: 'AI Onboarding Agent' },
  auto_trigger_pipeline:{ tier: 'enterprise',   description: 'Event-driven auto-analysis + auto-playbook' },
  feedback_loop:        { tier: 'enterprise',   description: 'Playbook outcome agent learning loop' },
  mcp_connectors:       { tier: 'enterprise',   description: 'MCP external connectors' },
  copilot_integration:  { tier: 'enterprise',   description: 'Microsoft Copilot / Teams integration' },
  multi_provider:       { tier: 'enterprise',   description: 'Multi-LLM provider support' },
  agent_memory_shared:  { tier: 'enterprise',   description: 'Cross-agent shared memory' },
};

// ---------------------------------------------------------------------------
// Tier hierarchy
// ---------------------------------------------------------------------------
const TIER_LEVEL: Record<Tier, number> = {
  starter: 0,
  professional: 1,
  enterprise: 2,
};

const TIER_INCLUDES: Record<Tier, Tier[]> = {
  starter:      ['starter'],
  professional: ['starter', 'professional'],
  enterprise:   ['starter', 'professional', 'enterprise'],
};

// ---------------------------------------------------------------------------
// Hooks
// ---------------------------------------------------------------------------

/**
 * Check a single feature entitlement.
 */
export function useEntitlement(featureName: string): {
  allowed: boolean;
  tier: Tier;
  requiredTier: Tier | null;
  description: string;
} {
  const { session } = useSession();
  const customerTier: Tier = session?.tier ?? 'enterprise';

  // 1. Check per-customer override from backend (entitlements map)
  if (session?.entitlements && featureName in session.entitlements) {
    return {
      allowed: session.entitlements[featureName],
      tier: customerTier,
      requiredTier: FEATURE_CATALOG[featureName]?.tier ?? null,
      description: FEATURE_CATALOG[featureName]?.description ?? '',
    };
  }

  // 2. Check tier-based default
  const featureInfo = FEATURE_CATALOG[featureName];
  if (!featureInfo) {
    return { allowed: false, tier: customerTier, requiredTier: null, description: '' };
  }

  const included = TIER_INCLUDES[customerTier] ?? ['starter'];
  const allowed = included.includes(featureInfo.tier);

  return {
    allowed,
    tier: customerTier,
    requiredTier: featureInfo.tier,
    description: featureInfo.description,
  };
}

/**
 * Get all entitlements — returns a check function and the current tier.
 */
export function useEntitlements(): {
  check: (featureName: string) => boolean;
  tier: Tier;
  tierLevel: number;
  tierLabel: string;
} {
  const { session } = useSession();
  const customerTier: Tier = session?.tier ?? 'enterprise';

  const check = (featureName: string): boolean => {
    // Per-customer override
    if (session?.entitlements && featureName in session.entitlements) {
      return session.entitlements[featureName];
    }
    // Tier-based default
    const featureInfo = FEATURE_CATALOG[featureName];
    if (!featureInfo) return false;
    const included = TIER_INCLUDES[customerTier] ?? ['starter'];
    return included.includes(featureInfo.tier);
  };

  const tierLabels: Record<Tier, string> = {
    starter: 'Starter',
    professional: 'Professional',
    enterprise: 'Enterprise',
  };

  return {
    check,
    tier: customerTier,
    tierLevel: TIER_LEVEL[customerTier],
    tierLabel: tierLabels[customerTier],
  };
}

/**
 * Get the required tier for a feature (for upgrade prompts).
 */
export function getRequiredTier(featureName: string): Tier | null {
  return FEATURE_CATALOG[featureName]?.tier ?? null;
}

/**
 * Get a human-readable tier label.
 */
export function tierLabel(tier: Tier): string {
  const labels: Record<Tier, string> = {
    starter: 'Starter',
    professional: 'Professional',
    enterprise: 'Enterprise',
  };
  return labels[tier] ?? tier;
}

export { FEATURE_CATALOG, TIER_LEVEL, TIER_INCLUDES };
