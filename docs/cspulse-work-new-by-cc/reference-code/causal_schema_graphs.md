# Learned causal schema vs. hand-authored templates

## Ground truth (latents shown dashed)

```mermaid
graph LR
  L_org_restructure((L_org_restructure)) -.-> champion_change[champion_change]
  L_org_restructure((L_org_restructure)) -.-> exec_sponsor_change[exec_sponsor_change]
  L_business_decline((L_business_decline)) -.-> budget_pressure[budget_pressure]
  L_business_decline((L_business_decline)) -.-> usage_decline[usage_decline]
  champion_change[champion_change] --> engagement_gap[engagement_gap]
  engagement_gap[engagement_gap] --> usage_decline[usage_decline]
  usage_decline[usage_decline] --> reserved_cluster_idle[reserved_cluster_idle]
  critical_incident[critical_incident] --> support_escalation[support_escalation]
  sla_breach[sla_breach] --> support_escalation[support_escalation]
  sla_breach[sla_breach] --> mttr_regression[mttr_regression]
  budget_pressure[budget_pressure] --> competitor_mention[competitor_mention]
  usage_decline[usage_decline] --> competitor_mention[competitor_mention]
  competitor_mention[competitor_mention] --> churn[churn]
  engagement_gap[engagement_gap] --> churn[churn]
  adoption_milestone[adoption_milestone] --> expansion_interest[expansion_interest]
  expansion_interest[expansion_interest] --> renewal_secured[renewal_secured]
  adoption_milestone[adoption_milestone] --> renewal_secured[renewal_secured]
```

## TEMPLATE — what ships today

```mermaid
graph LR
  champion_change[champion_change] -->|0.8| exec_sponsor_change[exec_sponsor_change]  %% WRONG
  champion_change[champion_change] -->|0.85| engagement_gap[engagement_gap]
  engagement_gap[engagement_gap] -->|0.8| usage_decline[usage_decline]
  usage_decline[usage_decline] -->|0.75| churn[churn]  %% WRONG
  budget_pressure[budget_pressure] -->|0.7| usage_decline[usage_decline]  %% WRONG
  support_escalation[support_escalation] -->|0.65| critical_incident[critical_incident]  %% WRONG
  competitor_mention[competitor_mention] -->|0.85| churn[churn]
  adoption_milestone[adoption_milestone] -->|0.72| renewal_secured[renewal_secured]
  sla_breach[sla_breach] -->|0.6| churn[churn]  %% WRONG
```

Every edge directed, every edge with a typed confidence, no abstentions.

## PC-stable — CPDAG

```mermaid
graph LR
  champion_change[champion_change] --- exec_sponsor_change[exec_sponsor_change]
  champion_change[champion_change] --- engagement_gap[engagement_gap]
  engagement_gap[engagement_gap] --- usage_decline[usage_decline]
  engagement_gap[engagement_gap] --- churn[churn]
  budget_pressure[budget_pressure] --> usage_decline[usage_decline]
  budget_pressure[budget_pressure] --- competitor_mention[competitor_mention]
  usage_decline[usage_decline] --> reserved_cluster_idle[reserved_cluster_idle]
  usage_decline[usage_decline] --- competitor_mention[competitor_mention]
  critical_incident[critical_incident] --> support_escalation[support_escalation]
  sla_breach[sla_breach] --> support_escalation[support_escalation]
  sla_breach[sla_breach] --- mttr_regression[mttr_regression]
  competitor_mention[competitor_mention] --> churn[churn]
  adoption_milestone[adoption_milestone] --- expansion_interest[expansion_interest]
  adoption_milestone[adoption_milestone] --- renewal_secured[renewal_secured]
  expansion_interest[expansion_interest] --- renewal_secured[renewal_secured]
```

Solid arrows = oriented. Plain lines = **related, direction not identifiable**.

## FCI — PAG

```mermaid
graph LR
  champion_change[champion_change] --> exec_sponsor_change[exec_sponsor_change]
  engagement_gap[engagement_gap] --> champion_change[champion_change]
  engagement_gap[engagement_gap] -.->|latent confounder| usage_decline[usage_decline]
  engagement_gap[engagement_gap] -.->|latent confounder| churn[churn]
  budget_pressure[budget_pressure] -.->|confounding not ruled out| usage_decline[usage_decline]
  budget_pressure[budget_pressure] --- competitor_mention[competitor_mention]
  usage_decline[usage_decline] --> reserved_cluster_idle[reserved_cluster_idle]
  usage_decline[usage_decline] --> competitor_mention[competitor_mention]
  critical_incident[critical_incident] -.->|confounding not ruled out| support_escalation[support_escalation]
  sla_breach[sla_breach] -.->|confounding not ruled out| support_escalation[support_escalation]
  sla_breach[sla_breach] --- mttr_regression[mttr_regression]
  competitor_mention[competitor_mention] -.->|confounding not ruled out| churn[churn]
  adoption_milestone[adoption_milestone] --- expansion_interest[expansion_interest]
  adoption_milestone[adoption_milestone] --- renewal_secured[renewal_secured]
  expansion_interest[expansion_interest] --- renewal_secured[renewal_secured]
```

Dotted = FCI cannot rule out an unmeasured common cause. That verdict has no representation in the template system at all.
