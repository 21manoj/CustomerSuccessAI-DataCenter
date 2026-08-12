/**
 * CSM Dashboard Mock Data — used as fallback when APIs are unreachable.
 * Provides a realistic demo experience without a running backend.
 */

export const MOCK_ACCOUNTS = [
  { account_id: 1001, account_name: 'Matterhorn AI Labs', health_score: 38, trend: -5, arr: 4200000, status: 'active', renewal_date: '2026-06-15', classification: 'critical' },
  { account_id: 1002, account_name: 'K2 Computing', health_score: 44, trend: -8, arr: 6800000, status: 'active', renewal_date: '2026-04-22', classification: 'critical' },
  { account_id: 1003, account_name: 'Denali DataWorks', health_score: 55, trend: 3, arr: 3100000, status: 'active', renewal_date: '2026-08-10', classification: 'at_risk' },
  { account_id: 1004, account_name: 'Everest Cloud Systems', health_score: 62, trend: -2, arr: 8500000, status: 'active', renewal_date: '2026-05-30', classification: 'at_risk' },
  { account_id: 1005, account_name: 'Kilimanjaro Inference', health_score: 58, trend: 1, arr: 2900000, status: 'active', renewal_date: '2026-09-18', classification: 'at_risk' },
  { account_id: 1006, account_name: 'Rainier GPU Cluster', health_score: 78, trend: 4, arr: 5400000, status: 'active', renewal_date: '2026-07-01', classification: 'healthy' },
  { account_id: 1007, account_name: 'Fuji Neural Networks', health_score: 85, trend: 2, arr: 7200000, status: 'active', renewal_date: '2026-11-05', classification: 'healthy' },
  { account_id: 1008, account_name: 'Elbrus Training Co', health_score: 91, trend: 6, arr: 4800000, status: 'active', renewal_date: '2026-12-20', classification: 'healthy' },
];

export const MOCK_ACTIONS = [
  {
    rank: 1, account_id: 1002, account_name: 'K2 Computing', playbook_id: 'PB-01',
    action: 'Initiate emergency churn prevention — health dropped 8 pts, renewal in 23 days',
    urgency: 'critical' as const, estimated_hours: 4, projected_impact: 680000,
    metric_id: 'churn_risk', arr: 6800000, health_score: 44, churn_risk: 72,
  },
  {
    rank: 2, account_id: 1001, account_name: 'Matterhorn AI Labs', playbook_id: 'PB-02',
    action: 'Champion recovery — VP Eng left last month, no replacement identified',
    urgency: 'critical' as const, estimated_hours: 3, projected_impact: 420000,
    metric_id: 'exec_sponsor_change', arr: 4200000, health_score: 38, churn_risk: 68,
  },
  {
    rank: 3, account_id: 1004, account_name: 'Everest Cloud Systems', playbook_id: 'PB-03',
    action: 'Schedule QBR — GPU utilization dropped to 52%, engagement declining',
    urgency: 'high' as const, estimated_hours: 2, projected_impact: 340000,
    metric_id: 'silent_churn', arr: 8500000, health_score: 62, churn_risk: 45,
  },
  {
    rank: 4, account_id: 1003, account_name: 'Denali DataWorks', playbook_id: 'PB-06',
    action: 'Send ROI report ahead of renewal — demonstrate 18% efficiency gain',
    urgency: 'medium' as const, estimated_hours: 1.5, projected_impact: 155000,
    metric_id: 'NRR', arr: 3100000, health_score: 55,
  },
  {
    rank: 5, account_id: 1008, account_name: 'Elbrus Training Co', playbook_id: 'PB-05',
    action: 'Expansion opportunity — capacity at 88%, training for next GPU cluster',
    urgency: 'opportunity' as const, estimated_hours: 2, projected_impact: 960000,
    metric_id: 'expansion_rate', arr: 4800000, health_score: 91,
  },
];

export const MOCK_APPROVALS = [
  {
    id: 'appr-1', playbook_id: 'PB-01', playbook_name: 'Churn Prevention Sprint',
    account_id: 1002, account_name: 'K2 Computing',
    projected_impact: 680000, requested_by: 'CS Pulse AI', requested_at: '2026-03-29T14:30:00Z', status: 'pending' as const,
  },
  {
    id: 'appr-2', playbook_id: 'PB-05', playbook_name: 'Expansion Opportunity',
    account_id: 1008, account_name: 'Elbrus Training Co',
    projected_impact: 960000, requested_by: 'CS Pulse AI', requested_at: '2026-03-29T10:15:00Z', status: 'pending' as const,
  },
];

export const MOCK_ACCOUNT_DETAIL = {
  1001: {
    account_id: 1001, account_name: 'Matterhorn AI Labs', health_score: 38, trend: -5,
    pillar_scores: { P1: 52, P2: 35, P3: 28, P4: 45, P5: 30, P6: 30 },
    champion: { name: 'Position Vacant', title: 'VP Engineering (departed)', last_contact_days: 35 },
    contract: { arr: 4200000, renewal_date: '2026-06-15' },
    signals: [
      { date: '2026-03-25', summary: 'VP Engineering resigned — no successor identified', type: 'exec_sponsor_change' },
      { date: '2026-03-18', summary: 'GPU utilization dropped to 32% (was 68%)', type: 'kpi_decline' },
      { date: '2026-03-10', summary: '3 P1 tickets open > 48 hours', type: 'escalation' },
    ],
    open_tickets: 5,
  },
  1002: {
    account_id: 1002, account_name: 'K2 Computing', health_score: 44, trend: -8,
    pillar_scores: { P1: 60, P2: 42, P3: 38, P4: 50, P5: 35, P6: 35 },
    champion: { name: 'Sarah Chen', title: 'CTO', last_contact_days: 14 },
    contract: { arr: 6800000, renewal_date: '2026-04-22' },
    signals: [
      { date: '2026-03-28', summary: 'Renewal at risk — competitor POC in progress', type: 'competitive_displacement' },
      { date: '2026-03-20', summary: 'Training job completion rate fell to 71%', type: 'kpi_decline' },
    ],
    open_tickets: 3,
  },
  1004: {
    account_id: 1004, account_name: 'Everest Cloud Systems', health_score: 62, trend: -2,
    pillar_scores: { P1: 72, P2: 65, P3: 55, P4: 58, P5: 60, P6: 60 },
    champion: { name: 'James Park', title: 'Director of AI Infrastructure', last_contact_days: 21 },
    contract: { arr: 8500000, renewal_date: '2026-05-30' },
    signals: [
      { date: '2026-03-22', summary: 'QBR missed — rescheduled twice', type: 'silent_churn' },
    ],
    open_tickets: 1,
  },
  1008: {
    account_id: 1008, account_name: 'Elbrus Training Co', health_score: 91, trend: 6,
    pillar_scores: { P1: 88, P2: 92, P3: 95, P4: 85, P5: 90, P6: 90 },
    champion: { name: 'Maria Volkov', title: 'Head of ML Platform', last_contact_days: 3 },
    contract: { arr: 4800000, renewal_date: '2026-12-20' },
    signals: [
      { date: '2026-03-28', summary: 'Capacity utilization hit 88% — expansion discussion started', type: 'expansion_signal' },
      { date: '2026-03-15', summary: 'Signed 2-year renewal early', type: 'positive' },
    ],
    open_tickets: 0,
  },
};

export const MOCK_RECOMMENDATIONS: Record<number, Array<{ playbook_id: string; playbook_name: string; description: string; projected_impact: number }>> = {
  1001: [
    { playbook_id: 'PB-02', playbook_name: 'Champion Recovery', description: 'Identify and onboard new executive sponsor', projected_impact: 420000 },
    { playbook_id: 'PB-01', playbook_name: 'Churn Prevention Sprint', description: 'Rapid engagement cadence with escalation path', projected_impact: 336000 },
  ],
  1002: [
    { playbook_id: 'PB-01', playbook_name: 'Churn Prevention Sprint', description: 'Competitive displacement defense — demonstrate unique value', projected_impact: 680000 },
  ],
  1004: [
    { playbook_id: 'PB-03', playbook_name: 'Executive Business Review', description: 'Re-engage executive sponsor with ROI narrative', projected_impact: 340000 },
  ],
  1008: [
    { playbook_id: 'PB-05', playbook_name: 'Expansion Opportunity', description: 'Next GPU cluster sizing and commercial proposal', projected_impact: 960000 },
  ],
};
