# Agentic Action Layer — Positioning & Design Note

**Status:** positioning + architecture note; the "4th layer" of the platform.
Substrate largely exists; the reasoning agent is the build. Parked as a durable
record. **Date:** 2026-08-07.

## The thesis in one line

CS Pulse is already an **agent runtime** — the MCP tool layer, the causal graph,
the signal engine, and the graduated-autonomy governance fields all exist. What's
missing is the **autonomous agent that closes the loop**: sense a signal → reason
about the right action → act at the appropriate autonomy level → measure the
outcome → learn. Adding that turns "an AI-assisted dashboard" into "an AI-native
CS system that acts."

## The hook: extend "3 Layers of AI" to 4

The platform already positions three layers of AI. **Agentic (Actuating) is the
capstone** — the layer that turns insight into governed action and closes the loop:

**Predictive** (what will happen) → **Causal** (why) → **Generative** (explain /
converse) → **Agentic** (do something about it, and measure it).

This is an evolution of the existing narrative, not a pivot.

## What already exists (the substrate) vs the gap (the last mile)

| Capability | Exists today | Where |
|------------|--------------|-------|
| **Agent runtime** | ✅ the platform is an MCP tool provider (~69 tools incl. `execute_playbook`, `trigger_wizard`) | Module 07; `agent_tool_registry.py` ("backbone for the agentic loop") |
| **Reasoning memory** | ✅ the causal context graph (signal→decision→outcome) | Module 04 |
| **Sense (signals)** | ✅ the leading-layer signal engine + `should_trigger_playbook()` + `arc_playbook_map.json` | Modules 06 / 05 |
| **Action plumbing** | ✅ `fire_playbook_webhook`, `trigger_n8n_workflow`, connectors, sync health; notifications | `cs_pulse_integrations.py`, `notifications_api.py`, `push_intelligence_subscriber.py`, `Notification` model |
| **Governance model** | ✅ **per-playbook** `automation_level` (low/med/high) + `human_approval_required` | `verticals/*/vertical_config.py` |
| **Business-DNA context** | ✅ the agent acts with *this client's* playbooks/thresholds/nomenclature | the MCP business-DNA bridge |
| **The reasoning agent loop** | ❌ **the gap** — nothing ties sense→reason→act→measure into a closed loop | to build |
| **Action templates** (Slack nudge, draft email, task) | ❌ delegated to n8n today; no first-class low-effort actions | to build (n8n templates or native) |
| **Human-in-the-loop approval UX** | ⚠️ partial — the cockpit has an approvals surface | extend |
| **Agent-action audit trail** | ❌ every autonomous action logged (who/what/why/outcome) | to build; ties to Module 10 governance |

Net: the plumbing, the tool surface, and the governance data-model exist. The
**reasoning agent + low-effort action templates + approval UX + action audit** are
the build.

## The architecture — the closed loop

```
  SENSE   →   REASON      →   GATE          →   ACT           →   MEASURE      →  LEARN
  signal      LLM + causal    automation_     auto-execute       write outcome     calibrate
  fires       graph: is it    level +          (low-risk) OR      back to the       (Wizard C /
  (Mod 06)    real? what      human_approval   route to 1-click   graph — did it    the loop)
              play? effort/    _required        approval           work? ROI?
              impact?          (Mod 07 + cfg)   (n8n/native)       (Mod 04/08)
```

Each stage maps to something that exists (Sense, Reason, Gate, Plumbing) or is the
bounded build (the loop service, action templates, approval UX, audit).

## The differentiator: graduated autonomy, governed and audited

No CS leader buys "autonomous AI that emails my customers unsupervised." The
sellable version is **autonomy you dial per action** — which the
`automation_level` + `human_approval_required` model already encodes. Frame it as a
ladder:

- **L0 · Suggest** — surface the recommended play (today's state).
- **L1 · Draft & approve** — the agent drafts (e.g. an email); a human sends.
- **L2 · Auto-execute (low-risk, internal)** — e.g. a Slack nudge to the CSM.
- **L3 · Autonomous (audited)** — customer-facing, only with a full audit trail and
  a proven track record.

Internal / low-stakes = auto; customer-facing / high-stakes = human-gated. **That
is the trust story**, and it's what generic "AI agents" can't credibly claim.

## Agentic ≠ vanity — it's measured

Every autonomous action carries a **Power-of-1 ROI** (revenue protected /
CSM-hours saved). The pitch is quantified: *"the agent handled N low-effort
actions this quarter — X hours of CSM time returned, $Y protected — so one CSM now
covers 1.5× the book."* This is the investment-allocation story, made agentic.

## The wedge — start here (safe, high-ROI, ships fast)

All **internal or human-gated** — zero customer-facing autonomous risk:

1. **Auto Slack nudge to the CSM** when a signal fires: *"Acme showing silent-churn
   pattern, health −12 in 2 wks, suggested play PB-06 →"* (L2, internal)
2. **Draft email for one-click CSM approval** — agent writes, human sends (L1)
3. **Auto-create the task / kanban card** (the cockpit already renders cards) (L2)
4. **Auto-flag the renewal / schedule the QBR** (L1/L2)

These prove the agentic value and *earn the trust* to graduate autonomy — and the
plumbing (webhooks / n8n / notifications) already exists, so the wedge ships fast.

## The elevator pitch

> *"Most CS platforms give you a dashboard and a chatbot. CS Pulse senses the
> leading signal, reasons about it on a causal graph, takes the right action at the
> right autonomy level — starting with the low-effort, high-impact ones — and
> measures whether it worked, then learns. It's not a report about your customers;
> it's an AI-native system that acts on their behalf, with autonomy you dial and a
> full audit trail. Your CS system is already an agent runtime."*

## The build gap (bounded — so the pitch isn't hype)

Real but contained; you are **not** rebuilding connectors or governance:
1. **The agent loop service** — sense→reason→gate→act→measure as a running service.
2. **Action templates** — Slack / email / task (n8n templates or native).
3. **Approval UX** — extend the cockpit's approvals surface for L1.
4. **Agent-action audit trail** — every action logged (who/what/why/outcome); this
   is a Module 10 (Governance) concern and closes the WizardRun-style audit gap.

If built the same rigorous way as the framework, this is a natural **Module 12 —
Agentic Action Layer** (Interface/Ops): the loop, the autonomy gate, the action
contracts, the audit — with a Build Prompt + adversarial rebuild like the rest.

## Provenance

Verified 2026-08-07 against HEAD `6257b7a98`:
`kpi-dashboard/backend/mcp_server/cs_pulse_integrations.py` (`fire_playbook_webhook`,
`trigger_n8n_workflow`, connectors, sync health), `notifications_api.py`,
`push_intelligence_subscriber.py`, `models.py:2001` (`Notification`),
`verticals/dc2_s/vertical_config.py` (`automation_level` / `human_approval_required`
per playbook), `agent_tool_registry.py` (the internal agentic-loop registry), the
MCP tool layer (`consulting-framework/modules/07-interface-mcp-tool-layer.md`), the
signal engine (Module 06), the causal graph (Module 04). Positioning builds on the
platform's existing "3 Layers of AI" and Power-of-1 / investment-allocation
narratives.
