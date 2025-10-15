/**
 * Playbooks Definitions
 * 
 * Contains the 5 core playbooks:
 * 1. VoC Sprint
 * 2. Activation Blitz  
 * 3. SLA Stabilizer
 * 4. Renewal Safeguard
 * 5. Expansion Timing
 */

import { PlaybookDefinition } from './types';

// Re-export PlaybookDefinition for convenience
export type { PlaybookDefinition } from './types';

export const playbooks: PlaybookDefinition[] = [
  {
    id: 'voc-sprint',
    name: 'VoC Sprint',
    description: 'Rapidly surface value gaps/themes and convert them into actions your execs and product team will stand behind',
    category: 'voc-sprint',
    icon: '🎤',
    color: 'blue',
    estimatedDuration: 1440, // 30 days (4 weeks)
    version: '2.0.0',
    lastUpdated: '2025-10-14',
    author: 'Triad Partners',
    prerequisites: [
      'Customer contact information available',
      'Access to support tickets and QBR notes',
      'Executive stakeholder commitment',
      'NPS/CSAT baseline data available',
      'Health score tracking enabled'
    ],
    successCriteria: [
      'Themes logged and categorized',
      '3 fixes committed with owners assigned',
      '"We heard you" communications sent',
      'NPS follow-up scheduled',
      'NPS improvement +6-10 points',
      'CSAT improvement +0.2-0.3 points',
      'Ticket sentiment improvement',
      'Renewal intent increase'
    ],
    tags: ['customer-feedback', 'sprint', 'value-gaps', 'executive-alignment', 'rapid-execution'],
    steps: [
      {
        id: 'voc-trigger-check',
        title: 'Trigger Assessment',
        description: 'Evaluate VoC Sprint triggers: NPS < 10, CSAT < 3.6, Churn risk ≥ 0.30, Health score drop ≥ 10 pts, or 2+ churn mentions in last quarter',
        type: 'automation',
        status: 'not-started',
        estimatedTime: 15,
        data: {
          triggers: {
            nps_threshold: 10,
            csat_threshold: 3.6,
            churn_risk_threshold: 0.30,
            health_score_drop_threshold: 10,
            churn_mentions_threshold: 2
          }
        }
      },
      {
        id: 'voc-week1-recruit',
        title: 'Week 1: Recruit Sponsor/Users',
        description: 'Identify and recruit 6-10 sponsor users for 30-40 minute interviews. Focus on power users, champions, and at-risk accounts',
        type: 'manual',
        status: 'not-started',
        dependencies: ['voc-trigger-check'],
        estimatedTime: 120
      },
      {
        id: 'voc-week1-interviews',
        title: 'Week 1: Conduct Interviews',
        description: 'Run 30-40 minute structured interviews with recruited users. Focus on value gaps, adoption challenges, and support experience',
        type: 'manual',
        status: 'not-started',
        dependencies: ['voc-week1-recruit'],
        estimatedTime: 300
      },
      {
        id: 'voc-week1-mine-data',
        title: 'Week 1: Mine Tickets & QBR Notes',
        description: 'Analyze last 60 days of support tickets, QBR notes, and customer communications for recurring themes and pain points',
        type: 'action',
        status: 'not-started',
        dependencies: ['voc-week1-interviews'],
        estimatedTime: 180
      },
      {
        id: 'voc-week2-theme-clustering',
        title: 'Week 2: Theme Clustering',
        description: 'Cluster findings into categories: Value gaps, Adoption challenges, Support issues, Roadmap requests. Identify patterns and priorities',
        type: 'action',
        status: 'not-started',
        dependencies: ['voc-week1-mine-data'],
        estimatedTime: 240
      },
      {
        id: 'voc-week2-evidence-gaps',
        title: 'Week 2: Draft Evidence & Quick Wins',
        description: 'Document "evidence of value" gaps with customer quotes and data. Identify quick wins vs. longer-term fixes',
        type: 'manual',
        status: 'not-started',
        dependencies: ['voc-week2-theme-clustering'],
        estimatedTime: 180
      },
      {
        id: 'voc-week3-exec-readout',
        title: 'Week 3: Executive Readout',
        description: 'Present findings to executive team with clear evidence, customer quotes, and recommended actions. Secure commitment for 2-3 fixes',
        type: 'manual',
        status: 'not-started',
        dependencies: ['voc-week2-evidence-gaps'],
        estimatedTime: 90
      },
      {
        id: 'voc-week3-commit-fixes',
        title: 'Week 3: Commit 2-3 Fixes',
        description: 'Secure executive commitment for: 1 "now" fix, 1 "next release" fix, 1 "process" improvement. Assign clear owners and timelines',
        type: 'decision',
        status: 'not-started',
        dependencies: ['voc-week3-exec-readout'],
        estimatedTime: 120
      },
      {
        id: 'voc-week4-action-tracker',
        title: 'Week 4: Publish Action Tracker',
        description: 'Create and publish VoC → Action tracker in QBR format. Include themes, committed fixes, owners, and timelines',
        type: 'manual',
        status: 'not-started',
        dependencies: ['voc-week3-commit-fixes'],
        estimatedTime: 60
      },
      {
        id: 'voc-week4-customer-comms',
        title: 'Week 4: Customer Communications',
        description: 'Send "we heard you" communications to interviewed customers and broader account base. Highlight changes being made',
        type: 'manual',
        status: 'not-started',
        dependencies: ['voc-week4-action-tracker'],
        estimatedTime: 90
      },
      {
        id: 'voc-week4-nps-followup',
        title: 'Week 4: Schedule NPS Follow-up',
        description: 'Schedule NPS follow-up survey for 30-60 days post-implementation. Set up monitoring for CSAT and ticket sentiment',
        type: 'automation',
        status: 'not-started',
        dependencies: ['voc-week4-customer-comms'],
        estimatedTime: 30
      },
      {
        id: 'voc-rag-brief',
        title: 'Generate VoC Sprint Brief',
        description: 'Use RAG to generate comprehensive VoC sprint brief with top 5 themes, customer quotes, and 3 fastest actions with owners',
        type: 'automation',
        status: 'not-started',
        dependencies: ['voc-week4-nps-followup'],
        estimatedTime: 15,
        data: {
          rag_prompt: "Generate a VoC sprint brief for {Account} using last 60 days of notes, tickets, and KPI deltas. List top 5 themes, customer quotes, and the 3 fastest actions with owners.",
          output_format: {
            top_5_themes: "Array of theme objects with evidence",
            customer_quotes: "Direct quotes supporting each theme", 
            fastest_actions: "3 prioritized actions with owners and timelines",
            kpi_impact: "Expected NPS, CSAT, and sentiment improvements"
          }
        }
      }
    ]
  },
  {
    id: 'activation-blitz',
    name: 'Activation Blitz',
    description: 'Compress time-to-value; get more users to first and meaningful outcomes',
    category: 'activation-blitz',
    icon: '🚀',
    color: 'green',
    estimatedDuration: 1440, // 30 days (4 weeks)
    version: '2.0.0',
    lastUpdated: '2025-10-14',
    author: 'Triad Partners',
    prerequisites: [
      'Customer onboarding data available',
      'Feature usage tracking enabled',
      'In-app messaging capabilities',
      'Training materials and use cases prepared',
      'Executive stakeholder commitment'
    ],
    successCriteria: [
      'Two features activated successfully',
      'DAU/MAU ≥ 25%',
      'Adoption index ≥ 60 (or +10 vs. baseline)',
      'Adoption improvement +10-15 points',
      'Active users increase +20-30%',
      'Time-to-value reduction',
      'Two success stories secured for QBR'
    ],
    tags: ['activation', 'time-to-value', 'feature-adoption', 'onboarding', 'user-engagement'],
    steps: [
      {
        id: 'activation-trigger-check',
        title: 'Trigger Assessment',
        description: 'Evaluate Activation Blitz triggers: Adoption index < 60, Active users < 50 or DAU/MAU < 25%, Feature X/Y not used but included in plan',
        type: 'automation',
        status: 'not-started',
        estimatedTime: 15,
        data: {
          triggers: {
            adoption_index_threshold: 60,
            active_users_threshold: 50,
            dau_mau_threshold: 0.25,
            unused_feature_check: true
          }
        }
      },
      {
        id: 'activation-week1-walkthroughs',
        title: 'Week 1: In-App Walkthroughs',
        description: 'Deploy in-app walkthroughs and live office hours targeting 2 "aha" moments per user',
        type: 'automation',
        status: 'not-started',
        dependencies: ['activation-trigger-check'],
        estimatedTime: 120
      },
      {
        id: 'activation-week1-office-hours',
        title: 'Week 1: Live Office Hours',
        description: 'Schedule and conduct live office hours for hands-on support and Q&A sessions',
        type: 'manual',
        status: 'not-started',
        dependencies: ['activation-week1-walkthroughs'],
        estimatedTime: 180
      },
      {
        id: 'activation-week2-role-training',
        title: 'Week 2: Role-Based Training',
        description: 'Conduct role-based training sessions for power users and viewers with specific use cases',
        type: 'manual',
        status: 'not-started',
        dependencies: ['activation-week1-office-hours'],
        estimatedTime: 240
      },
      {
        id: 'activation-week2-kpi-cases',
        title: 'Week 2: Publish KPI-Aligned Use Cases',
        description: 'Create and publish 3 KPI-aligned use cases showing clear value demonstration',
        type: 'manual',
        status: 'not-started',
        dependencies: ['activation-week2-role-training'],
        estimatedTime: 180
      },
      {
        id: 'activation-week3-exec-checkpoint',
        title: 'Week 3: Executive Checkpoint',
        description: 'Present executive checkpoint with value story including before/after screenshots and KPI improvements',
        type: 'manual',
        status: 'not-started',
        dependencies: ['activation-week2-kpi-cases'],
        estimatedTime: 90
      },
      {
        id: 'activation-week4-nudge-campaign',
        title: 'Week 4: Nudge Campaign',
        description: 'Launch targeted nudge campaign to non-adopters with personalized activation paths',
        type: 'automation',
        status: 'not-started',
        dependencies: ['activation-week3-exec-checkpoint'],
        estimatedTime: 120
      },
      {
        id: 'activation-week4-success-stories',
        title: 'Week 4: Secure Success Stories',
        description: 'Identify and secure 2 success stories from activated users for QBR presentation',
        type: 'manual',
        status: 'not-started',
        dependencies: ['activation-week4-nudge-campaign'],
        estimatedTime: 150
      },
      {
        id: 'activation-rag-plan',
        title: 'Generate Activation Plan',
        description: 'Use RAG to generate comprehensive 4-week activation plan with in-app steps, emails, and KPIs',
        type: 'automation',
        status: 'not-started',
        dependencies: ['activation-week4-success-stories'],
        estimatedTime: 15,
        data: {
          rag_prompt: "Given {Account}'s low adoption and usage metrics, propose a 4-week activation plan with in-app steps, emails, and two KPIs to prove value by day 30.",
          output_format: {
            activation_plan: "4-week structured activation plan",
            in_app_steps: "Detailed in-app onboarding steps",
            email_sequence: "Targeted email campaign sequence",
            kpi_targets: "Two specific KPIs to prove value",
            success_metrics: "Day 30 success measurement criteria"
          }
        }
      }
    ]
  },
  {
    id: 'sla-stabilizer',
    name: 'SLA Stabilizer',
    description: 'Rapid SLA recovery and process stabilization to prevent future breaches',
    category: 'sla-stabilizer',
    icon: '⚡',
    color: 'orange',
    estimatedDuration: 720, // 14 days (2 weeks)
    version: '2.0.0',
    lastUpdated: '2025-10-14',
    author: 'Triad Partners',
    prerequisites: [
      'SLA metrics tracking enabled',
      'Support ticket system access',
      'Escalation procedures defined',
      'Support team capacity data',
      'Customer communication channels'
    ],
    successCriteria: [
      'SLA compliance restored to > 95%',
      'Response time < 2 hours (or agreed target)',
      'Resolution time improved by 30%',
      'Ticket reopen rate < 10%',
      'Customer satisfaction with support > 4.0/5',
      'Escalation reduction by 50%'
    ],
    tags: ['sla', 'support', 'quality', 'recovery', 'rapid-response'],
    steps: [
      {
        id: 'sla-trigger-check',
        title: 'Trigger Assessment',
        description: 'Evaluate SLA Stabilizer triggers: SLA breaches > 5 in 30 days, Response time > 2x target, Escalations increasing, Reopen rate > 20%',
        type: 'automation',
        status: 'not-started',
        estimatedTime: 15,
        data: {
          triggers: {
            sla_breach_threshold: 5,
            response_time_multiplier: 2.0,
            escalation_trend: 'increasing',
            reopen_rate_threshold: 0.20
          }
        }
      },
      {
        id: 'sla-week1-audit',
        title: 'Week 1: SLA Breach Root Cause Analysis',
        description: 'Analyze all SLA breaches in last 60 days, categorize by root cause (volume, complexity, staffing, process)',
        type: 'action',
        status: 'not-started',
        dependencies: ['sla-trigger-check'],
        estimatedTime: 120
      },
      {
        id: 'sla-week1-capacity',
        title: 'Week 1: Support Capacity Assessment',
        description: 'Review support team capacity, ticket routing, and workload distribution',
        type: 'action',
        status: 'not-started',
        dependencies: ['sla-week1-audit'],
        estimatedTime: 90
      },
      {
        id: 'sla-week1-immediate-actions',
        title: 'Week 1: Deploy Immediate Actions',
        description: 'Implement top 3 quick fixes: automated responses, ticket routing optimization, emergency staffing',
        type: 'action',
        status: 'not-started',
        dependencies: ['sla-week1-capacity'],
        estimatedTime: 180
      },
      {
        id: 'sla-week2-monitoring',
        title: 'Week 2: Real-Time Monitoring Dashboard',
        description: 'Deploy SLA monitoring dashboard with real-time alerts and predictive breach warnings',
        type: 'automation',
        status: 'not-started',
        dependencies: ['sla-week1-immediate-actions'],
        estimatedTime: 120
      },
      {
        id: 'sla-week2-escalation',
        title: 'Week 2: Escalation Process Refinement',
        description: 'Update escalation procedures with clear thresholds, owners, and response timelines',
        type: 'manual',
        status: 'not-started',
        dependencies: ['sla-week2-monitoring'],
        estimatedTime: 90
      },
      {
        id: 'sla-week2-customer-comms',
        title: 'Week 2: Customer Communications',
        description: 'Communicate SLA improvements to affected customers with new commitments and direct contacts',
        type: 'manual',
        status: 'not-started',
        dependencies: ['sla-week2-escalation'],
        estimatedTime: 60
      },
      {
        id: 'sla-week2-validation',
        title: 'Week 2: SLA Compliance Validation',
        description: 'Measure and validate SLA compliance improvement, response times, and customer satisfaction',
        type: 'action',
        status: 'not-started',
        dependencies: ['sla-week2-customer-comms'],
        estimatedTime: 60
      },
      {
        id: 'sla-rag-analysis',
        title: 'Generate SLA Recovery Analysis',
        description: 'Use RAG to analyze SLA breach patterns and generate comprehensive stabilization recommendations',
        type: 'automation',
        status: 'not-started',
        dependencies: ['sla-week2-validation'],
        estimatedTime: 15,
        data: {
          rag_prompt: "Analyze {Account}'s SLA breach patterns from last 60 days. Identify top 3 root causes with frequency, recommend 3 preventive measures with implementation steps, and predict SLA compliance improvement timeline with milestones.",
          output_format: {
            root_causes: "Top 3 root causes with frequency and impact analysis",
            preventive_measures: "3 specific preventive measures with detailed implementation steps",
            compliance_prediction: "Expected SLA compliance improvement timeline with key milestones",
            resource_recommendations: "Support team resource optimization and capacity recommendations"
          }
        }
      }
    ]
  },
  {
    id: 'renewal-safeguard',
    name: 'Renewal Safeguard',
    description: 'Proactive 90-day renewal risk mitigation and value demonstration campaign',
    category: 'renewal-safeguard',
    icon: '🛡️',
    color: 'red',
    estimatedDuration: 2880, // 90 days (12 weeks)
    version: '2.0.0',
    lastUpdated: '2025-10-14',
    author: 'Triad Partners',
    prerequisites: [
      'Renewal date within 90 days',
      'Customer health scores available',
      'Usage analytics accessible',
      'Executive relationships established',
      'Business case template ready'
    ],
    successCriteria: [
      'Renewal secured or timeline extended',
      'Health score improved by 15+ points',
      'Executive engagement restored',
      'ROI documented and validated',
      'Business case presented and approved',
      'Contract terms negotiated'
    ],
    tags: ['renewal', 'retention', 'risk-mitigation', 'value-demonstration', '90-day'],
    steps: [
      {
        id: 'renewal-trigger-check',
        title: 'Trigger Assessment',
        description: 'Evaluate Renewal Safeguard triggers: Renewal within 90 days AND (Health < 70 OR Engagement declining OR Budget concerns OR Champion departed)',
        type: 'automation',
        status: 'not-started',
        estimatedTime: 15,
        data: {
          triggers: {
            renewal_window_days: 90,
            health_score_threshold: 70,
            engagement_trend: 'declining',
            budget_risk: true,
            champion_status: 'departed'
          }
        }
      },
      {
        id: 'renewal-day1-assessment',
        title: 'Day 1-7: Comprehensive Risk Assessment',
        description: 'Complete renewal risk assessment: health score, usage trends, stakeholder sentiment, competitive threats, budget status',
        type: 'action',
        status: 'not-started',
        dependencies: ['renewal-trigger-check'],
        estimatedTime: 180
      },
      {
        id: 'renewal-day7-stakeholder-map',
        title: 'Day 7-14: Stakeholder Mapping & Re-engagement',
        description: 'Map all stakeholders, identify champions and detractors, schedule executive meetings',
        type: 'manual',
        status: 'not-started',
        dependencies: ['renewal-day1-assessment'],
        estimatedTime: 240
      },
      {
        id: 'renewal-day14-value-analysis',
        title: 'Day 14-30: Value Realization Analysis',
        description: 'Document achieved ROI, usage patterns, business outcomes, and unrealized value opportunities',
        type: 'action',
        status: 'not-started',
        dependencies: ['renewal-day7-stakeholder-map'],
        estimatedTime: 300
      },
      {
        id: 'renewal-day30-business-case',
        title: 'Day 30-45: Build Renewal Business Case',
        description: 'Create comprehensive business case: ROI achieved, future value projection, expansion opportunities',
        type: 'manual',
        status: 'not-started',
        dependencies: ['renewal-day14-value-analysis'],
        estimatedTime: 240
      },
      {
        id: 'renewal-day45-exec-presentation',
        title: 'Day 45-60: Executive Business Review',
        description: 'Present business case to executive team, address concerns, demonstrate continued value',
        type: 'manual',
        status: 'not-started',
        dependencies: ['renewal-day30-business-case'],
        estimatedTime: 120
      },
      {
        id: 'renewal-day60-negotiation',
        title: 'Day 60-75: Contract Negotiation',
        description: 'Negotiate renewal terms, pricing, expansion options, and multi-year commitments',
        type: 'decision',
        status: 'not-started',
        dependencies: ['renewal-day45-exec-presentation'],
        estimatedTime: 180
      },
      {
        id: 'renewal-day75-finalization',
        title: 'Day 75-90: Contract Finalization',
        description: 'Finalize contract terms, secure signatures, plan success celebration and future roadmap',
        type: 'manual',
        status: 'not-started',
        dependencies: ['renewal-day60-negotiation'],
        estimatedTime: 120
      },
      {
        id: 'renewal-rag-strategy',
        title: 'Generate Renewal Strategy',
        description: 'Use RAG to analyze renewal risk factors and generate personalized retention strategy',
        type: 'automation',
        status: 'not-started',
        dependencies: ['renewal-day75-finalization'],
        estimatedTime: 15,
        data: {
          rag_prompt: "Analyze {Account}'s renewal risk profile including health score trends, engagement patterns, and competitive signals from last 90 days. Generate a personalized retention strategy with 5 specific actions, expected outcomes, and contingency plans for contract negotiation.",
          output_format: {
            risk_analysis: "Comprehensive risk factor analysis with likelihood scores",
            retention_actions: "5 prioritized retention actions with timelines and owners",
            value_proposition: "Customized value proposition based on achieved outcomes",
            negotiation_strategy: "Contract negotiation approach with pricing and terms recommendations",
            contingency_plans: "Backup strategies if primary approach fails"
          }
        }
      }
    ]
  },
  {
    id: 'expansion-timing',
    name: 'Expansion Timing',
    description: 'Strategic expansion opportunity identification and optimal timing analysis for upsell/cross-sell',
    category: 'expansion-timing',
    icon: '📈',
    color: 'purple',
    estimatedDuration: 1440, // 30 days (4 weeks)
    version: '2.0.0',
    lastUpdated: '2025-10-14',
    author: 'Triad Partners',
    prerequisites: [
      'High customer health score (> 80)',
      'Usage analytics accessible',
      'Product catalog and pricing ready',
      'Executive relationships established',
      'Budget cycle timing known'
    ],
    successCriteria: [
      'Expansion opportunity identified and qualified',
      'Business case presented to customer',
      'Expansion proposal submitted',
      'Revenue expansion > 20%',
      'Customer satisfaction maintained or improved',
      'Implementation plan agreed'
    ],
    tags: ['expansion', 'growth', 'upsell', 'cross-sell', 'revenue-growth'],
    steps: [
      {
        id: 'expansion-trigger-check',
        title: 'Trigger Assessment',
        description: 'Evaluate Expansion Timing triggers: Health score > 80, Adoption > 85%, Usage approaching limits, Budget window open, or Strategic initiative alignment',
        type: 'automation',
        status: 'not-started',
        estimatedTime: 15,
        data: {
          triggers: {
            health_score_threshold: 80,
            adoption_threshold: 85,
            usage_limit_percentage: 0.80,
            budget_window: 'Q1_Q4',
            strategic_alignment: true
          }
        }
      },
      {
        id: 'expansion-week1-usage-analysis',
        title: 'Week 1: Usage Pattern & Growth Analysis',
        description: 'Analyze usage trends, feature adoption, user growth, and capacity utilization to identify expansion signals',
        type: 'action',
        status: 'not-started',
        dependencies: ['expansion-trigger-check'],
        estimatedTime: 120
      },
      {
        id: 'expansion-week1-whitespace',
        title: 'Week 1: Whitespace & Adjacent Use Case Mapping',
        description: 'Identify adjacent use cases, cross-sell opportunities, and unmet needs within the account',
        type: 'action',
        status: 'not-started',
        dependencies: ['expansion-week1-usage-analysis'],
        estimatedTime: 180
      },
      {
        id: 'expansion-week2-roi-analysis',
        title: 'Week 2: ROI & Value Quantification',
        description: 'Document current ROI achieved, calculate incremental value from expansion, build financial justification',
        type: 'manual',
        status: 'not-started',
        dependencies: ['expansion-week1-whitespace'],
        estimatedTime: 240
      },
      {
        id: 'expansion-week2-business-case',
        title: 'Week 2: Expansion Business Case Development',
        description: 'Create compelling expansion business case with ROI projections, use cases, and implementation timeline',
        type: 'manual',
        status: 'not-started',
        dependencies: ['expansion-week2-roi-analysis'],
        estimatedTime: 180
      },
      {
        id: 'expansion-week3-stakeholder-alignment',
        title: 'Week 3: Executive Stakeholder Alignment',
        description: 'Socialize expansion opportunity with executive sponsors, validate budget availability and strategic fit',
        type: 'manual',
        status: 'not-started',
        dependencies: ['expansion-week2-business-case'],
        estimatedTime: 120
      },
      {
        id: 'expansion-week3-proposal',
        title: 'Week 3: Expansion Proposal Presentation',
        description: 'Present formal expansion proposal to decision-makers with pricing, timeline, and expected outcomes',
        type: 'manual',
        status: 'not-started',
        dependencies: ['expansion-week3-stakeholder-alignment'],
        estimatedTime: 90
      },
      {
        id: 'expansion-week4-negotiation',
        title: 'Week 4: Terms Negotiation & Closing',
        description: 'Negotiate expansion terms, finalize pricing and scope, secure contract signatures',
        type: 'decision',
        status: 'not-started',
        dependencies: ['expansion-week3-proposal'],
        estimatedTime: 180
      },
      {
        id: 'expansion-week4-implementation',
        title: 'Week 4: Implementation Planning',
        description: 'Create detailed implementation plan with milestones, resources, and success metrics',
        type: 'manual',
        status: 'not-started',
        dependencies: ['expansion-week4-negotiation'],
        estimatedTime: 120
      },
      {
        id: 'expansion-rag-strategy',
        title: 'Generate Expansion Strategy',
        description: 'Use RAG to analyze expansion readiness signals and generate optimal timing and approach strategy',
        type: 'automation',
        status: 'not-started',
        dependencies: ['expansion-week4-implementation'],
        estimatedTime: 15,
        data: {
          rag_prompt: "Analyze {Account}'s expansion readiness including adoption rates, usage growth, feature utilization, and strategic initiatives. Identify the optimal expansion opportunity (upsell/cross-sell), timing window, and approach strategy. Include pricing recommendations and expected revenue impact.",
          output_format: {
            expansion_opportunity: "Specific expansion opportunity with product/feature recommendations",
            readiness_score: "Expansion readiness score (0-100) with supporting metrics",
            timing_recommendation: "Optimal timing window with justification",
            approach_strategy: "Recommended approach and messaging for expansion conversation",
            revenue_projection: "Expected revenue impact and expansion ROI",
            risk_factors: "Potential obstacles and mitigation strategies"
          }
        }
      }
    ]
  }
];

// Helper functions
export function getPlaybookById(id: string): PlaybookDefinition | undefined {
  return playbooks.find(playbook => playbook.id === id);
}

export function getPlaybooksByCategory(category: string): PlaybookDefinition[] {
  return playbooks.filter(playbook => playbook.category === category);
}

export function getPlaybooksByTag(tag: string): PlaybookDefinition[] {
  return playbooks.filter(playbook => playbook.tags.includes(tag));
}
