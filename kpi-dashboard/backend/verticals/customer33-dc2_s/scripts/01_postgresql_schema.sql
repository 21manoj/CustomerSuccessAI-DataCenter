-- ============================================================================
-- CS PULSE - SIGNAL ANALYST DATABASE SCHEMA
-- Customer 33 Test Environment
-- ============================================================================
-- Version: 2.0
-- Date: January 5, 2026
-- Purpose: Complete schema for Customer 33 test data with Signal Analyst
-- ============================================================================

-- Drop existing tables (in reverse dependency order)
DROP TABLE IF EXISTS account_products CASCADE;
DROP TABLE IF EXISTS products CASCADE;
DROP TABLE IF EXISTS playbook_executions CASCADE;
DROP TABLE IF EXISTS expansion_readiness_scores CASCADE;
DROP TABLE IF EXISTS account_health_history CASCADE;
DROP TABLE IF EXISTS qualitative_signals CASCADE;
DROP TABLE IF EXISTS kpi_measurements CASCADE;
DROP TABLE IF EXISTS kpi_definitions CASCADE;
DROP TABLE IF EXISTS account_profiles CASCADE;
DROP TABLE IF EXISTS accounts CASCADE;
DROP TABLE IF EXISTS partner_definitions CASCADE;
DROP TABLE IF EXISTS customers CASCADE;

-- ============================================================================
-- 1. CUSTOMERS TABLE
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
    
    -- Customer Success Information
    csm_director VARCHAR(255),
    account_executive VARCHAR(255),
    solutions_architect VARCHAR(255),
    executive_sponsor VARCHAR(255),
    
    -- Relationship Timeline
    customer_since DATE,
    contract_type VARCHAR(100),
    payment_terms VARCHAR(50),
    contract_end_date DATE,
    
    -- Account Portfolio
    total_accounts INTEGER,
    active_accounts INTEGER,
    churned_accounts INTEGER,
    total_gpus_deployed INTEGER,
    datacenters_count INTEGER,
    
    -- Financial Summary
    total_initial_arr BIGINT,
    total_current_arr BIGINT,
    total_expansion_arr BIGINT,
    arr_growth_percent DECIMAL(10,2),
    average_account_arr BIGINT,
    
    -- Health & Engagement
    overall_customer_health INTEGER,
    customer_nps INTEGER,
    executive_engagement_level VARCHAR(50),
    strategic_customer BOOLEAN,
    reference_customer BOOLEAN,
    number_of_qbrs_ytd INTEGER,
    
    -- Partner Ecosystem
    primary_partner_id VARCHAR(50),
    primary_partner_name VARCHAR(255),
    partner_satisfaction DECIMAL(3,1),
    
    -- Usage & Adoption
    average_gpu_utilization INTEGER,
    active_workload_types TEXT,
    platform_adoption_score INTEGER,
    
    -- Success Metrics
    time_to_value_days INTEGER,
    expansion_velocity VARCHAR(50),
    churn_risk_level VARCHAR(50),
    retention_probability INTEGER,
    
    -- Competitive Intelligence
    competitive_threats TEXT,
    competitive_wins INTEGER,
    competitive_losses INTEGER,
    
    -- Support & Satisfaction
    support_tier VARCHAR(50),
    average_response_time_hours DECIMAL(5,2),
    support_satisfaction DECIMAL(3,1),
    escalations_ytd INTEGER,
    
    -- Notes
    key_strengths TEXT,
    key_risks TEXT,
    strategic_initiatives TEXT,
    executive_summary TEXT,
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_customers_type ON customers(customer_type);
CREATE INDEX idx_customers_strategic ON customers(strategic_customer);

COMMENT ON TABLE customers IS 'Customer-level profiles and aggregated metrics';

-- ============================================================================
-- 2. PARTNER DEFINITIONS TABLE
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
    notes TEXT,
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_partners_tier ON partner_definitions(partner_tier);

COMMENT ON TABLE partner_definitions IS 'Partner ecosystem profiles and performance metrics';

-- ============================================================================
-- 3. ACCOUNTS TABLE (Basic)
-- ============================================================================

CREATE TABLE accounts (
    account_id INTEGER PRIMARY KEY,
    customer_id INTEGER NOT NULL REFERENCES customers(customer_id),
    account_name VARCHAR(255) NOT NULL,
    industry VARCHAR(100),
    account_tier VARCHAR(50),
    partner_id VARCHAR(50) REFERENCES partner_definitions(partner_id),
    initial_arr BIGINT,
    current_arr BIGINT,
    gpu_count INTEGER,
    datacenter_location VARCHAR(100),
    health_score INTEGER,
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_accounts_customer ON accounts(customer_id);
CREATE INDEX idx_accounts_partner ON accounts(partner_id);
CREATE INDEX idx_accounts_health ON accounts(health_score);

COMMENT ON TABLE accounts IS 'Basic account information (lightweight)';

-- ============================================================================
-- 4. ACCOUNT PROFILES TABLE (Detailed)
-- ============================================================================

CREATE TABLE account_profiles (
    account_id INTEGER PRIMARY KEY REFERENCES accounts(account_id),
    account_nickname VARCHAR(255),
    industry_subcategory VARCHAR(100),
    company_size VARCHAR(50),
    annual_revenue BIGINT,
    employee_count INTEGER,
    
    -- Financial Profile
    arr_growth_amount BIGINT,
    arr_growth_percent DECIMAL(10,2),
    expansion_count INTEGER,
    total_expansion_value BIGINT,
    average_expansion_value BIGINT,
    contraction_count INTEGER,
    lifetime_value_3yr BIGINT,
    
    -- Contract Details
    contract_start_date DATE,
    contract_end_date DATE,
    contract_term_months INTEGER,
    renewal_likelihood INTEGER,
    contract_type VARCHAR(100),
    payment_terms VARCHAR(50),
    billing_frequency VARCHAR(50),
    
    -- Health & Engagement
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
    
    -- Team & Relationships
    csm_assigned VARCHAR(255),
    account_executive VARCHAR(255),
    solutions_architect VARCHAR(255),
    executive_sponsor VARCHAR(255),
    executive_sponsor_engagement VARCHAR(50),
    qbr_frequency VARCHAR(50),
    qbrs_completed_ytd INTEGER,
    last_qbr_date DATE,
    next_qbr_date DATE,
    
    -- Technical Profile
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
    
    -- Partner Information (detailed)
    partner_satisfaction DECIMAL(3,1),
    partner_engagement_level VARCHAR(50),
    partner_value_delivered VARCHAR(50),
    
    -- Journey Characteristics
    journey_type VARCHAR(50),
    journey_phase VARCHAR(100),
    customer_maturity VARCHAR(50),
    adoption_stage VARCHAR(100),
    time_to_value_days INTEGER,
    time_to_production_days INTEGER,
    onboarding_completion INTEGER,
    feature_adoption_rate INTEGER,
    
    -- Success Metrics
    playbook_executions_count INTEGER,
    playbook_success_rate INTEGER,
    proactive_interventions INTEGER,
    reactive_interventions INTEGER,
    escalations_ytd INTEGER,
    support_tickets_ytd INTEGER,
    p1_incidents_ytd INTEGER,
    average_resolution_time_hours DECIMAL(5,2),
    
    -- Risk & Opportunity
    churn_risk_level VARCHAR(50),
    churn_risk_score INTEGER,
    expansion_opportunity VARCHAR(50),
    expansion_readiness_score INTEGER,
    competitive_risk VARCHAR(50),
    competitive_threats TEXT,
    budget_risk VARCHAR(50),
    champion_risk_level VARCHAR(50),
    
    -- Strategic Importance
    strategic_account BOOLEAN,
    reference_customer BOOLEAN,
    case_study_approved BOOLEAN,
    logo_usage_approved BOOLEAN,
    innovation_partner BOOLEAN,
    advisory_board_member BOOLEAN,
    co_marketing_opportunities INTEGER,
    
    -- Competitive Intelligence
    previous_vendor VARCHAR(255),
    competitive_wins INTEGER,
    competitive_losses INTEGER,
    win_reasons TEXT,
    differentiation TEXT,
    
    -- Usage & Adoption
    monthly_active_users INTEGER,
    power_users_count INTEGER,
    platform_login_frequency VARCHAR(50),
    api_usage_volume VARCHAR(50),
    training_sessions_completed INTEGER,
    certification_count INTEGER,
    
    -- Financial Health
    payment_history VARCHAR(50),
    payment_timeliness INTEGER,
    days_sales_outstanding INTEGER,
    credit_risk VARCHAR(50),
    budget_approved_next_year BOOLEAN,
    budget_amount_next_year BIGINT,
    
    -- Key Milestones
    first_value_milestone_date DATE,
    first_expansion_date DATE,
    strategic_partnership_date DATE,
    reference_customer_date DATE,
    
    -- Notes & Summary
    key_strengths TEXT,
    key_risks TEXT,
    success_factors TEXT,
    expansion_pipeline TEXT,
    executive_summary TEXT,
    narrative_available BOOLEAN,
    proof_point_category VARCHAR(100),
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_account_profiles_journey ON account_profiles(journey_type);
CREATE INDEX idx_account_profiles_health ON account_profiles(overall_health_score);
CREATE INDEX idx_account_profiles_strategic ON account_profiles(strategic_account);

COMMENT ON TABLE account_profiles IS 'Detailed account profiles with 100+ attributes';

-- ============================================================================
-- 5. KPI DEFINITIONS TABLE
-- ============================================================================

CREATE TABLE kpi_definitions (
    kpi_code VARCHAR(50) PRIMARY KEY,
    kpi_name VARCHAR(255) NOT NULL,
    category VARCHAR(50) NOT NULL,
    subcategory VARCHAR(100),
    description TEXT,
    rationale TEXT,
    
    -- Signal Analyst Metadata (38 attributes)
    data_type VARCHAR(50),
    unit_of_measurement VARCHAR(50),
    calculation_method TEXT,
    data_source VARCHAR(100),
    update_frequency VARCHAR(50),
    typical_range_min DECIMAL(20,6),
    typical_range_max DECIMAL(20,6),
    health_state_optimal_min DECIMAL(20,6),
    health_state_optimal_max DECIMAL(20,6),
    health_state_healthy_min DECIMAL(20,6),
    health_state_healthy_max DECIMAL(20,6),
    health_state_at_risk_min DECIMAL(20,6),
    health_state_at_risk_max DECIMAL(20,6),
    health_state_critical_min DECIMAL(20,6),
    health_state_critical_max DECIMAL(20,6),
    threshold_breach_significance VARCHAR(50),
    
    -- Predictive Attributes
    indicator_type VARCHAR(50),
    predictive_horizon_days INTEGER,
    confidence_level VARCHAR(50),
    causal_relationships TEXT,
    correlated_kpis TEXT,
    
    -- Priority & Weighting
    base_priority_weight DECIMAL(5,2),
    scenario_normal_weight DECIMAL(5,2),
    scenario_at_risk_weight DECIMAL(5,2),
    scenario_expansion_weight DECIMAL(5,2),
    scenario_churn_prevention_weight DECIMAL(5,2),
    priority_reasoning TEXT,
    
    -- Business Impact
    business_impact_level VARCHAR(50),
    revenue_impact_potential DECIMAL(15,2),
    churn_impact_potential DECIMAL(5,2),
    expansion_signal_strength DECIMAL(5,2),
    
    -- Actionability
    playbook_triggers TEXT,
    recommended_actions TEXT,
    escalation_criteria TEXT,
    time_sensitivity VARCHAR(50),
    
    -- Metadata
    owner VARCHAR(100),
    last_reviewed_date DATE,
    version VARCHAR(20),
    active BOOLEAN DEFAULT TRUE,
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_kpi_definitions_category ON kpi_definitions(category);
CREATE INDEX idx_kpi_definitions_indicator ON kpi_definitions(indicator_type);
CREATE INDEX idx_kpi_definitions_active ON kpi_definitions(active);

COMMENT ON TABLE kpi_definitions IS 'KPI metadata with 38 Signal Analyst attributes';

-- ============================================================================
-- 6. KPI MEASUREMENTS TABLE
-- ============================================================================

CREATE TABLE kpi_measurements (
    measurement_id SERIAL PRIMARY KEY,
    account_id INTEGER NOT NULL REFERENCES accounts(account_id),
    customer_id INTEGER NOT NULL REFERENCES customers(customer_id),
    kpi_code VARCHAR(50) NOT NULL REFERENCES kpi_definitions(kpi_code),
    measurement_date DATE NOT NULL,
    measurement_value DECIMAL(20,6),
    health_state VARCHAR(50),
    threshold_breached BOOLEAN,
    trend VARCHAR(50),
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(account_id, kpi_code, measurement_date)
);

CREATE INDEX idx_kpi_measurements_account ON kpi_measurements(account_id);
CREATE INDEX idx_kpi_measurements_date ON kpi_measurements(measurement_date);
CREATE INDEX idx_kpi_measurements_kpi ON kpi_measurements(kpi_code);
CREATE INDEX idx_kpi_measurements_health ON kpi_measurements(health_state);
CREATE INDEX idx_kpi_measurements_breach ON kpi_measurements(threshold_breached);

COMMENT ON TABLE kpi_measurements IS 'Time-series KPI measurements for all accounts';

-- ============================================================================
-- 7. QUALITATIVE SIGNALS TABLE
-- ============================================================================

CREATE TABLE qualitative_signals (
    signal_id VARCHAR(50) PRIMARY KEY,
    account_id INTEGER NOT NULL REFERENCES accounts(account_id),
    customer_id INTEGER NOT NULL REFERENCES customers(customer_id),
    signal_date DATE NOT NULL,
    signal_type VARCHAR(50),
    from_contact VARCHAR(255),
    from_title VARCHAR(100),
    to_contact VARCHAR(255),
    subject VARCHAR(500),
    summary TEXT,
    sentiment_score DECIMAL(5,2),
    sentiment_label VARCHAR(50),
    priority VARCHAR(50),
    keywords TEXT,
    stakeholder_level VARCHAR(50),
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_qualitative_signals_account ON qualitative_signals(account_id);
CREATE INDEX idx_qualitative_signals_date ON qualitative_signals(signal_date);
CREATE INDEX idx_qualitative_signals_type ON qualitative_signals(signal_type);
CREATE INDEX idx_qualitative_signals_sentiment ON qualitative_signals(sentiment_label);
CREATE INDEX idx_qualitative_signals_stakeholder ON qualitative_signals(stakeholder_level);

COMMENT ON TABLE qualitative_signals IS 'Qualitative signals (emails, meetings, calls, slack)';

-- ============================================================================
-- 8. ACCOUNT HEALTH HISTORY TABLE
-- ============================================================================

CREATE TABLE account_health_history (
    history_id SERIAL PRIMARY KEY,
    account_id INTEGER NOT NULL REFERENCES accounts(account_id),
    customer_id INTEGER NOT NULL REFERENCES customers(customer_id),
    snapshot_month DATE NOT NULL,
    overall_health_score INTEGER,
    health_trend VARCHAR(50),
    deployment_score INTEGER,
    operational_score INTEGER,
    ai_performance_score INTEGER,
    channel_score INTEGER,
    expansion_score INTEGER,
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(account_id, snapshot_month)
);

CREATE INDEX idx_account_health_account ON account_health_history(account_id);
CREATE INDEX idx_account_health_month ON account_health_history(snapshot_month);
CREATE INDEX idx_account_health_score ON account_health_history(overall_health_score);

COMMENT ON TABLE account_health_history IS 'Monthly account health snapshots';

-- ============================================================================
-- 9. EXPANSION READINESS SCORES TABLE
-- ============================================================================

CREATE TABLE expansion_readiness_scores (
    readiness_id SERIAL PRIMARY KEY,
    account_id INTEGER NOT NULL REFERENCES accounts(account_id),
    customer_id INTEGER NOT NULL REFERENCES customers(customer_id),
    snapshot_month DATE NOT NULL,
    readiness_score INTEGER,
    readiness_level VARCHAR(50),
    expansion_potential_amount BIGINT,
    expansion_likelihood_percent INTEGER,
    estimated_timeline_days INTEGER,
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(account_id, snapshot_month)
);

CREATE INDEX idx_expansion_readiness_account ON expansion_readiness_scores(account_id);
CREATE INDEX idx_expansion_readiness_month ON expansion_readiness_scores(snapshot_month);
CREATE INDEX idx_expansion_readiness_level ON expansion_readiness_scores(readiness_level);

COMMENT ON TABLE expansion_readiness_scores IS 'Monthly expansion readiness tracking';

-- ============================================================================
-- 10. PLAYBOOK EXECUTIONS TABLE
-- ============================================================================

CREATE TABLE playbook_executions (
    execution_id SERIAL PRIMARY KEY,
    account_id INTEGER NOT NULL REFERENCES accounts(account_id),
    customer_id INTEGER NOT NULL REFERENCES customers(customer_id),
    playbook_id VARCHAR(50) NOT NULL,
    playbook_name VARCHAR(255) NOT NULL,
    execution_date DATE NOT NULL,
    triggered_by TEXT,
    success BOOLEAN,
    confidence_score DECIMAL(5,2),
    outcome_description TEXT,
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_playbook_executions_account ON playbook_executions(account_id);
CREATE INDEX idx_playbook_executions_date ON playbook_executions(execution_date);
CREATE INDEX idx_playbook_executions_playbook ON playbook_executions(playbook_id);
CREATE INDEX idx_playbook_executions_success ON playbook_executions(success);

COMMENT ON TABLE playbook_executions IS 'Playbook execution history and outcomes';

-- ============================================================================
-- 11. PRODUCTS TABLE
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
    launched_date DATE,
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_products_category ON products(product_category);
CREATE INDEX idx_products_tier ON products(product_tier);

COMMENT ON TABLE products IS 'Product catalog';

-- ============================================================================
-- 12. ACCOUNT PRODUCTS TABLE
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
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(account_id, product_id)
);

CREATE INDEX idx_account_products_account ON account_products(account_id);
CREATE INDEX idx_account_products_product ON account_products(product_id);
CREATE INDEX idx_account_products_status ON account_products(status);

COMMENT ON TABLE account_products IS 'Account-product usage mapping';

-- ============================================================================
-- GRANT PERMISSIONS (Optional - adjust as needed)
-- ============================================================================

-- Grant access to application user (example)
-- GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA public TO app_user;
-- GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO app_user;

-- ============================================================================
-- VERIFICATION QUERIES
-- ============================================================================

-- List all tables
SELECT table_name, 
       (SELECT COUNT(*) FROM information_schema.columns WHERE table_name = t.table_name) as column_count
FROM information_schema.tables t
WHERE table_schema = 'public' 
  AND table_type = 'BASE TABLE'
ORDER BY table_name;

-- Check indexes
SELECT 
    tablename,
    indexname,
    indexdef
FROM pg_indexes
WHERE schemaname = 'public'
ORDER BY tablename, indexname;

COMMENT ON SCHEMA public IS 'CS Pulse Signal Analyst - Customer 33 Test Environment';
