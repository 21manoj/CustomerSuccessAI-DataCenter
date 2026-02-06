-- ============================================================
-- SIGNAL ANALYST AGENT - SCHEMA EXTENSIONS
-- ============================================================

-- Add new tables for Signal Analyst Agent

-- 1. Qualitative Signals Table
CREATE TABLE IF NOT EXISTS qualitative_signals (
    signal_id SERIAL PRIMARY KEY,
    account_id INTEGER NOT NULL REFERENCES accounts(account_id),
    date DATE NOT NULL,
    signal_type VARCHAR(50) NOT NULL, -- email, meeting, escalation, news
    from_contact VARCHAR(255),
    to_contact VARCHAR(255),
    subject VARCHAR(500),
    summary TEXT NOT NULL,
    sentiment VARCHAR(20) NOT NULL, -- positive, neutral, negative
    priority VARCHAR(20), -- low, medium, high
    keywords TEXT[], -- Array of keywords
    source_system VARCHAR(50), -- gmail, zoom, zendesk, salesforce
    created_at TIMESTAMP DEFAULT NOW()
);

-- Indexes for qualitative_signals
CREATE INDEX IF NOT EXISTS idx_signals_account_date ON qualitative_signals(account_id, date);
CREATE INDEX IF NOT EXISTS idx_signals_sentiment ON qualitative_signals(sentiment);
CREATE INDEX IF NOT EXISTS idx_signals_type ON qualitative_signals(signal_type);

-- 2. Health Trends Table (monthly snapshots)
CREATE TABLE IF NOT EXISTS health_trends (
    trend_id SERIAL PRIMARY KEY,
    account_id INTEGER NOT NULL REFERENCES accounts(account_id),
    month DATE NOT NULL, -- First day of month
    health_score INTEGER NOT NULL,
    trend VARCHAR(20), -- improving, stable, declining
    velocity DECIMAL(5,2), -- Points per month
    
    -- Pillar scores
    p1_score DECIMAL(5,2),
    p2_score DECIMAL(5,2),
    p3_score DECIMAL(5,2),
    p4_score DECIMAL(5,2),
    p5_score DECIMAL(5,2),
    
    -- Signal metrics
    total_signals INTEGER,
    positive_signals INTEGER,
    neutral_signals INTEGER,
    negative_signals INTEGER,
    escalations INTEGER,
    
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_health_account_month ON health_trends(account_id, month);

-- 3. External Events Table (news, benchmarks)
CREATE TABLE IF NOT EXISTS external_events (
    event_id SERIAL PRIMARY KEY,
    account_id INTEGER REFERENCES accounts(account_id), -- NULL for industry-wide
    event_date DATE NOT NULL,
    event_type VARCHAR(50) NOT NULL, -- news, benchmark, competitor, economic
    source VARCHAR(255),
    title VARCHAR(500),
    summary TEXT,
    sentiment VARCHAR(20),
    relevance_score DECIMAL(3,2), -- 0.00 to 1.00
    impact VARCHAR(50), -- budget_risk, expansion_opportunity, etc.
    url TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_events_account_date ON external_events(account_id, event_date);
CREATE INDEX IF NOT EXISTS idx_events_type ON external_events(event_type);

-- 4. Playbooks Table
CREATE TABLE IF NOT EXISTS playbooks (
    playbook_id VARCHAR(20) PRIMARY KEY, -- e.g., PB-009
    playbook_name VARCHAR(255) NOT NULL,
    description TEXT,
    trigger_conditions JSONB NOT NULL, -- JSON with trigger rules
    actions JSONB NOT NULL, -- JSON array of actions
    success_rate DECIMAL(5,2), -- 0.00 to 100.00
    times_triggered INTEGER DEFAULT 0,
    times_successful INTEGER DEFAULT 0,
    avg_health_impact DECIMAL(5,2), -- Average health score change
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- 5. Action Log Table (tracks what was done)
CREATE TABLE IF NOT EXISTS action_log (
    action_id SERIAL PRIMARY KEY,
    account_id INTEGER NOT NULL REFERENCES accounts(account_id),
    playbook_id VARCHAR(20) REFERENCES playbooks(playbook_id),
    date_taken DATE NOT NULL,
    action_type VARCHAR(50) NOT NULL, -- EBR, workload_audit, renewal_prep
    owner VARCHAR(255) NOT NULL, -- CSM name
    description TEXT,
    
    -- Baseline metrics at time of action
    baseline_health INTEGER,
    baseline_sentiment VARCHAR(20),
    
    -- Context snapshot
    context_snapshot JSONB,
    
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_actions_account ON action_log(account_id);
CREATE INDEX IF NOT EXISTS idx_actions_playbook ON action_log(playbook_id);
CREATE INDEX IF NOT EXISTS idx_actions_date ON action_log(date_taken);

-- 6. Action Outcomes Table (tracks results)
CREATE TABLE IF NOT EXISTS action_outcomes (
    outcome_id SERIAL PRIMARY KEY,
    action_id INTEGER NOT NULL REFERENCES action_log(action_id),
    measurement_date DATE NOT NULL,
    days_since_action INTEGER,
    
    -- Outcome metrics
    health_score INTEGER,
    health_delta INTEGER, -- Change from baseline
    sentiment VARCHAR(20),
    signal_changes JSONB,
    
    -- Business outcomes
    business_outcome VARCHAR(50), -- renewed, churned, expanded, ongoing
    outcome_value DECIMAL(12,2), -- $ impact
    
    -- Feedback
    csm_feedback TEXT,
    csm_rating INTEGER CHECK (csm_rating BETWEEN 1 AND 5),
    
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_outcomes_action ON action_outcomes(action_id);
CREATE INDEX IF NOT EXISTS idx_outcomes_date ON action_outcomes(measurement_date);

-- 7. Benchmarks Table (peer performance data)
CREATE TABLE IF NOT EXISTS benchmarks (
    benchmark_id SERIAL PRIMARY KEY,
    industry VARCHAR(100) NOT NULL,
    company_size VARCHAR(50), -- Enterprise, Mid-Market, Startup
    kpi_code VARCHAR(20) NOT NULL,
    
    -- Percentile values
    p25 DECIMAL(10,2),
    p50 DECIMAL(10,2),
    p75 DECIMAL(10,2),
    p90 DECIMAL(10,2),
    
    data_source VARCHAR(100),
    as_of_date DATE NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_benchmarks_industry_kpi ON benchmarks(industry, kpi_code);

-- 8. Best Practices Table (proven interventions)
CREATE TABLE IF NOT EXISTS best_practices (
    practice_id VARCHAR(20) PRIMARY KEY, -- e.g., BP-047
    category VARCHAR(50), -- recovery, expansion, onboarding
    situation TEXT NOT NULL,
    action_taken TEXT NOT NULL,
    success_rate DECIMAL(5,2),
    avg_impact DECIMAL(10,2), -- e.g., +14 health points
    time_to_impact_days INTEGER,
    applicable_to TEXT[], -- Array: industries, tiers, stages
    evidence_source TEXT,
    sample_size INTEGER,
    created_at TIMESTAMP DEFAULT NOW()
);

-- ============================================================
-- SEED DATA - PLAYBOOKS
-- ============================================================

INSERT INTO playbooks (playbook_id, playbook_name, description, trigger_conditions, actions, success_rate) VALUES
('PB-009', 'High-Risk Account Recovery', 'Emergency intervention for accounts at high churn risk', 
 '{"health_below": 65, "days_to_renewal_below": 120, "arr_above": 500000}'::jsonb,
 '[
    {"action": "Schedule Executive Business Review", "owner": "CSM Manager", "timeline": "7 days"},
    {"action": "Deploy TAM for workload audit", "owner": "TAM", "timeline": "14 days"},
    {"action": "Prepare renewal scenarios", "owner": "AE", "timeline": "30 days"}
 ]'::jsonb,
 78.0),

('PB-023', 'Expansion Opportunity Pursuit', 'Proactive expansion for healthy high-utilization accounts',
 '{"health_above": 85, "gpu_utilization_above": 85, "positive_sentiment_pct_above": 60}'::jsonb,
 '[
    {"action": "Schedule capacity planning QBR", "owner": "CSM", "timeline": "14 days"},
    {"action": "Prepare technical sizing proposal", "owner": "TAM", "timeline": "21 days"},
    {"action": "Build ROI analysis", "owner": "AE", "timeline": "21 days"}
 ]'::jsonb,
 78.0),

('PB-012', 'Pre-Renewal Health Check', 'Ensure smooth renewal for borderline accounts',
 '{"days_to_renewal_between": [90, 120], "health_between": [70, 80], "no_qbr_days": 90}'::jsonb,
 '[
    {"action": "Schedule renewal planning QBR", "owner": "CSM", "timeline": "7 days"},
    {"action": "Review success criteria progress", "owner": "CSM", "timeline": "14 days"},
    {"action": "Prepare renewal business case", "owner": "AE", "timeline": "30 days"}
 ]'::jsonb,
 85.0)
ON CONFLICT (playbook_id) DO NOTHING;

-- ============================================================
-- SEED DATA - BENCHMARKS (Sample)
-- ============================================================

INSERT INTO benchmarks (industry, company_size, kpi_code, p25, p50, p75, p90, data_source, as_of_date) VALUES
('Financial Services', 'Enterprise', 'P1-KPI1', 72, 81, 88, 93, 'Industry Survey 2024', '2024-12-01'),
('Manufacturing', 'Enterprise', 'P1-KPI1', 58, 67, 74, 82, 'Industry Survey 2024', '2024-12-01'),
('AI Research', 'Enterprise', 'P1-KPI1', 78, 85, 91, 95, 'Industry Survey 2024', '2024-12-01'),
('Healthcare', 'Enterprise', 'P1-KPI1', 70, 79, 86, 92, 'Industry Survey 2024', '2024-12-01')
ON CONFLICT DO NOTHING;

-- ============================================================
-- SEED DATA - BEST PRACTICES (Sample)
-- ============================================================

INSERT INTO best_practices (practice_id, category, situation, action_taken, success_rate, avg_impact, time_to_impact_days, applicable_to, evidence_source, sample_size) VALUES
('BP-047', 'recovery', 'At-risk account with executive turnover', 'Schedule EBR within 7 days with new exec sponsor', 92.0, 14.0, 60, ARRAY['Manufacturing', 'Enterprise', 'At-Risk'], '12 successful recoveries (2023-2024)', 12),
('BP-023', 'expansion', 'Healthy account with growing workload', 'Proactive capacity planning QBR', 78.0, 32.0, 90, ARRAY['All Industries', 'Healthy', 'Growth Phase'], '23 successful expansions', 23),
('BP-015', 'onboarding', 'New deployment in first 90 days', 'Weekly technical check-ins with TAM', 88.0, 18.0, 30, ARRAY['All Industries', 'Onboarding'], '45 successful onboardings', 45)
ON CONFLICT (practice_id) DO NOTHING;

-- ============================================================
-- CREATE VIEWS FOR COMMON QUERIES
-- ============================================================

-- View: Current account health with latest signals
CREATE OR REPLACE VIEW v_account_health_current AS
SELECT 
    a.account_id,
    a.account_name,
    a.revenue as arr,
    a.account_status,
    (a.profile_metadata::jsonb)->>'assigned_csm' as csm,
    (a.profile_metadata::jsonb)->>'account_tier' as tier,
    (a.profile_metadata::jsonb)->'engagement'->>'lifecycle_stage' as lifecycle_stage,
    (a.profile_metadata::jsonb)->'engagement'->>'engagement_score' as engagement_score,
    
    -- Latest health trend
    ht.health_score,
    ht.trend,
    ht.velocity,
    
    -- Signal counts (last 90 days)
    COUNT(CASE WHEN qs.sentiment = 'positive' THEN 1 END) as positive_signals_90d,
    COUNT(CASE WHEN qs.sentiment = 'neutral' THEN 1 END) as neutral_signals_90d,
    COUNT(CASE WHEN qs.sentiment = 'negative' THEN 1 END) as negative_signals_90d,
    COUNT(CASE WHEN qs.signal_type = 'escalation' THEN 1 END) as escalations_90d

FROM accounts a
LEFT JOIN LATERAL (
    SELECT * FROM health_trends 
    WHERE account_id = a.account_id 
    ORDER BY month DESC 
    LIMIT 1
) ht ON true
LEFT JOIN qualitative_signals qs ON qs.account_id = a.account_id 
    AND qs.date >= CURRENT_DATE - INTERVAL '90 days'
GROUP BY a.account_id, a.account_name, a.revenue, a.account_status, a.profile_metadata::text;

-- ============================================================
-- SUCCESS MESSAGE
-- ============================================================

SELECT 'Schema extensions completed successfully!' as message,
       'Created 8 new tables, 3 playbooks, 4 benchmarks, 3 best practices' as details;


