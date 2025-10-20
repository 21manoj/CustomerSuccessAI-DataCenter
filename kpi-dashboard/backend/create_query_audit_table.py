#!/usr/bin/env python3
"""
Create QueryAudit table
"""
import sqlite3
import os

db_path = os.path.join(os.path.dirname(__file__), '..', 'instance', 'kpi_dashboard.db')

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Create query_audits table
cursor.execute('''
CREATE TABLE IF NOT EXISTS query_audits (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id INTEGER NOT NULL,
    user_id INTEGER,
    query_text TEXT NOT NULL,
    query_type VARCHAR(50) DEFAULT 'general',
    
    -- Response metadata
    response_text TEXT,
    response_time_ms INTEGER,
    results_count INTEGER,
    
    -- Classification
    is_deterministic BOOLEAN DEFAULT 0,
    cache_hit BOOLEAN DEFAULT 0,
    
    -- Enhancements
    mcp_enhanced BOOLEAN DEFAULT 0,
    playbook_enhanced BOOLEAN DEFAULT 0,
    
    -- Conversation context
    has_conversation_history BOOLEAN DEFAULT 0,
    conversation_turn INTEGER DEFAULT 1,
    
    -- Cost tracking
    estimated_cost REAL DEFAULT 0.0,
    
    -- Audit fields
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    ip_address VARCHAR(45),
    user_agent VARCHAR(500),
    
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id),
    FOREIGN KEY (user_id) REFERENCES users(user_id)
)
''')

# Create indexes
cursor.execute('CREATE INDEX IF NOT EXISTS idx_query_audits_customer ON query_audits(customer_id)')
cursor.execute('CREATE INDEX IF NOT EXISTS idx_query_audits_created ON query_audits(created_at)')
cursor.execute('CREATE INDEX IF NOT EXISTS idx_query_audits_customer_date ON query_audits(customer_id, created_at)')

conn.commit()
conn.close()

print('✅ QueryAudit table created successfully')
print('   - Table: query_audits')
print('   - Indexes: 3 created')
print('   - Ready for audit logging')

