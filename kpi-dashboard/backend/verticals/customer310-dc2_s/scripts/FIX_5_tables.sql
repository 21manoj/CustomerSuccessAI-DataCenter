-- ============================================================================
-- FIX 5 FAILED TABLES - Customer 310 Schema Corrections
-- ============================================================================
-- This script fixes all schema mismatches for the 5 tables that failed to load
-- Run this AFTER creating the schema but BEFORE loading data
-- ============================================================================

\echo '=========================================='
\echo 'FIXING 5 TABLE SCHEMAS'
\echo '=========================================='
\echo ''

-- ============================================================================
-- 1. FIX kpi_definitions - Rename range_* columns to match CSV
-- ============================================================================
\echo '1. Fixing kpi_definitions column names...'

-- Rename state_* columns to range_* to match CSV
ALTER TABLE kpi_definitions 
    RENAME COLUMN state_critical_min TO range_critical_min;

ALTER TABLE kpi_definitions 
    RENAME COLUMN state_critical_max TO range_critical_max;

ALTER TABLE kpi_definitions 
    RENAME COLUMN state_atrisk_min TO range_atrisk_min;

ALTER TABLE kpi_definitions 
    RENAME COLUMN state_atrisk_max TO range_atrisk_max;

ALTER TABLE kpi_definitions 
    RENAME COLUMN state_healthy_min TO range_healthy_min;

ALTER TABLE kpi_definitions 
    RENAME COLUMN state_healthy_max TO range_healthy_max;

ALTER TABLE kpi_definitions 
    RENAME COLUMN state_optimal_min TO range_optimal_min;

ALTER TABLE kpi_definitions 
    RENAME COLUMN state_optimal_max TO range_optimal_max;

\echo '   ✅ kpi_definitions: Renamed 8 columns (state_* → range_*)'

-- ============================================================================
-- 2. FIX kpi_measurements - Change measurement_id from INTEGER to TEXT
-- ============================================================================
\echo '2. Fixing kpi_measurements.measurement_id data type...'

-- Drop the primary key constraint first
ALTER TABLE kpi_meements DROP CONSTRAINT kpi_measurements_pkey;

-- Change column type from INTEGER to TEXT
ALTER TABLE kpi_measurements 
    ALTER COLUMN measurement_id TYPE TEXT;

-- Recreate primary key
ALTER TABLE kpi_measurements 
    ADD PRIMARY KEY (measurement_id);

\echo '   ✅ kpi_measurements: Changed measurement_id INTEGER → TEXT'

-- ============================================================================
-- 3. FIX account_health_history - Change month from DATE to TEXT
-- ============================================================================
\echo '3. Fixing account_health_history.month data type...'

-- Change month column from DATE to TEXT (CSV has 'YYYY-MM' format)
ALTER TABLE account_health_history 
    ALTER COLUMN month TYPE TEXT;

\echo '   ✅ account_health_history: Changed month DATE → TEXT'

-- ============================================================================
-- 4. FIX expansion_readiness_scores - Change month from DATE to TEXT
-- ====================================================================
\echo '4. Fixing expansion_readiness_scores.month data type...'

-- Change month column from DATE to TEXT (CSV has 'YYYY-MM' format)
ALTER TABLE expansion_readiness_scores 
    ALTER COLUMN month TYPE TEXT;

\echo '   ✅ expansion_readiness_scores: Changed month DATE → TEXT'

-- ============================================================================
-- 5. FIX playbook_executions - Change execution_id from INTEGER to TEXT
-- ============================================================================
\echo '5. Fixing playbook_executions.execution_id data type...'

-- Drop the primary key constraint first
ALTER TABLE playbook_executions DROP CONSTRAINT playbook_executions_pkey;

-- Change column type from INTEGER to TEXT
ALTER TABLE playbook_executions 
    ALTER COLUMN execution_id TYPE TEXT;

-- Recreate primary key
ALTER TABLE playbook_executions 
    ADD PRIMARY KEY (execution_id);

\echo '   ✅ playbook_executions: Changed execution_id INTEGER → TEXT'

-- ====================================================================
-- VERIFICATION
-- ============================================================================
\echo ''
\echo '=========================================='
\echo 'SCHEMA FIXES COMPLETE'
\echo '=========================================='
\echo ''
\echo 'Fixed tables:'
\echo '  1. kpi_definitions        - 8 columns renamed'
\echo '  2. kpi_measurements       - measurement_id → TEXT'
\echo '  3. account_health_history - month → TEXT'  
\echo '  4. expansion_readiness_scores - month → TEXT'
\echo '  5. playbook_executions    - execution_id → TEXT'
\echo ''
\echo 'You can now run: python3 scripts/02_load_customer310_data.py'
\echo ''
