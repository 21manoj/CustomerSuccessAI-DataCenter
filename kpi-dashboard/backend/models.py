from extensions import db

class Customer(db.Model):
    __tablename__ = 'customers'
    customer_id = db.Column(db.Integer, primary_key=True)
    customer_name = db.Column(db.String, nullable=False)
    email = db.Column(db.String, unique=True)
    phone = db.Column(db.String)
    domain = db.Column(db.String, unique=True, nullable=True)  # Email domain for multi-tenant identification
    created_at = db.Column(db.DateTime, server_default=db.func.now())
    updated_at = db.Column(db.DateTime, server_default=db.func.now(), onupdate=db.func.now())

class CustomerConfig(db.Model):
    __tablename__ = 'customer_configs'
    config_id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.customer_id'), unique=True)
    kpi_upload_mode = db.Column(db.String, default='corporate')  # 'corporate' or 'account_rollup'
    category_weights = db.Column(db.Text)  # JSON string of category weights
    master_file_name = db.Column(db.String)  # Name of uploaded master file
    # OpenAI API Key (encrypted)
    openai_api_key_encrypted = db.Column(db.Text, nullable=True)  # Encrypted OpenAI API key
    openai_api_key_updated_at = db.Column(db.DateTime, nullable=True)  # When key was last updated
    created_at = db.Column(db.DateTime, server_default=db.func.now())
    updated_at = db.Column(db.DateTime, server_default=db.func.now(), onupdate=db.func.now())

class Account(db.Model):
    __tablename__ = 'accounts'
    account_id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.customer_id'))
    account_name = db.Column(db.String, nullable=False)
    revenue = db.Column(db.Numeric(15, 2), default=0)
    account_status = db.Column(db.String, default='active')  # active, inactive, etc.
    industry = db.Column(db.String)
    region = db.Column(db.String)
    external_account_id = db.Column(db.String)  # External account ID from customer profile
    profile_metadata = db.Column(db.JSON)  # JSON field for customer profile data
    created_at = db.Column(db.DateTime, server_default=db.func.now())
    updated_at = db.Column(db.DateTime, server_default=db.func.now(), onupdate=db.func.now())

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
    created_at = db.Column(db.DateTime, server_default=db.func.now())
    updated_at = db.Column(db.DateTime, server_default=db.func.now(), onupdate=db.func.now())
    
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
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.customer_id'))
    account_id = db.Column(db.Integer, db.ForeignKey('accounts.account_id'))  # Link to account
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id'))
    uploaded_at = db.Column(db.DateTime, server_default=db.func.now())
    version = db.Column(db.Integer, nullable=False)
    original_filename = db.Column(db.String)
    raw_excel = db.Column(db.LargeBinary)  # Store original file
    parsed_json = db.Column(db.JSON)       # Optionally store parsed structure

class KPI(db.Model):
    __tablename__ = 'kpis'
    kpi_id = db.Column(db.Integer, primary_key=True)
    upload_id = db.Column(db.Integer, db.ForeignKey('kpi_uploads.upload_id'))
    account_id = db.Column(db.Integer, db.ForeignKey('accounts.account_id'))  # Direct account link
    product_id = db.Column(db.Integer, db.ForeignKey('products.product_id'), nullable=True)  # Product-level KPI
    aggregation_type = db.Column(db.String(50), nullable=True)  # 'account' or 'product'
    category = db.Column(db.String)  # Tab name
    row_index = db.Column(db.Integer)
    health_score_component = db.Column(db.String)
    weight = db.Column(db.String)
    data = db.Column(db.String)
    source_review = db.Column(db.String)
    kpi_parameter = db.Column(db.String)
    impact_level = db.Column(db.String)
    measurement_frequency = db.Column(db.String)
    last_edited_by = db.Column(db.Integer, db.ForeignKey('users.user_id'))
    last_edited_at = db.Column(db.DateTime)

class HealthTrend(db.Model):
    __tablename__ = 'health_trends'
    trend_id = db.Column(db.Integer, primary_key=True)
    account_id = db.Column(db.Integer, db.ForeignKey('accounts.account_id'), nullable=False)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.customer_id'), nullable=False)
    month = db.Column(db.Integer, nullable=False)  # 1-12
    year = db.Column(db.Integer, nullable=False)
    overall_health_score = db.Column(db.Numeric(5, 2), nullable=False)  # 0.00-100.00
    product_usage_score = db.Column(db.Numeric(5, 2))
    support_score = db.Column(db.Numeric(5, 2))
    customer_sentiment_score = db.Column(db.Numeric(5, 2))
    business_outcomes_score = db.Column(db.Numeric(5, 2))
    relationship_strength_score = db.Column(db.Numeric(5, 2))
    total_kpis = db.Column(db.Integer, default=0)
    valid_kpis = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, server_default=db.func.now())
    updated_at = db.Column(db.DateTime, server_default=db.func.now(), onupdate=db.func.now())
    
    # Ensure unique combination of account, month, and year
    __table_args__ = (db.UniqueConstraint('account_id', 'month', 'year', name='unique_account_month_year'),)

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
    __table_args__ = (db.UniqueConstraint('kpi_id', 'month', 'year', name='unique_kpi_month_year'),)

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