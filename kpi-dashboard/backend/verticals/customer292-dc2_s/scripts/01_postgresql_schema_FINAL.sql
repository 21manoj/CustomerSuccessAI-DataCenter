-- ============================================================================
-- CS PULSE - SIGNAL ANALYST DATABASE SCHEMA (FINAL - MATCHES CSV EXACTLY)
-- ============================================================================
-- Version: 3.0 - FINAL - Matches actual CSV structure
-- Date: January 6, 2026
-- Purpose: Schema that matches Customer 292 CSV files EXACTLY
-- ============================================================================

-- Drop existing tables (in reverse dependency order)
DROP TABLE IF EXISTS playbook_executions CASCADE;
DROP TABLE IF EXISTS expansion_readiness_scores CASCADE;
DROP TABLE IF EXISTS account_health_history CASCADE;
DROP TABLE IF EXISTS account_products CASCADE;
DROP TABLE IF EXISTS products CASCADE;
DROP TABLE IF EXISTS qualitative_signals CASCADE;
DROP TABLE IF EXISTS kpi_measurements CASCADE;
DROP TABLE IF EXISTS kpi_definitions CASCADE;
DROP TABLE IF EXISTS account_profiles CASCADE;
DROP TABLE IF EXISTS accounts CASCADE;
DROP TABLE IF EXISTS partner_definitions CASCADE;
DROP TABLE IF EXISTS customers CASCADE;

-- ============================================================================
-- 1. CUSTOMERS TABLE - 56 columns (matches CSV)
-- ============================================================================

CREATE TABLE customers (
    customer_id INTEGER PRIMARY KEY,
    customer_name VARCHAR(255) NOT NULL,
    customer_type VARCHAR(100),
    industry_vertical VARCHAR(100),
    company_size VARCHAR(50),
    headquarters_location VARCHAR(255),
    founded_year INTEGER,
    employee_count INTEGER,
    total_revenue_annual BIGINT,
    funding_stage VARCHAR(50),
    total_funding_raised BIGINT,
    csm_director VARCHAR(255),
    account_executive VARCHAR(255),
    solutions_architect VARCHAR(255),
    executive_sponsor VARCHAR(255),
    customer_since DATE,
    contract_type VARCHAR(100),
    payment_terms VARCHAR(50),
    contract_end_date DATE,
    total_accounts INTEGER,
    active_accounts INTEGER,
    churned_accounts INTEGER,
    total_gpus_deployed INTEGER,
    datacenters_count INTEGER,
    total_initial_arr BIGINT,
    total_current_arr BIGINT,
    total_expansion_arr BIGINT,
    arr_growth_percent DECIMAL(10,2),
    average_account_arr BIGINT,
    overall_customer_health INTEGER,
    customer_nps INTEGER,
    executive_engagement_level VARCHAR(50),
    strategic_customer BOOLEAN,
    reference_customer BOOLEAN,
    number_of_qbrs_ytd INTEGER,
    primary_partner_id VARCHAR(50),
    primary_partner_name VARCHAR(255),
    partner_satisfaction DECIMAL(3,1),
    average_gpu_utilization INTEGER,
    active_workload_types TEXT,
    platform_adoption_score INTEGER,
    time_to_value_days INTEGER,
    expansion_velocity VARCHAR(50),
    churn_risk_level VARCHAR(50),
    retention_probability INTEGER,
    competitive_threats TEXT,
    competitive_wins INTEGER,
    competitive_losses INTEGER,
    support_tier VARCHAR(50),
    average_response_time_hours DECIMAL(5,2),
    support_satisfaction DECIMAL(3,1),
    escalations_ytd INTEGER,
    key_strengths TEXT,
    key_risks TEXT,
    strategic_initiatives TEXT,
    executive_summary TEXT
);

CREATE INDEX idx_customers_type ON customers(customer_type);
CREATE INDEX idx_customers_strategic ON customers(strategic_customer);

-- ============================================================================
-- 2. PARTNER DEFINITIONS TABLE - 11 columns (matches CSV)
-- ============================================================================

CREATE TABLE partner_definitions (
    partner_id VARCHAR(50) PRIMARY KEY,
    partner_name VARCHAR(255) NOT NULL,
    partner_tier VARCHAR(50),
    relationship_strength VARCHAR(50),
    certification_rate INTEGER,
    account_count INTEGER,
    total_arr BIGINT,
    avg_satisfaction_score DECIMAL(3,1),
    specialization TEXT,
    geographic_focus TEXT,
    notes TEXT
);

CREATE INDEX idx_partners_tier ON partner_definitions(partner_tier);

-- ============================================================================
-- 3. ACCOUNTS TABLE - 20 columns (matches CSV)
-- ============================================================================

CREATE TABLE accounts (
    account_id INTEGER PRIMARY KEY,
    customer_id INTEGER NOT NULL REFERENCES customers(customer_id),
    account_name VARCHAR(255) NOT NULL,
    account_type VARCHAR(100),
    industry VARCHAR(100),
    account_tier VARCHAR(50),
    initial_arr BIGINT,
    final_arr BIGINT,
    contract_start_date DATE,
    contract_end_date DATE,
    partner_id VARCHAR(50) REFERENCES partner_definitions(partner_id),
    partner_name VARCHAR(255),
    partner_tier VARCHAR(50),
    gpu_count INTEGER,
    datacenter_location VARCHAR(100),
    csm_assigned VARCHAR(255),
    executive_sponsor VARCHAR(255),
    journey_type VARCHAR(50),
    outcome TEXT,
    has_narrative BOOLEAN
);

CREATE INDEX idx_accounts_customer ON accounts(customer_id);
CREATE INDEX idx_accounts_partner ON accounts(partner_id);
CREATE INDEX idx_accounts_journey ON accounts(journey_type);

-- ============================================================================
-- 4. ACCOUNT PROFILES TABLE - 121 columns (matches CSV EXACTLY)
-- ============================================================================

CREATE TABLE account_profiles (
    account_id INTEGER PRIMARY KEY REFERENCES accounts(account_id),
    customer_id INTEGER REFERENCES customers(customer_id),  -- Column 2 in CSV
    account_name VARCHAR(255),
    account_nickname VARCHAR(255),
    industry VARCHAR(100),
    industry_subcategory VARCHAR(100),
    account_tier VARCHAR(50),
    company_size VARCHAR(50),
    annual_revenue BIGINT,
    employee_count INTEGER,
    initial_arr BIGINT,
    current_arr BIGINT,
    arr_growth_amount BIGINT,
    arr_growth_percent DECIMAL(10,2),
    expansion_count INTEGER,
    total_expansion_value BIGINT,
    average_expansion_value BIGINT,
    contraction_count INTEGER,
    lifetime_value_3yr BIGINT,
    contract_start_date DATE,
    contract_end_date DATE,
    contract_term_months INTEGER,
    renewal_likelihood INTEGER,
    contract_type VARCHAR(100),
    payment_terms VARCHAR(50),
    billing_frequency VARCHAR(50),
    overall_health_score INTEGER,
    health_score_trend VARCHAR(50),
    health_score_trajectory VARCHAR(50),
    nps_score INTEGER,
    nps_trend VARCHAR(50),
    csat_score DECIMAL(3,1),
    executive_engagement_level VARCHAR(50),
    champion_strength VARCHAR(50),
    champion_name VARCHAR(255),
    champion_tenure_months INTEGER,
    champion_risk VARCHAR(50),
    csm_assigned VARCHAR(255),
    account_executive VARCHAR(255),
    solutions_architect VARCHAR(255),
    executive_sponsor VARCHAR(255),
    executive_sponsor_engagement VARCHAR(50),
    qbr_frequency VARCHAR(50),
    qbrs_completed_ytd INTEGER,
    last_qbr_date DATE,
    next_qbr_date DATE,
    gpu_count_initial INTEGER,
    gpu_count_current INTEGER,
    gpu_type VARCHAR(50),
    datacenter_location VARCHAR(100),
    datacenter_count INTEGER,
    average_gpu_utilization INTEGER,
    utilization_trend VARCHAR(50),
    workload_types TEXT,
    primary_use_case TEXT,
    technical_complexity VARCHAR(50),
    partner_id VARCHAR(50),
    partner_name VARCHAR(255),
    partner_tier VARCHAR(50),
    partner_satisfaction DECIMAL(3,1),
    partner_engagement_level VARCHAR(50),
    partner_value_delivered VARCHAR(50),
    journey_type VARCHAR(50),
    journey_phase VARCHAR(100),
    customer_maturity VARCHAR(50),
    adoption_stage VARCHAR(100),
    time_to_value_days INTEGER,
    time_to_production_days INTEGER,
    onboarding_completion INTEGER,
    feature_adoption_rate INTEGER,
    playbook_executions_count INTEGER,
    playbook_success_rate INTEGER,
    proactive_interventions INTEGER,
    reactive_interventions INTEGER,
    escalations_ytd INTEGER,
    support_tickets_ytd INTEGER,
    p1_incidents_ytd INTEGER,
    average_resolution_time_hours DECIMAL(5,2),
    churn_risk_level VARCHAR(50),
    churn_risk_score INTEGER,
    expansion_opportunity VARCHAR(50),
    expansion_readiness_score INTEGER,
    competitive_risk VARCHAR(50),
    competitive_threats TEXT,
    budget_risk VARCHAR(50),
    champion_risk_level VARCHAR(50),
    strategic_account BOOLEAN,
    reference_customer BOOLEAN,
    case_study_approved BOOLEAN,
    logo_usage_approved BOOLEAN,
    innovation_partner BOOLEAN,
    advisory_board_member BOOLEAN,
    co_marketing_opportunities INTEGER,
    previous_vendor VARCHAR(255),
    competitive_wins INTEGER,
    competitive_losses INTEGER,
    win_reasons TEXT,
    differentiation TEXT,
    monthly_active_users INTEGER,
    power_users_count INTEGER,
    platform_login_frequency VARCHAR(50),
    api_usage_volume VARCHAR(50),
    training_sessions_completed INTEGER,
    certification_count INTEGER,
    payment_history VARCHAR(50),
    payment_timeliness INTEGER,
    days_sales_outstanding INTEGER,
    credit_risk VARCHAR(50),
    budget_approved_next_year BOOLEAN,
    budget_amount_next_year BIGINT,
    first_value_milestone_date DATE,
    first_expansion_date DATE,
    strategic_partnership_date DATE,
    reference_customer_date DATE,
    key_strengths TEXT,
    key_risks TEXT,
    success_factors TEXT,
    expansion_pipeline TEXT,
    executive_summary TEXT,
    narrative_available BOOLEAN,
    proof_point_category VARCHAR(100)
);

CREATE INDEX idx_account_profiles_journey ON account_profiles(journey_type);
CREATE INDEX idx_account_profiles_health ON account_profiles(overall_health_score);
CREATE INDEX idx_account_profiles_strategic ON account_profiles(strategic_account);

-- ============================================================================
-- 5. KPI DEFINITIONS TABLE - Matches CSV (38+ columns)
-- ============================================================================

CREATE TABLE kpi_definitions (
    kpi_code VARCHAR(50) PRIMARY KEY,
    kpi_name VARCHAR(255) NOT NULL,
    pillar VARCHAR(50),  -- Column 3 in CSV
    pillar_weight DECIMAL(5,2),
    kpi_weight_in_pillar DECIMAL(5,2),
    indicator_type VARCHAR(50),
    predictive_horizon_days INTEGER,
    confidence_level VARCHAR(50),
    direction VARCHAR(20),
    source_review TEXT,
    data_source_system VARCHAR(100),
    data_collection_method TEXT,
    impact_level VARCHAR(50),
    measurement_frequency VARCHAR(50),
    range_type VARCHAR(50),
    range_min DECIMAL(20,6),
    range_max DECIMAL(20,6),
    target_value DECIMAL(20,6),
    target_operator VARCHAR(20),
    unit VARCHAR(50),
    state_optimal_min DECIMAL(20,6),
    state_optimal_max DECIMAL(20,6),
    state_healthy_min DECIMAL(20,6),
    state_healthy_max DECIMAL(20,6),
    state_at_risk_min DECIMAL(20,6),
    state_at_risk_max DECIMAL(20,6),
    state_critical_min DECIMAL(20,6),
    state_critical_max DECIMAL(20,6),
    priority_normal DECIMAL(5,2),
    priority_at_risk DECIMAL(5,2),
    priority_expansion DECIMAL(5,2),
    priority_churn_prevention DECIMAL(5,2),
    causal_kpis TEXT,
    correlated_kpis TEXT,
    triggered_playbooks TEXT,
    business_impact TEXT,
    notes TEXT,
    active BOOLEAN DEFAULT TRUE
);

CREATE INDEX idx_kpi_definitions_pillar ON kpi_definitions(pillar);
CREATE INDEX idx_kpi_definitions_indicator ON kpi_definitions(indicator_type);
CREATE INDEX idx_kpi_definitions_active ON kpi_definitions(active);

-- ============================================================================
-- 6. KPI MEASUREMENTS TABLE - 9 columns (matches CSV EXACTLY)
-- ============================================================================

CREATE TABLE kpi_measurements (
    measurement_id SERIAL PRIMARY KEY,
    account_id INTEGER NOT NULL REFERENCES accounts(account_id),
    kpi_code VARCHAR(50) NOT NULL REFERENCES kpi_definitions(kpi_code),
    measurement_month DATE NOT NULL,  -- CSV uses "measurement_month" not "measurement_date"
    value DECIMAL(20,6),
    target_value DECIMAL(20,6),
    health_state VARCHAR(50),
    threshold_breached BOOLEAN,
    unit VARCHAR(50),
    UNIQUE(account_id, kpi_code, measurement_month)
);

CREATE INDEX idx_kpi_measurements_account ON kpi_measurements(account_id);
CREATE INDEX idx_kpi_measurements_month ON kpi_measurements(measurement_month);
CREATE INDEX idx_kpi_measurements_kpi ON kpi_measurements(kpi_code);
CREATE INDEX idx_kpi_measurements_health ON kpi_measurements(health_state);

-- ============================================================================
-- 7. QUALITATIVE SIGNALS TABLE - 11 columns (matches CSV EXACTLY)
-- ============================================================================

CREATE TABLE qualitative_signals (
    signal_id VARCHAR(50) PRIMARY KEY,
    account_id INTEGER NOT NULL REFERENCES accounts(account_id),
    signal_date DATE NOT NULL,
    signal_type VARCHAR(50),
    stakeholder_level VARCHAR(50),
    stakeholder_title VARCHAR(255),  -- Column 6 in CSV
    content TEXT,  -- CSV uses "content" not "summary"
    sentiment VARCHAR(50),  -- CSV uses "sentiment" not "sentiment_label"
    sentiment_score DECIMAL(5,2),
    keywords TEXT,
    is_narrative_signal BOOLEAN
);

CREATE INDEX idx_qualitative_signals_account ON qualitative_signals(account_id);
CREATE INDEX idx_qualitative_signals_date ON qualitative_signals(signal_date);
CREATE INDEX idx_qualitative_signals_type ON qualitative_signals(signal_type);
CREATE INDEX idx_qualitative_signals_sentiment ON qualitative_signals(sentiment);

-- ============================================================================
-- 8. ACCOUNT HEALTH HISTORY TABLE - 11 columns (matches CSV EXACTLY)
-- ============================================================================

CREATE TABLE account_health_history (
    history_id SERIAL PRIMARY KEY,
    account_id INTEGER NOT NULL REFERENCES accounts(account_id),
    month DATE NOT NULL,  -- CSV uses "month" not "snapshot_month"
    overall_health_score INTEGER,
    health_status VARCHAR(50),
    status_color VARCHAR(20),
    p1_deployment_score INTEGER,
    p2_operational_score INTEGER,
    p3_performance_score INTEGER,
    p4_channel_score INTEGER,
    p5_expansion_score INTEGER,
    trend VARCHAR(50),
    UNIQUE(account_id, month)
);

CREATE INDEX idx_account_health_account ON account_health_history(account_id);
CREATE INDEX idx_account_health_month ON account_health_history(month);

-- ============================================================================
-- 9. EXPANSION READINESS SCORES TABLE - 11 columns (matches CSV EXACTLY)
-- ============================================================================

CREATE TABLE expansion_readiness_scores (
    readiness_id SERIAL PRIMARY KEY,
    account_id INTEGER NOT NULL REFERENCES accounts(account_id),
    month DATE NOT NULL,  -- CSV uses "month" not "snapshot_month"
    expansion_readiness_score INTEGER,
    readiness_level VARCHAR(50),
    recommendation TEXT,
    gpu_utilization_component INTEGER,
    usage_growth_component INTEGER,
    capacity_runway_component INTEGER,
    health_score_component INTEGER,
    days_to_capacity_constraint INTEGER,
    expansion_potential_dollars BIGINT,
    UNIQUE(account_id, month)
);

CREATE INDEX idx_expansion_readiness_account ON expansion_readiness_scores(account_id);
CREATE INDEX idx_expansion_readiness_month ON expansion_readiness_scores(month);

-- ============================================================================
-- 10. PLAYBOOK EXECUTIONS TABLE - 12 columns (matches CSV EXACTLY)
-- ============================================================================

CREATE TABLE playbook_executions (
    execution_id SERIAL PRIMARY KEY,
    account_id INTEGER NOT NULL REFERENCES accounts(account_id),
    playbook_id VARCHAR(50) NOT NULL,
    playbook_name VARCHAR(255) NOT NULL,
    execution_date DATE NOT NULL,
    trigger_kpi VARCHAR(255),  -- Column 6 in CSV
    trigger_value DECIMAL(20,6),
    actions_taken TEXT,
    outcome_kpi_change TEXT,
    business_impact TEXT,
    success BOOLEAN,
    confidence_score DECIMAL(5,2)
);

CREATE INDEX idx_playbook_executions_account ON playbook_executions(account_id);
CREATE INDEX idx_playbook_executions_date ON playbook_executions(execution_date);
CREATE INDEX idx_playbook_executions_playbook ON playbook_executions(playbook_id);

-- ============================================================================
-- 11. PRODUCTS TABLE - 12 columns (matches CSV)
-- ============================================================================

CREATE TABLE products (
    product_id VARCHAR(50) PRIMARY KEY,
    product_name VARCHAR(255) NOT NULL,
    product_category VARCHAR(100),
    product_tier VARCHAR(50),
    gpu_type VARCHAR(50),
    description TEXT,
    target_use_case TEXT,
    price_per_gpu_monthly DECIMAL(10,2),
    minimum_commitment_gpus INTEGER,
    contract_term_months INTEGER,
    performance_benchmark VARCHAR(255),
    launched_date DATE
);

CREATE INDEX idx_products_category ON products(product_category);

-- ============================================================================
-- 12. ACCOUNT PRODUCTS TABLE - 16 columns (matches CSV)
-- ============================================================================

CREATE TABLE account_products (
    account_product_id SERIAL PRIMARY KEY,
    account_id INTEGER NOT NULL REFERENCES accounts(account_id),
    product_id VARCHAR(50) NOT NULL REFERENCES products(product_id),
    product_name VARCHAR(255),
    quantity INTEGER,
    adoption_date DATE,
    status VARCHAR(50),
    usage_level VARCHAR(50),
    utilization_percent INTEGER,
    monthly_spend BIGINT,
    satisfaction_score DECIMAL(3,1),
    primary_product BOOLEAN,
    expansion_potential VARCHAR(50),
    churn_risk VARCHAR(50),
    last_usage_date DATE,
    feature_adoption_rate INTEGER,
    notes TEXT,
    UNIQUE(account_id, product_id)
);

CREATE INDEX idx_account_products_account ON account_products(account_id);
CREATE INDEX idx_account_products_product ON account_products(product_id);

-- ============================================================================
-- VERIFICATION
-- ============================================================================

SELECT table_name, 
       (SELECT COUNT(*) FROM information_schema.columns 
        WHERE table_name = t.table_name) as column_count
FROM information_schema.tables t
WHERE table_schema = 'public' 
  AND table_type = 'BASE TABLE'
ORDER BY table_name;

COMMENT ON SCHEMA public IS 'CS Pulse Signal Analyst - Customer 292 (FINAL - Matches CSV Exactly)';
