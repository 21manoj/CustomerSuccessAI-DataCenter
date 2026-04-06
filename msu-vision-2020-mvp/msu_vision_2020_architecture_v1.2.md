# MSU Vision 2020 — Alumni Foundation Platform

## Architecture & Design Document

**Version:** 1.2  
**Date:** March 2026  
**Status:** Draft for Review

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Domain Model](#2-domain-model)
3. [Entity Relationship Diagram](#3-entity-relationship-diagram)
4. [State Machines](#4-state-machines)
5. [RBAC Matrix](#5-rbac-matrix)
6. [Milestone Tracking & Visualization](#6-milestone-tracking--visualization)
7. [Application Structure](#7-application-structure)
8. [URL & API Structure](#8-url--api-structure)
9. [Tech Stack](#9-tech-stack)
10. [Infrastructure](#10-infrastructure)
11. [Phase 1 Scope](#11-phase-1-scope)
12. [Open Items](#12-open-items)

---

## 1. Executive Summary

### Purpose

A unified platform for MSU Vision 2020 Alumni Foundation to manage:

- Stakeholder ecosystem (donors, alumni, university partners, volunteers, governance)
- Need-to-project lifecycle (HOD request → donor matching → delivery → success story)
- Fund management with dual-jurisdiction compliance (India CSR + US 501(c)(3))
- Project milestone tracking with visual timeline
- Events (fundraising, lectures, networking)
- Communication tracking (email ingestion, opt-in based)

### Scale

| Metric | Volume |
|--------|--------|
| Active donors/year | ~200 |
| Projects/year | 24-30 |
| Concurrent users | <50 |
| Events/year | ~20-40 (estimated) |
| Governance team | ~20 members |

### Key Design Decisions

| Decision | Resolution |
|----------|------------|
| Auth | Google OAuth via django-allauth |
| Currency | Multi-currency (INR + USD), normalized to USD |
| Funding model | Tracked at both Need and Project level |
| Jurisdiction | Tagged at Contribution (origin) + FundPool (destination) |
| Audit | Field-level change tracking (django-simple-history) |
| Email tracking | Feature-toggled (off by default), BCC/IMAP ingestion, opt-in consent required |
| Media storage | S3-compatible (Cloudflare R2) |
| Deployment | Render (recommended) |
| Approval workflow | Threshold-based routing to Governance Team |
| Milestone visualization | Gantt-style timeline with status indicators |

---

## 2. Domain Model

### Core Entities

```
STAKEHOLDER          — Users and organizations in the ecosystem
    ├── User         — Individual (donor, HOD, alumni, staff, volunteer, finance, governance, auditor)
    └── Organization — Corporate donor, department, CSR partner

NEED                 — Request originated by HOD/Dean
    ├── Funding model (pooled | anchor)
    ├── Scope (department | cross-cutting)
    ├── Jurisdiction (india | us | both)
    └── Approval level (standard | governance)

PROJECT              — Approved initiative fulfilling a Need
    ├── Lead (alumni volunteer)
    ├── Team (volunteers)
    ├── Milestones (with visual timeline)
    └── Approval level (standard | governance)

MILESTONE            — Trackable deliverable within a Project
    ├── Timeline (start_date, due_date, completed_date)
    ├── Status (pending | approved | in_progress | done | cancelled)
    ├── Sequence ordering
    └── Dependencies (optional, Phase 2)

CONTRIBUTION         — Monetary pledge/receipt from donor
    ├── Jurisdiction origin
    └── Allocation to project or fund pool

FUND POOL            — Segregated funds by jurisdiction
    ├── India CSR pool
    └── US 501(c)(3) pool

EXPENSE              — Disbursement against a project
    └── Approval level (standard | finance | governance)

EVENT                — Foundation-organized activity
    ├── Registrations
    ├── Media (photos, videos)
    └── Linked contributions

EMAIL                — Tracked communication (feature-toggled)
    └── Linked to stakeholders, projects, needs

CONSENT              — Opt-in tracking for email ingestion

APPROVAL             — Workflow for high-value items requiring Governance sign-off
```

### Relationships

```
Stakeholder (HOD) ──creates──► Need
Need ──spawns──► Project
Project ──has──► Milestone[] (timeline-tracked)
Stakeholder (Donor) ──funds──► Contribution ──allocates──► Project | FundPool
Project ──has──► Expense[]
Project ──assigned──► Stakeholder (Lead)
Project ──team──► Stakeholder[] (Volunteers)
Event ──has──► Registration[] ──links──► Stakeholder
Event ──has──► Media[]
Event ──raises──► Contribution[]
Email ──links──► Stakeholder[], Project?, Need?
Stakeholder ──grants──► Consent
Need/Project/Expense ──requires──► Approval (if above threshold)
Stakeholder (Governance) ──approves──► Approval
```

---

## 3. Entity Relationship Diagram

```mermaid
erDiagram
    %% ===== STAKEHOLDERS =====
    User ||--o{ UserProfile : has
    User ||--o{ Consent : grants
    User }o--|| Organization : belongs_to
    
    UserProfile {
        int id PK
        int user_id FK
        enum stakeholder_type "donor|hod|alumni|staff|volunteer|finance_controller|governance|auditor"
        enum jurisdiction "india|us|other"
        bool email_opt_in
        datetime created_at
        datetime updated_at
    }
    
    Organization {
        int id PK
        string name
        enum org_type "corporate|department|csr_partner|govt"
        enum jurisdiction "india|us|other"
        datetime created_at
    }
    
    Consent {
        int id PK
        int user_id FK
        enum consent_type "email_tracking"
        datetime granted_at
        datetime revoked_at
    }

    %% ===== NEEDS =====
    Need {
        int id PK
        int created_by_id FK
        int department_id FK "nullable"
        string title
        text description
        enum funding_model "pooled|anchor"
        enum jurisdiction "india|us|both"
        enum scope "department|cross_cutting"
        enum status "draft|cataloged|pending_governance|matched|rejected|closed"
        decimal target_amount
        string target_currency
        bool requires_governance_approval
        datetime created_at
        datetime updated_at
    }
    
    User ||--o{ Need : creates
    Organization ||--o{ Need : department

    %% ===== PROJECTS =====
    Project {
        int id PK
        int need_id FK
        int lead_id FK
        string title
        text description
        enum funding_model "inherited|pooled|anchor"
        enum status "proposed|pending_governance|approved|in_progress|on_hold|completed|rejected"
        decimal budget
        string budget_currency
        bool requires_governance_approval
        date start_date
        date target_end_date
        date actual_end_date
        int progress_percent "computed"
        datetime created_at
        datetime updated_at
    }
    
    Need ||--o{ Project : spawns
    User ||--o{ Project : leads
    
    ProjectTeam {
        int id PK
        int project_id FK
        int user_id FK
        enum role "lead|volunteer"
        datetime joined_at
    }
    
    Project ||--o{ ProjectTeam : has
    User ||--o{ ProjectTeam : member_of

    Milestone {
        int id PK
        int project_id FK
        int assigned_to_id FK "nullable"
        string title
        text description
        date start_date
        date due_date
        date completed_date "nullable"
        enum status "pending|approved|in_progress|done|overdue|cancelled"
        int sequence
        int weight_percent "default 0, for progress calculation"
        text completion_notes "nullable"
        datetime created_at
        datetime updated_at
    }
    
    Project ||--o{ Milestone : has
    User ||--o{ Milestone : assigned_to

    %% ===== FUNDING =====
    FundPool {
        int id PK
        enum jurisdiction "india|us"
        string name
        text description
        datetime created_at
    }
    
    Contribution {
        int id PK
        int donor_id FK
        int project_id FK "nullable"
        int fund_pool_id FK "nullable"
        int event_id FK "nullable"
        int recorded_by_id FK
        decimal amount
        string currency
        decimal amount_usd "normalized"
        enum jurisdiction_origin "india|us|other"
        enum status "pledged|received|allocated|utilized|cancelled"
        date pledge_date
        date received_date
        string reference_number
        text notes
        datetime created_at
    }
    
    User ||--o{ Contribution : donates
    User ||--o{ Contribution : records
    Project ||--o{ Contribution : receives
    FundPool ||--o{ Contribution : pools
    
    Expense {
        int id PK
        int project_id FK
        int fund_pool_id FK
        int requested_by_id FK
        int approved_by_id FK "nullable"
        decimal amount
        string currency
        decimal amount_usd
        string description
        date expense_date
        string receipt_reference
        enum status "pending|pending_governance|approved|disbursed|rejected"
        bool requires_governance_approval
        datetime created_at
    }
    
    Project ||--o{ Expense : incurs
    FundPool ||--o{ Expense : source
    User ||--o{ Expense : requests
    User ||--o{ Expense : approves

    %% ===== APPROVALS =====
    Approval {
        int id PK
        string content_type "need|project|expense"
        int object_id
        int requested_by_id FK
        int approved_by_id FK "nullable"
        enum status "pending|approved|rejected"
        text notes
        datetime requested_at
        datetime resolved_at
    }
    
    User ||--o{ Approval : requests
    User ||--o{ Approval : resolves

    %% ===== EVENTS =====
    Event {
        int id PK
        int organized_by_id FK
        int linked_project_id FK "nullable"
        int linked_need_id FK "nullable"
        string title
        text description
        enum event_type "fundraising|lecture|networking|recognition"
        string venue
        string location
        string virtual_link "nullable"
        datetime start_datetime
        datetime end_datetime
        enum status "draft|published|registration_open|ongoing|completed|archived|cancelled"
        decimal target_amount "nullable"
        enum jurisdiction "india|us|both"
        datetime created_at
    }
    
    User ||--o{ Event : organizes
    Project ||--o{ Event : linked_to
    Need ||--o{ Event : supports
    Event ||--o{ Contribution : raises
    
    EventRegistration {
        int id PK
        int event_id FK
        int user_id FK
        enum role "attendee|speaker|organizer|volunteer"
        datetime registered_at
        bool attended
    }
    
    Event ||--o{ EventRegistration : has
    User ||--o{ EventRegistration : registers
    
    EventMedia {
        int id PK
        int event_id FK
        int uploaded_by_id FK
        string file_url
        enum media_type "photo|video|document|presentation"
        string caption
        datetime uploaded_at
    }
    
    Event ||--o{ EventMedia : has
    User ||--o{ EventMedia : uploads

    %% ===== EMAIL TRACKING (Feature-Toggled) =====
    Email {
        int id PK
        string message_id UK
        int sender_id FK "nullable"
        int linked_project_id FK "nullable"
        int linked_need_id FK "nullable"
        string subject
        text body_text
        text body_html
        datetime received_at
        tsvector search_vector
        datetime created_at
    }
    
    User ||--o{ Email : sends
    Project ||--o{ Email : related_to
    Need ||--o{ Email : related_to
    
    EmailRecipient {
        int id PK
        int email_id FK
        int user_id FK
        enum recipient_type "to|cc|bcc"
    }
    
    Email ||--o{ EmailRecipient : has
    User ||--o{ EmailRecipient : receives

    %% ===== SYSTEM SETTINGS =====
    SystemSetting {
        int id PK
        string key UK
        string value
        text description
    }
```

---

## 4. State Machines

### 4.1 Need Lifecycle

```mermaid
stateDiagram-v2
    [*] --> Draft: HOD creates
    Draft --> Cataloged: Foundation reviews
    Draft --> Rejected: Not viable
    Cataloged --> PendingGovernance: Above threshold
    Cataloged --> Matched: Below threshold + donor identified
    PendingGovernance --> Matched: Governance approves
    PendingGovernance --> Rejected: Governance rejects
    Matched --> Closed: Project created
    Rejected --> [*]
    Closed --> [*]
    
    note right of Draft: Editable by HOD
    note right of PendingGovernance: High-value needs
    note right of Matched: Ready for project creation
```

**Transitions:**

| From | To | Actor | Conditions |
|------|----|-------|------------|
| Draft | Cataloged | Foundation Admin | Required fields complete |
| Draft | Rejected | Foundation Admin | Not aligned with mission |
| Cataloged | PendingGovernance | System | target_amount ≥ threshold |
| Cataloged | Matched | Foundation Admin | Below threshold, ≥1 donor linked |
| PendingGovernance | Matched | Governance Team | Approved |
| PendingGovernance | Rejected | Governance Team | Rejected |
| Matched | Closed | Foundation Admin | Project created |

---

### 4.2 Project Lifecycle

```mermaid
stateDiagram-v2
    [*] --> Proposed: From matched Need
    Proposed --> PendingGovernance: Above threshold
    Proposed --> Approved: Below threshold
    PendingGovernance --> Approved: Governance approves
    PendingGovernance --> Rejected: Governance rejects
    Approved --> InProgress: Work begins
    Approved --> OnHold: Funding delayed
    InProgress --> OnHold: Issues arise
    OnHold --> InProgress: Resolved
    InProgress --> Completed: All milestones done
    Rejected --> [*]
    Completed --> [*]
    
    note right of Proposed: Lead assigned
    note right of PendingGovernance: High-value projects
    note right of Approved: Budget confirmed
    note right of InProgress: Milestones tracked visually
```

**Transitions:**

| From | To | Actor | Conditions |
|------|----|-------|------------|
| Proposed | PendingGovernance | System | budget ≥ threshold |
| Proposed | Approved | Foundation Admin | Below threshold, lead assigned |
| PendingGovernance | Approved | Governance Team | Approved |
| PendingGovernance | Rejected | Governance Team | Rejected |
| Approved | InProgress | Project Lead | At least 1 milestone created |
| Approved | OnHold | Foundation Admin | Funding not received |
| InProgress | OnHold | Foundation Admin | — |
| OnHold | InProgress | Foundation Admin | Issue resolved |
| InProgress | Completed | Foundation Admin | All milestones done |

---

### 4.3 Milestone Lifecycle

```mermaid
stateDiagram-v2
    [*] --> Pending: Created by Lead
    Pending --> Approved: Scope confirmed
    Approved --> InProgress: Work starts
    InProgress --> Done: Deliverable accepted
    InProgress --> Overdue: Past due_date, not done
    Overdue --> Done: Completed late
    Pending --> Cancelled: Scope change
    Approved --> Cancelled: Scope change
    Cancelled --> [*]
    Done --> [*]
    
    note right of Pending: Awaiting approval
    note right of InProgress: Tracked on timeline
    note right of Overdue: Alert triggered
    note right of Done: Completion logged
```

**Transitions:**

| From | To | Actor | Conditions |
|------|----|-------|------------|
| Pending | Approved | Foundation Admin / Lead | Scope validated |
| Approved | InProgress | Project Lead | Work commenced |
| InProgress | Done | Project Lead | Deliverable submitted & accepted |
| InProgress | Overdue | System | due_date passed, status != Done |
| Overdue | Done | Project Lead | Completed late |
| Pending/Approved | Cancelled | Foundation Admin | Scope change |

---

### 4.4 Contribution Lifecycle

```mermaid
stateDiagram-v2
    [*] --> Pledged: Donor commits
    Pledged --> Received: Funds arrive
    Pledged --> Cancelled: Donor withdraws
    Received --> Allocated: Assigned to project/pool
    Allocated --> Utilized: Expenses disbursed
    Cancelled --> [*]
    Utilized --> [*]
    
    note right of Pledged: Commitment recorded
    note right of Received: Bank confirmed
    note right of Allocated: Jurisdiction tagged
```

**Transitions:**

| From | To | Actor | Conditions |
|------|----|-------|------------|
| Pledged | Received | Finance Controller | Bank confirmation |
| Pledged | Cancelled | Finance Controller | Donor request |
| Received | Allocated | Finance Controller | Project or pool assigned |
| Allocated | Utilized | System | Expenses ≥ contribution |

---

### 4.5 Expense Lifecycle

```mermaid
stateDiagram-v2
    [*] --> Pending: Lead requests
    Pending --> PendingGovernance: Above threshold
    Pending --> Approved: Below threshold
    PendingGovernance --> Approved: Governance approves
    PendingGovernance --> Rejected: Governance rejects
    Approved --> Disbursed: Finance disburses
    Pending --> Rejected: Finance rejects
    Rejected --> [*]
    Disbursed --> [*]
    
    note right of Pending: Awaiting Finance review
    note right of PendingGovernance: High-value expense
    note right of Approved: Ready for disbursement
```

**Transitions:**

| From | To | Actor | Conditions |
|------|----|-------|------------|
| Pending | PendingGovernance | System | amount ≥ threshold |
| Pending | Approved | Finance Controller | Below threshold, valid |
| Pending | Rejected | Finance Controller | Invalid/insufficient funds |
| PendingGovernance | Approved | Governance Team | Approved |
| PendingGovernance | Rejected | Governance Team | Rejected |
| Approved | Disbursed | Finance Controller | Funds released |

---

### 4.6 Event Lifecycle

```mermaid
stateDiagram-v2
    [*] --> Draft: Admin creates
    Draft --> Published: Details finalized
    Published --> RegistrationOpen: Registration enabled
    RegistrationOpen --> Ongoing: Event starts
    Ongoing --> Completed: Event ends
    Completed --> Archived: Media uploaded, closed
    Draft --> Cancelled: Event dropped
    Published --> Cancelled: Event dropped
    RegistrationOpen --> Cancelled: Event dropped
    Cancelled --> [*]
    Archived --> [*]
    
    note right of RegistrationOpen: Stakeholders can register
    note right of Completed: Attendance marked
    note right of Archived: Read-only
```

---

## 5. RBAC Matrix

### 5.1 Roles

| Role | Count | Description |
|------|-------|-------------|
| **Foundation Admin** | Few | Full platform access, manages all entities |
| **HOD / Dean** | Many | Creates needs for their department, views project status |
| **Donor** | ~200/yr | Views their contributions, matched projects, events |
| **Project Lead** | ~25/yr | Manages assigned project, milestones, team |
| **Volunteer** | Many | Views assigned project tasks, updates own progress |
| **Finance Controller** | Few | Fund accounting, contribution management, expense approval |
| **Governance Team** | ~20 | Strategic oversight, high-value approvals, policy decisions |
| **Auditor** | Few | Read-only access to all data for compliance review |

### 5.2 Permission Matrix

| Resource | Action | Admin | HOD | Donor | Lead | Volunteer | Finance | Governance | Auditor |
|----------|--------|-------|-----|-------|------|-----------|---------|------------|---------|
| **Stakeholder** | Create | ✅ | — | — | — | — | — | — | — |
| | View all | ✅ | — | — | — | — | — | ✅ | ✅ |
| | View own | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| | Edit own | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | — |
| | Delete | ✅ | — | — | — | — | — | — | — |
| **Organization** | CRUD | ✅ | — | — | — | — | — | — | — |
| | View | ✅ | own dept | — | — | — | — | ✅ | ✅ |
| **Need** | Create | ✅ | ✅ | — | — | — | — | — | — |
| | View all | ✅ | — | — | — | — | ✅ | ✅ | ✅ |
| | View own dept | ✅ | ✅ | — | — | — | — | — | — |
| | View matched | ✅ | ✅ | ✅ | ✅ | — | ✅ | ✅ | ✅ |
| | Edit | ✅ | own draft | — | — | — | — | — | — |
| | Change status | ✅ | — | — | — | — | — | — | — |
| | **Approve (high-value)** | — | — | — | — | — | — | ✅ | — |
| **Project** | Create | ✅ | — | — | — | — | — | — | — |
| | View all | ✅ | — | — | — | — | ✅ | ✅ | ✅ |
| | View funded | ✅ | — | ✅ | — | — | ✅ | ✅ | — |
| | View assigned | ✅ | — | — | ✅ | ✅ | — | — | — |
| | Edit | ✅ | — | — | ✅ | — | — | — | — |
| | Change status | ✅ | — | — | — | — | — | — | — |
| | **Approve (high-value)** | — | — | — | — | — | — | ✅ | — |
| | **View timeline** | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| **Milestone** | Create | ✅ | — | — | ✅ | — | — | — | — |
| | View | ✅ | — | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| | Edit | ✅ | — | — | ✅ | — | — | — | — |
| | Change status | ✅ | — | — | ✅ | — | — | — | — |
| | Assign volunteer | ✅ | — | — | ✅ | — | — | — | — |
| **Contribution** | Create | ✅ | — | — | — | — | ✅ | — | — |
| | View all | ✅ | — | — | — | — | ✅ | ✅ | ✅ |
| | View own | ✅ | — | ✅ | — | — | — | — | — |
| | View project | ✅ | — | — | ✅ | — | ✅ | ✅ | — |
| | Edit | ✅ | — | — | — | — | ✅ | — | — |
| | Change status | ✅ | — | — | — | — | ✅ | — | — |
| **FundPool** | Create/Edit | ✅ | — | — | — | — | ✅ | — | — |
| | View | ✅ | — | — | — | — | ✅ | ✅ | ✅ |
| **Expense** | Create | ✅ | — | — | ✅ | — | ✅ | — | — |
| | View all | ✅ | — | — | — | — | ✅ | ✅ | ✅ |
| | View project | ✅ | — | — | ✅ | — | ✅ | ✅ | — |
| | Approve (standard) | ✅ | — | — | — | — | ✅ | — | — |
| | **Approve (high-value)** | — | — | — | — | — | — | ✅ | — |
| | Disburse | ✅ | — | — | — | — | ✅ | — | — |
| **Event** | Create | ✅ | — | — | — | — | — | — | — |
| | View | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| | Edit | ✅ | — | — | organizer | — | — | — | — |
| | Change status | ✅ | — | — | — | — | — | — | — |
| | Register | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | — |
| **EventMedia** | Upload | ✅ | — | — | organizer | event vol | — | — | — |
| | View | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| | Delete | ✅ | — | — | organizer | — | — | — | — |
| **Email** | Search all | ✅ | — | — | — | — | — | ✅ | ✅ |
| | Search own project | ✅ | — | — | ✅ | — | — | — | — |
| | View | ✅ | — | — | own project | — | — | ✅ | ✅ |
| **Consent** | Grant/Revoke own | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | — |
| | View all | ✅ | — | — | — | — | — | ✅ | ✅ |
| **Audit Log** | View | ✅ | — | — | — | — | ✅ | ✅ | ✅ |
| **Compliance Reports** | Generate | ✅ | — | — | — | — | ✅ | ✅ | ✅ |
| **System Settings** | Edit | ✅ | — | — | — | — | — | — | — |
| | View | ✅ | — | — | — | — | ✅ | ✅ | ✅ |
| **Dashboard** | View all projects | ✅ | — | — | — | — | ✅ | ✅ | ✅ |
| | View own projects | ✅ | ✅ | ✅ | ✅ | ✅ | — | — | — |

### 5.3 Approval Thresholds

Configurable via System Settings:

| Item | Standard Approval | Governance Approval Required |
|------|-------------------|------------------------------|
| Need (target amount) | < ₹10,00,000 / $12,000 | ≥ ₹10,00,000 / $12,000 |
| Project (budget) | < ₹10,00,000 / $12,000 | ≥ ₹10,00,000 / $12,000 |
| Expense (single) | < ₹2,00,000 / $2,500 | ≥ ₹2,00,000 / $2,500 |

*Thresholds are illustrative — configure based on Foundation policy.*

### 5.4 Governance Workflow

```
┌─────────────────────────────────────────────────────────────────┐
│                    HIGH-VALUE ITEM CREATED                      │
│              (Need / Project / Expense ≥ threshold)             │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                 STATUS: PENDING_GOVERNANCE                      │
│                                                                 │
│  • Notification sent to Governance Team (email + in-app)        │
│  • Item visible in Governance Dashboard                         │
│  • Standard workflow paused                                     │
└─────────────────────────────────────────────────────────────────┘
                              │
              ┌───────────────┴───────────────┐
              │                               │
              ▼                               ▼
┌──────────────────────┐         ┌──────────────────────┐
│      APPROVED        │         │      REJECTED        │
│                      │         │                      │
│  • Governance member │         │  • Governance member │
│    records approval  │         │    records rejection │
│  • Notes required    │         │  • Notes required    │
│  • Workflow resumes  │         │  • Workflow ends     │
└──────────────────────┘         └──────────────────────┘
```

---

## 6. Milestone Tracking & Visualization

### 6.1 Overview

The platform provides visual milestone tracking for all projects, enabling stakeholders to monitor progress at a glance.

| Feature | Description |
|---------|-------------|
| **Gantt-style timeline** | Horizontal bar chart showing milestones on a calendar timeline |
| **Status indicators** | Color-coded by status (see below) |
| **Progress rollup** | Project-level progress bar (% milestones completed, weighted) |
| **Overdue alerts** | Automatic flagging when milestones pass due date |
| **Assignment tracking** | Optional assignment of milestones to volunteers |
| **Dashboard rollup** | All-projects view for Admin, Finance, Governance |

### 6.2 Milestone Model Fields

| Field | Type | Description |
|-------|------|-------------|
| `project_id` | FK | Parent project |
| `title` | string | Short name (e.g., "Site Survey") |
| `description` | text | Detailed scope |
| `start_date` | date | When work begins |
| `due_date` | date | Target completion |
| `completed_date` | date (nullable) | Actual completion |
| `status` | enum | pending, approved, in_progress, done, overdue, cancelled |
| `sequence` | int | Display order |
| `weight_percent` | int | Contribution to project progress (default 0 = equal weight) |
| `assigned_to_id` | FK (nullable) | Volunteer responsible |
| `completion_notes` | text (nullable) | Notes on deliverable |

### 6.3 Status Color Coding

| Status | Color | Hex | Description |
|--------|-------|-----|-------------|
| Pending | Gray | `#9CA3AF` | Not yet started |
| Approved | Blue | `#3B82F6` | Scope confirmed, ready to start |
| In Progress | Amber | `#F59E0B` | Work underway |
| Done | Green | `#10B981` | Completed |
| Overdue | Red | `#EF4444` | Past due date, not done |
| Cancelled | Slate | `#64748B` | Removed from scope |

### 6.4 Progress Calculation

```python
def calculate_project_progress(project):
    milestones = project.milestones.exclude(status='cancelled')
    
    if not milestones.exists():
        return 0
    
    # If weights are set, use weighted average
    total_weight = milestones.aggregate(Sum('weight_percent'))['weight_percent__sum']
    
    if total_weight and total_weight > 0:
        done_weight = milestones.filter(status='done').aggregate(
            Sum('weight_percent')
        )['weight_percent__sum'] or 0
        return int((done_weight / total_weight) * 100)
    
    # Otherwise, equal weight per milestone
    total = milestones.count()
    done = milestones.filter(status='done').count()
    return int((done / total) * 100)
```

### 6.5 Visual Wireframes

#### 6.5.1 Project Detail — Milestone Timeline

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│  PROJECT: Science Lab Renovation                                                │
│  Lead: Raj Kumar  •  Budget: ₹25,00,000  •  Status: In Progress                │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  PROGRESS  ████████████████░░░░░░░░░░  67%                                     │
│                                                                                 │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  MILESTONE TIMELINE                                                             │
│  ─────────────────────────────────────────────────────────────────────────────  │
│                                                                                 │
│                        MAR        APR        MAY        JUN        JUL         │
│                        ├──────────┼──────────┼──────────┼──────────┤           │
│                                                                                 │
│  1. Site Survey        ████████                                    ✅ Done      │
│     Assigned: Amit P   ▲ Mar 1   ▲ Mar 15                                      │
│                                                                                 │
│  2. Architect Plans            ██████████████                      ✅ Done      │
│     Assigned: —                 ▲ Mar 20      ▲ Apr 15                         │
│                                                                                 │
│  3. Procurement                          ████████████░░░░░░        🔄 In Progress
│     Assigned: Neha G                      ▲ Apr 10      ▲ May 20               │
│                                                                                 │
│  4. Construction                                      ░░░░░░░░░░░░░ ⏳ Pending  │
│     Assigned: —                                        ▲ May 15   ▲ Jun 30     │
│                                                                                 │
│  5. Handover                                                    ░░░░ ⏳ Pending │
│     Assigned: —                                                  ▲ Jul 1  ▲15  │
│                                                                                 │
│                        TODAY ────────────────────▼                              │
│                                                                                 │
├─────────────────────────────────────────────────────────────────────────────────┤
│  ⚠️  ALERTS                                                                     │
│  • Milestone 3 (Procurement) is 5 days behind schedule                         │
│  • Milestone 4 (Construction) has no assignee                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
│                                                                                 │
│  [ + Add Milestone ]    [ Edit Timeline ]    [ Export PDF ]                    │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

#### 6.5.2 Dashboard — All Projects Rollup

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│  ALL PROJECTS — MILESTONE TRACKER                                     Q2 2026  │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  ┌─────────────────┬───────────────┬────────────────┬──────────┬─────────────┐ │
│  │ PROJECT         │ LEAD          │ PROGRESS       │ STATUS   │ ALERTS      │ │
│  ├─────────────────┼───────────────┼────────────────┼──────────┼─────────────┤ │
│  │ Science Lab     │ Raj Kumar     │ ████████░░ 67% │ On Track │             │ │
│  │ Renovation      │               │                │          │             │ │
│  ├─────────────────┼───────────────┼────────────────┼──────────┼─────────────┤ │
│  │ Merit Scholar-  │ Priya Shah    │ ██████████ 100%│ Complete │             │ │
│  │ ships 2026      │               │                │          │             │ │
│  ├─────────────────┼───────────────┼────────────────┼──────────┼─────────────┤ │
│  │ Library         │ Amit Patel    │ █████░░░░░ 50% │ At Risk  │ ⚠️ 2 overdue│ │
│  │ Digitization    │               │                │          │             │ │
│  ├─────────────────┼───────────────┼────────────────┼──────────┼─────────────┤ │
│  │ Sports Complex  │ Neha Gupta    │ ██░░░░░░░░ 20% │ On Track │             │ │
│  │ Phase 1         │               │                │          │             │ │
│  └─────────────────┴───────────────┴────────────────┴──────────┴─────────────┘ │
│                                                                                 │
│  SUMMARY                                                                        │
│  ────────────────────────────────────────────────────────────────────────────── │
│  Total Projects: 4   │   On Track: 2   │   At Risk: 1   │   Completed: 1       │
│  Overdue Milestones: 2   │   Pending Governance: 0                              │
│                                                                                 │
├─────────────────────────────────────────────────────────────────────────────────┤
│  FILTERS: [ All Statuses ▼ ]  [ All Leads ▼ ]  [ Date Range ▼ ]  [ Search 🔍 ] │
└─────────────────────────────────────────────────────────────────────────────────┘
```

#### 6.5.3 Milestone Card (Detail Modal)

```
┌─────────────────────────────────────────────────────────────────┐
│  MILESTONE DETAILS                                        [ × ] │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Title:        Procurement                                      │
│  Project:      Science Lab Renovation                           │
│  Sequence:     3 of 5                                           │
│                                                                 │
│  ─────────────────────────────────────────────────────────────  │
│                                                                 │
│  Status:       🔄 In Progress                                   │
│  Assigned To:  Neha Gupta                                       │
│                                                                 │
│  Start Date:   Apr 10, 2026                                     │
│  Due Date:     May 20, 2026                                     │
│  Days Left:    12 days                                          │
│                                                                 │
│  ─────────────────────────────────────────────────────────────  │
│                                                                 │
│  Description:                                                   │
│  Procure lab equipment from approved vendors. Includes:         │
│  - Microscopes (10 units)                                       │
│  - Centrifuges (5 units)                                        │
│  - Safety equipment                                             │
│                                                                 │
│  ─────────────────────────────────────────────────────────────  │
│                                                                 │
│  HISTORY                                                        │
│  Apr 10 — Status changed to In Progress (by Raj Kumar)          │
│  Apr 05 — Status changed to Approved (by Admin)                 │
│  Apr 01 — Milestone created (by Raj Kumar)                      │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│  [ Edit ]    [ Mark as Done ]    [ Reassign ]    [ Cancel ]     │
└─────────────────────────────────────────────────────────────────┘
```

### 6.6 Implementation Approach

| Layer | Technology | Notes |
|-------|------------|-------|
| **Backend** | Django model + DRF serializer | Milestone model with computed fields |
| **Timeline Rendering** | [Frappe Gantt](https://frappe.io/gantt) or custom SVG | Lightweight, no heavy JS frameworks |
| **Interactivity** | HTMX + Alpine.js | Inline status updates, modal editing |
| **Progress Bar** | Tailwind CSS | Animated progress component |
| **Alerts** | Celery Beat | Daily job to flag overdue milestones |
| **Export** | WeasyPrint | PDF export of project timeline |

### 6.7 Alerts & Notifications

| Trigger | Recipients | Channel |
|---------|------------|---------|
| Milestone approaching due (3 days) | Project Lead, Assignee | In-app + Email |
| Milestone overdue | Project Lead, Assignee, Admin | In-app + Email |
| All milestones done | Project Lead, Admin, Governance | In-app + Email |
| Milestone status changed | Project Lead | In-app |

---

## 7. Application Structure

```
msu_vision_2020/
├── manage.py
├── pyproject.toml
├── requirements/
│   ├── base.txt
│   ├── dev.txt
│   └── prod.txt
│
├── config/                          # Project configuration
│   ├── __init__.py
│   ├── settings/
│   │   ├── __init__.py
│   │   ├── base.py
│   │   ├── dev.py
│   │   └── prod.py
│   ├── urls.py
│   ├── wsgi.py
│   └── asgi.py
│
├── apps/
│   ├── __init__.py
│   │
│   ├── core/                        # Shared utilities
│   │   ├── __init__.py
│   │   ├── models.py               # Abstract base models (audit mixin)
│   │   ├── middleware.py           # Request context, feature flags
│   │   ├── permissions.py          # Base permission classes
│   │   ├── utils.py                # Currency conversion, helpers
│   │   ├── feature_flags.py        # Feature toggle registry
│   │   └── thresholds.py           # Approval threshold logic
│   │
│   ├── stakeholders/               # Users, orgs, RBAC
│   │   ├── __init__.py
│   │   ├── models.py               # User, UserProfile, Organization
│   │   ├── admin.py
│   │   ├── views.py
│   │   ├── forms.py
│   │   ├── urls.py
│   │   ├── permissions.py          # Role-based permissions
│   │   ├── signals.py              # Post-save hooks
│   │   └── templates/
│   │       └── stakeholders/
│   │
│   ├── needs/                      # Need catalog
│   │   ├── __init__.py
│   │   ├── models.py               # Need
│   │   ├── admin.py
│   │   ├── views.py
│   │   ├── forms.py
│   │   ├── urls.py
│   │   ├── state_machine.py        # Need transitions
│   │   └── templates/
│   │       └── needs/
│   │
│   ├── projects/                   # Projects, milestones, teams
│   │   ├── __init__.py
│   │   ├── models.py               # Project, Milestone, ProjectTeam
│   │   ├── admin.py
│   │   ├── views.py
│   │   ├── forms.py
│   │   ├── urls.py
│   │   ├── state_machine.py        # Project, Milestone transitions
│   │   ├── progress.py             # Progress calculation logic
│   │   ├── timeline.py             # Gantt data preparation
│   │   ├── alerts.py               # Overdue detection
│   │   └── templates/
│   │       └── projects/
│   │           ├── project_detail.html
│   │           ├── project_list.html
│   │           ├── milestone_timeline.html
│   │           ├── milestone_card.html
│   │           └── dashboard_rollup.html
│   │
│   ├── funding/                    # Contributions, pools, expenses
│   │   ├── __init__.py
│   │   ├── models.py               # Contribution, FundPool, Expense
│   │   ├── admin.py
│   │   ├── views.py
│   │   ├── forms.py
│   │   ├── urls.py
│   │   ├── state_machine.py        # Contribution, Expense transitions
│   │   ├── currency.py             # Multi-currency handling
│   │   └── templates/
│   │       └── funding/
│   │
│   ├── events/                     # Events, registrations, media
│   │   ├── __init__.py
│   │   ├── models.py               # Event, EventRegistration, EventMedia
│   │   ├── admin.py
│   │   ├── views.py
│   │   ├── forms.py
│   │   ├── urls.py
│   │   ├── state_machine.py        # Event transitions
│   │   └── templates/
│   │       └── events/
│   │
│   ├── approvals/                  # Governance approval workflow
│   │   ├── __init__.py
│   │   ├── models.py               # Approval
│   │   ├── admin.py
│   │   ├── views.py
│   │   ├── urls.py
│   │   ├── signals.py              # Auto-create approval on threshold
│   │   └── templates/
│   │       └── approvals/
│   │
│   ├── compliance/                 # Audit, consent, reporting
│   │   ├── __init__.py
│   │   ├── models.py               # Consent
│   │   ├── admin.py
│   │   ├── views.py                # Audit log viewer
│   │   ├── urls.py
│   │   └── templates/
│   │       └── compliance/
│   │
│   ├── email_tracker/              # Email ingestion (feature-toggled)
│   │   ├── __init__.py
│   │   ├── models.py               # Email, EmailRecipient
│   │   ├── admin.py
│   │   ├── views.py                # Search interface
│   │   ├── urls.py
│   │   ├── ingest.py               # IMAP ingestion logic
│   │   ├── tasks.py                # Celery tasks
│   │   ├── search.py               # Full-text search helpers
│   │   └── templates/
│   │       └── email_tracker/
│   │
│   └── dashboard/                  # Cross-module dashboards
│       ├── __init__.py
│       ├── views.py                # Home, project rollup, governance queue
│       ├── urls.py
│       └── templates/
│           └── dashboard/
│               ├── home.html
│               ├── project_rollup.html
│               └── governance_queue.html
│
├── templates/                      # Global templates
│   ├── base.html
│   ├── includes/
│   │   ├── navbar.html
│   │   ├── sidebar.html
│   │   ├── messages.html
│   │   └── progress_bar.html
│   └── registration/               # allauth overrides
│       ├── login.html
│       └── logout.html
│
├── static/
│   ├── css/
│   │   └── timeline.css            # Gantt styling
│   ├── js/
│   │   ├── timeline.js             # Gantt interactivity
│   │   └── alpine-components.js
│   └── img/
│
└── media/                          # Local dev only; S3 in prod
```

---

## 8. URL & API Structure

### 8.1 URL Patterns

```python
# config/urls.py

urlpatterns = [
    # Admin
    path("admin/", admin.site.urls),
    
    # Auth (Google OAuth)
    path("accounts/", include("allauth.urls")),
    
    # Dashboard
    path("", include("apps.dashboard.urls")),
    
    # Apps
    path("stakeholders/", include("apps.stakeholders.urls")),
    path("needs/", include("apps.needs.urls")),
    path("projects/", include("apps.projects.urls")),
    path("funding/", include("apps.funding.urls")),
    path("events/", include("apps.events.urls")),
    path("approvals/", include("apps.approvals.urls")),
    path("compliance/", include("apps.compliance.urls")),
    path("emails/", include("apps.email_tracker.urls")),
]
```

### 8.2 Per-App URL Structure

#### Dashboard

| URL | View | Method | Description |
|-----|------|--------|-------------|
| `/` | `HomeView` | GET | Role-based home dashboard |
| `/projects/rollup/` | `ProjectRollupView` | GET | All projects milestone tracker |
| `/governance/queue/` | `GovernanceQueueView` | GET | Pending governance approvals |

#### Stakeholders

| URL | View | Method | Description |
|-----|------|--------|-------------|
| `/stakeholders/` | `StakeholderListView` | GET | List all stakeholders |
| `/stakeholders/create/` | `StakeholderCreateView` | GET, POST | Onboard new user |
| `/stakeholders/<id>/` | `StakeholderDetailView` | GET | View profile |
| `/stakeholders/<id>/edit/` | `StakeholderUpdateView` | GET, POST | Edit profile |
| `/stakeholders/<id>/offboard/` | `StakeholderOffboardView` | POST | Deactivate user |
| `/organizations/` | `OrganizationListView` | GET | List organizations |
| `/organizations/create/` | `OrganizationCreateView` | GET, POST | Add organization |

#### Needs

| URL | View | Method | Description |
|-----|------|--------|-------------|
| `/needs/` | `NeedListView` | GET | List needs (filtered by role) |
| `/needs/create/` | `NeedCreateView` | GET, POST | HOD creates need |
| `/needs/<id>/` | `NeedDetailView` | GET | View need details |
| `/needs/<id>/edit/` | `NeedUpdateView` | GET, POST | Edit need |
| `/needs/<id>/transition/` | `NeedTransitionView` | POST | Change status (HTMX) |
| `/needs/<id>/match/` | `NeedMatchDonorView` | GET, POST | Link donor(s) |

#### Projects

| URL | View | Method | Description |
|-----|------|--------|-------------|
| `/projects/` | `ProjectListView` | GET | List projects |
| `/projects/create/<need_id>/` | `ProjectCreateView` | GET, POST | Create from need |
| `/projects/<id>/` | `ProjectDetailView` | GET | View project + timeline |
| `/projects/<id>/edit/` | `ProjectUpdateView` | GET, POST | Edit project |
| `/projects/<id>/transition/` | `ProjectTransitionView` | POST | Change status |
| `/projects/<id>/team/` | `ProjectTeamView` | GET, POST | Manage team |
| `/projects/<id>/timeline/` | `ProjectTimelineView` | GET | Gantt timeline (HTMX partial) |
| `/projects/<id>/timeline/export/` | `ProjectTimelineExportView` | GET | PDF export |
| `/projects/<id>/milestones/` | `MilestoneListView` | GET | List milestones |
| `/projects/<id>/milestones/create/` | `MilestoneCreateView` | GET, POST | Add milestone |
| `/projects/<id>/milestones/reorder/` | `MilestoneReorderView` | POST | Update sequence |
| `/milestones/<id>/` | `MilestoneDetailView` | GET | View milestone card |
| `/milestones/<id>/edit/` | `MilestoneUpdateView` | GET, POST | Edit milestone |
| `/milestones/<id>/transition/` | `MilestoneTransitionView` | POST | Change status (HTMX) |
| `/milestones/<id>/assign/` | `MilestoneAssignView` | POST | Assign volunteer |

#### Funding

| URL | View | Method | Description |
|-----|------|--------|-------------|
| `/funding/contributions/` | `ContributionListView` | GET | List contributions |
| `/funding/contributions/create/` | `ContributionCreateView` | GET, POST | Record contribution |
| `/funding/contributions/<id>/` | `ContributionDetailView` | GET | View details |
| `/funding/contributions/<id>/transition/` | `ContributionTransitionView` | POST | Change status |
| `/funding/pools/` | `FundPoolListView` | GET | View fund pools |
| `/funding/expenses/` | `ExpenseListView` | GET | List expenses |
| `/funding/expenses/create/` | `ExpenseCreateView` | GET, POST | Record expense |
| `/funding/expenses/<id>/approve/` | `ExpenseApproveView` | POST | Approve expense |
| `/funding/expenses/<id>/disburse/` | `ExpenseDisburseView` | POST | Mark disbursed |

#### Events

| URL | View | Method | Description |
|-----|------|--------|-------------|
| `/events/` | `EventListView` | GET | List events |
| `/events/create/` | `EventCreateView` | GET, POST | Create event |
| `/events/<id>/` | `EventDetailView` | GET | View event |
| `/events/<id>/edit/` | `EventUpdateView` | GET, POST | Edit event |
| `/events/<id>/transition/` | `EventTransitionView` | POST | Change status |
| `/events/<id>/register/` | `EventRegisterView` | POST | Register for event |
| `/events/<id>/attendance/` | `EventAttendanceView` | GET, POST | Mark attendance |
| `/events/<id>/media/` | `EventMediaListView` | GET | View media |
| `/events/<id>/media/upload/` | `EventMediaUploadView` | POST | Upload media |

#### Approvals

| URL | View | Method | Description |
|-----|------|--------|-------------|
| `/approvals/` | `ApprovalListView` | GET | List pending approvals |
| `/approvals/<id>/` | `ApprovalDetailView` | GET | View approval request |
| `/approvals/<id>/approve/` | `ApprovalApproveView` | POST | Approve item |
| `/approvals/<id>/reject/` | `ApprovalRejectView` | POST | Reject item |

#### Compliance

| URL | View | Method | Description |
|-----|------|--------|-------------|
| `/compliance/audit-log/` | `AuditLogView` | GET | View audit trail |
| `/compliance/consents/` | `ConsentListView` | GET | View consents |
| `/compliance/consent/grant/` | `ConsentGrantView` | POST | Grant consent |
| `/compliance/consent/revoke/` | `ConsentRevokeView` | POST | Revoke consent |

#### Email Tracker (Feature-Toggled)

| URL | View | Method | Description |
|-----|------|--------|-------------|
| `/emails/` | `EmailSearchView` | GET | Search emails |
| `/emails/<id>/` | `EmailDetailView` | GET | View email |
| `/emails/<id>/link/` | `EmailLinkView` | POST | Link to project/need |

---

## 9. Tech Stack

### 9.1 Pinned Versions

| Component | Version | Notes |
|-----------|---------|-------|
| Python | 3.12.x | Latest stable |
| Django | 5.1.x | LTS candidate |
| Django REST Framework | 3.15.x | API endpoints if needed |
| PostgreSQL | 16.x | Full-text search, JSONB |
| Redis | 7.x | Celery broker, caching |
| Celery | 5.4.x | Background tasks (email ingestion, alerts) |

### 9.2 Key Dependencies

```toml
# pyproject.toml [project.dependencies]

dependencies = [
    # Core
    "django>=5.1,<5.2",
    "psycopg[binary]>=3.1",
    "django-environ>=0.11",
    
    # Auth
    "django-allauth[socialaccount]>=0.61",
    
    # Frontend
    "django-htmx>=1.17",
    "django-widget-tweaks>=1.5",
    
    # Audit
    "django-simple-history>=3.5",
    
    # Storage
    "django-storages[s3]>=1.14",
    "boto3>=1.34",
    
    # Background tasks
    "celery[redis]>=5.4",
    "django-celery-beat>=2.6",
    
    # Currency
    "django-money>=3.4",
    "py-moneyed>=3.0",
    
    # PDF Export
    "weasyprint>=61.0",
    
    # Utilities
    "django-filter>=24.1",
    "django-crispy-forms>=2.1",
    "crispy-tailwind>=1.0",
]
```

### 9.3 Dev Dependencies

```toml
[project.optional-dependencies]
dev = [
    "django-debug-toolbar>=4.3",
    "pytest-django>=4.8",
    "factory-boy>=3.3",
    "coverage>=7.4",
    "ruff>=0.3",
    "pre-commit>=3.6",
]
```

---

## 10. Infrastructure

### 10.1 Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                         INTERNET                                │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      CLOUDFLARE (CDN)                           │
│                    (Static assets, R2)                          │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                         RENDER                                  │
│  ┌──────────────────┐  ┌──────────────────┐  ┌───────────────┐ │
│  │   Web Service    │  │  Background      │  │   Cron Job    │ │
│  │   (Django +      │  │  Worker          │  │   (Celery     │ │
│  │    Gunicorn)     │  │  (Celery)        │  │    Beat)      │ │
│  └────────┬─────────┘  └────────┬─────────┘  └───────┬───────┘ │
│           │                     │                     │         │
│           └──────────┬──────────┴─────────────────────┘         │
│                      │                                          │
│           ┌──────────▼──────────┐  ┌──────────────────┐        │
│           │     PostgreSQL      │  │      Redis       │        │
│           │     (Managed)       │  │    (Managed)     │        │
│           └─────────────────────┘  └──────────────────┘        │
└─────────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
        ▼                     ▼                     ▼
┌──────────────┐     ┌──────────────┐      ┌──────────────┐
│ Cloudflare   │     │   Google     │      │ IMAP Inbox   │
│     R2       │     │   OAuth      │      │ (BCC email)  │
│  (Media)     │     │              │      │              │
└──────────────┘     └──────────────┘      └──────────────┘
```

### 10.2 Environment Variables

```bash
# .env.example

# Django
SECRET_KEY=
DEBUG=False
ALLOWED_HOSTS=msu2020.example.com

# Database
DATABASE_URL=postgres://user:pass@host:5432/dbname

# Redis
REDIS_URL=redis://host:6379/0

# Google OAuth
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=

# Cloudflare R2
AWS_ACCESS_KEY_ID=         # R2 uses S3-compatible API
AWS_SECRET_ACCESS_KEY=
AWS_STORAGE_BUCKET_NAME=msu2020-media
AWS_S3_ENDPOINT_URL=https://<account>.r2.cloudflarestorage.com
AWS_S3_CUSTOM_DOMAIN=media.msu2020.example.com

# Email ingestion (feature-toggled)
FEATURE_EMAIL_INGESTION=false
IMAP_HOST=
IMAP_USER=
IMAP_PASSWORD=

# Currency
EXCHANGE_RATE_API_KEY=     # Optional, for live rates
DEFAULT_CURRENCY=USD

# Approval thresholds (in USD equivalent)
GOVERNANCE_THRESHOLD_NEED=12000
GOVERNANCE_THRESHOLD_PROJECT=12000
GOVERNANCE_THRESHOLD_EXPENSE=2500
```

### 10.3 Render Services

| Service | Type | Specs | Notes |
|---------|------|-------|-------|
| `msu2020-web` | Web Service | Starter ($7/mo) | Django + Gunicorn |
| `msu2020-worker` | Background Worker | Starter ($7/mo) | Celery |
| `msu2020-db` | PostgreSQL | Starter ($7/mo) | 1GB, auto-backups |
| `msu2020-redis` | Redis | Free tier | Celery broker |

**Estimated monthly cost:** ~$21-30/mo (scales with usage)

---

## 11. Phase 1 Scope

### 11.1 In Scope

| Module | Features |
|--------|----------|
| **Stakeholders** | User CRUD, Google OAuth, RBAC (8 roles), profile management, organizations |
| **Needs** | Create, catalog, status transitions, department/cross-cutting, funding model flag |
| **Donor Matching** | Manual linking of donor(s) to need, pooled vs anchor flag |
| **Projects** | Create from need, lead assignment, team management, status tracking |
| **Milestones** | CRUD, status transitions, **visual timeline (Gantt)**, progress tracking, alerts |
| **Funding** | Contributions (pledge → received → allocated), fund pools (India/US), expenses, approval workflow |
| **Events** | CRUD, event types, registrations, attendance, media upload |
| **Approvals** | Threshold-based governance routing, approval queue |
| **Compliance** | Field-level audit log, consent management |
| **Email Tracker** | IMAP ingestion, stakeholder matching, project linking, search (feature-toggled OFF) |
| **Dashboard** | Home (role-based), project rollup, governance queue |

### 11.2 Out of Scope (Phase 2+)

| Feature | Rationale |
|---------|-----------|
| Success Stories | Manual process sufficient for now |
| Compliance Reports (CSR/501c) | Need to define exact formats |
| Donor Recommendation Engine | Manual matching first |
| CMS Integration | Manual export for now |
| Milestone Dependencies | Core tracking first, dependencies later |
| Mobile App | Web-first, responsive design |
| Multi-language | English only for MVP |

### 11.3 Milestones

| # | Milestone | Duration | Deliverable |
|---|-----------|----------|-------------|
| 1 | Project setup, auth | 1 week | Google OAuth, base templates, RBAC skeleton |
| 2 | Stakeholders + Organizations | 1 week | Full CRUD, role assignment (8 roles) |
| 3 | Needs + Matching | 1.5 weeks | Need lifecycle, donor linking |
| 4 | Projects + Milestones + Timeline | 2 weeks | Project lifecycle, team, **Gantt visualization** |
| 5 | Funding | 1.5 weeks | Contributions, pools, expenses |
| 6 | Approvals (Governance) | 1 week | Threshold routing, approval queue |
| 7 | Events | 1 week | Event lifecycle, registrations, media |
| 8 | Compliance + Audit | 1 week | Audit log viewer, consent UI |
| 9 | Email Tracker | 1 week | Ingestion, search (behind toggle) |
| 10 | Dashboard + Polish | 1 week | Rollup views, testing |
| 11 | Deploy | 0.5 week | Render deployment, DNS, SSL |

**Total estimate:** 12-13 weeks for MVP

---

## 12. Open Items

| # | Item | Owner | Status |
|---|------|-------|--------|
| 1 | Google OAuth credentials | Foundation | Pending |
| 2 | Domain for deployment | Foundation | Pending |
| 3 | Cloudflare R2 account setup | Foundation | Pending |
| 4 | IMAP inbox credentials (for email tracking) | Foundation | Pending |
| 5 | CSR/501(c) reporting format specs | Foundation | Phase 2 |
| 6 | Currency exchange rate source | Dev team | Use static rates or API? |
| 7 | UI/Branding guidelines | Foundation | Pending |
| 8 | Approval threshold values (INR/USD) | Governance Team | Pending |
| 9 | Gantt library preference | Dev team | Frappe Gantt vs custom SVG |

---

## Appendix A: Glossary

| Term | Definition |
|------|------------|
| **Need** | A request originated by HOD/Dean for funding/support |
| **Anchor Donor** | Single HNI donor funding entire project |
| **Pooled** | Multiple donors contributing to same project |
| **Jurisdiction** | Tax/compliance region (India CSR or US 501(c)(3)) |
| **Fund Pool** | Segregated account by jurisdiction |
| **CSR** | Corporate Social Responsibility (India compliance) |
| **501(c)(3)** | US tax-exempt nonprofit status |
| **Milestone** | Trackable deliverable within a project |
| **Governance Team** | Board-level oversight (~20 members) |
| **Finance Controller** | Fund accounting and expense approval role |

---

## Appendix B: Audit Fields

All core models include:

```python
class AuditMixin(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="+")
    updated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="+")
    
    class Meta:
        abstract = True
```

Plus `django-simple-history` for field-level change tracking:

```python
from simple_history.models import HistoricalRecords

class Need(AuditMixin):
    # ... fields ...
    history = HistoricalRecords()
```

---

## Appendix C: Milestone Progress Calculation

```python
# apps/projects/progress.py

from django.db.models import Sum

def calculate_project_progress(project) -> int:
    """
    Calculate project completion percentage based on milestones.
    
    - If milestones have weights, use weighted average
    - Otherwise, equal weight per milestone
    - Cancelled milestones are excluded
    
    Returns: int (0-100)
    """
    milestones = project.milestones.exclude(status='cancelled')
    
    if not milestones.exists():
        return 0
    
    total_weight = milestones.aggregate(
        total=Sum('weight_percent')
    )['total'] or 0
    
    if total_weight > 0:
        # Weighted calculation
        done_weight = milestones.filter(status='done').aggregate(
            done=Sum('weight_percent')
        )['done'] or 0
        return min(100, int((done_weight / total_weight) * 100))
    
    # Equal weight calculation
    total = milestones.count()
    done = milestones.filter(status='done').count()
    return int((done / total) * 100)


def get_project_health_status(project) -> str:
    """
    Determine project health based on milestone status.
    
    Returns: 'on_track' | 'at_risk' | 'completed'
    """
    milestones = project.milestones.exclude(status='cancelled')
    
    if not milestones.exists():
        return 'on_track'
    
    all_done = not milestones.exclude(status='done').exists()
    if all_done:
        return 'completed'
    
    overdue_count = milestones.filter(status='overdue').count()
    if overdue_count > 0:
        return 'at_risk'
    
    return 'on_track'
```

---

*End of Document*
