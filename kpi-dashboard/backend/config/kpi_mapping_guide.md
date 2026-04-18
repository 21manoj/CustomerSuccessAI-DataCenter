# KPI Mapping Guide — CS Pulse Onboarding

How to map your existing metrics to CS Pulse KPI codes for `kpi_measurements.csv`.

## How it works

CS Pulse uses a 5-pillar, 38-KPI framework. You don't need all 38 — start with the KPIs you already track. The platform auto-adjusts weights for missing KPIs.

**Minimum recommended: 9 KPIs** (Starter tier) — at least 1-2 per pillar.

## CSV format

```csv
source_account_id,kpi_code,measured_at,value,target
ACCT-001,P1-KPI1,2026-01-01,14,10
ACCT-001,P2-KPI4,2026-01-01,99.2,99.5
```

## Pillar 1: Deployment Velocity

*How fast are customers getting value from your product?*

| KPI Code | Name | Unit | Your metric might be called... |
|----------|------|------|-------------------------------|
| P1-KPI1 | Time-to-First-Workload | days | Time to value, TTFV, onboarding time, days to first use, activation time |
| P1-KPI2 | Installation Completion Rate | % | Setup completion %, onboarding completion, provisioning success rate |
| P1-KPI3 | Configuration Accuracy | % | Setup accuracy, config error rate (invert), first-time-right % |
| P1-KPI4 | Deployment Cycle Time | days | Implementation time, go-live duration, project delivery time |
| P1-KPI5 | Hardware Commissioning Time | days | Provisioning time, environment setup time, infrastructure readiness |
| P1-KPI6 | Network Readiness Score | % | Integration health, connectivity score, API readiness |
| P1-KPI7 | Deployment Team Velocity | servers/day | Throughput, units deployed/week, seats provisioned/day |
| P1-KPI8 | Documentation Completeness | % | Runbook coverage, knowledge base completeness |

**Start with**: P1-KPI1 (TTFV) + P1-KPI2 (completion rate)

## Pillar 2: Operational Stability

*Is the product running reliably for this customer?*

| KPI Code | Name | Unit | Your metric might be called... |
|----------|------|------|-------------------------------|
| P2-KPI1 | RMA Frequency Rate | % | Defect rate, hardware failure rate, return rate |
| P2-KPI2 | MTBF | hours | Mean time between failures, reliability score, uptime streak |
| P2-KPI3 | Critical Incidents (30d) | count | P1 tickets, severity 1 incidents, outages/month |
| P2-KPI4 | System Uptime | % | Availability, SLA compliance, uptime % |
| P2-KPI5 | Thermal Management Score | % | Environmental health, facility score, infrastructure health |
| P2-KPI6 | Power Efficiency (PUE) | ratio | Resource efficiency, cost per unit, overhead ratio |
| P2-KPI7 | MTTR | hours | Mean time to repair, resolution time, incident duration |
| P2-KPI8 | Preventive Maintenance | % | Maintenance compliance, scheduled upkeep completion |

**Start with**: P2-KPI3 (incidents) + P2-KPI4 (uptime)

## Pillar 3: AI Workload Performance

*Is the customer getting value from what they're using?*

| KPI Code | Name | Unit | Your metric might be called... |
|----------|------|------|-------------------------------|
| P3-KPI1 | GPU Utilization Rate | % | Feature adoption, DAU/MAU, active usage %, seat utilization |
| P3-KPI2 | Training Job Completion Rate | % | Task success rate, workflow completion, job success % |
| P3-KPI3 | Inference Latency (P95) | ms | Response time, API latency, page load time |
| P3-KPI4 | Model Training Time | hours | Processing time, batch duration, execution time |
| P3-KPI5 | GPU Memory Efficiency | % | Resource efficiency, memory utilization, capacity usage |
| P3-KPI6 | Distributed Training Efficiency | % | Scaling efficiency, multi-node performance |
| P3-KPI7 | Workload Diversity Score | count | Feature breadth, modules used, use case count |
| P3-KPI8 | Batch Processing Throughput | samples/hr | Processing volume, transactions/hour, throughput |

**Start with**: P3-KPI1 (utilization) + P3-KPI2 (completion rate)

## Pillar 4: Channel & Partner Health

*How healthy is the partner/channel relationship?*

| KPI Code | Name | Unit | Your metric might be called... |
|----------|------|------|-------------------------------|
| P4-KPI1 | Partner Engagement Score | score | Partner health, channel engagement, partner NPS |
| P4-KPI2 | VAR Performance Rating | score | Partner quality, reseller rating, channel performance |
| P4-KPI3 | Joint QBR Frequency | count | Meeting cadence, review frequency, touchpoints/quarter |
| P4-KPI4 | Channel Conflict Score | score | Conflict rate, overlap incidents, territory disputes |
| P4-KPI5 | Co-selling Opportunities | count | Joint pipeline, partner-sourced deals, co-sell volume |
| P4-KPI6 | Partner NPS | score | Partner satisfaction, channel CSAT |

**Start with**: P4-KPI1 (engagement) + P4-KPI3 (QBR frequency)

## Pillar 5: Expansion Readiness

*Is this customer likely to grow?*

| KPI Code | Name | Unit | Your metric might be called... |
|----------|------|------|-------------------------------|
| P5-KPI1 | Capacity Utilization Rate | % | Usage %, license consumption, seat fill rate |
| P5-KPI2 | Capacity Utilization Trajectory | % change | Usage trend, growth rate, consumption velocity |
| P5-KPI3 | Workload Growth Velocity | % change | MRR growth, ARR expansion rate, usage growth |
| P5-KPI4 | Compute Hour Consumption Trend | % change | Consumption trend, volume trajectory |
| P5-KPI5 | Budget Availability Signals | score | Budget health, procurement readiness, spend capacity |
| P5-KPI6 | New Use Case Adoption | count | New features adopted, modules activated, expansion breadth |
| P5-KPI7 | Expansion Probability (90d) | % | Upsell likelihood, growth probability, expansion score |
| P5-KPI8 | Technical Champion Engagement | score | Champion health, advocate engagement, power user activity |

**Start with**: P5-KPI1 (utilization) + P5-KPI7 (expansion probability)

## Starter 9 KPIs (recommended minimum)

If you only have a few metrics, map them to these 9:

| Code | What to map | Why it matters |
|------|------------|---------------|
| P1-KPI1 | Time to value / onboarding days | Predicts early churn |
| P1-KPI2 | Setup completion rate | Deployment health |
| P2-KPI3 | P1 incidents / month | Operational risk |
| P2-KPI4 | Uptime / availability % | SLA compliance |
| P3-KPI1 | Usage / adoption rate | Value realization |
| P3-KPI2 | Task/workflow success rate | Product stickiness |
| P4-KPI1 | Partner engagement score | Channel health |
| P5-KPI1 | Capacity / license utilization | Expansion signal |
| P5-KPI7 | Expansion probability | Growth forecast |

## Tips

- **Don't have an exact match?** Use the closest metric. GPU Utilization (P3-KPI1) maps to any "adoption rate" or "active usage %" metric.
- **Inverse metrics**: If your metric is "error rate" (lower = better), invert it: `100 - error_rate` → map to the corresponding positive KPI.
- **Missing a pillar entirely?** That's OK. The platform re-weights the remaining pillars. But health scores will be less accurate for that dimension.
- **Targets**: If you provide `target` values, health scoring is more precise. Without targets, the platform uses industry benchmarks.
- **Monthly cadence**: KPIs should be measured monthly. Weekly data gets aggregated to monthly averages.
