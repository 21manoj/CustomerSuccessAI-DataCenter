-- CS Pulse — PostgreSQL Schema
-- Auto-generated from SQLAlchemy models
-- 39 tables in dependency order

-- ============================================================
-- TIER 0 — No foreign-key dependencies
-- ============================================================

-- 1. customers
CREATE TABLE customers (
    customer_id    SERIAL PRIMARY KEY,
    customer_name  VARCHAR        NOT NULL,
    email          VARCHAR        UNIQUE,
    phone          VARCHAR,
    domain         VARCHAR        UNIQUE,
    uuid           VARCHAR(60)    UNIQUE,
    vertical       VARCHAR(20),
    created_at     TIMESTAMP      NOT NULL DEFAULT NOW(),
    updated_at     TIMESTAMP      NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_customers_uuid ON customers (uuid);
CREATE INDEX idx_customers_vertical ON customers (vertical);

-- 2. portfolios
CREATE TABLE portfolios (
    portfolio_id    SERIAL PRIMARY KEY,
    portfolio_name  VARCHAR(255)   NOT NULL,
    portfolio_type  VARCHAR(50)    DEFAULT 'pe_fund',
    description     TEXT,
    total_aum       NUMERIC(15,2),
    investment_thesis TEXT,
    config          JSONB,
    enabled         BOOLEAN        DEFAULT TRUE,
    created_at      TIMESTAMP      NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMP      NOT NULL DEFAULT NOW()
);

-- ============================================================
-- TIER 1 — Depend only on TIER 0 tables
-- ============================================================

-- 3. customer_configs
CREATE TABLE customer_configs (
    config_id                SERIAL PRIMARY KEY,
    customer_id              INTEGER UNIQUE REFERENCES customers (customer_id) ON DELETE CASCADE,
    kpi_upload_mode          VARCHAR        DEFAULT 'corporate',
    category_weights         TEXT,
    master_file_name         VARCHAR,
    openai_api_key_encrypted TEXT,
    openai_api_key_updated_at TIMESTAMP,
    vertical                 VARCHAR(50)    DEFAULT 'saas',
    dc2s_pillar_weights      JSONB,
    dc2s_enabled_kpis        JSONB,
    dc2s_kpi_overrides       JSONB,
    dc2s_kpi_weights         JSONB,
    dc2s_kpi_definitions     JSONB,
    config_version           VARCHAR(20)    DEFAULT '1.0',
    customized_by            VARCHAR(255),
    created_at               TIMESTAMP      NOT NULL DEFAULT NOW(),
    updated_at               TIMESTAMP      NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_customer_configs_customer ON customer_configs (customer_id);

-- 4. accounts
CREATE TABLE accounts (
    account_id          SERIAL PRIMARY KEY,
    customer_id         INTEGER NOT NULL REFERENCES customers (customer_id) ON DELETE CASCADE,
    account_name        VARCHAR NOT NULL,
    revenue             NUMERIC(15,2) DEFAULT 0,
    account_status      VARCHAR DEFAULT 'active',
    industry            VARCHAR,
    vertical            VARCHAR(50),
    region              VARCHAR,
    external_account_id VARCHAR,
    profile_metadata    JSONB,
    uuid                VARCHAR(60)  UNIQUE,
    customer_uuid       VARCHAR(60),
    created_at          TIMESTAMP    NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMP    NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_accounts_customer_id ON accounts (customer_id);
CREATE INDEX idx_accounts_account_name ON accounts (account_name);
CREATE INDEX idx_accounts_account_status ON accounts (account_status);
CREATE INDEX idx_accounts_industry ON accounts (industry);
CREATE INDEX idx_accounts_region ON accounts (region);
CREATE INDEX idx_accounts_external_account_id ON accounts (external_account_id);
CREATE INDEX idx_accounts_created_at ON accounts (created_at);
CREATE INDEX idx_account_customer_status ON accounts (customer_id, account_status);
CREATE INDEX idx_account_customer_industry ON accounts (customer_id, industry);
CREATE INDEX idx_account_customer_region ON accounts (customer_id, region);

-- 5. users
CREATE TABLE users (
    user_id        SERIAL PRIMARY KEY,
    customer_id    INTEGER REFERENCES customers (customer_id) ON DELETE CASCADE,
    user_name      VARCHAR NOT NULL,
    email          VARCHAR NOT NULL,
    password_hash  VARCHAR(128),
    active         BOOLEAN DEFAULT TRUE,
    last_login     TIMESTAMP,
    uuid           VARCHAR(60) UNIQUE,
    customer_uuid  VARCHAR(60),
    created_at     TIMESTAMP   NOT NULL DEFAULT NOW(),
    updated_at     TIMESTAMP   NOT NULL DEFAULT NOW(),
    vertical       VARCHAR(50),
    role           VARCHAR(50),
    CONSTRAINT unique_customer_username UNIQUE (customer_id, user_name),
    CONSTRAINT unique_user_email        UNIQUE (email)
);

CREATE INDEX idx_users_customer_id ON users (customer_id);

-- 6. playbook_triggers
CREATE TABLE playbook_triggers (
    trigger_id              SERIAL PRIMARY KEY,
    customer_id             INTEGER NOT NULL REFERENCES customers (customer_id) ON DELETE CASCADE,
    playbook_type           VARCHAR(50) NOT NULL,
    trigger_config          TEXT,
    auto_trigger_enabled    BOOLEAN     DEFAULT FALSE,
    last_evaluated          TIMESTAMP,
    last_triggered          TIMESTAMP,
    trigger_count           INTEGER     DEFAULT 0,
    created_at              TIMESTAMP   NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMP   NOT NULL DEFAULT NOW(),
    playbook_id             VARCHAR(50),
    trigger_conditions      JSONB,
    execution_mode          VARCHAR(20),
    requires_llm_validation BOOLEAN     DEFAULT TRUE,
    CONSTRAINT unique_customer_playbook UNIQUE (customer_id, playbook_type)
);

CREATE INDEX idx_playbook_triggers_customer ON playbook_triggers (customer_id);

-- 7. feature_toggles
CREATE TABLE feature_toggles (
    id            SERIAL PRIMARY KEY,
    customer_id   INTEGER NOT NULL REFERENCES customers (customer_id) ON DELETE CASCADE,
    feature_name  VARCHAR(100) NOT NULL,
    enabled       BOOLEAN      NOT NULL DEFAULT FALSE,
    config        JSONB,
    description   TEXT,
    created_at    TIMESTAMP    NOT NULL DEFAULT NOW(),
    updated_at    TIMESTAMP    NOT NULL DEFAULT NOW(),
    CONSTRAINT unique_customer_feature UNIQUE (customer_id, feature_name)
);

CREATE INDEX idx_feature_toggles_customer ON feature_toggles (customer_id);
CREATE INDEX idx_feature_toggles_feature ON feature_toggles (feature_name);

-- 8. customer_workflow_configs
CREATE TABLE customer_workflow_configs (
    id                                SERIAL PRIMARY KEY,
    customer_id                       INTEGER NOT NULL UNIQUE REFERENCES customers (customer_id) ON DELETE CASCADE,
    workflow_system                    VARCHAR(50),
    n8n_instance_type                 VARCHAR(50),
    n8n_base_url                      VARCHAR(500),
    n8n_webhook_url                   VARCHAR(500),
    n8n_api_key_encrypted             VARCHAR(500),
    n8n_api_key_updated_at            TIMESTAMP,
    webhook_secret_encrypted          VARCHAR(500),
    webhook_secret_old_encrypted      VARCHAR(500),
    webhook_secret_rotated_at         TIMESTAMP,
    webhook_secret_grace_period_until TIMESTAMP,
    enabled_playbooks                 JSONB,
    config                            JSONB,
    created_at                        TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at                        TIMESTAMP NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_customer_workflow_config UNIQUE (customer_id)
);

CREATE INDEX idx_customer_workflow_configs_customer ON customer_workflow_configs (customer_id);

-- 9. portfolio_memberships
CREATE TABLE portfolio_memberships (
    id                   SERIAL PRIMARY KEY,
    portfolio_id         INTEGER NOT NULL REFERENCES portfolios (portfolio_id) ON DELETE CASCADE,
    customer_id          INTEGER NOT NULL REFERENCES customers (customer_id) ON DELETE CASCADE,
    acquisition_date     TIMESTAMP,
    status               VARCHAR(20)   DEFAULT 'owned',
    vertical             VARCHAR(50),
    role                 VARCHAR(20)   DEFAULT 'platform',
    synergies_identified INTEGER       DEFAULT 0,
    synergies_realized   INTEGER       DEFAULT 0,
    synergy_value        NUMERIC(15,2) DEFAULT 0,
    created_at           TIMESTAMP     NOT NULL DEFAULT NOW(),
    updated_at           TIMESTAMP     NOT NULL DEFAULT NOW(),
    CONSTRAINT unique_portfolio_customer UNIQUE (portfolio_id, customer_id)
);

CREATE INDEX idx_portfolio_memberships_portfolio ON portfolio_memberships (portfolio_id);
CREATE INDEX idx_portfolio_memberships_customer ON portfolio_memberships (customer_id);

-- 10. weight_calibration_history
CREATE TABLE weight_calibration_history (
    id                       SERIAL PRIMARY KEY,
    customer_id              INTEGER NOT NULL REFERENCES customers (customer_id) ON DELETE CASCADE,
    calibration_type         VARCHAR(50) NOT NULL,
    vertical                 VARCHAR(50),
    previous_weights         JSONB       NOT NULL,
    new_weights              JSONB       NOT NULL,
    weight_deltas            JSONB,
    sample_size              INTEGER,
    prediction_error_before  NUMERIC(8,4),
    prediction_error_after   NUMERIC(8,4),
    error_reduction_pct      NUMERIC(5,2),
    triggered_by             VARCHAR(50),
    approved                 BOOLEAN     DEFAULT TRUE,
    notes                    TEXT,
    calibrated_at            TIMESTAMP   NOT NULL DEFAULT NOW(),
    created_at               TIMESTAMP   NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_calibration_customer_type ON weight_calibration_history (customer_id, calibration_type);
CREATE INDEX idx_calibration_date ON weight_calibration_history (calibrated_at);

-- 11. wizard_runs
CREATE TABLE wizard_runs (
    id             SERIAL PRIMARY KEY,
    run_id         VARCHAR(50)  NOT NULL UNIQUE,
    customer_id    INTEGER      REFERENCES customers (customer_id) ON DELETE CASCADE,
    job_id         VARCHAR(100),
    status         VARCHAR(20)  NOT NULL DEFAULT 'queued',
    current_phase  VARCHAR(50),
    progress       JSONB,
    config         JSONB        NOT NULL,
    results        JSONB,
    error_message  TEXT,
    created_at     TIMESTAMP    NOT NULL DEFAULT NOW(),
    started_at     TIMESTAMP,
    completed_at   TIMESTAMP,
    created_by     VARCHAR(100)
);

CREATE INDEX idx_wizard_runs_run_id ON wizard_runs (run_id);
CREATE INDEX idx_wizard_runs_customer ON wizard_runs (customer_id);
CREATE INDEX idx_wizard_runs_job ON wizard_runs (job_id);
CREATE INDEX idx_wizard_runs_status ON wizard_runs (status);
CREATE INDEX idx_wizard_runs_created ON wizard_runs (created_at);

-- 12. integration_credentials
CREATE TABLE integration_credentials (
    id                        SERIAL PRIMARY KEY,
    customer_id               INTEGER NOT NULL REFERENCES customers (customer_id) ON DELETE CASCADE,
    provider                  VARCHAR(50) NOT NULL,
    credential_type           VARCHAR(50) NOT NULL,
    encrypted_data            BYTEA       NOT NULL,
    expires_at                TIMESTAMP,
    refresh_token_encrypted   BYTEA,
    created_at                TIMESTAMP   NOT NULL DEFAULT NOW(),
    updated_at                TIMESTAMP   NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_integration_credentials_customer ON integration_credentials (customer_id);
CREATE INDEX idx_cred_customer_provider ON integration_credentials (customer_id, provider);

-- 13. product_catalog
CREATE TABLE product_catalog (
    product_id    SERIAL PRIMARY KEY,
    customer_id   INTEGER NOT NULL REFERENCES customers (customer_id) ON DELETE CASCADE,
    product_name  VARCHAR(255) NOT NULL,
    product_sku   VARCHAR(100),
    product_type  VARCHAR(100),
    status        VARCHAR(50) DEFAULT 'active',
    created_at    TIMESTAMP   NOT NULL DEFAULT NOW(),
    updated_at    TIMESTAMP   NOT NULL DEFAULT NOW(),
    CONSTRAINT unique_customer_product_name UNIQUE (customer_id, product_name)
);

CREATE INDEX idx_product_catalog_customer ON product_catalog (customer_id);
CREATE INDEX idx_product_catalog_name ON product_catalog (product_name);

-- ============================================================
-- TIER 2 — Depend on TIER 0 + TIER 1 tables
-- ============================================================

-- 14. products
CREATE TABLE products (
    product_id    SERIAL PRIMARY KEY,
    account_id    INTEGER NOT NULL REFERENCES accounts (account_id) ON DELETE CASCADE,
    customer_id   INTEGER NOT NULL REFERENCES customers (customer_id) ON DELETE CASCADE,
    product_name  VARCHAR(255) NOT NULL,
    product_sku   VARCHAR(100),
    product_type  VARCHAR(100),
    revenue       NUMERIC(15,2),
    status        VARCHAR(50) DEFAULT 'active',
    created_at    TIMESTAMP   NOT NULL DEFAULT NOW(),
    updated_at    TIMESTAMP   NOT NULL DEFAULT NOW(),
    CONSTRAINT unique_account_product UNIQUE (account_id, product_name)
);

CREATE INDEX idx_products_account ON products (account_id);
CREATE INDEX idx_products_customer ON products (customer_id);

-- 15. kpi_uploads
CREATE TABLE kpi_uploads (
    upload_id          SERIAL PRIMARY KEY,
    customer_id        INTEGER NOT NULL REFERENCES customers (customer_id) ON DELETE CASCADE,
    account_id         INTEGER REFERENCES accounts (account_id) ON DELETE CASCADE,
    user_id            INTEGER REFERENCES users (user_id) ON DELETE SET NULL,
    uploaded_at        TIMESTAMP NOT NULL DEFAULT NOW(),
    version            INTEGER   NOT NULL,
    original_filename  VARCHAR,
    raw_excel          BYTEA,
    parsed_json        JSONB
);

CREATE INDEX idx_kpi_uploads_customer ON kpi_uploads (customer_id);
CREATE INDEX idx_kpi_uploads_account ON kpi_uploads (account_id);
CREATE INDEX idx_kpi_uploads_user ON kpi_uploads (user_id);
CREATE INDEX idx_kpi_uploads_uploaded_at ON kpi_uploads (uploaded_at);
CREATE INDEX idx_upload_customer_uploaded ON kpi_uploads (customer_id, uploaded_at);
CREATE INDEX idx_upload_account_uploaded ON kpi_uploads (account_id, uploaded_at);

-- 16. health_trends
CREATE TABLE health_trends (
    trend_id                   SERIAL PRIMARY KEY,
    account_id                 INTEGER      NOT NULL REFERENCES accounts (account_id) ON DELETE CASCADE,
    customer_id                INTEGER      NOT NULL REFERENCES customers (customer_id) ON DELETE CASCADE,
    month                      INTEGER      NOT NULL,
    year                       INTEGER      NOT NULL,
    overall_health_score       NUMERIC(5,2) NOT NULL,
    product_usage_score        NUMERIC(5,2),
    support_score              NUMERIC(5,2),
    customer_sentiment_score   NUMERIC(5,2),
    business_outcomes_score    NUMERIC(5,2),
    relationship_strength_score NUMERIC(5,2),
    total_kpis                 INTEGER      DEFAULT 0,
    valid_kpis                 INTEGER      DEFAULT 0,
    created_at                 TIMESTAMP    NOT NULL DEFAULT NOW(),
    updated_at                 TIMESTAMP    NOT NULL DEFAULT NOW(),
    CONSTRAINT unique_account_month_year UNIQUE (account_id, month, year)
);

CREATE INDEX idx_health_trends_account ON health_trends (account_id);
CREATE INDEX idx_health_trends_customer ON health_trends (customer_id);
CREATE INDEX idx_health_trends_month ON health_trends (month);
CREATE INDEX idx_health_trends_year ON health_trends (year);
CREATE INDEX idx_health_trends_created ON health_trends (created_at);
CREATE INDEX idx_health_trend_account_date ON health_trends (account_id, year, month);
CREATE INDEX idx_health_trend_customer_date ON health_trends (customer_id, year, month);

-- 17. kpi_reference_ranges
CREATE TABLE kpi_reference_ranges (
    range_id       SERIAL PRIMARY KEY,
    customer_id    INTEGER REFERENCES customers (customer_id) ON DELETE CASCADE,
    kpi_name       VARCHAR NOT NULL,
    unit           VARCHAR NOT NULL,
    higher_is_better BOOLEAN NOT NULL DEFAULT TRUE,
    critical_min   NUMERIC(10,2) NOT NULL,
    critical_max   NUMERIC(10,2) NOT NULL,
    risk_min       NUMERIC(10,2) NOT NULL,
    risk_max       NUMERIC(10,2) NOT NULL,
    healthy_min    NUMERIC(10,2) NOT NULL,
    healthy_max    NUMERIC(10,2) NOT NULL,
    critical_range VARCHAR(100),
    risk_range     VARCHAR(100),
    healthy_range  VARCHAR(100),
    description    TEXT,
    created_at     TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at     TIMESTAMP NOT NULL DEFAULT NOW(),
    created_by     INTEGER REFERENCES users (user_id) ON DELETE SET NULL,
    updated_by     INTEGER REFERENCES users (user_id) ON DELETE SET NULL,
    CONSTRAINT uq_customer_kpi_name UNIQUE (customer_id, kpi_name)
);

CREATE INDEX idx_ref_range_customer_kpi ON kpi_reference_ranges (customer_id, kpi_name);

-- 18. playbook_executions
CREATE TABLE playbook_executions (
    id                    SERIAL PRIMARY KEY,
    execution_id          VARCHAR(36)  NOT NULL UNIQUE,
    customer_id           INTEGER      NOT NULL REFERENCES customers (customer_id) ON DELETE CASCADE,
    account_id            INTEGER      REFERENCES accounts (account_id) ON DELETE CASCADE,
    playbook_id           VARCHAR(50)  NOT NULL,
    status                VARCHAR(20)  DEFAULT 'in-progress',
    current_step          VARCHAR(100),
    execution_data        JSONB        NOT NULL,
    started_at            TIMESTAMP    NOT NULL,
    completed_at          TIMESTAMP,
    created_at            TIMESTAMP    NOT NULL DEFAULT NOW(),
    updated_at            TIMESTAMP    NOT NULL DEFAULT NOW(),
    execution_mode        VARCHAR(20),
    trigger_context       JSONB,
    outcome               VARCHAR(50),
    outcome_notes         TEXT,
    llm_validation_result JSONB
);

CREATE INDEX idx_playbook_executions_execution_id ON playbook_executions (execution_id);
CREATE INDEX idx_playbook_executions_customer ON playbook_executions (customer_id);
CREATE INDEX idx_playbook_executions_account ON playbook_executions (account_id);
CREATE INDEX idx_playbook_executions_playbook ON playbook_executions (playbook_id);
CREATE INDEX idx_customer_playbook_exec ON playbook_executions (customer_id, playbook_id);
CREATE INDEX idx_account_playbook_exec ON playbook_executions (account_id, playbook_id);
CREATE INDEX idx_status ON playbook_executions (status);

-- 19. query_audits
CREATE TABLE query_audits (
    id                         SERIAL PRIMARY KEY,
    customer_id                INTEGER NOT NULL REFERENCES customers (customer_id) ON DELETE CASCADE,
    user_id                    INTEGER REFERENCES users (user_id) ON DELETE SET NULL,
    query_text                 TEXT    NOT NULL,
    query_type                 VARCHAR(50)  DEFAULT 'general',
    response_text              TEXT,
    response_time_ms           INTEGER,
    results_count              INTEGER,
    is_deterministic           BOOLEAN DEFAULT FALSE,
    cache_hit                  BOOLEAN DEFAULT FALSE,
    mcp_enhanced               BOOLEAN DEFAULT FALSE,
    playbook_enhanced          BOOLEAN DEFAULT FALSE,
    has_conversation_history   BOOLEAN DEFAULT FALSE,
    conversation_turn          INTEGER DEFAULT 1,
    estimated_cost             DOUBLE PRECISION DEFAULT 0.0,
    created_at                 TIMESTAMP NOT NULL DEFAULT NOW(),
    ip_address                 VARCHAR(45),
    user_agent                 VARCHAR(500)
);

CREATE INDEX idx_query_audits_customer ON query_audits (customer_id);
CREATE INDEX idx_query_audits_user ON query_audits (user_id);
CREATE INDEX idx_query_audits_created ON query_audits (created_at);

-- 20. activity_logs
CREATE TABLE activity_logs (
    id                 SERIAL PRIMARY KEY,
    customer_id        INTEGER NOT NULL REFERENCES customers (customer_id) ON DELETE CASCADE,
    user_id            INTEGER REFERENCES users (user_id) ON DELETE SET NULL,
    action_type        VARCHAR(50)  NOT NULL,
    action_category    VARCHAR(50)  NOT NULL,
    resource_type      VARCHAR(50),
    resource_id        VARCHAR(100),
    action_description TEXT         NOT NULL,
    details            JSONB,
    changed_fields     JSONB,
    before_values      JSONB,
    after_values       JSONB,
    ip_address         VARCHAR(45),
    user_agent         VARCHAR(500),
    session_id         VARCHAR(255),
    status             VARCHAR(20)  NOT NULL DEFAULT 'success',
    error_message      TEXT,
    created_at         TIMESTAMP    NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_activity_logs_customer ON activity_logs (customer_id);
CREATE INDEX idx_activity_logs_user ON activity_logs (user_id);
CREATE INDEX idx_activity_logs_action_type ON activity_logs (action_type);
CREATE INDEX idx_activity_logs_action_category ON activity_logs (action_category);
CREATE INDEX idx_activity_logs_resource_type ON activity_logs (resource_type);
CREATE INDEX idx_activity_logs_created ON activity_logs (created_at);
CREATE INDEX idx_activity_logs_customer_date ON activity_logs (customer_id, created_at);
CREATE INDEX idx_activity_logs_user_date ON activity_logs (user_id, created_at);
CREATE INDEX idx_activity_logs_action_type_date ON activity_logs (action_type, created_at);
CREATE INDEX idx_activity_logs_resource ON activity_logs (resource_type, resource_id);

-- 21. account_notes
CREATE TABLE account_notes (
    note_id              SERIAL PRIMARY KEY,
    account_id           INTEGER   NOT NULL REFERENCES accounts (account_id) ON DELETE CASCADE,
    customer_id          INTEGER   NOT NULL REFERENCES customers (customer_id) ON DELETE CASCADE,
    note_type            VARCHAR(50) NOT NULL,
    note_content         TEXT        NOT NULL,
    note_title           VARCHAR(255),
    created_by           INTEGER     NOT NULL REFERENCES users (user_id) ON DELETE CASCADE,
    created_at           TIMESTAMP   NOT NULL DEFAULT NOW(),
    updated_at           TIMESTAMP   NOT NULL DEFAULT NOW(),
    meeting_date         DATE,
    participants         JSONB,
    tags                 JSONB,
    is_important         BOOLEAN     DEFAULT FALSE,
    related_playbook_id  VARCHAR(50)
);

CREATE INDEX idx_account_notes_account ON account_notes (account_id);
CREATE INDEX idx_account_notes_customer ON account_notes (customer_id);
CREATE INDEX idx_account_notes_created ON account_notes (created_at);
CREATE INDEX idx_account_note_timestamp ON account_notes (account_id, created_at);
CREATE INDEX idx_customer_note_timestamp ON account_notes (customer_id, created_at);
CREATE INDEX idx_note_type ON account_notes (note_type);

-- 22. account_snapshots
CREATE TABLE account_snapshots (
    snapshot_id                    SERIAL PRIMARY KEY,
    account_id                     INTEGER   NOT NULL REFERENCES accounts (account_id) ON DELETE CASCADE,
    customer_id                    INTEGER   NOT NULL REFERENCES customers (customer_id) ON DELETE CASCADE,
    snapshot_timestamp             TIMESTAMP NOT NULL,
    snapshot_type                  VARCHAR(50) NOT NULL,
    snapshot_reason                VARCHAR(255),
    snapshot_version               INTEGER   DEFAULT 1,
    created_by                     INTEGER   REFERENCES users (user_id) ON DELETE SET NULL,
    trigger_event                  VARCHAR(100),
    revenue                        NUMERIC(15,2),
    revenue_change_from_last       NUMERIC(15,2),
    revenue_change_percent         NUMERIC(5,2),
    overall_health_score           NUMERIC(5,2),
    product_usage_score            NUMERIC(5,2),
    support_score                  NUMERIC(5,2),
    customer_sentiment_score       NUMERIC(5,2),
    business_outcomes_score        NUMERIC(5,2),
    relationship_strength_score    NUMERIC(5,2),
    health_score_change_from_last  NUMERIC(5,2),
    health_score_trend             VARCHAR(20),
    account_status                 VARCHAR(50),
    industry                       VARCHAR(100),
    region                         VARCHAR(100),
    account_tier                   VARCHAR(50),
    external_account_id            VARCHAR(100),
    assigned_csm                   VARCHAR(100),
    csm_manager                    VARCHAR(100),
    account_owner                  VARCHAR(100),
    products_used                  JSONB,
    product_count                  INTEGER   DEFAULT 0,
    primary_product                VARCHAR(100),
    playbooks_running              JSONB,
    playbooks_running_count        INTEGER   DEFAULT 0,
    playbooks_completed_count      INTEGER   DEFAULT 0,
    playbooks_completed_last_30_days INTEGER  DEFAULT 0,
    last_playbook_executed         JSONB,
    playbook_recommendations_active JSONB,
    recent_playbook_report_ids     JSONB,
    total_kpis                     INTEGER   DEFAULT 0,
    account_level_kpis             INTEGER   DEFAULT 0,
    product_level_kpis             INTEGER   DEFAULT 0,
    critical_kpis_count            INTEGER   DEFAULT 0,
    at_risk_kpis_count             INTEGER   DEFAULT 0,
    healthy_kpis_count             INTEGER   DEFAULT 0,
    top_critical_kpis              JSONB,
    lifecycle_stage                VARCHAR(50),
    onboarding_status              VARCHAR(50),
    last_qbr_date                  DATE,
    next_qbr_date                  DATE,
    engagement_score               NUMERIC(5,2),
    primary_champion               VARCHAR(100),
    champion_status                VARCHAR(50),
    stakeholder_count              INTEGER   DEFAULT 0,
    recent_csm_note_ids            JSONB,
    days_since_last_snapshot       INTEGER,
    snapshot_sequence_number        INTEGER   DEFAULT 1,
    is_significant_change          BOOLEAN   DEFAULT FALSE,
    created_at                     TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at                     TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_account_snapshots_account ON account_snapshots (account_id);
CREATE INDEX idx_account_snapshots_customer ON account_snapshots (customer_id);
CREATE INDEX idx_account_snapshots_timestamp ON account_snapshots (snapshot_timestamp);
CREATE INDEX idx_account_snapshot_timestamp ON account_snapshots (account_id, snapshot_timestamp);
CREATE INDEX idx_customer_snapshot_timestamp ON account_snapshots (customer_id, snapshot_timestamp);
CREATE INDEX idx_snapshot_type ON account_snapshots (snapshot_type);

-- 23. dc2s_kpis
CREATE TABLE dc2s_kpis (
    kpi_id       SERIAL PRIMARY KEY,
    account_id   INTEGER      NOT NULL REFERENCES accounts (account_id) ON DELETE CASCADE,
    kpi_code     VARCHAR(50)  NOT NULL,
    value        NUMERIC(10,2) NOT NULL,
    target       NUMERIC(10,2),
    pillar       VARCHAR(10),
    weight       NUMERIC(5,4),
    status       VARCHAR(20),
    measured_at  TIMESTAMP    DEFAULT NOW(),
    created_at   TIMESTAMP    DEFAULT NOW(),
    CONSTRAINT unique_dc2s_kpi UNIQUE (account_id, kpi_code, measured_at)
);

CREATE INDEX idx_dc2s_kpis_account ON dc2s_kpis (account_id);
CREATE INDEX idx_dc2s_kpis_kpi_code ON dc2s_kpis (kpi_code);
CREATE INDEX idx_dc2s_kpis_pillar ON dc2s_kpis (pillar);
CREATE INDEX idx_dc2s_kpis_measured_at ON dc2s_kpis (measured_at);
CREATE INDEX idx_dc2s_account_code ON dc2s_kpis (account_id, kpi_code);

-- 24. qualitative_signals
CREATE TABLE qualitative_signals (
    signal_id          VARCHAR(50) PRIMARY KEY,
    account_id         INTEGER NOT NULL REFERENCES accounts (account_id) ON DELETE CASCADE,
    signal_date        DATE    NOT NULL,
    signal_type        VARCHAR(50),
    content            TEXT,
    sentiment          VARCHAR(50),
    stakeholder_level  VARCHAR(50),
    stakeholder_title  VARCHAR(255),
    sentiment_score    NUMERIC,
    keywords           TEXT,
    is_narrative_signal BOOLEAN
);

CREATE INDEX idx_qualitative_signals_account ON qualitative_signals (account_id);
CREATE INDEX idx_qualitative_signals_date ON qualitative_signals (signal_date);
CREATE INDEX idx_qualitative_signals_type ON qualitative_signals (signal_type);
CREATE INDEX idx_qualitative_signals_sentiment ON qualitative_signals (sentiment);

-- 25. kpi_scores (L1)
CREATE TABLE kpi_scores (
    score_id          SERIAL PRIMARY KEY,
    account_id        INTEGER     NOT NULL REFERENCES accounts (account_id) ON DELETE CASCADE,
    measurement_month DATE        NOT NULL,
    kpi_code          VARCHAR(50) NOT NULL,
    kpi_value         NUMERIC(10,2),
    kpi_target        NUMERIC(10,2),
    kpi_score         NUMERIC(5,2),
    kpi_status        VARCHAR(20),
    calculated_at     TIMESTAMP   DEFAULT NOW(),
    CONSTRAINT unique_kpi_score UNIQUE (account_id, kpi_code, measurement_month)
);

CREATE INDEX idx_kpi_scores_account ON kpi_scores (account_id);
CREATE INDEX idx_kpi_scores_month ON kpi_scores (measurement_month);
CREATE INDEX idx_kpi_scores_code ON kpi_scores (kpi_code);
CREATE INDEX idx_kpi_score_account_month ON kpi_scores (account_id, measurement_month);
CREATE INDEX idx_kpi_score_code ON kpi_scores (kpi_code);

-- 26. pillar_scores (L2)
CREATE TABLE pillar_scores (
    pillar_score_id   SERIAL PRIMARY KEY,
    account_id        INTEGER     NOT NULL REFERENCES accounts (account_id) ON DELETE CASCADE,
    measurement_month DATE        NOT NULL,
    pillar_code       VARCHAR(10) NOT NULL,
    pillar_score      NUMERIC(5,2),
    pillar_status     VARCHAR(20),
    contributing_kpis JSONB,
    kpi_weights       JSONB,
    calculated_at     TIMESTAMP   DEFAULT NOW(),
    CONSTRAINT unique_pillar_score UNIQUE (account_id, pillar_code, measurement_month)
);

CREATE INDEX idx_pillar_scores_account ON pillar_scores (account_id);
CREATE INDEX idx_pillar_scores_month ON pillar_scores (measurement_month);
CREATE INDEX idx_pillar_scores_pillar ON pillar_scores (pillar_code);
CREATE INDEX idx_pillar_score_account_month ON pillar_scores (account_id, measurement_month);
CREATE INDEX idx_pillar_score_pillar ON pillar_scores (pillar_code);

-- 27. health_scores (L3)
CREATE TABLE health_scores (
    health_score_id        SERIAL PRIMARY KEY,
    account_id             INTEGER     NOT NULL REFERENCES accounts (account_id) ON DELETE CASCADE,
    measurement_month      DATE        NOT NULL,
    health_score           NUMERIC(5,2),
    health_status          VARCHAR(20),
    trend                  VARCHAR(20),
    change_from_last_month NUMERIC(5,2),
    contributing_pillars   JSONB,
    pillar_weights         JSONB,
    calculated_at          TIMESTAMP   DEFAULT NOW(),
    CONSTRAINT unique_health_score UNIQUE (account_id, measurement_month)
);

CREATE INDEX idx_health_scores_account ON health_scores (account_id);
CREATE INDEX idx_health_scores_month ON health_scores (measurement_month);
CREATE INDEX idx_health_score_account_month ON health_scores (account_id, measurement_month);
CREATE INDEX idx_health_score_status ON health_scores (health_status);

-- 28. customer_action_bindings
CREATE TABLE customer_action_bindings (
    id                  SERIAL PRIMARY KEY,
    customer_id         INTEGER      NOT NULL REFERENCES customers (customer_id) ON DELETE CASCADE,
    action_name         VARCHAR(100) NOT NULL,
    provider            VARCHAR(50)  NOT NULL,
    config              JSONB        NOT NULL DEFAULT '{}',
    auth_credential_id  INTEGER      REFERENCES integration_credentials (id) ON DELETE SET NULL,
    fallback            VARCHAR(50),
    enabled             BOOLEAN      NOT NULL DEFAULT TRUE,
    created_at          TIMESTAMP    NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMP    NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_customer_action UNIQUE (customer_id, action_name)
);

CREATE INDEX idx_customer_action_bindings_customer ON customer_action_bindings (customer_id);

-- 29. crm_field_mappings
CREATE TABLE crm_field_mappings (
    id               SERIAL PRIMARY KEY,
    customer_id      INTEGER      NOT NULL REFERENCES customers (customer_id) ON DELETE CASCADE,
    cs_pulse_field   VARCHAR(100) NOT NULL,
    crm_object       VARCHAR(50)  NOT NULL,
    crm_field        VARCHAR(100) NOT NULL,
    transform        VARCHAR(50),
    transform_config JSONB,
    CONSTRAINT uq_customer_field_object UNIQUE (customer_id, cs_pulse_field, crm_object)
);

CREATE INDEX idx_crm_field_mappings_customer ON crm_field_mappings (customer_id);

-- 30. customer_contacts
CREATE TABLE customer_contacts (
    id              SERIAL PRIMARY KEY,
    customer_id     INTEGER      NOT NULL REFERENCES customers (customer_id) ON DELETE CASCADE,
    account_id      INTEGER      REFERENCES accounts (account_id) ON DELETE SET NULL,
    role            VARCHAR(50)  NOT NULL,
    name            VARCHAR(200),
    email           VARCHAR(200) NOT NULL,
    title           VARCHAR(200),
    crm_contact_id  VARCHAR(100),
    is_active       BOOLEAN      NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMP    NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_customer_contacts_customer ON customer_contacts (customer_id);
CREATE INDEX idx_customer_contacts_account ON customer_contacts (account_id);
CREATE INDEX idx_contact_customer_account ON customer_contacts (customer_id, account_id);
CREATE INDEX idx_contact_role ON customer_contacts (role);

-- 31. wizard_learnings
CREATE TABLE wizard_learnings (
    id                     SERIAL PRIMARY KEY,
    version                VARCHAR(20)  NOT NULL UNIQUE,
    source_runs            JSONB,
    run_id                 VARCHAR(50)  REFERENCES wizard_runs (run_id) ON DELETE SET NULL,
    learnings              JSONB        NOT NULL,
    industry_benchmarks    JSONB,
    validation_rules       JSONB,
    edge_cases             JSONB,
    created_at             TIMESTAMP    NOT NULL DEFAULT NOW(),
    is_active              BOOLEAN      DEFAULT TRUE,
    total_accounts_tested  INTEGER,
    avg_accuracy           DOUBLE PRECISION
);

CREATE INDEX idx_wizard_learnings_version ON wizard_learnings (version);
CREATE INDEX idx_wizard_learnings_created ON wizard_learnings (created_at);
CREATE INDEX idx_wizard_learnings_active ON wizard_learnings (is_active);

-- 32. wizard_files
CREATE TABLE wizard_files (
    id           SERIAL PRIMARY KEY,
    run_id       VARCHAR(50)  NOT NULL REFERENCES wizard_runs (run_id) ON DELETE CASCADE,
    filename     VARCHAR(255) NOT NULL,
    filepath     VARCHAR(500) NOT NULL,
    file_type    VARCHAR(50),
    file_size    INTEGER,
    created_at   TIMESTAMP    NOT NULL DEFAULT NOW(),
    description  TEXT
);

CREATE INDEX idx_wizard_files_run ON wizard_files (run_id);

-- 33. product_trends
CREATE TABLE product_trends (
    trend_id                    SERIAL PRIMARY KEY,
    product_id                  INTEGER      NOT NULL REFERENCES product_catalog (product_id) ON DELETE CASCADE,
    account_id                  INTEGER      NOT NULL REFERENCES accounts (account_id) ON DELETE CASCADE,
    customer_id                 INTEGER      NOT NULL REFERENCES customers (customer_id) ON DELETE CASCADE,
    month                       INTEGER      NOT NULL,
    year                        INTEGER      NOT NULL,
    overall_health_score        NUMERIC(5,2) NOT NULL,
    product_usage_score         NUMERIC(5,2),
    support_score               NUMERIC(5,2),
    customer_sentiment_score    NUMERIC(5,2),
    business_outcomes_score     NUMERIC(5,2),
    relationship_strength_score NUMERIC(5,2),
    total_kpis                  INTEGER      DEFAULT 0,
    valid_kpis                  INTEGER      DEFAULT 0,
    product_level_kpis          INTEGER      DEFAULT 0,
    account_level_kpis          INTEGER      DEFAULT 0,
    revenue                     NUMERIC(15,2),
    created_at                  TIMESTAMP    NOT NULL DEFAULT NOW(),
    updated_at                  TIMESTAMP    NOT NULL DEFAULT NOW(),
    CONSTRAINT unique_product_account_month_year UNIQUE (product_id, account_id, month, year)
);

CREATE INDEX idx_product_trends_product ON product_trends (product_id);
CREATE INDEX idx_product_trends_account ON product_trends (account_id);
CREATE INDEX idx_product_trends_customer ON product_trends (customer_id);
CREATE INDEX idx_product_trends_month ON product_trends (month);
CREATE INDEX idx_product_trends_year ON product_trends (year);
CREATE INDEX idx_product_trend_product_date ON product_trends (product_id, year, month);
CREATE INDEX idx_product_trend_account_date ON product_trends (account_id, year, month);
CREATE INDEX idx_product_trend_customer_date ON product_trends (customer_id, year, month);
CREATE INDEX idx_product_trend_product_account ON product_trends (product_id, account_id);

-- 34. product_aggregate_trends
CREATE TABLE product_aggregate_trends (
    aggregate_trend_id           SERIAL PRIMARY KEY,
    product_id                   INTEGER      NOT NULL REFERENCES product_catalog (product_id) ON DELETE CASCADE,
    customer_id                  INTEGER      NOT NULL REFERENCES customers (customer_id) ON DELETE CASCADE,
    month                        INTEGER      NOT NULL,
    year                         INTEGER      NOT NULL,
    overall_health_score         NUMERIC(5,2) NOT NULL,
    product_usage_score          NUMERIC(5,2),
    support_score                NUMERIC(5,2),
    customer_sentiment_score     NUMERIC(5,2),
    business_outcomes_score      NUMERIC(5,2),
    relationship_strength_score  NUMERIC(5,2),
    total_accounts               INTEGER      DEFAULT 0,
    total_revenue                NUMERIC(15,2),
    average_revenue_per_account  NUMERIC(15,2),
    total_kpis                   INTEGER      DEFAULT 0,
    valid_kpis                   INTEGER      DEFAULT 0,
    created_at                   TIMESTAMP    NOT NULL DEFAULT NOW(),
    updated_at                   TIMESTAMP    NOT NULL DEFAULT NOW(),
    CONSTRAINT unique_product_aggregate_month_year UNIQUE (product_id, month, year)
);

CREATE INDEX idx_product_aggregate_product ON product_aggregate_trends (product_id);
CREATE INDEX idx_product_aggregate_customer ON product_aggregate_trends (customer_id);
CREATE INDEX idx_product_aggregate_product_date ON product_aggregate_trends (product_id, year, month);
CREATE INDEX idx_product_aggregate_customer_date ON product_aggregate_trends (customer_id, year, month);

-- ============================================================
-- TIER 3 — Depend on TIER 2 tables
-- ============================================================

-- 35. kpis
CREATE TABLE kpis (
    kpi_id                 SERIAL PRIMARY KEY,
    upload_id              INTEGER REFERENCES kpi_uploads (upload_id) ON DELETE CASCADE,
    account_id             INTEGER NOT NULL REFERENCES accounts (account_id) ON DELETE CASCADE,
    product_id             INTEGER REFERENCES products (product_id) ON DELETE SET NULL,
    aggregation_type       VARCHAR(50),
    category               VARCHAR,
    row_index              INTEGER,
    health_score_component VARCHAR,
    weight                 VARCHAR,
    data                   VARCHAR,
    source_review          VARCHAR,
    kpi_parameter          VARCHAR,
    impact_level           VARCHAR,
    measurement_frequency  VARCHAR,
    last_edited_by         INTEGER REFERENCES users (user_id) ON DELETE SET NULL,
    last_edited_at         TIMESTAMP
);

CREATE INDEX idx_kpis_upload ON kpis (upload_id);
CREATE INDEX idx_kpis_account ON kpis (account_id);
CREATE INDEX idx_kpis_product ON kpis (product_id);
CREATE INDEX idx_kpis_aggregation_type ON kpis (aggregation_type);
CREATE INDEX idx_kpis_category ON kpis (category);
CREATE INDEX idx_kpis_health_score_component ON kpis (health_score_component);
CREATE INDEX idx_kpis_kpi_parameter ON kpis (kpi_parameter);
CREATE INDEX idx_kpis_impact_level ON kpis (impact_level);
CREATE INDEX idx_kpis_last_edited_at ON kpis (last_edited_at);
CREATE INDEX idx_kpi_account_category ON kpis (account_id, category);
CREATE INDEX idx_kpi_account_parameter ON kpis (account_id, kpi_parameter);
CREATE INDEX idx_kpi_account_aggregation ON kpis (account_id, aggregation_type);
CREATE INDEX idx_kpi_upload_account ON kpis (upload_id, account_id);

-- 36. kpi_time_series
CREATE TABLE kpi_time_series (
    id            SERIAL PRIMARY KEY,
    kpi_id        INTEGER      NOT NULL REFERENCES kpis (kpi_id) ON DELETE CASCADE,
    account_id    INTEGER      NOT NULL REFERENCES accounts (account_id) ON DELETE CASCADE,
    customer_id   INTEGER      NOT NULL REFERENCES customers (customer_id) ON DELETE CASCADE,
    month         INTEGER      NOT NULL,
    year          INTEGER      NOT NULL,
    value         NUMERIC(10,2),
    health_status VARCHAR(20),
    health_score  NUMERIC(5,2),
    created_at    TIMESTAMP    NOT NULL DEFAULT NOW(),
    updated_at    TIMESTAMP    NOT NULL DEFAULT NOW(),
    CONSTRAINT unique_kpi_month_year UNIQUE (kpi_id, month, year)
);

CREATE INDEX idx_kpi_time_series_kpi ON kpi_time_series (kpi_id);
CREATE INDEX idx_kpi_time_series_account ON kpi_time_series (account_id);
CREATE INDEX idx_kpi_time_series_customer ON kpi_time_series (customer_id);
CREATE INDEX idx_time_series_kpi_date ON kpi_time_series (kpi_id, year, month);
CREATE INDEX idx_time_series_account_date ON kpi_time_series (account_id, year, month);
CREATE INDEX idx_time_series_customer_date ON kpi_time_series (customer_id, year, month);

-- 37. playbook_reports
CREATE TABLE playbook_reports (
    report_id            SERIAL PRIMARY KEY,
    execution_id         VARCHAR(36)  NOT NULL UNIQUE REFERENCES playbook_executions (execution_id) ON DELETE CASCADE,
    customer_id          INTEGER      NOT NULL REFERENCES customers (customer_id) ON DELETE CASCADE,
    account_id           INTEGER      REFERENCES accounts (account_id) ON DELETE CASCADE,
    playbook_id          VARCHAR(50)  NOT NULL,
    playbook_name        VARCHAR(100) NOT NULL,
    account_name         VARCHAR(200),
    status               VARCHAR(20)  DEFAULT 'in-progress',
    report_data          JSONB        NOT NULL,
    duration             VARCHAR(50),
    steps_completed      INTEGER      DEFAULT 0,
    total_steps          INTEGER,
    started_at           TIMESTAMP    NOT NULL,
    completed_at         TIMESTAMP,
    report_generated_at  TIMESTAMP    NOT NULL DEFAULT NOW(),
    created_at           TIMESTAMP    NOT NULL DEFAULT NOW(),
    updated_at           TIMESTAMP    NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_playbook_reports_execution ON playbook_reports (execution_id);
CREATE INDEX idx_playbook_reports_customer ON playbook_reports (customer_id);
CREATE INDEX idx_playbook_reports_account ON playbook_reports (account_id);
CREATE INDEX idx_playbook_reports_playbook ON playbook_reports (playbook_id);
CREATE INDEX idx_customer_playbook ON playbook_reports (customer_id, playbook_id);
CREATE INDEX idx_account_playbook ON playbook_reports (account_id, playbook_id);

-- 38. action_economics
CREATE TABLE action_economics (
    id                   SERIAL PRIMARY KEY,
    customer_id          INTEGER      NOT NULL REFERENCES customers (customer_id) ON DELETE CASCADE,
    account_id           INTEGER      NOT NULL REFERENCES accounts (account_id) ON DELETE CASCADE,
    execution_id         VARCHAR(36)  REFERENCES playbook_executions (execution_id) ON DELETE SET NULL,
    action_type          VARCHAR(50)  NOT NULL,
    action_id            VARCHAR(100) NOT NULL,
    action_name          VARCHAR(255),
    csm_hours            NUMERIC(8,2)  DEFAULT 0,
    cs_ops_hours         NUMERIC(8,2)  DEFAULT 0,
    product_hours        NUMERIC(8,2)  DEFAULT 0,
    platform_hours       NUMERIC(8,2)  DEFAULT 0,
    leadership_hours     NUMERIC(8,2)  DEFAULT 0,
    cs_initiative_cost   NUMERIC(12,2) DEFAULT 0,
    platform_cost        NUMERIC(12,2) DEFAULT 0,
    total_action_cost    NUMERIC(12,2) DEFAULT 0,
    kpi_before           JSONB,
    kpi_after            JSONB,
    kpi_deltas           JSONB,
    power_of_1_metric    VARCHAR(50),
    dollar_impact_annual NUMERIC(15,2),
    dollar_impact_monthly NUMERIC(15,2),
    revenue_increase     NUMERIC(15,2) DEFAULT 0,
    cost_savings         NUMERIC(15,2) DEFAULT 0,
    roi                  NUMERIC(10,4),
    payback_days         INTEGER,
    category             VARCHAR(50),
    journey_phase        VARCHAR(50),
    improvement_pct      NUMERIC(5,2),
    started_at           TIMESTAMP,
    completed_at         TIMESTAMP,
    measured_at          TIMESTAMP     DEFAULT NOW(),
    created_at           TIMESTAMP     NOT NULL DEFAULT NOW(),
    updated_at           TIMESTAMP     NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_action_economics_customer ON action_economics (customer_id);
CREATE INDEX idx_action_economics_account ON action_economics (account_id);
CREATE INDEX idx_action_economics_execution ON action_economics (execution_id);
CREATE INDEX idx_action_econ_customer_account ON action_economics (customer_id, account_id);
CREATE INDEX idx_action_econ_type ON action_economics (action_type, action_id);
CREATE INDEX idx_action_econ_measured ON action_economics (measured_at);

-- 39. playbook_step_log
CREATE TABLE playbook_step_log (
    id                SERIAL PRIMARY KEY,
    execution_id      VARCHAR(36)  NOT NULL REFERENCES playbook_executions (execution_id) ON DELETE CASCADE,
    step_index        INTEGER      NOT NULL,
    action_name       VARCHAR(100) NOT NULL,
    provider          VARCHAR(50)  NOT NULL,
    params_sent       JSONB,
    response_received JSONB,
    status            VARCHAR(20)  NOT NULL,
    error_message     TEXT,
    executed_at       TIMESTAMP    DEFAULT NOW(),
    duration_ms       INTEGER
);

CREATE INDEX idx_playbook_step_log_execution ON playbook_step_log (execution_id);
CREATE INDEX idx_step_log_execution ON playbook_step_log (execution_id, step_index);

-- ============================================================
-- END OF SCHEMA — 39 tables created
-- ============================================================
