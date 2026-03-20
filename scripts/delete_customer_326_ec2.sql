-- Delete Clone1dc2s (customer_id 326) on EC2 - run inside cspulse-postgres container
-- Order: account_id children -> accounts -> customer_id children -> customers
\set ON_ERROR_STOP 0

-- By account_id (accounts of customer 326)
DELETE FROM account_notes WHERE account_id IN (SELECT account_id FROM accounts WHERE customer_id = 326);
DELETE FROM account_snapshots WHERE account_id IN (SELECT account_id FROM accounts WHERE customer_id = 326);
DELETE FROM action_economics WHERE account_id IN (SELECT account_id FROM accounts WHERE customer_id = 326);
DELETE FROM agent_memory WHERE account_id IN (SELECT account_id FROM accounts WHERE customer_id = 326);
DELETE FROM context_nodes WHERE account_id IN (SELECT account_id FROM accounts WHERE customer_id = 326);
DELETE FROM dc2s_kpis WHERE account_id IN (SELECT account_id FROM accounts WHERE customer_id = 326);
DELETE FROM health_scores WHERE account_id IN (SELECT account_id FROM accounts WHERE customer_id = 326);
DELETE FROM health_trends WHERE account_id IN (SELECT account_id FROM accounts WHERE customer_id = 326);
DELETE FROM journey_data WHERE account_id IN (SELECT account_id FROM accounts WHERE customer_id = 326);
DELETE FROM kpi_scores WHERE account_id IN (SELECT account_id FROM accounts WHERE customer_id = 326);
DELETE FROM kpi_time_series WHERE account_id IN (SELECT account_id FROM accounts WHERE customer_id = 326);
DELETE FROM kpi_uploads WHERE account_id IN (SELECT account_id FROM accounts WHERE customer_id = 326);
DELETE FROM kpis WHERE account_id IN (SELECT account_id FROM accounts WHERE customer_id = 326);
DELETE FROM pillar_scores WHERE account_id IN (SELECT account_id FROM accounts WHERE customer_id = 326);
DELETE FROM playbook_executions WHERE account_id IN (SELECT account_id FROM accounts WHERE customer_id = 326);
DELETE FROM playbook_reports WHERE account_id IN (SELECT account_id FROM accounts WHERE customer_id = 326);
DELETE FROM playbook_step_log WHERE account_id IN (SELECT account_id FROM accounts WHERE customer_id = 326);
DELETE FROM product_trends WHERE account_id IN (SELECT account_id FROM accounts WHERE customer_id = 326);
DELETE FROM products WHERE account_id IN (SELECT account_id FROM accounts WHERE customer_id = 326);
DELETE FROM qualitative_signals WHERE account_id IN (SELECT account_id FROM accounts WHERE customer_id = 326);

-- Accounts
DELETE FROM accounts WHERE customer_id = 326;

-- By customer_id
DELETE FROM activity_logs WHERE customer_id = 326;
DELETE FROM context_edges WHERE customer_id = 326;
DELETE FROM crm_field_mappings WHERE customer_id = 326;
DELETE FROM customer_action_bindings WHERE customer_id = 326;
DELETE FROM customer_api_keys WHERE customer_id = 326;
DELETE FROM customer_configs WHERE customer_id = 326;
DELETE FROM customer_contacts WHERE customer_id = 326;
DELETE FROM customer_workflow_configs WHERE customer_id = 326;
DELETE FROM feature_toggles WHERE customer_id = 326;
DELETE FROM integration_credentials WHERE customer_id = 326;
DELETE FROM kpi_reference_ranges WHERE customer_id = 326;
DELETE FROM playbook_triggers WHERE customer_id = 326;
DELETE FROM portfolio_memberships WHERE customer_id = 326;
DELETE FROM product_aggregate_trends WHERE customer_id = 326;
DELETE FROM product_catalog WHERE customer_id = 326;
DELETE FROM query_audits WHERE customer_id = 326;
DELETE FROM roi_snapshots WHERE customer_id = 326;
DELETE FROM users WHERE customer_id = 326;
DELETE FROM weight_calibration_history WHERE customer_id = 326;
DELETE FROM wizard_runs WHERE customer_id = 326;
DELETE FROM wizard_files WHERE customer_id = 326;
DELETE FROM wizard_learnings WHERE customer_id = 326;

-- Finally customer
DELETE FROM customers WHERE customer_id = 326;
