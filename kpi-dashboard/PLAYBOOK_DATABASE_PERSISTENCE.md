# Playbook Database Persistence

## Overview
All playbook executions and reports are now automatically persisted to the database and will be available across server restarts.

## Database Tables

### 1. `playbook_executions`
Stores all playbook execution data including status, steps, and progress.

**Columns:**
- `id` - Primary key
- `execution_id` - UUID (unique, indexed)
- `customer_id` - Foreign key to customers
- `account_id` - Foreign key to accounts (nullable)
- `playbook_id` - Playbook type (voc-sprint, activation-blitz, etc.)
- `status` - in-progress, completed, failed, cancelled
- `current_step` - Current step being executed
- `execution_data` - JSON: Full execution object with context, results, metadata
- `started_at` - When execution started
- `completed_at` - When execution completed (nullable)
- `created_at` - Record creation timestamp
- `updated_at` - Record update timestamp

**Indexes:**
- `execution_id` (unique)
- `customer_id, playbook_id` (composite)
- `account_id, playbook_id` (composite)
- `status`

### 2. `playbook_reports`
Stores comprehensive playbook execution reports with RACI matrices, outcomes, and exit criteria.

**Columns:**
- `report_id` - Primary key
- `execution_id` - Foreign key to playbook_executions (CASCADE DELETE)
- `customer_id` - Foreign key to customers
- `account_id` - Foreign key to accounts (nullable)
- `playbook_id` - Playbook type
- `playbook_name` - Human-readable playbook name
- `account_name` - Account name for display
- `status` - in-progress, completed, failed
- `report_data` - JSON: Full report with RACI, outcomes, exit criteria
- `duration` - Playbook duration (e.g., "30 days", "90 days")
- `steps_completed` - Number of steps completed
- `total_steps` - Total number of steps (nullable)
- `started_at` - When execution started
- `completed_at` - When execution completed (nullable)
- `report_generated_at` - When report was generated
- `created_at` - Record creation timestamp
- `updated_at` - Record update timestamp

**Indexes:**
- `execution_id` (unique, foreign key with CASCADE DELETE)
- `customer_id, playbook_id` (composite)
- `account_id, playbook_id` (composite)

**Important:** When a playbook execution is deleted, its associated report is automatically deleted due to CASCADE DELETE constraint.

## API Endpoints

### Executions

#### POST `/api/playbooks/executions`
Create a new playbook execution (automatically saved to DB)

**Request:**
```json
{
  "id": "uuid",
  "playbookId": "voc-sprint",
  "customerId": 1,
  "accountId": 123,
  "status": "in-progress",
  "startedAt": "2025-10-14T...",
  "results": [],
  "context": { ... },
  "metadata": { ... }
}
```

**Response:**
```json
{
  "status": "success",
  "execution": { ... },
  "persisted": true
}
```

#### GET `/api/playbooks/executions`
Get all executions for a customer (loaded from DB on first access)

**Query Parameters:**
- `playbookId` - Filter by playbook type
- `status` - Filter by status

#### POST `/api/playbooks/executions/{execution_id}/steps`
Execute a step (automatically updates DB)

**Request:**
```json
{
  "stepId": "step-id",
  "result": { ... }
}
```

**Response:**
```json
{
  "status": "success",
  "execution": { ... },
  "stepResult": { ... },
  "persisted": true
}
```

#### DELETE `/api/playbooks/executions/{execution_id}`
Delete an execution and its associated report (CASCADE DELETE)

**Response:**
```json
{
  "status": "success",
  "message": "Execution and associated report deleted",
  "cascade_delete": true
}
```

### Reports

#### GET `/api/playbooks/executions/{execution_id}/report`
Generate or retrieve a playbook execution report (automatically saved to DB)

**Response:**
```json
{
  "status": "success",
  "report": {
    "execution_id": "uuid",
    "playbook_name": "VoC Sprint",
    "playbook_id": "voc-sprint",
    "account_name": "Acme Corp",
    "duration": "30 days",
    "status": "Completed",
    "themes_discovered": [ ... ],
    "committed_fixes": [ ... ],
    "raci_matrix": { ... },
    "outcomes_achieved": { ... },
    "exit_criteria": [ ... ],
    "executive_summary": "...",
    "next_steps": [ ... ]
  },
  "cached": false,
  "persisted": true
}
```

#### GET `/api/playbooks/reports`
Get all reports for a customer (from database)

**Query Parameters:**
- `playbook_type` - Filter by playbook ID
- `status` - Filter by status

**Response:**
```json
{
  "status": "success",
  "reports": [
    {
      "execution_id": "uuid",
      "playbook_name": "voc-sprint",
      "account_name": "Acme Corp",
      "account_id": 123,
      "status": "completed",
      "started_at": "2025-10-14T...",
      "completed_at": "2025-11-13T...",
      "steps_completed": 12,
      "has_full_report": true,
      "report_generated_at": "2025-11-13T..."
    }
  ],
  "total": 5,
  "total_in_database": 7,
  "deduplicated": 2,
  "source": "database"
}
```

## Automatic Loading

On server startup, both executions and reports are automatically loaded from the database into memory for fast access:

```
✓ Loaded 15 playbook executions from database
✓ Loaded 10 playbook reports from database
```

## Data Flow

### Creating an Execution
1. Frontend calls `POST /api/playbooks/executions`
2. Backend creates execution object
3. **Saved to memory cache**
4. **Saved to database** → `playbook_executions` table
5. Returns execution with `persisted: true`

### Executing a Step
1. Frontend calls `POST /api/playbooks/executions/{id}/steps`
2. Backend updates execution with step result
3. **Updated in memory cache**
4. **Updated in database** → `playbook_executions` table
5. Returns execution with `persisted: true`

### Generating a Report
1. Frontend calls `GET /api/playbooks/executions/{id}/report`
2. Backend generates comprehensive report
3. **Cached in memory**
4. **Saved to database** → `playbook_reports` table
5. Returns report with `persisted: true`

### Deleting an Execution
1. Frontend calls `DELETE /api/playbooks/executions/{id}`
2. Backend removes from memory cache
3. **Deletes from database** → `playbook_executions` table
4. **Automatically deletes report** → CASCADE DELETE to `playbook_reports` table
5. Returns success with `cascade_delete: true`

### Server Restart
1. Server starts
2. **Automatically loads all executions** from `playbook_executions` table
3. **Automatically loads all reports** from `playbook_reports` table
4. All data available immediately in memory
5. Frontend queries work seamlessly

## Migration Scripts

### Initial Migrations
```bash
# Create playbook_reports table
python backend/migrations/add_playbook_reports_table.py

# Create playbook_executions table
python backend/migrations/add_playbook_executions_table.py
```

## Benefits

1. **Persistence**: All playbook data survives server restarts
2. **Performance**: In-memory caching for fast access
3. **Consistency**: Database as source of truth
4. **Cascade Delete**: Deleting an execution automatically removes its report
5. **Queryability**: Can filter and search executions/reports by customer, account, playbook type, status
6. **Timestamps**: Full audit trail with created/updated timestamps
7. **Scalability**: Database indexes optimize query performance

## Report Content

Each report includes:
- **Executive Summary**: High-level overview
- **RACI Matrix**: Responsible, Accountable, Consulted, Informed for each phase
- **Outcomes Achieved**: Baseline vs current metrics with improvement percentages
- **Exit Criteria**: All success criteria with Met/Not Met status and evidence
- **Next Steps**: Recommended follow-up actions
- **Playbook-Specific Data**:
  - VoC Sprint: Themes, customer quotes, committed fixes
  - Activation Blitz: Features activated, training metrics, use cases
  - SLA Stabilizer: Root causes, preventive measures, SLA metrics
  - Renewal Safeguard: Risk assessment, value activities, renewal outcome
  - Expansion Timing: Opportunities, triggers met, value propositions

## Database Schema

```sql
-- Simplified schema representation

CREATE TABLE playbook_executions (
    id INTEGER PRIMARY KEY,
    execution_id VARCHAR(36) UNIQUE NOT NULL,
    customer_id INTEGER NOT NULL,
    account_id INTEGER,
    playbook_id VARCHAR(50) NOT NULL,
    status VARCHAR(20) DEFAULT 'in-progress',
    current_step VARCHAR(100),
    execution_data JSON NOT NULL,
    started_at DATETIME NOT NULL,
    completed_at DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id),
    FOREIGN KEY (account_id) REFERENCES accounts(account_id)
);

CREATE TABLE playbook_reports (
    report_id INTEGER PRIMARY KEY,
    execution_id VARCHAR(36) UNIQUE NOT NULL,
    customer_id INTEGER NOT NULL,
    account_id INTEGER,
    playbook_id VARCHAR(50) NOT NULL,
    playbook_name VARCHAR(100) NOT NULL,
    account_name VARCHAR(200),
    status VARCHAR(20) DEFAULT 'in-progress',
    report_data JSON NOT NULL,
    duration VARCHAR(50),
    steps_completed INTEGER DEFAULT 0,
    total_steps INTEGER,
    started_at DATETIME NOT NULL,
    completed_at DATETIME,
    report_generated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (execution_id) REFERENCES playbook_executions(execution_id) ON DELETE CASCADE,
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id),
    FOREIGN KEY (account_id) REFERENCES accounts(account_id)
);

-- Indexes for performance
CREATE INDEX idx_customer_playbook_exec ON playbook_executions(customer_id, playbook_id);
CREATE INDEX idx_customer_playbook ON playbook_reports(customer_id, playbook_id);
```

## Testing

After server restart:
1. Navigate to "Playbooks" tab
2. All previous executions should be visible
3. Navigate to "Reports" tab
4. All previous reports should be visible
5. Delete a playbook execution
6. Verify its report is also deleted
7. Restart server again
8. Verify deletion persisted

All data is now permanent and survives server restarts! 🎉

