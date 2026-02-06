/**
 * RCA Enhanced Analysis Utilities
 * =================================
 * 
 * Functions to calculate pillar contributions, event impacts, correlations,
 * and root cause chains for the Root Cause Analysis view.
 */

import { WeekData, QualitativeSignal } from './JourneyDashboardV3';

export interface PillarContribution {
  pillar: string;
  pillar_name: string;
  contribution_pct: number;
  score_change: number;
  primary_driver: boolean;
  key_kpis: Array<{
    kpi: string;
    change: number;
    impact: 'high' | 'medium' | 'low';
  }>;
}

export interface EventImpact {
  week: number;
  event: string;
  type: string;
  health_impact: number;
  description: string;
}

export interface Correlation {
  correlation: string;
  strength: number;
  lag_weeks: number;
  explanation: string;
}

export interface RootCauseChain {
  level: number;
  cause: string;
  type: 'trigger_event' | 'consequence' | 'outcome';
}

/**
 * Calculate pillar contributions to health change
 */
export function calculatePillarContributions(
  weeklyData: WeekData[]
): PillarContribution[] {
  if (weeklyData.length < 2) return [];

  const firstWeek = weeklyData[0];
  const lastWeek = weeklyData[weeklyData.length - 1];
  
  const totalHealthChange = lastWeek.health_score - firstWeek.health_score;
  if (Math.abs(totalHealthChange) < 0.1) return [];

  // Get all unique pillars
  const allPillars = new Set<string>();
  weeklyData.forEach(week => {
    Object.keys(week.pillar_scores || {}).forEach(pillar => allPillars.add(pillar));
  });

  const contributions: PillarContribution[] = [];
  let totalAbsChange = 0;

  // Calculate change per pillar
  const pillarChanges: Record<string, number> = {};
  allPillars.forEach(pillar => {
    const startScore = firstWeek.pillar_scores?.[pillar] || 0;
    const endScore = lastWeek.pillar_scores?.[pillar] || 0;
    const change = endScore - startScore;
    pillarChanges[pillar] = change;
    totalAbsChange += Math.abs(change);
  });

  // Calculate contributions
  allPillars.forEach(pillar => {
    const change = pillarChanges[pillar];
    const absChange = Math.abs(change);
    const contributionPct = totalAbsChange > 0 
      ? (absChange / totalAbsChange) * 100 
      : 0;

    // Find key KPIs for this pillar
    const keyKpis = findKeyKPIsForPillar(weeklyData, pillar);

    contributions.push({
      pillar,
      pillar_name: formatPillarName(pillar),
      contribution_pct: Math.round(contributionPct * 10) / 10,
      score_change: Math.round(change * 10) / 10,
      primary_driver: contributionPct > 30,
      key_kpis: keyKpis
    });
  });

  // Sort by contribution percentage (descending)
  return contributions.sort((a, b) => b.contribution_pct - a.contribution_pct);
}

/**
 * Find key KPIs for a pillar that changed significantly
 */
function findKeyKPIsForPillar(
  weeklyData: WeekData[],
  pillar: string
): Array<{ kpi: string; change: number; impact: 'high' | 'medium' | 'low' }> {
  if (weeklyData.length < 2) return [];

  const firstWeek = weeklyData[0];
  const lastWeek = weeklyData[weeklyData.length - 1];
  
  const kpiChanges: Array<{ kpi: string; change: number; changePct: number }> = [];

  // Find KPIs that belong to this pillar (we'll need to infer from KPI names or use category)
  // For now, we'll look at all KPIs and see which ones changed significantly
  const firstWeekKpis = firstWeek.kpis || {};
  const lastWeekKpis = lastWeek.kpis || {};
  
  const allKpiNames = new Set([
    ...Object.keys(firstWeekKpis),
    ...Object.keys(lastWeekKpis)
  ]);

  allKpiNames.forEach(kpiName => {
    const firstValue = firstWeekKpis[kpiName] || 0;
    const lastValue = lastWeekKpis[kpiName] || 0;
    const change = lastValue - firstValue;
    const changePct = firstValue !== 0 ? (change / firstValue) * 100 : 0;

    if (Math.abs(changePct) > 10) { // Only include significant changes
      kpiChanges.push({ kpi: kpiName, change, changePct });
    }
  });

  // Sort by absolute change percentage and take top 3
  kpiChanges.sort((a, b) => Math.abs(b.changePct) - Math.abs(a.changePct));
  
  return kpiChanges.slice(0, 3).map(kpi => ({
    kpi: kpi.kpi,
    change: Math.round(kpi.change * 10) / 10,
    impact: Math.abs(kpi.changePct) > 30 ? 'high' : 
            Math.abs(kpi.changePct) > 15 ? 'medium' : 'low'
  }));
}

/**
 * Build event impact timeline from weekly data and signals
 */
export function buildEventImpactTimeline(
  weeklyData: WeekData[],
  signals: QualitativeSignal[]
): EventImpact[] {
  const events: EventImpact[] = [];

  // Add events from journey_events (in weeklyData)
  weeklyData.forEach((week, index) => {
    if (week.events && week.events.length > 0) {
      week.events.forEach((event: any) => {
        const healthImpact = calculateEventHealthImpact(week, weeklyData, index);
        events.push({
          week: week.week_number || index + 1,
          event: event.description || event.event_type || 'Event',
          type: event.event_type || 'unknown',
          health_impact: healthImpact,
          description: event.description || `${event.event_type} in week ${week.week_number}`
        });
      });
    }
  });

  // Add significant signals as events
  signals.forEach(signal => {
    if (signal.health_impact && Math.abs(signal.health_impact) >= 5) {
      events.push({
        week: signal.week_number || 1,
        event: signal.subject || signal.summary || 'Signal',
        type: signal.signal_type || 'signal',
        health_impact: signal.health_impact,
        description: signal.summary || signal.subject || 'Qualitative signal'
      });
    }
  });

  // Sort by week
  events.sort((a, b) => a.week - b.week);

  return events;
}

/**
 * Calculate health impact of an event by comparing weeks
 */
function calculateEventHealthImpact(
  week: WeekData,
  allWeeks: WeekData[],
  weekIndex: number
): number {
  if (weekIndex === 0) return 0;
  
  const prevWeek = allWeeks[weekIndex - 1];
  const nextWeek = allWeeks[weekIndex + 1];
  
  if (nextWeek) {
    // Impact is the change from previous to next week
    return nextWeek.health_score - prevWeek.health_score;
  }
  
  // If no next week, use current week vs previous
  return week.health_score - prevWeek.health_score;
}

/**
 * Calculate correlations between events and health changes
 */
export function calculateCorrelations(
  weeklyData: WeekData[],
  events: EventImpact[]
): Correlation[] {
  const correlations: Correlation[] = [];

  // For each event, find health changes in subsequent weeks
  events.forEach(event => {
    const eventWeekIndex = weeklyData.findIndex(w => w.week_number === event.week);
    if (eventWeekIndex === -1) return;

    // Look for health changes in the next 1-3 weeks
    for (let lag = 1; lag <= 3; lag++) {
      const futureWeekIndex = eventWeekIndex + lag;
      if (futureWeekIndex >= weeklyData.length) break;

      const eventWeek = weeklyData[eventWeekIndex];
      const futureWeek = weeklyData[futureWeekIndex];
      const healthChange = futureWeek.health_score - eventWeek.health_score;

      // If health changed in the same direction as event impact, there's a correlation
      if (Math.abs(healthChange) > 2 && 
          (event.health_impact > 0 && healthChange > 0) ||
          (event.health_impact < 0 && healthChange < 0)) {
        
        const strength = Math.min(Math.abs(healthChange) / 10, 1.0);
        
        correlations.push({
          correlation: `${event.event} → Health ${healthChange > 0 ? 'improvement' : 'decline'}`,
          strength: Math.round(strength * 100) / 100,
          lag_weeks: lag,
          explanation: `Health ${healthChange > 0 ? 'improved' : 'declined'} ${Math.abs(healthChange).toFixed(1)} points ${lag} week(s) after ${event.event}`
        });
      }
    }
  });

  // Sort by strength
  return correlations.sort((a, b) => b.strength - a.strength).slice(0, 5);
}

/**
 * Build root cause chain from events and correlations
 */
export function buildRootCauseChain(
  events: EventImpact[],
  correlations: Correlation[]
): RootCauseChain[] {
  const chain: RootCauseChain[] = [];

  // Find the earliest significant negative event
  const negativeEvents = events
    .filter(e => e.health_impact < -5)
    .sort((a, b) => a.week - b.week);

  if (negativeEvents.length === 0) return chain;

  const triggerEvent = negativeEvents[0];
  
  // Build chain starting from trigger
  chain.push({
    level: 1,
    cause: `${triggerEvent.event} (Week ${triggerEvent.week})`,
    type: 'trigger_event'
  });

  // Find consequences
  const relatedEvents = events.filter(e => 
    e.week > triggerEvent.week && 
    e.week <= triggerEvent.week + 4 &&
    e.health_impact < 0
  );

  relatedEvents.forEach((event, index) => {
    chain.push({
      level: index + 2,
      cause: inferConsequence(event, triggerEvent),
      type: 'consequence'
    });
  });

  // Add final outcome
  if (chain.length > 1) {
    chain.push({
      level: chain.length + 1,
      cause: 'Health score decline and increased churn risk',
      type: 'outcome'
    });
  }

  return chain;
}

/**
 * Infer consequence description from event
 */
function inferConsequence(event: EventImpact, trigger: EventImpact): string {
  const eventType = event.type.toLowerCase();
  
  if (eventType.includes('support') || eventType.includes('escalation')) {
    return 'Support response time degradation';
  }
  if (eventType.includes('usage') || eventType.includes('adoption')) {
    return 'Reduced platform utilization';
  }
  if (eventType.includes('champion') || eventType.includes('executive')) {
    return 'Knowledge gap in remaining team';
  }
  if (eventType.includes('nps') || eventType.includes('satisfaction')) {
    return 'Frustration and declining satisfaction';
  }
  
  return event.event;
}

/**
 * Format pillar name for display
 */
function formatPillarName(pillar: string): string {
  const pillarMap: Record<string, string> = {
    'P1': 'Performance',
    'P1_Performance': 'Performance',
    'P2': 'Usage & Adoption',
    'P2_Usage': 'Usage & Adoption',
    'P3': 'Business Value',
    'P3_Business': 'Business Value',
    'P4': 'Relationship',
    'P4_Relationship': 'Relationship',
    'P5': 'Growth',
    'P5_Growth': 'Growth'
  };

  return pillarMap[pillar] || pillar.replace(/_/g, ' ');
}
