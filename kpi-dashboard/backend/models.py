from extensions import db
from datetime import datetime

# Import product analytics models
try:
    from product_analytics_models import ProductCatalog, ProductTrend, ProductAggregateTrend
except ImportError:
    # Models will be available after tables are created
    pass 
class Customer(db.Model):
    __tablename__ = 'customers'
    customer_id = db.Column(db.Integer, primary_key=True)
    customer_name = db.Column(db.String, nullable=False)
    email = db.Column(db.String, unique=True)
    phone = db.Column(db.String)
    domain = db.Column(db.String, unique=True, nullable=True)  # Email domain for multi-tenant identification
    # UUID migration columns (added by phase1a_add_uuid_columns.py)
    uuid = db.Column(db.String(60), nullable=True, unique=True)  # e.g. saas_cust_019c3409-...
    vertical = db.Column(db.String(20), nullable=True)  # saas, dc, msp
    created_at = db.Column(db.DateTime, server_default=db.func.now())
    updated_at = db.Column(db.DateTime, server_default=db.func.now(), onupdate=db.func.now())

class CustomerConfig(db.Model):
    __tablename__ = 'customer_configs'
    config_id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.customer_id'), unique=True)
    
    # ============================================================
    # EXISTING SaaS FIELDS (DO NOT MODIFY - KEEP AS IS)
    # ============================================================
    kpi_upload_mode = db.Column(db.String, default='corporate')  # 'corporate' or 'account_rollup'
    category_weights = db.Column(db.Text)  # JSON string of category weights
    master_file_name = db.Column(db.String)  # Name of uploaded master file
    # OpenAI API Key (encrypted)
    openai_api_key_encrypted = db.Column(db.Text, nullable=True)  # Encrypted OpenAI API key
    openai_api_key_updated_at = db.Column(db.DateTime, nullable=True)  # When key was last updated
    
    # ============================================================
    # NEW DC2_S FIELDS (ADDED FOR PHASE 1 MIGRATION)
    # ============================================================
    
    # Vertical identifier
    vertical = db.Column(db.String(50), default='saas')  # 'saas' or 'dc2_s'
    
    # DC2_S Configuration (JSON blobs)
    dc2s_pillar_weights = db.Column(db.JSON, nullable=True)     # {"AI": 0.25, "CH": 0.20, ...}
    dc2s_enabled_kpis = db.Column(db.JSON, nullable=True)       # ["AI-KPI1", "CUSTOM-GPU-1", ...]
    dc2s_kpi_overrides = db.Column(db.JSON, nullable=True)      # {"AI-KPI1": {"target": 90}, ...}
    dc2s_kpi_weights = db.Column(db.JSON, nullable=True)        # {"AI": {"AI-KPI1": 0.4, ...}, ...}
    dc2s_kpi_definitions = db.Column(db.JSON, nullable=True)    # Custom KPI definitions
    
    # Metadata
    config_version = db.Column(db.String(20), default='1.0')
    customized_by = db.Column(db.String(255))
    
    # Timestamps (already exist, don't duplicate)
    created_at = db.Column(db.DateTime, server_default=db.func.now())
    updated_at = db.Column(db.DateTime, server_default=db.func.now(), onupdate=db.func.now())

class Account(db.Model):
    __tablename__ = 'accounts'
    account_id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.customer_id'), nullable=False, index=True)
    account_name = db.Column(db.String, nullable=False, index=True)
    revenue = db.Column(db.Numeric(15, 2), default=0)
    account_status = db.Column(db.String, default='active', index=True)  # active, inactive, etc.
    industry = db.Column(db.String, index=True)
    vertical = db.Column(db.String(50))
    region = db.Column(db.String, index=True)
    external_account_id = db.Column(db.String, index=True)  # External account ID from customer profile
    profile_metadata = db.Column(db.JSON)  # JSON field for customer profile data
    # UUID migration columns (added by phase1a_add_uuid_columns.py)
    uuid = db.Column(db.String(60), nullable=True, unique=True)  # e.g. saas_acct_019c3409-...
    customer_uuid = db.Column(db.String(60), nullable=True)  # FK to customers.uuid
    created_at = db.Column(db.DateTime, server_default=db.func.now(), index=True)
    updated_at = db.Column(db.DateTime, server_default=db.func.now(), onupdate=db.func.now())
    
    # Composite indexes for common query patterns
    __table_args__ = (
        db.Index('idx_account_customer_status', 'customer_id', 'account_status'),
        db.Index('idx_account_customer_industry', 'customer_id', 'industry'),
        db.Index('idx_account_customer_region', 'customer_id', 'region'),
    )

class Product(db.Model):
    __tablename__ = 'products'
    product_id = db.Column(db.Integer, primary_key=True)
    account_id = db.Column(db.Integer, db.ForeignKey('accounts.account_id'), nullable=False)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.customer_id'), nullable=False)
    product_name = db.Column(db.String(255), nullable=False)
    product_sku = db.Column(db.String(100))
    product_type = db.Column(db.String(100))
    revenue = db.Column(db.Numeric(15, 2))
    status = db.Column(db.String(50), default='active')
    created_at = db.Column(db.DateTime, server_default=db.func.now())
    updated_at = db.Column(db.DateTime, server_default=db.func.now(), onupdate=db.func.now())
    
    __table_args__ = (
        db.UniqueConstraint('account_id', 'product_name', name='unique_account_product'),
    )

class User(db.Model):
    __tablename__ = 'users'
    user_id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.customer_id'))
    user_name = db.Column(db.String, nullable=False)
    email = db.Column(db.String, nullable=False)
    password_hash = db.Column(db.String(128))
    active = db.Column(db.Boolean, default=True)  # For account deactivation
    last_login = db.Column(db.DateTime)
    # UUID migration columns (added by phase1a_add_uuid_columns.py)
    uuid = db.Column(db.String(60), nullable=True, unique=True)  # e.g. saas_user_019c3409-...
    customer_uuid = db.Column(db.String(60), nullable=True)  # FK to customers.uuid
    created_at = db.Column(db.DateTime, server_default=db.func.now())
    updated_at = db.Column(db.DateTime, server_default=db.func.now(), onupdate=db.func.now())
    vertical = db.Column(db.String(50))
    role = db.Column(db.String(50))    
    # Ensure username is unique within each customer domain
    # Email must be unique globally
    __table_args__ = (
        db.UniqueConstraint('customer_id', 'user_name', name='unique_customer_username'),
        db.UniqueConstraint('email', name='unique_user_email'),
    )
    
    # Flask-Login required methods
    def is_authenticated(self):
        """User is authenticated if they have a valid session"""
        return True
    
    def is_active(self):
        """Check if user account is active"""
        return self.active
    
    def is_anonymous(self):
        """User is not anonymous"""
        return False
    
    def get_id(self):
        """Return user ID as string (Flask-Login requirement)"""
        return str(self.user_id)

# Note: Flask-Session automatically creates 'sessions' table
# We don't need to define it here - it manages its own schema

class KPIUpload(db.Model):
    __tablename__ = 'kpi_uploads'
    upload_id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.customer_id'), nullable=False, index=True)
    account_id = db.Column(db.Integer, db.ForeignKey('accounts.account_id'), index=True)  # Link to account
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), index=True)
    uploaded_at = db.Column(db.DateTime, server_default=db.func.now(), index=True)
    version = db.Column(db.Integer, nullable=False)
    original_filename = db.Column(db.String)
    raw_excel = db.Column(db.LargeBinary)  # Store original file
    parsed_json = db.Column(db.JSON)       # Optionally store parsed structure
    
    # Composite indexes for common query patterns
    __table_args__ = (
        db.Index('idx_upload_customer_uploaded', 'customer_id', 'uploaded_at'),
        db.Index('idx_upload_account_uploaded', 'account_id', 'uploaded_at'),
    )

class KPI(db.Model):
    __tablename__ = 'kpis'
    kpi_id = db.Column(db.Integer, primary_key=True)
    upload_id = db.Column(db.Integer, db.ForeignKey('kpi_uploads.upload_id'), index=True)
    account_id = db.Column(db.Integer, db.ForeignKey('accounts.account_id'), nullable=False, index=True)  # Direct account link
    product_id = db.Column(db.Integer, db.ForeignKey('products.product_id'), nullable=True, index=True)  # Product-level KPI
    aggregation_type = db.Column(db.String(50), nullable=True, index=True)  # 'account' or 'product'
    category = db.Column(db.String, index=True)  # Tab name
    row_index = db.Column(db.Integer)
    health_score_component = db.Column(db.String, index=True)
    weight = db.Column(db.String)
    data = db.Column(db.String)
    source_review = db.Column(db.String)
    kpi_parameter = db.Column(db.String, index=True)  # Frequently queried
    impact_level = db.Column(db.String, index=True)
    measurement_frequency = db.Column(db.String)
    last_edited_by = db.Column(db.Integer, db.ForeignKey('users.user_id'))
    last_edited_at = db.Column(db.DateTime, index=True)
    
    # Composite indexes for common query patterns
    __table_args__ = (
        db.Index('idx_kpi_account_category', 'account_id', 'category'),
        db.Index('idx_kpi_account_parameter', 'account_id', 'kpi_parameter'),
        db.Index('idx_kpi_account_aggregation', 'account_id', 'aggregation_type'),
        db.Index('idx_kpi_upload_account', 'upload_id', 'account_id'),
    )

class HealthTrend(db.Model):
    __tablename__ = 'health_trends'
    trend_id = db.Column(db.Integer, primary_key=True)
    account_id = db.Column(db.Integer, db.ForeignKey('accounts.account_id'), nullable=False, index=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.customer_id'), nullable=False, index=True)
    month = db.Column(db.Integer, nullable=False, index=True)  # 1-12
    year = db.Column(db.Integer, nullable=False, index=True)
    overall_health_score = db.Column(db.Numeric(5, 2), nullable=False)  # 0.00-100.00
    product_usage_score = db.Column(db.Numeric(5, 2))
    support_score = db.Column(db.Numeric(5, 2))
    customer_sentiment_score = db.Column(db.Numeric(5, 2))
    business_outcomes_score = db.Column(db.Numeric(5, 2))
    relationship_strength_score = db.Column(db.Numeric(5, 2))
    total_kpis = db.Column(db.Integer, default=0)
    valid_kpis = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, server_default=db.func.now(), index=True)
    updated_at = db.Column(db.DateTime, server_default=db.func.now(), onupdate=db.func.now())
    
    # Ensure unique combination of account, month, and year
    __table_args__ = (
        db.UniqueConstraint('account_id', 'month', 'year', name='unique_account_month_year'),
        db.Index('idx_health_trend_account_date', 'account_id', 'year', 'month'),
        db.Index('idx_health_trend_customer_date', 'customer_id', 'year', 'month'),
    )

class KPIReferenceRange(db.Model):
    __tablename__ = 'kpi_reference_ranges'
    range_id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.customer_id', ondelete='CASCADE'), nullable=True)  # NULL = system default
    kpi_name = db.Column(db.String, nullable=False)
    unit = db.Column(db.String, nullable=False)
    higher_is_better = db.Column(db.Boolean, nullable=False, default=True)
    
    # Critical range (low performance)
    critical_min = db.Column(db.Numeric(10, 2), nullable=False)
    critical_max = db.Column(db.Numeric(10, 2), nullable=False)
    
    # Risk range (medium performance)
    risk_min = db.Column(db.Numeric(10, 2), nullable=False)
    risk_max = db.Column(db.Numeric(10, 2), nullable=False)
    
    # Healthy range (high performance)
    healthy_min = db.Column(db.Numeric(10, 2), nullable=False)
    healthy_max = db.Column(db.Numeric(10, 2), nullable=False)
    
    # String representations for UI display
    critical_range = db.Column(db.String(100))
    risk_range = db.Column(db.String(100))
    healthy_range = db.Column(db.String(100))
    description = db.Column(db.Text)
    
    # Metadata
    created_at = db.Column(db.DateTime, server_default=db.func.now())
    updated_at = db.Column(db.DateTime, server_default=db.func.now(), onupdate=db.func.now())
    created_by = db.Column(db.Integer, db.ForeignKey('users.user_id'))
    updated_by = db.Column(db.Integer, db.ForeignKey('users.user_id'))
    
    # Composite unique constraint: same kpi_name allowed for different customers
    __table_args__ = (
        db.UniqueConstraint('customer_id', 'kpi_name', name='uq_customer_kpi_name'),
        db.Index('idx_ref_range_customer_kpi', 'customer_id', 'kpi_name'),
    )

class KPITimeSeries(db.Model):
    __tablename__ = 'kpi_time_series'
    id = db.Column(db.Integer, primary_key=True)
    kpi_id = db.Column(db.Integer, db.ForeignKey('kpis.kpi_id'), nullable=False)
    account_id = db.Column(db.Integer, db.ForeignKey('accounts.account_id'), nullable=False)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.customer_id'), nullable=False)
    month = db.Column(db.Integer, nullable=False)  # 1-12
    year = db.Column(db.Integer, nullable=False)
    value = db.Column(db.Numeric(10, 2))  # The actual KPI value
    health_status = db.Column(db.String(20))  # Healthy/Risk/Critical
    health_score = db.Column(db.Numeric(5, 2))  # 0.00-100.00
    created_at = db.Column(db.DateTime, server_default=db.func.now())
    updated_at = db.Column(db.DateTime, server_default=db.func.now(), onupdate=db.func.now())
    
    # Ensure unique combination of kpi, month, and year
    __table_args__ = (
        db.UniqueConstraint('kpi_id', 'month', 'year', name='unique_kpi_month_year'),
        db.Index('idx_time_series_kpi_date', 'kpi_id', 'year', 'month'),
        db.Index('idx_time_series_account_date', 'account_id', 'year', 'month'),
        db.Index('idx_time_series_customer_date', 'customer_id', 'year', 'month'),
    )

class PlaybookTrigger(db.Model):
    __tablename__ = 'playbook_triggers'
    trigger_id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.customer_id'), nullable=False)
    playbook_type = db.Column(db.String(50), nullable=False)  # 'voc', 'activation', 'sla', 'renewal', 'expansion'
    trigger_config = db.Column(db.Text)  # JSON string of trigger configuration
    auto_trigger_enabled = db.Column(db.Boolean, default=False)
    last_evaluated = db.Column(db.DateTime)
    last_triggered = db.Column(db.DateTime)
    trigger_count = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, server_default=db.func.now())
    updated_at = db.Column(db.DateTime, server_default=db.func.now(), onupdate=db.func.now())
    
    # Ensure unique combination of customer and playbook type
    __table_args__ = (db.UniqueConstraint('customer_id', 'playbook_type', name='unique_customer_playbook'),)

class PlaybookExecution(db.Model):
    __tablename__ = 'playbook_executions'
    id = db.Column(db.Integer, primary_key=True)
    execution_id = db.Column(db.String(36), nullable=False, unique=True, index=True)  # UUID
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.customer_id'), nullable=False, index=True)
    account_id = db.Column(db.Integer, db.ForeignKey('accounts.account_id'), nullable=True, index=True)
    playbook_id = db.Column(db.String(50), nullable=False, index=True)  # 'voc-sprint', 'activation-blitz', etc.
    
    # Execution status
    status = db.Column(db.String(20), default='in-progress')  # 'in-progress', 'completed', 'failed', 'cancelled'
    current_step = db.Column(db.String(100))
    
    # Execution data stored as JSON
    execution_data = db.Column(db.JSON, nullable=False)  # Full execution object with context, results, metadata
    
    # Timestamps
    started_at = db.Column(db.DateTime, nullable=False)
    completed_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, server_default=db.func.now())
    updated_at = db.Column(db.DateTime, server_default=db.func.now(), onupdate=db.func.now())
    
    # Relationship to reports (cascade delete)
    reports = db.relationship('PlaybookReport', backref='execution', cascade='all, delete-orphan', passive_deletes=True)
    
    # Indexes for common queries
    __table_args__ = (
        db.Index('idx_customer_playbook_exec', 'customer_id', 'playbook_id'),
        db.Index('idx_account_playbook_exec', 'account_id', 'playbook_id'),
        db.Index('idx_status', 'status'),
    )

class PlaybookReport(db.Model):
    __tablename__ = 'playbook_reports'
    report_id = db.Column(db.Integer, primary_key=True)
    execution_id = db.Column(db.String(36), db.ForeignKey('playbook_executions.execution_id', ondelete='CASCADE'), nullable=False, unique=True, index=True)  # UUID
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.customer_id'), nullable=False, index=True)
    account_id = db.Column(db.Integer, db.ForeignKey('accounts.account_id'), nullable=True, index=True)
    playbook_id = db.Column(db.String(50), nullable=False, index=True)  # 'voc-sprint', 'activation-blitz', etc.
    playbook_name = db.Column(db.String(100), nullable=False)
    account_name = db.Column(db.String(200))
    status = db.Column(db.String(20), default='in-progress')  # 'in-progress', 'completed', 'failed'
    
    # Report data stored as JSON
    report_data = db.Column(db.JSON, nullable=False)  # Full report with RACI, outcomes, exit criteria
    
    # Metadata
    duration = db.Column(db.String(50))  # '30 days', '90 days', etc.
    steps_completed = db.Column(db.Integer, default=0)
    total_steps = db.Column(db.Integer)
    
    # Timestamps
    started_at = db.Column(db.DateTime, nullable=False)
    completed_at = db.Column(db.DateTime)
    report_generated_at = db.Column(db.DateTime, server_default=db.func.now())
    created_at = db.Column(db.DateTime, server_default=db.func.now())
    updated_at = db.Column(db.DateTime, server_default=db.func.now(), onupdate=db.func.now())
    
    # Indexes for common queries
    __table_args__ = (
        db.Index('idx_customer_playbook', 'customer_id', 'playbook_id'),
        db.Index('idx_account_playbook', 'account_id', 'playbook_id'),
    )

class FeatureToggle(db.Model):
    __tablename__ = 'feature_toggles'
    
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.customer_id'), nullable=False, index=True)
    feature_name = db.Column(db.String(100), nullable=False, index=True)
    enabled = db.Column(db.Boolean, default=False, nullable=False)
    config = db.Column(db.JSON)  # Feature-specific configuration
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, server_default=db.func.now())
    updated_at = db.Column(db.DateTime, server_default=db.func.now(), onupdate=db.func.now())
    
    # Ensure unique combination of customer and feature
    __table_args__ = (
        db.UniqueConstraint('customer_id', 'feature_name', name='unique_customer_feature'),
    )

class QueryAudit(db.Model):
    """Audit log for all RAG queries - for compliance and analytics"""
    __tablename__ = 'query_audits'
    
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.customer_id'), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=True, index=True)
    query_text = db.Column(db.Text, nullable=False)
    query_type = db.Column(db.String(50), default='general')
    
    # Response metadata
    response_text = db.Column(db.Text)  # AI response
    response_time_ms = db.Column(db.Integer)  # Response time in milliseconds
    results_count = db.Column(db.Integer)  # Number of results returned
    
    # Classification
    is_deterministic = db.Column(db.Boolean, default=False)  # Deterministic vs analytical query
    cache_hit = db.Column(db.Boolean, default=False)  # Was result from cache?
    
    # Enhancements
    mcp_enhanced = db.Column(db.Boolean, default=False)  # MCP data included?
    playbook_enhanced = db.Column(db.Boolean, default=False)  # Playbook insights included?
    
    # Conversation context
    has_conversation_history = db.Column(db.Boolean, default=False)
    conversation_turn = db.Column(db.Integer, default=1)  # Turn number in conversation
    
    # Cost tracking
    estimated_cost = db.Column(db.Float, default=0.0)  # Estimated OpenAI API cost
    
    # Audit fields
    created_at = db.Column(db.DateTime, server_default=db.func.now(), index=True)
    ip_address = db.Column(db.String(45))  # IPv4 or IPv6
    user_agent = db.Column(db.String(500))
    
    # Relationships
    customer = db.relationship('Customer', backref='query_audits')
    user = db.relationship('User', backref='query_audits')

class ActivityLog(db.Model):
    """Comprehensive activity logging for governance and compliance"""
    __tablename__ = 'activity_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.customer_id', ondelete='CASCADE'), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id', ondelete='SET NULL'), nullable=True, index=True)
    
    # Action details
    action_type = db.Column(db.String(50), nullable=False, index=True)
    action_category = db.Column(db.String(50), nullable=False, index=True)
    resource_type = db.Column(db.String(50), nullable=True, index=True)
    resource_id = db.Column(db.String(100), nullable=True)
    
    # Action description
    action_description = db.Column(db.Text, nullable=False)
    details = db.Column(db.JSON, nullable=True)
    
    # Change tracking
    changed_fields = db.Column(db.JSON, nullable=True)
    before_values = db.Column(db.JSON, nullable=True)
    after_values = db.Column(db.JSON, nullable=True)
    
    # Metadata
    ip_address = db.Column(db.String(45), nullable=True)
    user_agent = db.Column(db.String(500), nullable=True)
    session_id = db.Column(db.String(255), nullable=True)
    
    # Status
    status = db.Column(db.String(20), server_default='success', nullable=False)
    error_message = db.Column(db.Text, nullable=True)
    
    # Timestamp
    created_at = db.Column(db.DateTime, server_default=db.func.now(), nullable=False, index=True)
    
    # Relationships
    customer_rel = db.relationship('Customer', backref='activity_logs')
    user_rel = db.relationship('User', backref='activity_logs')
    
    # Property aliases for backward compatibility
    @property
    def user(self):
        """Alias for user_rel for backward compatibility"""
        return self.user_rel
    
    @property
    def customer(self):
        """Alias for customer_rel for backward compatibility"""
        return self.customer_rel
    
    # Indexes (defined in migration, but also specify here for clarity)
    __table_args__ = (
        db.Index('idx_activity_logs_customer_date', 'customer_id', 'created_at'),
        db.Index('idx_activity_logs_user_date', 'user_id', 'created_at'),
        db.Index('idx_activity_logs_action_type_date', 'action_type', 'created_at'),
        db.Index('idx_activity_logs_resource', 'resource_type', 'resource_id'),
    )

class CustomerWorkflowConfig(db.Model):
    """Configuration for n8n workflow system and playbook execution"""
    __tablename__ = 'customer_workflow_configs'
    
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.customer_id', ondelete='CASCADE'), nullable=False, unique=True, index=True)
    
    # Workflow system configuration
    workflow_system = db.Column(db.String(50), nullable=True)  # 'n8n', 'zapier', etc.
    n8n_instance_type = db.Column(db.String(50), nullable=True)  # 'cloud', 'self-hosted'
    n8n_base_url = db.Column(db.String(500), nullable=True)
    n8n_webhook_url = db.Column(db.String(500), nullable=True)
    
    # API key (encrypted)
    n8n_api_key_encrypted = db.Column(db.String(500), nullable=True)
    n8n_api_key_updated_at = db.Column(db.DateTime, nullable=True)
    
    # Webhook secrets (encrypted)
    webhook_secret_encrypted = db.Column(db.String(500), nullable=True)
    webhook_secret_old_encrypted = db.Column(db.String(500), nullable=True)  # For rotation grace period
    webhook_secret_rotated_at = db.Column(db.DateTime, nullable=True)
    webhook_secret_grace_period_until = db.Column(db.DateTime, nullable=True)
    
    # Playbook configuration
    enabled_playbooks = db.Column(db.JSON, nullable=True)  # List of enabled playbook IDs
    config = db.Column(db.JSON, nullable=True)  # Additional configuration
    
    # Timestamps
    created_at = db.Column(db.DateTime, server_default=db.func.now(), nullable=False)
    updated_at = db.Column(db.DateTime, server_default=db.func.now(), onupdate=db.func.now(), nullable=False)
    
    # Relationships
    customer_rel = db.relationship('Customer', backref='workflow_config')
    
    # Unique constraint: one config per customer
    __table_args__ = (
        db.UniqueConstraint('customer_id', name='uq_customer_workflow_config'),
    )

class AccountNote(db.Model):
    """CSM notes, meeting notes, QBR notes, and other account-related notes"""
    __tablename__ = 'account_notes'
    
    note_id = db.Column(db.Integer, primary_key=True)
    account_id = db.Column(db.Integer, db.ForeignKey('accounts.account_id'), nullable=False, index=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.customer_id'), nullable=False, index=True)
    
    # Note Content
    note_type = db.Column(db.String(50), nullable=False)  # 'meeting', 'qbr', 'call', 'email', 'general', 'interaction'
    note_content = db.Column(db.Text, nullable=False)  # Full note text
    note_title = db.Column(db.String(255))  # Optional title/subject
    
    # Metadata
    created_by = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)
    created_at = db.Column(db.DateTime, server_default=db.func.now(), nullable=False, index=True)
    updated_at = db.Column(db.DateTime, server_default=db.func.now(), onupdate=db.func.now())
    
    # Optional Fields
    meeting_date = db.Column(db.Date)  # Date of meeting/call (if applicable)
    participants = db.Column(db.JSON)  # List of participant names
    tags = db.Column(db.JSON)  # List of tags for categorization
    is_important = db.Column(db.Boolean, default=False)  # Flag for important notes
    related_playbook_id = db.Column(db.String(50))  # Link to playbook if note is playbook-related
    
    # Indexes
    __table_args__ = (
        db.Index('idx_account_note_timestamp', 'account_id', 'created_at'),
        db.Index('idx_customer_note_timestamp', 'customer_id', 'created_at'),
        db.Index('idx_note_type', 'note_type'),
    )

class AccountSnapshot(db.Model):
    """Unified account snapshot capturing complete account state at a point in time"""
    __tablename__ = 'account_snapshots'
    
    # Primary Key
    snapshot_id = db.Column(db.Integer, primary_key=True)
    
    # Account & Customer
    account_id = db.Column(db.Integer, db.ForeignKey('accounts.account_id'), nullable=False, index=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.customer_id'), nullable=False, index=True)
    
    # Snapshot Metadata
    snapshot_timestamp = db.Column(db.DateTime, nullable=False, index=True)
    snapshot_type = db.Column(db.String(50), nullable=False)  # manual, scheduled, event_driven, post_upload, post_health_calc
    snapshot_reason = db.Column(db.String(255))  # Optional reason
    snapshot_version = db.Column(db.Integer, default=1)  # Schema version
    created_by = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=True)
    trigger_event = db.Column(db.String(100))  # Event that triggered snapshot
    
    # Financial
    revenue = db.Column(db.Numeric(15, 2))
    revenue_change_from_last = db.Column(db.Numeric(15, 2))
    revenue_change_percent = db.Column(db.Numeric(5, 2))
    
    # Health Scores
    overall_health_score = db.Column(db.Numeric(5, 2))
    product_usage_score = db.Column(db.Numeric(5, 2))
    support_score = db.Column(db.Numeric(5, 2))
    customer_sentiment_score = db.Column(db.Numeric(5, 2))
    business_outcomes_score = db.Column(db.Numeric(5, 2))
    relationship_strength_score = db.Column(db.Numeric(5, 2))
    health_score_change_from_last = db.Column(db.Numeric(5, 2))
    health_score_trend = db.Column(db.String(20))  # improving, declining, stable
    
    # Account Status
    account_status = db.Column(db.String(50))
    industry = db.Column(db.String(100))
    region = db.Column(db.String(100))
    account_tier = db.Column(db.String(50))
    external_account_id = db.Column(db.String(100))
    
    # CSM & Team
    assigned_csm = db.Column(db.String(100))
    csm_manager = db.Column(db.String(100))
    account_owner = db.Column(db.String(100))
    
    # Products
    products_used = db.Column(db.JSON)  # List of product names
    product_count = db.Column(db.Integer, default=0)
    primary_product = db.Column(db.String(100))
    
    # Playbooks
    playbooks_running = db.Column(db.JSON)  # List of playbook IDs
    playbooks_running_count = db.Column(db.Integer, default=0)
    playbooks_completed_count = db.Column(db.Integer, default=0)
    playbooks_completed_last_30_days = db.Column(db.Integer, default=0)
    last_playbook_executed = db.Column(db.JSON)  # {playbook_id, date}
    playbook_recommendations_active = db.Column(db.JSON)  # List of recommended playbooks
    recent_playbook_report_ids = db.Column(db.JSON)  # [report_id1, report_id2, report_id3] - Last 3 reports
    
    # KPI Summary
    total_kpis = db.Column(db.Integer, default=0)
    account_level_kpis = db.Column(db.Integer, default=0)
    product_level_kpis = db.Column(db.Integer, default=0)
    critical_kpis_count = db.Column(db.Integer, default=0)
    at_risk_kpis_count = db.Column(db.Integer, default=0)
    healthy_kpis_count = db.Column(db.Integer, default=0)
    top_critical_kpis = db.Column(db.JSON)  # [{kpi_name, value, health_status}, ...]
    
    # Engagement
    lifecycle_stage = db.Column(db.String(50))
    onboarding_status = db.Column(db.String(50))
    last_qbr_date = db.Column(db.Date)
    next_qbr_date = db.Column(db.Date)
    engagement_score = db.Column(db.Numeric(5, 2))
    
    # Champions
    primary_champion = db.Column(db.String(100))
    champion_status = db.Column(db.String(50))
    stakeholder_count = db.Column(db.Integer, default=0)
    
    # CSM Notes & Playbook Reports (References)
    recent_csm_note_ids = db.Column(db.JSON)  # [note_id1, note_id2, ...] - Last 5 notes
    # Note: recent_playbook_report_ids is already defined above in Playbooks section
    
    # Calculated
    days_since_last_snapshot = db.Column(db.Integer)
    snapshot_sequence_number = db.Column(db.Integer, default=1)
    is_significant_change = db.Column(db.Boolean, default=False)
    
    # Timestamps
    created_at = db.Column(db.DateTime, server_default=db.func.now())
    updated_at = db.Column(db.DateTime, server_default=db.func.now(), onupdate=db.func.now())
    
    # Indexes
    __table_args__ = (
        db.Index('idx_account_snapshot_timestamp', 'account_id', 'snapshot_timestamp'),
        db.Index('idx_customer_snapshot_timestamp', 'customer_id', 'snapshot_timestamp'),
        db.Index('idx_snapshot_type', 'snapshot_type'),
    )
class DC2SKPI(db.Model):
    """DC2_S Vertical KPI Table - separate from SaaS kpis table"""
    __tablename__ = 'dc2s_kpis'
    
    kpi_id = db.Column(db.Integer, primary_key=True)
    account_id = db.Column(db.Integer, db.ForeignKey('accounts.account_id'), nullable=False, index=True)
    kpi_code = db.Column(db.String(50), nullable=False, index=True)
    value = db.Column(db.Numeric(10, 2), nullable=False)
    target = db.Column(db.Numeric(10, 2))
    pillar = db.Column(db.String(10), index=True)
    weight = db.Column(db.Numeric(5, 4))
    status = db.Column(db.String(20))
    measured_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        db.UniqueConstraint('account_id', 'kpi_code', 'measured_at', name='unique_dc2s_kpi'),
        db.Index('idx_dc2s_account_code', 'account_id', 'kpi_code'),
    )
    
    def to_dict(self):
        return {
            'kpi_id': self.kpi_id,
            'account_id': self.account_id,
            'kpi_code': self.kpi_code,
            'value': float(self.value),
            'target': float(self.target) if self.target else None,
            'pillar': self.pillar,
            'weight': float(self.weight) if self.weight else None,
            'status': self.status,
            'measured_at': self.measured_at.isoformat() if self.measured_at else None
        }


class QualitativeSignal(db.Model):
    """Qualitative Signals - Customer engagement signals (emails, meetings, tickets, etc.)"""
    __tablename__ = 'qualitative_signals'
    
    # Match existing table schema exactly
    signal_id = db.Column(db.String(50), primary_key=True)  # VARCHAR(50) in existing table
    account_id = db.Column(db.Integer, db.ForeignKey('accounts.account_id'), nullable=False, index=True)
    signal_date = db.Column(db.Date, nullable=False, index=True)
    signal_type = db.Column(db.String(50), nullable=True, index=True)  # email, meeting, ticket, etc.
    # Use 'content' not 'signal_text' - matches existing table column name
    content = db.Column(db.Text, nullable=True)  # Existing table uses 'content' not 'signal_text'
    sentiment = db.Column(db.String(50), nullable=True, index=True)  # positive, negative, neutral
    # Additional columns that exist in the table
    stakeholder_level = db.Column(db.String(50), nullable=True)
    stakeholder_title = db.Column(db.String(255), nullable=True)
    sentiment_score = db.Column(db.Numeric, nullable=True)
    keywords = db.Column(db.Text, nullable=True)
    is_narrative_signal = db.Column(db.Boolean, nullable=True)
    
    def to_dict(self):
        return {
            'signal_id': self.signal_id,
            'account_id': self.account_id,
            'signal_date': self.signal_date.isoformat() if self.signal_date else None,
            'signal_type': self.signal_type,
            'signal_text': self.content,  # Map content to signal_text for API compatibility
            'content': self.content,
            'sentiment': self.sentiment,
            'stakeholder_level': self.stakeholder_level,
            'stakeholder_title': self.stakeholder_title,
            'sentiment_score': float(self.sentiment_score) if self.sentiment_score else None,
            'keywords': self.keywords,
            'is_narrative_signal': self.is_narrative_signal
        }


# ============================================================
# L1/L2/L3 SCORE TABLES FOR DC2_S
# ============================================================

class KPIScore(db.Model):
    """L1: Individual KPI scores (0-100 normalized scale)"""
    __tablename__ = 'kpi_scores'
    
    score_id = db.Column(db.Integer, primary_key=True)
    account_id = db.Column(db.Integer, db.ForeignKey('accounts.account_id'), nullable=False, index=True)
    measurement_month = db.Column(db.Date, nullable=False, index=True)
    
    # KPI Information
    kpi_code = db.Column(db.String(50), nullable=False, index=True)  # Can be catalog or CUSTOM-*
    kpi_value = db.Column(db.Numeric(10, 2))        # Raw measured value
    kpi_target = db.Column(db.Numeric(10, 2))       # Target value
    kpi_score = db.Column(db.Numeric(5, 2))         # Normalized 0-100 score
    kpi_status = db.Column(db.String(20))           # excellent, good, warning, critical
    
    # Metadata
    calculated_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        db.UniqueConstraint('account_id', 'kpi_code', 'measurement_month', name='unique_kpi_score'),
        db.Index('idx_kpi_score_account_month', 'account_id', 'measurement_month'),
        db.Index('idx_kpi_score_code', 'kpi_code'),
    )
    
    def to_dict(self):
        return {
            'score_id': self.score_id,
            'account_id': self.account_id,
            'kpi_code': self.kpi_code,
            'kpi_value': float(self.kpi_value) if self.kpi_value else None,
            'kpi_target': float(self.kpi_target) if self.kpi_target else None,
            'kpi_score': float(self.kpi_score) if self.kpi_score else None,
            'kpi_status': self.kpi_status,
            'measurement_month': self.measurement_month.isoformat() if self.measurement_month else None
        }


class PillarScore(db.Model):
    """L2: Pillar scores (weighted average of KPI scores)"""
    __tablename__ = 'pillar_scores'
    
    pillar_score_id = db.Column(db.Integer, primary_key=True)
    account_id = db.Column(db.Integer, db.ForeignKey('accounts.account_id'), nullable=False, index=True)
    measurement_month = db.Column(db.Date, nullable=False, index=True)
    
    # Pillar Information
    pillar_code = db.Column(db.String(10), nullable=False, index=True)  # AI, CH, DV, EX, OS
    pillar_score = db.Column(db.Numeric(5, 2))      # 0-100 weighted average
    pillar_status = db.Column(db.String(20))        # excellent, good, warning, critical
    
    # Contributing KPIs (for transparency)
    contributing_kpis = db.Column(db.JSON)  # {"AI-KPI1": 85, "AI-KPI2": 90, "CUSTOM-GPU-1": 88}
    kpi_weights = db.Column(db.JSON)        # {"AI-KPI1": 0.4, "AI-KPI2": 0.35, "CUSTOM-GPU-1": 0.25}
    
    # Metadata
    calculated_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        db.UniqueConstraint('account_id', 'pillar_code', 'measurement_month', name='unique_pillar_score'),
        db.Index('idx_pillar_score_account_month', 'account_id', 'measurement_month'),
        db.Index('idx_pillar_score_pillar', 'pillar_code'),
    )
    
    def to_dict(self):
        return {
            'pillar_score_id': self.pillar_score_id,
            'account_id': self.account_id,
            'pillar_code': self.pillar_code,
            'pillar_score': float(self.pillar_score) if self.pillar_score else None,
            'pillar_status': self.pillar_status,
            'contributing_kpis': self.contributing_kpis,
            'kpi_weights': self.kpi_weights,
            'measurement_month': self.measurement_month.isoformat() if self.measurement_month else None
        }


class HealthScore(db.Model):
    """L3: Overall health score (weighted average of pillar scores)"""
    __tablename__ = 'health_scores'
    
    health_score_id = db.Column(db.Integer, primary_key=True)
    account_id = db.Column(db.Integer, db.ForeignKey('accounts.account_id'), nullable=False, index=True)
    measurement_month = db.Column(db.Date, nullable=False, index=True)
    
    # Health Information
    health_score = db.Column(db.Numeric(5, 2))      # 0-100 weighted average
    health_status = db.Column(db.String(20))        # excellent, good, warning, critical
    trend = db.Column(db.String(20))                # improving, declining, stable
    change_from_last_month = db.Column(db.Numeric(5, 2))
    
    # Contributing Pillars (for transparency)
    contributing_pillars = db.Column(db.JSON)  # {"AI": 85, "CH": 90, "DV": 80, "EX": 88, "OS": 92}
    pillar_weights = db.Column(db.JSON)        # {"AI": 0.25, "CH": 0.20, "DV": 0.15, "EX": 0.20, "OS": 0.20}
    
    # Metadata
    calculated_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        db.UniqueConstraint('account_id', 'measurement_month', name='unique_health_score'),
        db.Index('idx_health_score_account_month', 'account_id', 'measurement_month'),
        db.Index('idx_health_score_status', 'health_status'),
    )
    
    def to_dict(self):
        return {
            'health_score_id': self.health_score_id,
            'account_id': self.account_id,
            'health_score': float(self.health_score) if self.health_score else None,
            'health_status': self.health_status,
            'trend': self.trend,
            'change_from_last_month': float(self.change_from_last_month) if self.change_from_last_month else None,
            'contributing_pillars': self.contributing_pillars,
            'pillar_weights': self.pillar_weights,
            'measurement_month': self.measurement_month.isoformat() if self.measurement_month else None
        }
