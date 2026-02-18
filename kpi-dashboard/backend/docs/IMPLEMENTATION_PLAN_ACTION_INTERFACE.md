# Implementation Plan: Action Interface + LLM Validation Layer

**Context:** Merges the Abstract Action Interface Specification (v1.0, Feb 2026) with the existing CS Pulse codebase. Adds the missing LLM validation gate, leverages existing infrastructure, and defines concrete build order.

**Guiding constraint:** Extend what exists. Don't replace `PlaybookOrchestrator`, `SignalAnalystAgent`, `CustomerWorkflowConfig`, or the 3 MCP mock servers. Wire them together, generalize where needed, and add the new pieces.

---

## Phase 0: Foundation Fixes (Week 1-2)

These are prerequisites. The action interface can't function without them.

### 0.1 Add `journey_phase` and `renewal_date` to the Account model

**Problem:** The `Account` model (`models.py:Account`) has no `journey_phase` or `renewal_date` fields. SaaS-PB-02 (Renewal Tracking) triggers at T-120 days before renewal. PB-DC-01 needs deployment phase context. Without these, playbooks can't trigger on lifecycle events.

**Changes:**

File: `backend/models.py`
```python
# Add to Account model
class Account(db.Model):
    # ... existing fields ...
    journey_phase = db.Column(db.String(50), default='onboarding')
      # Values: 'onboarding', 'adoption', 'expanding', 'renewing', 'mature'
    renewal_date = db.Column(db.DateTime, nullable=True)
    contract_start_date = db.Column(db.DateTime, nullable=True)
    contract_value = db.Column(db.Numeric(15, 2), nullable=True)
```

File: `backend/alembic/` (create if not exists)
- Add Alembic migration for the new columns
- Backfill `journey_phase = 'mature'` for existing accounts
- Backfill `renewal_date` from CRM data where available (or NULL)

### 0.2 Wire `determine_customer_phase()` into health score recalculation

**Problem:** `determine_customer_phase()` exists in the codebase but isn't called during score recalculation. Journey phase is never actually set.

**Changes:**

- Identify where `HealthScoreStorageService` or the DC2S health calculator runs
- After each recalculation, call `determine_customer_phase(account)` and persist the result to `account.journey_phase`
- This makes journey-phase-based triggers (onboarding, renewal) actually work

### 0.3 Remove proxy playbook recommendations

**Problem:** Playbook recommendations in the health endpoint use `health_score / 10` instead of real trigger logic.

**Changes:**

- Find the health endpoint code that generates playbook recommendations
- Replace the proxy formula with real threshold checks against the trigger conditions defined in the spec (e.g., `P1-KPI1 > 20 days` for PB-DC-01)
- For now, these can be simple threshold checks — the LLM validation layer (Phase 2) will gate actual execution

---

## Phase 1: Database Schema for Action Bindings + Credential Vault (Week 3)

### 1.1 New tables

Create these tables from the spec, with adjustments to integrate with the existing schema:

**`customer_action_bindings`** — Generalizes `CustomerWorkflowConfig`

```sql
CREATE TABLE customer_action_bindings (
    id SERIAL PRIMARY KEY,                    -- Match existing PK convention (Integer, not UUID)
    customer_id INTEGER NOT NULL REFERENCES customers(customer_id),
    action_name VARCHAR(100) NOT NULL,        -- 'create_task', 'send_alert', etc.
    provider VARCHAR(50) NOT NULL,            -- 'jira', 'slack', 'salesforce', 'cs_pulse_internal'
    config JSONB NOT NULL DEFAULT '{}',
    auth_credential_id INTEGER,               -- FK to integration_credentials
    fallback VARCHAR(50),                     -- 'log_only', 'email', null
    enabled BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(customer_id, action_name)
);
```

**`integration_credentials`** — Generalizes the per-field encrypted credential pattern

```sql
CREATE TABLE integration_credentials (
    id SERIAL PRIMARY KEY,
    customer_id INTEGER NOT NULL REFERENCES customers(customer_id),
    provider VARCHAR(50) NOT NULL,
    credential_type VARCHAR(50) NOT NULL,     -- 'oauth2', 'api_key', 'bot_token', 'smtp_credentials'
    encrypted_data BYTEA NOT NULL,            -- Uses same encryption as existing webhook_secret_encrypted
    expires_at TIMESTAMP,
    refresh_token_encrypted BYTEA,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

**`playbook_step_log`** — Audit trail for individual step execution

```sql
CREATE TABLE playbook_step_log (
    id SERIAL PRIMARY KEY,
    execution_id VARCHAR(36) NOT NULL REFERENCES playbook_executions(execution_id),
    step_index INTEGER NOT NULL,
    action_name VARCHAR(100) NOT NULL,
    provider VARCHAR(50) NOT NULL,
    params_sent JSONB,
    response_received JSONB,
    status VARCHAR(20) NOT NULL,              -- 'success', 'failed', 'skipped', 'pending'
    error_message TEXT,
    executed_at TIMESTAMP DEFAULT NOW(),
    duration_ms INTEGER
);
```

**`crm_field_mappings`** — Per-customer CRM field mapping

```sql
CREATE TABLE crm_field_mappings (
    id SERIAL PRIMARY KEY,
    customer_id INTEGER NOT NULL REFERENCES customers(customer_id),
    cs_pulse_field VARCHAR(100) NOT NULL,
    crm_object VARCHAR(50) NOT NULL,
    crm_field VARCHAR(100) NOT NULL,
    transform VARCHAR(50),
    transform_config JSONB,
    UNIQUE(customer_id, cs_pulse_field, crm_object)
);
```

**`customer_contacts`** — Contact role mapping for variable interpolation

```sql
CREATE TABLE customer_contacts (
    id SERIAL PRIMARY KEY,
    customer_id INTEGER NOT NULL REFERENCES customers(customer_id),
    account_id INTEGER REFERENCES accounts(account_id),
    role VARCHAR(50) NOT NULL,                -- 'champion', 'executive_sponsor', 'technical_lead'
    name VARCHAR(200),
    email VARCHAR(200) NOT NULL,
    title VARCHAR(200),
    crm_contact_id VARCHAR(100),
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT NOW()
);
```

### 1.2 Extend `PlaybookExecution` model

Add columns that the spec defines and the existing model lacks:

```python
# Add to PlaybookExecution in models.py
execution_mode = db.Column(db.String(20))      # 'mcp_direct', 'workflow'
trigger_context = db.Column(db.JSON)            # KPIs that triggered it
outcome = db.Column(db.String(50))              # 'resolved', 'escalated', 'timeout', 'manual_close'
outcome_notes = db.Column(db.Text)
llm_validation_result = db.Column(db.JSON)      # Signal Analyst output that approved this execution
```

### 1.3 Extend `PlaybookTrigger` model

The existing `playbook_type` enum (`'voc', 'activation', 'sla', 'renewal', 'expansion'`) is SaaS-only. Extend for the 14 playbook IDs:

```python
# Keep existing playbook_type for backward compat, add:
playbook_id = db.Column(db.String(50))          # 'PB-DC-01', 'SaaS-PB-01', etc.
trigger_conditions = db.Column(db.JSON)          # Structured trigger rules (KPI code, operator, threshold)
execution_mode = db.Column(db.String(20))        # 'mcp_direct', 'workflow'
requires_llm_validation = db.Column(db.Boolean, default=True)
```

### 1.4 SQLAlchemy models for new tables

Create `backend/models_action_interface.py` with SQLAlchemy models for the 5 new tables. Register them in the app factory.

### 1.5 Migration

- Alembic migration for all new tables and column additions
- No data migration needed — these are new capabilities

**Key design decision:** The existing `CustomerWorkflowConfig` stays as-is. It manages n8n connection details. The new `customer_action_bindings` table manages per-action routing (which might or might not go through n8n). They're complementary, not redundant.

---

## Phase 2: LLM Validation Gate (Week 4)

This is the critical missing piece from the spec.

### 2.1 `PlaybookTriggerValidator` class

New file: `backend/playbook_trigger_validator.py`

```python
class PlaybookTriggerValidator:
    """
    Sits between KPI threshold detection and playbook execution.
    Uses SignalAnalystAgent to validate that a playbook should actually fire.
    """

    def __init__(self, openai_api_key: str):
        self.signal_analyst = SignalAnalystAgent(openai_api_key=openai_api_key)

    def validate_trigger(
        self,
        account_id: str,
        customer_id: int,
        playbook_id: str,
        trigger_context: dict,  # KPIs that breached thresholds
    ) -> TriggerValidationResult:
        """
        Returns:
        - approved: bool
        - confidence: float (0-1)
        - reasoning: str
        - modified_priority: Optional[str]  # LLM may suggest different priority
        - recommended_playbook: Optional[str]  # LLM may suggest a different playbook
        """
```

**Logic:**

1. Fetch signals from Qdrant (quantitative + qualitative + historical) — reuse existing `get_quantitative_signals_from_qdrant()` etc.
2. Build `SignalAnalystInput` with the trigger context
3. Call `self.signal_analyst.analyze(input_data)`
4. Read the `SignalAnalystOutput`:
   - Check `data_alignment` from Decision Matrix — if DISAGREEMENT with low confidence, reject
   - Check `predicted_outcome` — if trigger is churn playbook but LLM predicts EXPANSION, reject
   - Check `confidence.overall_confidence`
5. Apply thresholds:
   - `confidence > 0.8` → **auto-approve**, fire playbook
   - `confidence < 0.4` → **auto-reject**, log signal for CSM review
   - `0.4 <= confidence <= 0.8` → **manual approval**, create a task for CSM

### 2.2 `TriggerValidationResult` model

New file or add to `backend/agents/models.py`:

```python
class TriggerValidationResult(BaseModel):
    approved: bool
    confidence: float  # 0-1
    reasoning: str
    decision: Literal["auto_approved", "auto_rejected", "pending_manual_approval"]
    signal_analyst_output: Optional[dict]  # Full output for audit trail
    modified_priority: Optional[str]
    recommended_playbook: Optional[str]
    validated_at: datetime
```

### 2.3 Integration point

Modify the trigger evaluation loop (wherever KPI thresholds are checked) to call the validator before dispatching:

```python
# Pseudocode for the trigger evaluation flow:
def evaluate_triggers(account_id, customer_id, current_kpis):
    for trigger in PlaybookTrigger.query.filter_by(customer_id=customer_id):
        if threshold_breached(trigger, current_kpis):
            if trigger.requires_llm_validation:
                result = validator.validate_trigger(
                    account_id=account_id,
                    customer_id=customer_id,
                    playbook_id=trigger.playbook_id,
                    trigger_context=build_trigger_context(trigger, current_kpis)
                )
                if result.decision == "auto_approved":
                    dispatch_playbook(trigger.playbook_id, account_id, result)
                elif result.decision == "pending_manual_approval":
                    create_approval_task(trigger, account_id, result)
                else:
                    log_rejected_trigger(trigger, account_id, result)
            else:
                # Some playbooks (e.g., QBR on quarterly cadence) skip LLM validation
                dispatch_playbook(trigger.playbook_id, account_id, None)
```

### 2.4 Cost control

The Signal Analyst uses GPT-4o at $2.50/$10.00 per 1M tokens. If 50 accounts breach thresholds in a day, that's 50 LLM calls just for validation.

Mitigations:
- Cache validation results per (account_id, playbook_id) for 24 hours
- Skip validation for `requires_llm_validation = False` playbooks (QBR cadence, advocacy)
- Use the existing `CostTracker` to monitor per-customer spend
- Circuit breaker on the Signal Analyst (already exists in `error_handling.py`) prevents runaway costs
- Fallback to rule-based Decision Matrix when LLM is unavailable

---

## Phase 3: Abstract Action Interface + Action Router (Week 5-6)

### 3.1 Action definitions

New file: `backend/actions/__init__.py`
New file: `backend/actions/abstract_actions.py`

Define the 25 abstract actions from the spec as Python classes:

```python
from pydantic import BaseModel
from typing import Optional, List, Dict
from enum import Enum

class ActionResult(BaseModel):
    success: bool
    data: dict  # Action-specific return values (task_id, message_id, etc.)
    error: Optional[str]

class CreateTaskParams(BaseModel):
    title: str
    description: Optional[str]
    assignee: str
    due_date: str  # ISO date or relative expression
    priority: Literal["p0", "p1", "p2", "p3"]
    labels: List[str] = []
    parent_id: Optional[str]
    custom_fields: Dict = {}

class SendAlertParams(BaseModel):
    channel: str  # logical channel name
    message: str
    severity: Literal["info", "warning", "critical"]
    thread_id: Optional[str]
    mentions: List[str] = []
    attachments: List[dict] = []

# ... one Params class per action from Section 2 of the spec
```

### 3.2 Action Router

New file: `backend/actions/action_router.py`

```python
class ActionRouter:
    """
    Resolves abstract action calls to provider-specific adapters.
    Uses customer_action_bindings table for routing decisions.
    """

    def __init__(self, customer_id: int):
        self.customer_id = customer_id
        self.bindings = self._load_bindings()
        self.adapters = {}  # Lazy-loaded provider adapters

    def execute(self, action_name: str, params: dict) -> ActionResult:
        binding = self.bindings.get(action_name)
        if not binding:
            if action_name in CS_PULSE_INTERNAL_ACTIONS:
                return self._execute_internal(action_name, params)
            raise ActionNotConfiguredError(action_name, self.customer_id)

        if not binding.enabled:
            return ActionResult(success=True, data={}, error=None)  # silently skip

        adapter = self._get_adapter(binding.provider)
        credential = self._decrypt_credential(binding.auth_credential_id)

        # Execute with retry + circuit breaker (reuse existing patterns)
        return adapter.execute(action_name, params, binding.config, credential)

    def _load_bindings(self) -> dict:
        rows = CustomerActionBinding.query.filter_by(customer_id=self.customer_id).all()
        return {row.action_name: row for row in rows}

    def _get_adapter(self, provider: str) -> ProviderAdapter:
        if provider not in self.adapters:
            self.adapters[provider] = ADAPTER_REGISTRY[provider]()
        return self.adapters[provider]
```

**`CS_PULSE_INTERNAL_ACTIONS`:** `log_playbook_action`, `update_health_override`, `trigger_wizard_rerun`, `set_account_flag`, `assign_csm`, `generate_report`, `generate_narrative` — these always execute locally, never routed externally.

### 3.3 Provider Adapter interface

New file: `backend/actions/adapters/base.py`

```python
from abc import ABC, abstractmethod

class ProviderAdapter(ABC):
    @abstractmethod
    def execute(self, action_name: str, params: dict, config: dict, credential: dict) -> ActionResult:
        """Execute an action against the provider."""

    def _map_priority(self, cs_pulse_priority: str) -> str:
        """Map CS Pulse priority (p0-p3) to provider-specific priority."""
        raise NotImplementedError
```

### 3.4 CS Pulse Internal adapter

New file: `backend/actions/adapters/cs_pulse_internal.py`

Handles all internal actions. This is the first adapter to build because it has zero external dependencies:

```python
class CSPulseInternalAdapter(ProviderAdapter):
    def execute(self, action_name: str, params: dict, config: dict, credential: dict) -> ActionResult:
        handler = {
            'log_playbook_action': self._log_action,
            'set_account_flag': self._set_flag,
            'update_health_override': self._update_override,
            'generate_report': self._generate_report,
            'generate_narrative': self._generate_narrative,
            'assign_csm': self._assign_csm,
        }.get(action_name)
        return handler(params)

    def _log_action(self, params):
        # Write to playbook_step_log table
        ...

    def _set_flag(self, params):
        # Write to account flags (new table or JSON field on Account)
        ...

    def _generate_narrative(self, params):
        # Call SignalAnalystAgent with narrative_type prompt
        # Return markdown narrative
        ...
```

---

## Phase 4: First External Adapters — Jira + Slack (Week 7-8)

### 4.1 Jira Adapter

New file: `backend/actions/adapters/jira_adapter.py`

```python
class JiraAdapter(ProviderAdapter):
    ACTIONS = ['create_task', 'update_task', 'close_task', 'check_task_status']

    def execute(self, action_name, params, config, credential):
        if action_name == 'create_task':
            return self._create_issue(params, config, credential)
        # ...

    def _create_issue(self, params, config, credential):
        jira_payload = {
            'fields': {
                'project': {'key': config['project_key']},
                'summary': params['title'],
                'description': self._markdown_to_adf(params.get('description', '')),
                'issuetype': {'name': config.get('issue_type', 'Task')},
                'priority': {'name': self._map_priority(params['priority'])},
                'assignee': {'accountId': self._resolve_user(params['assignee'], credential)},
                'labels': params.get('labels', []) + config.get('default_labels', []),
            }
        }
        if params.get('due_date'):
            jira_payload['fields']['duedate'] = self._resolve_date(params['due_date'])

        resp = requests.post(
            f"{config['instance_url']}/rest/api/3/issue",
            json=jira_payload,
            headers=self._auth_headers(credential),
            timeout=10
        )
        resp.raise_for_status()
        data = resp.json()
        return ActionResult(
            success=True,
            data={'task_id': data['key'], 'task_url': f"{config['instance_url']}/browse/{data['key']}"}
        )

    def _map_priority(self, p):
        return {'p0': 'Highest', 'p1': 'High', 'p2': 'Medium', 'p3': 'Low'}[p]
```

### 4.2 Slack Adapter

New file: `backend/actions/adapters/slack_adapter.py`

```python
class SlackAdapter(ProviderAdapter):
    ACTIONS = ['send_alert', 'send_direct_message', 'create_channel']

    def _send_alert(self, params, config, credential):
        channel = config['channel_mapping'].get(params['channel'], params['channel'])
        severity_emoji = {'info': 'large_blue_circle', 'warning': 'warning', 'critical': 'red_circle'}

        slack_payload = {
            'channel': channel,
            'text': params['message'],
            'thread_ts': params.get('thread_id'),
        }
        if params.get('mentions'):
            # Resolve emails to Slack user IDs
            ...

        resp = requests.post(
            'https://slack.com/api/chat.postMessage',
            json=slack_payload,
            headers={'Authorization': f"Bearer {credential['bot_token']}"},
            timeout=10
        )
        data = resp.json()
        return ActionResult(
            success=data.get('ok', False),
            data={'message_id': data.get('ts'), 'thread_id': data.get('ts'), 'channel_id': data.get('channel')}
        )
```

### 4.3 Adapter Registry

New file: `backend/actions/adapters/__init__.py`

```python
ADAPTER_REGISTRY = {
    'jira': JiraAdapter,
    'slack': SlackAdapter,
    'cs_pulse_internal': CSPulseInternalAdapter,
    # Phase 5: 'salesforce': SalesforceAdapter,
    # Phase 5: 'sendgrid': SendGridAdapter,
    # Phase 7: 'hubspot': HubSpotAdapter, 'linear': LinearAdapter, etc.
}
```

### 4.4 Error handling for external calls

Wrap all adapter HTTP calls with the existing retry + circuit breaker patterns:

```python
from utils.error_handling import CircuitBreaker

class JiraAdapter(ProviderAdapter):
    _circuit_breaker = CircuitBreaker(failure_threshold=3, timeout=120)

    def execute(self, action_name, params, config, credential):
        if self._circuit_breaker.is_open():
            return ActionResult(success=False, data={}, error="Jira circuit breaker open")
        try:
            result = self._do_execute(action_name, params, config, credential)
            self._circuit_breaker.record_success()
            return result
        except Exception as e:
            self._circuit_breaker.record_failure()
            raise
```

Also add per-action retry policy to the binding config:

```json
{
  "retry": {"max_attempts": 3, "backoff_base_seconds": 2},
  "timeout_seconds": 15
}
```

---

## Phase 5: CRM + Email Adapters (Week 9-10)

### 5.1 Salesforce Adapter

New file: `backend/actions/adapters/salesforce_adapter.py`

Actions: `update_crm_record`, `create_crm_record`, `get_crm_record`, `add_crm_note`, `create_crm_activity`

Key complexity: CRM field mapping. Uses `crm_field_mappings` table to translate CS Pulse fields to Salesforce custom fields:

```python
def _map_fields(self, cs_pulse_fields: dict, config: dict, customer_id: int) -> dict:
    mappings = CrmFieldMapping.query.filter_by(customer_id=customer_id).all()
    sf_fields = {}
    for key, value in cs_pulse_fields.items():
        mapping = next((m for m in mappings if m.cs_pulse_field == key), None)
        if mapping:
            sf_fields[mapping.crm_field] = self._apply_transform(value, mapping)
        else:
            sf_fields[key] = value  # pass through unmapped fields
    return sf_fields
```

**MCP bridge:** When a customer has their own Salesforce MCP server (instead of REST API), the adapter becomes:

```python
class SalesforceMCPAdapter(SalesforceAdapter):
    """Thin wrapper that calls MCP tools instead of REST API."""
    def _create_record(self, params, config, credential):
        # Call MCP tool instead of REST
        return self.mcp_client.call_tool('create_record', params)
```

This is how the spec's adapter pattern and MCP converge — MCP becomes one possible backend for an adapter.

### 5.2 SendGrid / SMTP Adapter

New file: `backend/actions/adapters/email_adapter.py`

Actions: `send_email`, `send_email_sequence`, `cancel_email_sequence`

Two implementations:
- `SendGridAdapter` — uses SendGrid API with template IDs
- `SMTPAdapter` — direct SMTP for customers without SendGrid

Email sequences require state tracking (which emails sent, when to send next). For now, delegate to n8n workflows. The adapter creates the sequence definition; n8n manages the schedule.

---

## Phase 6: Variable Interpolation Engine (Week 8, parallel with Phase 4)

### 6.1 Template resolver

New file: `backend/actions/variable_resolver.py`

```python
class VariableResolver:
    """
    Resolves {{variable}} expressions in playbook step params.
    Sources (in priority order):
    1. trigger_context (KPIs that triggered)
    2. previous_step_outputs (task_id, document_url, etc.)
    3. account record
    4. customer record
    5. contact mapping (customer_contacts table)
    6. CRM mapping
    7. temporal expressions ({{now}}, {{now + 7d}}, {{renewal_date - 90d}})
    """

    def resolve(self, template: Any, context: ResolutionContext) -> Any:
        if isinstance(template, str):
            return self._resolve_string(template, context)
        elif isinstance(template, dict):
            return {k: self.resolve(v, context) for k, v in template.items()}
        elif isinstance(template, list):
            return [self.resolve(item, context) for item in template]
        return template

    def _resolve_string(self, s: str, context: ResolutionContext) -> str:
        pattern = r'\{\{(.+?)\}\}'
        def replacer(match):
            expr = match.group(1).strip()
            if self._is_temporal(expr):
                return self._resolve_temporal(expr, context)
            return str(context.get(expr, match.group(0)))  # leave unresolved if not found
        return re.sub(pattern, replacer, s)

    def _resolve_temporal(self, expr: str, context: ResolutionContext) -> str:
        # Handles: "now", "now + 7d", "now + 48h", "renewal_date - 90d"
        ...
```

### 6.2 `ResolutionContext`

```python
class ResolutionContext:
    """
    Builds the variable resolution context from multiple data sources.
    """
    def __init__(self, account_id, customer_id, trigger_context=None, step_outputs=None):
        self.data = {}
        self._load_account(account_id)
        self._load_customer(customer_id)
        self._load_contacts(customer_id, account_id)
        self._load_crm_mapping(customer_id)
        if trigger_context:
            self.data.update(trigger_context)
        if step_outputs:
            self.data.update(step_outputs)

    def get(self, key, default=None):
        return self.data.get(key, default)
```

---

## Phase 7: Playbook Execution Engine (Week 11-12)

### 7.1 `PlaybookEngine` — orchestrates step execution

New file: `backend/playbook_engine.py`

This replaces the current "store execution in memory + DB" approach with actual step-by-step execution:

```python
class PlaybookEngine:
    """
    Executes playbook steps. For mcp_direct playbooks, runs all steps sequentially.
    For workflow playbooks, dispatches to n8n via PlaybookOrchestrator.
    """

    def __init__(self, customer_id: int):
        self.action_router = ActionRouter(customer_id)
        self.variable_resolver = VariableResolver()
        self.customer_id = customer_id

    def execute(self, playbook_definition: dict, account_id: str,
                trigger_context: dict, validation_result: TriggerValidationResult) -> str:
        """
        Main entry point. Returns execution_id.
        """
        execution = self._create_execution(playbook_definition, account_id, trigger_context, validation_result)
        mode = playbook_definition['execution_mode']

        if mode == 'mcp_direct':
            self._execute_direct(execution, playbook_definition, trigger_context)
        elif mode == 'workflow':
            self._dispatch_to_workflow(execution, playbook_definition, trigger_context)

        return execution.execution_id

    def _execute_direct(self, execution, playbook_def, trigger_context):
        """Execute all steps synchronously (for mcp_direct playbooks)."""
        context = ResolutionContext(execution.account_id, self.customer_id, trigger_context)
        step_outputs = {}

        for i, step in enumerate(playbook_def['steps']):
            resolved_params = self.variable_resolver.resolve(step['params'], context)
            result = self.action_router.execute(step['action'], resolved_params)

            # Log step
            self._log_step(execution.execution_id, i, step['action'], resolved_params, result)

            # Accumulate outputs for next steps
            if result.success:
                step_outputs.update(result.data)
                context = ResolutionContext(
                    execution.account_id, self.customer_id, trigger_context, step_outputs
                )

        execution.status = 'completed'
        execution.completed_at = datetime.utcnow()
        db.session.commit()

    def _dispatch_to_workflow(self, execution, playbook_def, trigger_context):
        """
        Dispatch to n8n via existing PlaybookOrchestrator.
        Sends the full playbook definition + bindings + resolved variables.
        """
        orchestrator = PlaybookOrchestrator()

        # Pre-resolve all non-step-dependent variables
        context = ResolutionContext(execution.account_id, self.customer_id, trigger_context)
        payload = {
            'playbook_id': playbook_def['playbook_id'],
            'account_id': str(execution.account_id),
            'customer_id': self.customer_id,
            'trigger_context': trigger_context,
            'steps': playbook_def['steps'],
            'bindings': self._serialize_bindings(),
            'variables': context.data,  # pre-resolved variables for n8n
        }

        orchestrator.trigger_execution(execution, payload)
```

### 7.2 Concurrency control

Add a constraint to prevent duplicate active playbook executions per account:

```python
# Before creating execution:
active = PlaybookExecution.query.filter_by(
    account_id=account_id,
    playbook_id=playbook_id,
    status='in-progress'
).first()
if active:
    logger.info(f"Playbook {playbook_id} already active for account {account_id}, skipping")
    return None
```

### 7.3 Playbook definitions storage

The 14 playbook definitions from the spec need to live somewhere. Options:
- **YAML files** in `backend/playbooks/` directory (recommended — version-controlled, easy to review)
- Database table (allows runtime editing but loses version control)

Decision: YAML files loaded at startup into an in-memory registry. A `PlaybookRegistry` class loads and validates all definitions.

New directory: `backend/playbooks/`
```
playbooks/
  PB-DC-01_deployment_acceleration.yaml
  PB-DC-02_rma_prevention.yaml
  PB-DC-03_gpu_optimization.yaml
  PB-DC-04_capacity_planning.yaml
  PB-DC-05_health_monitoring.yaml
  PB-DC-06_customer_engagement.yaml
  SaaS-PB-01_churn_prevention.yaml
  SaaS-PB-02_renewal_tracking.yaml
  SaaS-PB-03_expansion.yaml
  SaaS-PB-04_low_engagement.yaml
  SaaS-PB-05_onboarding.yaml
  SaaS-PB-06_qbr.yaml
  SaaS-PB-07_executive_escalation.yaml
  SaaS-PB-08_advocacy.yaml
```

---

## Phase 8: Workflow Orchestration Primitives for n8n (Week 12-13)

### 8.1 n8n template workflows

The workflow-mode playbooks need n8n to interpret `wait`, `branch`, `check_condition`, and `repeat_until`. Create n8n workflow templates that:

1. Receive the playbook payload via webhook (already supported by `PlaybookOrchestrator`)
2. Iterate through steps
3. For each action step, call back to CS Pulse's action execution endpoint
4. For `wait` steps, use n8n's Delay node
5. For `check_condition`, call CS Pulse's condition-check endpoint
6. For `branch`, use n8n's IF node
7. For `repeat_until`, use n8n's Loop node
8. On completion/failure, POST callback to CS Pulse (already supported by `PlaybookOrchestrator.process_callback()`)

### 8.2 CS Pulse endpoints for n8n callbacks

New endpoints that n8n calls during workflow execution:

```
POST /api/actions/execute          — n8n asks CS Pulse to execute an action
POST /api/actions/check-condition  — n8n asks CS Pulse to evaluate a condition
POST /api/playbooks/callback       — n8n reports step/workflow completion (already exists in orchestrator)
```

The key insight: n8n doesn't call Jira/Slack directly. It calls CS Pulse's action router, which routes through the customer's bindings. This keeps the binding logic centralized.

---

## Phase 9: Calendar + Reports + Narrative (Week 13-14)

### 9.1 Google Calendar Adapter

Actions: `schedule_meeting`, `cancel_meeting`, `check_availability`

### 9.2 Report Generator (Internal)

The `generate_report` action is always internal. Build template-based report generation:
- QBR deck: Pull KPIs from Qdrant, format into structured report
- Renewal scorecard: Pull health score + usage trends + ROI calculations
- Expansion business case: Pull capacity + growth metrics + forecast

Use the existing `generate_narrative` path through the Signal Analyst, but with a report-specific prompt template.

### 9.3 Narrative Generator (Internal)

The `generate_narrative` action calls the Signal Analyst with a specific prompt:

```python
def _generate_narrative(self, params):
    # Build a targeted prompt for the narrative type
    prompt_templates = {
        'executive_summary': "Write a concise executive summary...",
        'risk_assessment': "Analyze the risk factors for...",
        'expansion_case': "Build the business case for expansion...",
        'intervention_report': "Summarize the intervention status...",
    }
    # Call SignalAnalystAgent with appropriate context
    ...
```

---

## Phase 10: Additional Provider Adapters (Week 15-17)

Build on demand based on customer requirements:

| Provider | Adapter | Actions | Effort |
|----------|---------|---------|--------|
| HubSpot | `hubspot_adapter.py` | CRM + Email | 1 week |
| Linear | `linear_adapter.py` | Task management | 3 days |
| Microsoft Teams | `teams_adapter.py` | Messaging | 3 days |
| Microsoft Calendar | `ms_calendar_adapter.py` | Calendar | 3 days |
| Asana | `asana_adapter.py` | Task management | 3 days |

Each adapter follows the same `ProviderAdapter` interface. Testing with mock servers first, then real API integration.

---

## Phase 11: Binding Admin UI (Week 17-18)

### 11.1 Backend API

New endpoints on `backend/actions/action_bindings_api.py`:

```
GET    /api/integrations/bindings          — List all bindings for customer
POST   /api/integrations/bindings          — Create/update a binding
DELETE /api/integrations/bindings/:id      — Remove a binding
GET    /api/integrations/providers         — List available providers
POST   /api/integrations/credentials       — Store encrypted credential
POST   /api/integrations/test              — Test a binding (create a test task, send a test alert)
GET    /api/integrations/contacts          — List customer contacts
POST   /api/integrations/contacts          — Create/update contact mapping
```

### 11.2 Frontend

Settings page → Integrations tab:
- List of abstract actions with current binding status
- "Connect" flow per provider (OAuth2 redirect or API key input)
- Test button per binding
- Contact role mapping editor

---

## Phase 12: MCP Server Wrapping (Week 14-15, parallel with Phase 9)

### 12.1 CS Pulse as an MCP server

This is how you achieve the "agentic AI which leverages MCP to work across LLM providers" goal.

New file: `backend/mcp_servers/cs_pulse_mcp_server.py`

Expose CS Pulse's capabilities as MCP tools that any LLM client can discover and call:

**Resources:**
- `cspulse://accounts/{account_id}/health` — Current health score + breakdown
- `cspulse://accounts/{account_id}/signals` — Recent signals (quant + qual)
- `cspulse://accounts/{account_id}/playbooks` — Active/completed playbook executions
- `cspulse://accounts/{account_id}/kpis` — Current KPI values by pillar
- `cspulse://customers/{customer_id}/portfolio` — Portfolio overview

**Tools:**
- `analyze_account` — Trigger Signal Analyst analysis (wraps existing endpoint)
- `execute_playbook` — Manually trigger a playbook (with LLM validation)
- `create_task` — Create a task via action router
- `send_alert` — Send an alert via action router
- `update_health_override` — Manually override health score
- `set_account_flag` — Set account flag
- `generate_narrative` — Generate narrative report

This MCP server sits alongside the existing mock servers but represents CS Pulse's own capabilities. Any MCP-compatible LLM client (Claude, GPT with MCP plugin, etc.) can connect and use these tools.

### 12.2 Evolve existing mock servers

The 3 mock MCP servers (`MockSalesforceMCPServer`, `MockServiceNowMCPServer`, `MockSurveyMCPServer`) currently generate synthetic data. Evolution path:

1. **Now:** Mock servers with synthetic data (for development/demo)
2. **Phase 5:** Real adapters for Salesforce/ServiceNow via REST API
3. **Later:** Customer-provided MCP servers replace both mocks and adapters

The adapter pattern supports all three modes — the `provider` field in `customer_action_bindings` determines which path to take.

---

## Architecture Summary

After all phases are complete, the data flow is:

```
                                ┌─────────────────────────┐
                                │   KPI Threshold Check    │
                                │  (periodic evaluation)   │
                                └──────────┬──────────────┘
                                           │ breach detected
                                           ▼
                                ┌─────────────────────────┐
                                │  PlaybookTriggerValidator │
                                │  (Phase 2 — LLM gate)    │
                                │                           │
                                │  SignalAnalystAgent ──────┤──→ Qdrant signals
                                │  DecisionMatrix ─────────┤──→ Quant + Qual correlation
                                │                           │
                                │  Output: approved/rejected│
                                └──────────┬──────────────┘
                                           │ approved
                                           ▼
                                ┌─────────────────────────┐
                                │     PlaybookEngine       │
                                │  (Phase 7 — execution)   │
                                └──────┬──────────┬───────┘
                                       │          │
                          mcp_direct   │          │  workflow
                                       ▼          ▼
                              ┌──────────┐  ┌──────────────┐
                              │  Action   │  │  Playbook     │
                              │  Router   │  │  Orchestrator │
                              │ (Phase 3) │  │  (existing)   │
                              └────┬─────┘  └──────┬───────┘
                                   │               │
                         ┌─────────┼─────────┐     │ webhook
                         ▼         ▼         ▼     ▼
                    ┌────────┐ ┌───────┐ ┌───────┐ ┌──────┐
                    │  Jira  │ │ Slack │ │ SF    │ │  n8n │
                    │Adapter │ │Adapter│ │Adapter│ │      │
                    └────────┘ └───────┘ └───────┘ └──┬───┘
                                                      │
                                                      │ callback
                                                      ▼
                                              Action Router
                                            (n8n calls back to
                                             CS Pulse for each
                                             action step)
```

---

## Testing Strategy

### Unit Tests (per phase)
- Phase 2: Test `PlaybookTriggerValidator` with mock Signal Analyst responses
- Phase 3: Test `ActionRouter` with mock bindings and mock adapters
- Phase 4: Test Jira/Slack adapters with mock HTTP responses (use `responses` library)
- Phase 6: Test `VariableResolver` with all expression types
- Phase 7: Test `PlaybookEngine` with a complete mcp_direct playbook

### Integration Tests
- Full flow: KPI breach → LLM validation → playbook execution → action dispatch
- n8n callback flow: dispatch → n8n webhook → callback → status update
- Binding resolution: same playbook, different customer bindings, different outcomes

### E2E Tests (with mock servers)
- Use existing MCP mock servers as stand-ins for real providers
- Run a complete PB-DC-04 (mcp_direct) end to end
- Run a simplified PB-DC-01 (workflow) with mocked n8n

---

## Dependency Additions

Add to `requirements.txt`:
```
# For MCP server implementation
mcp>=1.0.0

# For YAML playbook definitions
pyyaml>=6.0

# (Already present but verify)
pydantic>=2.5.0
cryptography>=41.0.0
```

---

## Risk Register

| Risk | Impact | Mitigation |
|------|--------|------------|
| LLM validation adds latency to playbook triggers | Medium | Cache results, async execution, skip for cadence-based playbooks |
| LLM validation costs escalate | Medium | Circuit breaker + CostTracker (both exist), per-customer spend caps |
| Jira/Slack API changes | Low | Adapter pattern isolates changes to single file |
| n8n instance unreachable | High | Retry with backoff (exists), fallback to mcp_direct for simple workflows |
| Credential encryption key management | High | Define key rotation strategy in Phase 1.1, use existing `security_utils` |
| Concurrent playbook executions on same account | Medium | Active execution check before dispatch (Phase 7.2) |
| Variable interpolation fails (unresolved `{{var}}`) | Medium | Log warnings, pass through unresolved vars, fail step if critical param missing |
