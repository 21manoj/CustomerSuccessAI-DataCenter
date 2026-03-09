-- CS Pulse — Seed Data
-- Minimal data needed for a fresh platform instance

-- Default admin customer
INSERT INTO customers (customer_id, customer_name, email, domain, vertical, created_at)
VALUES (1, 'CS Pulse Admin', 'admin@cspulse.io', 'cspulse.io', 'dc2_s', CURRENT_TIMESTAMP)
ON CONFLICT (customer_id) DO NOTHING;

-- Default admin user (password: Admin2026!)
-- Hash generated with werkzeug.security.generate_password_hash
INSERT INTO users (customer_id, user_name, email, password_hash, role, vertical, active, created_at)
VALUES (
    1,
    'admin',
    'admin@cspulse.io',
    'scrypt:32768:8:1$salt$placeholder_hash_replace_at_runtime',
    'admin',
    'dc2_s',
    TRUE,
    CURRENT_TIMESTAMP
) ON CONFLICT DO NOTHING;

-- Default customer config
INSERT INTO customer_configs (customer_id, vertical, dc2s_enabled_kpis, dc2s_pillar_weights, config_version)
VALUES (
    1,
    'dc2_s',
    '["AI-KPI1","AI-KPI2","AI-KPI3","CH-KPI1","CH-KPI2","CH-KPI3","DV-KPI1","DV-KPI2","DV-KPI3","EX-KPI1","EX-KPI2","EX-KPI3","OS-KPI1","OS-KPI2","OS-KPI3"]',
    '{"AI": 0.25, "CH": 0.20, "DV": 0.15, "EX": 0.20, "OS": 0.20}',
    '1.0'
) ON CONFLICT (customer_id) DO NOTHING;
