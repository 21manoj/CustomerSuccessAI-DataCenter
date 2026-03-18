from extensions import db
from datetime import datetime
from sqlalchemy.orm import validates

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

class CustomerApiKey(db.Model):
    __tablename__ = 'customer_api_keys'
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.customer_id'), nullable=False)
    created_by = db.Column(db.Integer, nullable=True)
    key_prefix = db.Column(db.String(20), nullable=False, index=True)
    key_hash = db.Column(db.String(64), nullable=False)
    name = db.Column(db.String(255), nullable=False)
    scopes = db.Column(db.JSON, default=['read'])
    is_active = db.Column(db.Boolean, default=True)
    expires_at = db.Column(db.DateTime, nullable=True)
    last_used_at = db.Column(db.DateTime, nullable=True)
    last_used_ip = db.Column(db.String(45), nullable=True)
    created_at = db.Column(db.DateTime, server_default=db.func.now())
    allowed_account_ids = db.Column(db.JSON, nullable=True)
    partner_tier = db.Column(db.String(50), nullable=True)

    def has_account_access(self, account_id: int) -> bool:
        if self.allowed_account_ids is None:
            return True
        return account_id in self.allowed_account_ids

    def to_dict(self):
        return {
            'id': self.id,
            'customer_id': self.customer_id,
            'key_prefix': self.key_prefix,
            'name': self.name,
            'scopes': self.scopes,
            'is_active': self.is_active,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'last_used_at': self.last_used_at.isoformat() if self.last_used_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'allowed_account_ids': self.allowed_account_ids,
            'partner_tier': self.partner_tier,
        }


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
    dc2s_pillar_weights = db.Column(db.JSON, nullable=True)     # {"P1": 0.15, "P2": 0.20, ...}
    dc2s_enabled_kpis = db.Column(db.JSON, nullable=True)       # ["P3-KPI1", "CUSTOM-GPU-1", ...]
    dc2s_kpi_overrides = db.Column(db.JSON, nullable=True)      # {"P3-KPI1": {"target": 90}, ...}
    dc2s_kpi_weights = db.Column(db.JSON, nullable=True)        # {"P3": {"P3-KPI1": 0.4, ...}, ...}
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
    # Note: Lifecycle fields (journey_phase, renewal_date, contract_*) are DC/datacenter-only.
    # SaaS uses this schema as-is. DC vertical may store journey_phase in profile_metadata or use a DC-specific model.

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
    # RBAC fields for contractor/tester access management
    allowed_account_ids = db.Column(db.JSON, nullable=True)    # NULL = all accounts; [1,2,3] = restricted (within customer)
    allowed_customer_ids = db.Column(db.JSON, nullable=True)   # NULL = own customer only; [9,12] = Test Runner multi-customer access
    expires_at = db.Column(db.DateTime, nullable=True)         # NULL = never expires; set for contractors/testers
    is_contractor = db.Column(db.Boolean, default=False)       # Flag for contractor vs regular user
    # Ensure username is unique within each customer domain
    # Email must be unique globally
    __table_args__ = (
        db.UniqueConstraint('customer_id', 'user_name', name='unique_customer_username'),
        db.UniqueConstraint('email', name='unique_user_email'),
    )

    def has_account_access(self, account_id: int) -> bool:
        """Check if user can access a specific account.
        NULL allowed_account_ids = unrestricted (all accounts).
        """
        if self.allowed_account_ids is None:
            return True
        return int(account_id) in self.allowed_account_ids

    def has_customer_access(self, customer_id: int) -> bool:
        """Check if user can access a specific customer (Test Runner testers).
        NULL allowed_customer_ids = unrestricted.
        """
        if self.allowed_customer_ids is None:
            return True
        return int(customer_id) in self.allowed_customer_ids

    @property
    def is_expired(self) -> bool:
        """Check if user access has expired (contractors/testers)."""
        if self.expires_at is None:
            return False
        from datetime import datetime
        return datetime.utcnow() > self.expires_at

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
    
    # Valid aggregation types
    VALID_AGGREGATION_TYPES = {'weighted_avg', 'max', 'min', 'avg', 'sum', None}

    # Composite indexes for common query patterns
    __table_args__ = (
        db.Index('idx_kpi_account_category', 'account_id', 'category'),
        db.Index('idx_kpi_account_parameter', 'account_id', 'kpi_parameter'),
        db.Index('idx_kpi_account_aggregation', 'account_id', 'aggregation_type'),
        db.Index('idx_kpi_upload_account', 'upload_id', 'account_id'),
    )

    @validates('aggregation_type')
    def validate_aggregation_type(self, key, value):
        if value is not None and value not in self.VALID_AGGREGATION_TYPES:
            raise ValueError(
                f"Invalid aggregation_type '{value}'. "
                f"Valid types: {sorted(t for t in self.VALID_AGGREGATION_TYPES if t)}"
            )
        if value is not None and self.product_id is not None:
            raise ValueError(
                "product_id and aggregation_type cannot both be set. "
                "Product-level KPIs must have aggregation_type=NULL."
            )
        return value

    @validates('product_id')
    def validate_product_id(self, key, value):
        if value is not None and self.aggregation_type is not None:
            raise ValueError(
                "product_id and aggregation_type cannot both be set. "
                "Product-level KPIs must have aggregation_type=NULL."
            )
        return value

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

    # Phase 1 extensions — Action Interface
    playbook_id = db.Column(db.String(50), nullable=True)            # 'PB-01', 'PB-DC-01', 'SaaS-PB-01', …
    trigger_conditions = db.Column(db.JSON, nullable=True)           # Structured rules: [{kpi, operator, threshold}, …]
    execution_mode = db.Column(db.String(20), nullable=True)         # 'mcp_direct', 'workflow'
    requires_llm_validation = db.Column(db.Boolean, default=True)

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

    # Phase 1 extensions — Action Interface
    execution_mode = db.Column(db.String(20), nullable=True)     # 'mcp_direct', 'workflow'
    trigger_context = db.Column(db.JSON, nullable=True)          # KPIs that triggered it
    outcome = db.Column(db.String(50), nullable=True)            # 'resolved', 'escalated', 'timeout', 'manual_close'
    outcome_notes = db.Column(db.Text, nullable=True)
    llm_validation_result = db.Column(db.JSON, nullable=True)    # Signal Analyst output that approved this execution

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

# ============================================================
# CONTEXT GRAPH TABLES
# ============================================================
# Feature flag: 'context_graph' in FeatureToggle table
# Three-tier storage: T1 permanent, T2 decaying (TTL), T3 ephemeral
# Every node/edge carries revenue_impact for CRO/CFO lens.
# Guard: from feature_toggles import is_context_graph_enabled

class ContextNode(db.Model):
    """
    Graph node representing an entity in the account context graph.

    Node types: ACCOUNT, SIGNAL, STAKEHOLDER, DECISION, OUTCOME, EXTERNAL_CONTEXT
    Every node belongs to exactly one account (tenant isolation).
    Revenue impact fields support the CRO/CFO outcome-focused lens.
    """
    __tablename__ = 'context_nodes'

    node_id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.customer_id'), nullable=False, index=True)
    account_id = db.Column(db.Integer, db.ForeignKey('accounts.account_id'), nullable=False, index=True)

    # Node classification
    node_type = db.Column(db.String(30), nullable=False, index=True)
    # SIGNAL, STAKEHOLDER, DECISION, OUTCOME, EXTERNAL_CONTEXT
    node_subtype = db.Column(db.String(50), index=True)
    # e.g. SIGNAL→kpi_change|ticket|nps; DECISION→playbook|escalation|exec_engagement

    # Storage tier: 1=permanent, 2=decaying, 3=ephemeral
    tier = db.Column(db.SmallInteger, nullable=False, default=2)

    # Core content
    title = db.Column(db.String(500))
    properties = db.Column(db.JSON, nullable=False, default=dict)
    # Flexible payload — schema varies by node_type

    # Revenue impact (CRO/CFO lens — every node should answer "so what in $?")
    revenue_impact = db.Column(db.Numeric(15, 2))       # ARR at risk or protected
    revenue_impact_type = db.Column(db.String(30))       # at_risk, protected, expansion, lost
    confidence = db.Column(db.Numeric(3, 2), default=1.0) # 0.00-1.00

    # Source tracking
    source_platform = db.Column(db.String(50))           # sfdc, hubspot, intercom, cs_pulse, csv_import
    source_event_id = db.Column(db.String(200))          # External ID for dedup
    source_ref = db.Column(db.String(200))               # e.g. SFDC Opportunity ID

    # Temporal
    occurred_at = db.Column(db.DateTime, nullable=False, index=True)
    expires_at = db.Column(db.DateTime)                   # NULL = never expires (Tier 1)
    weight_decay = db.Column(db.Numeric(3, 2), default=1.0) # Current weight after decay

    # Lifecycle
    created_at = db.Column(db.DateTime, server_default=db.func.now())
    updated_at = db.Column(db.DateTime, server_default=db.func.now(), onupdate=db.func.now())

    __table_args__ = (
        db.Index('idx_ctx_node_account_type', 'account_id', 'node_type'),
        db.Index('idx_ctx_node_customer', 'customer_id', 'node_type'),
        db.Index('idx_ctx_node_occurred', 'account_id', 'occurred_at'),
        db.Index('idx_ctx_node_tier_expires', 'tier', 'expires_at'),
        db.Index('idx_ctx_node_source', 'source_platform', 'source_event_id'),
    )

    def to_dict(self):
        return {
            'node_id': self.node_id,
            'customer_id': self.customer_id,
            'account_id': self.account_id,
            'node_type': self.node_type,
            'node_subtype': self.node_subtype,
            'tier': self.tier,
            'title': self.title,
            'properties': self.properties,
            'revenue_impact': float(self.revenue_impact) if self.revenue_impact else None,
            'revenue_impact_type': self.revenue_impact_type,
            'confidence': float(self.confidence) if self.confidence else None,
            'source_platform': self.source_platform,
            'source_event_id': self.source_event_id,
            'occurred_at': self.occurred_at.isoformat() if self.occurred_at else None,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
        }


class ContextEdge(db.Model):
    """
    Typed, weighted, temporal edge between two context graph nodes.

    Edge types: CAUSED_BY, INDICATES, LED_TO, CORRELATES_WITH,
                INVOLVES, BELONGS_TO, BENCHMARKED_BY, SOURCED_FROM, SUPERSEDES

    Edges carry revenue context: "this signal CAUSED_BY that failure
    and the combined chain puts $2.4M ARR at risk."
    """
    __tablename__ = 'context_edges'

    edge_id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.customer_id'), nullable=True, index=True)
    from_node_id = db.Column(db.Integer, db.ForeignKey('context_nodes.node_id', ondelete='CASCADE'), nullable=False, index=True)
    to_node_id = db.Column(db.Integer, db.ForeignKey('context_nodes.node_id', ondelete='CASCADE'), nullable=False, index=True)

    # Edge classification
    edge_type = db.Column(db.String(30), nullable=False, index=True)
    lag_days = db.Column(db.Integer)
    # CAUSED_BY, INDICATES, LED_TO, CORRELATES_WITH, INVOLVES,
    # BELONGS_TO, BENCHMARKED_BY, SOURCED_FROM, SUPERSEDES

    # Weight and confidence
    weight = db.Column(db.Numeric(3, 2), nullable=False, default=1.0)  # 0.00-1.00
    confidence = db.Column(db.Numeric(3, 2), default=1.0)

    # Revenue context on the edge itself
    revenue_impact = db.Column(db.Numeric(15, 2))        # $ impact of this causal link
    revenue_impact_type = db.Column(db.String(30))

    # Edge payload
    properties = db.Column(db.JSON, default=dict)
    # e.g. {"lag_days": 14, "evidence": "ticket volume spike preceded churn signal"}

    # Source tracking
    source_platform = db.Column(db.String(50))
    created_by = db.Column(db.String(50))                 # "cs_pulse_engine", "csv_import", "mcp_sfdc"

    # Temporal
    occurred_at = db.Column(db.DateTime)
    expires_at = db.Column(db.DateTime)

    # Lifecycle
    created_at = db.Column(db.DateTime, server_default=db.func.now())

    # Relationships
    from_node = db.relationship('ContextNode', foreign_keys=[from_node_id], backref='outgoing_edges')
    to_node = db.relationship('ContextNode', foreign_keys=[to_node_id], backref='incoming_edges')

    __table_args__ = (
        db.Index('idx_ctx_edge_from', 'from_node_id', 'edge_type'),
        db.Index('idx_ctx_edge_to', 'to_node_id', 'edge_type'),
        db.Index('idx_ctx_edge_type', 'edge_type'),
        db.Index('idx_ctx_edge_pair', 'from_node_id', 'to_node_id', 'edge_type'),
    )

    def to_dict(self):
        return {
            'edge_id': self.edge_id,
            'from_node_id': self.from_node_id,
            'to_node_id': self.to_node_id,
            'edge_type': self.edge_type,
            'weight': float(self.weight) if self.weight else None,
            'confidence': float(self.confidence) if self.confidence else None,
            'revenue_impact': float(self.revenue_impact) if self.revenue_impact else None,
            'revenue_impact_type': self.revenue_impact_type,
            'properties': self.properties,
            'source_platform': self.source_platform,
            'created_by': self.created_by,
            'occurred_at': self.occurred_at.isoformat() if self.occurred_at else None,
        }


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
    pillar_code = db.Column(db.String(10), nullable=False, index=True)  # P1, P2, P3, P4, P5
    pillar_score = db.Column(db.Numeric(5, 2))      # 0-100 weighted average
    pillar_status = db.Column(db.String(20))        # excellent, good, warning, critical
    
    # Contributing KPIs (for transparency)
    contributing_kpis = db.Column(db.JSON)  # {"P3-KPI1": 85, "P3-KPI2": 90, "CUSTOM-GPU-1": 88}
    kpi_weights = db.Column(db.JSON)        # {"P3-KPI1": 0.4, "P3-KPI2": 0.35, "CUSTOM-GPU-1": 0.25}
    
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
    contributing_pillars = db.Column(db.JSON)  # {"P1": 80, "P2": 92, "P3": 85, "P4": 90, "P5": 88}
    pillar_weights = db.Column(db.JSON)        # {"P1": 0.15, "P2": 0.20, "P3": 0.25, "P4": 0.15, "P5": 0.25}
    
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


# ============================================================
# REVENUE INTELLIGENCE — POWER OF 1 MODELS
# ============================================================
# Feature flag: 'revenue_intelligence' in FeatureToggle table
# Designed for MCP agent access — each model has to_dict() for serialization.
# Agentic architecture: These models are the data layer that MCP tools
# (Signal Analyst, Playbook Orchestrator agents) read/write via tool calls.

class ActionEconomics(db.Model):
    """
    Tracks the cost and dollar value of every action (playbook execution,
    work package, CSM intervention) taken on an account.

    Cost side: Hours by role x hourly rate (from resource_capacity_model).
    Value side: KPI deltas converted to dollars via Power of 1 table.

    MCP tool: 'record_action_economics' / 'query_action_economics'
    """
    __tablename__ = 'action_economics'

    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.customer_id'), nullable=False, index=True)
    account_id = db.Column(db.Integer, db.ForeignKey('accounts.account_id'), nullable=False, index=True)
    execution_id = db.Column(db.String(36), db.ForeignKey('playbook_executions.execution_id'), nullable=True, index=True)

    # What action was taken
    action_type = db.Column(db.String(50), nullable=False, index=True)
    action_id = db.Column(db.String(100), nullable=False)
    action_name = db.Column(db.String(255))

    # Cost side — hours by role
    csm_hours = db.Column(db.Numeric(8, 2), default=0)
    cs_ops_hours = db.Column(db.Numeric(8, 2), default=0)
    product_hours = db.Column(db.Numeric(8, 2), default=0)
    platform_hours = db.Column(db.Numeric(8, 2), default=0)
    leadership_hours = db.Column(db.Numeric(8, 2), default=0)

    # Cost side — dollar amounts
    cs_initiative_cost = db.Column(db.Numeric(12, 2), default=0)
    platform_cost = db.Column(db.Numeric(12, 2), default=0)
    total_action_cost = db.Column(db.Numeric(12, 2), default=0)

    # Value side — KPI changes
    kpi_before = db.Column(db.JSON)
    kpi_after = db.Column(db.JSON)
    kpi_deltas = db.Column(db.JSON)

    # Value side — dollar impact (converted via Power of 1)
    power_of_1_metric = db.Column(db.String(50))
    dollar_impact_annual = db.Column(db.Numeric(15, 2))
    dollar_impact_monthly = db.Column(db.Numeric(15, 2))
    revenue_increase = db.Column(db.Numeric(15, 2), default=0)
    cost_savings = db.Column(db.Numeric(15, 2), default=0)

    # Derived economics
    roi = db.Column(db.Numeric(10, 4))
    payback_days = db.Column(db.Integer)
    category = db.Column(db.String(50))

    # Lifecycle context
    journey_phase = db.Column(db.String(50))
    improvement_pct = db.Column(db.Numeric(5, 2))

    # Timestamps
    started_at = db.Column(db.DateTime)
    completed_at = db.Column(db.DateTime)
    measured_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_at = db.Column(db.DateTime, server_default=db.func.now())
    updated_at = db.Column(db.DateTime, server_default=db.func.now(), onupdate=db.func.now())

    __table_args__ = (
        db.Index('idx_action_econ_customer_account', 'customer_id', 'account_id'),
        db.Index('idx_action_econ_type', 'action_type', 'action_id'),
        db.Index('idx_action_econ_measured', 'measured_at'),
    )

    def to_dict(self):
        return {
            'id': self.id,
            'customer_id': self.customer_id,
            'account_id': self.account_id,
            'execution_id': self.execution_id,
            'action_type': self.action_type,
            'action_id': self.action_id,
            'action_name': self.action_name,
            'cost': {
                'csm_hours': float(self.csm_hours or 0),
                'cs_ops_hours': float(self.cs_ops_hours or 0),
                'product_hours': float(self.product_hours or 0),
                'platform_hours': float(self.platform_hours or 0),
                'leadership_hours': float(self.leadership_hours or 0),
                'cs_initiative_cost': float(self.cs_initiative_cost or 0),
                'platform_cost': float(self.platform_cost or 0),
                'total_action_cost': float(self.total_action_cost or 0),
            },
            'value': {
                'kpi_before': self.kpi_before,
                'kpi_after': self.kpi_after,
                'kpi_deltas': self.kpi_deltas,
                'power_of_1_metric': self.power_of_1_metric,
                'dollar_impact_annual': float(self.dollar_impact_annual or 0),
                'dollar_impact_monthly': float(self.dollar_impact_monthly or 0),
                'revenue_increase': float(self.revenue_increase or 0),
                'cost_savings': float(self.cost_savings or 0),
            },
            'economics': {
                'roi': float(self.roi) if self.roi else None,
                'payback_days': self.payback_days,
                'category': self.category,
                'improvement_pct': float(self.improvement_pct) if self.improvement_pct else None,
            },
            'journey_phase': self.journey_phase,
            'measured_at': self.measured_at.isoformat() if self.measured_at else None,
        }


class Portfolio(db.Model):
    """
    PE fund or holding company that owns multiple businesses (customers).
    Top-level entity for multi-vertical PE portfolio management.

    MCP tool: 'query_portfolio' / 'find_synergies'
    """
    __tablename__ = 'portfolios'

    portfolio_id = db.Column(db.Integer, primary_key=True)
    portfolio_name = db.Column(db.String(255), nullable=False)
    portfolio_type = db.Column(db.String(50), default='pe_fund')
    description = db.Column(db.Text)

    total_aum = db.Column(db.Numeric(15, 2))
    investment_thesis = db.Column(db.Text)

    config = db.Column(db.JSON)
    enabled = db.Column(db.Boolean, default=True)

    created_at = db.Column(db.DateTime, server_default=db.func.now())
    updated_at = db.Column(db.DateTime, server_default=db.func.now(), onupdate=db.func.now())

    def to_dict(self):
        return {
            'portfolio_id': self.portfolio_id,
            'portfolio_name': self.portfolio_name,
            'portfolio_type': self.portfolio_type,
            'description': self.description,
            'total_aum': float(self.total_aum) if self.total_aum else None,
            'enabled': self.enabled,
        }


class PortfolioMembership(db.Model):
    """Links customers (portfolio companies) to a portfolio."""
    __tablename__ = 'portfolio_memberships'

    id = db.Column(db.Integer, primary_key=True)
    portfolio_id = db.Column(db.Integer, db.ForeignKey('portfolios.portfolio_id'), nullable=False, index=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.customer_id'), nullable=False, index=True)

    acquisition_date = db.Column(db.DateTime)
    status = db.Column(db.String(20), default='owned')
    vertical = db.Column(db.String(50))
    role = db.Column(db.String(20), default='platform')

    synergies_identified = db.Column(db.Integer, default=0)
    synergies_realized = db.Column(db.Integer, default=0)
    synergy_value = db.Column(db.Numeric(15, 2), default=0)

    created_at = db.Column(db.DateTime, server_default=db.func.now())
    updated_at = db.Column(db.DateTime, server_default=db.func.now(), onupdate=db.func.now())

    __table_args__ = (
        db.UniqueConstraint('portfolio_id', 'customer_id', name='unique_portfolio_customer'),
    )

    def to_dict(self):
        return {
            'id': self.id,
            'portfolio_id': self.portfolio_id,
            'customer_id': self.customer_id,
            'acquisition_date': self.acquisition_date.isoformat() if self.acquisition_date else None,
            'status': self.status,
            'vertical': self.vertical,
            'role': self.role,
            'synergies_identified': self.synergies_identified,
            'synergies_realized': self.synergies_realized,
            'synergy_value': float(self.synergy_value or 0),
        }


class WeightCalibrationHistory(db.Model):
    """
    Versioned weight calibration records. Never overwrites — always appends.
    Guardrails: No single weight shifts more than +/- 15% per cycle.
    Minimum sample size: 10 playbook outcomes before recalibration triggers.

    MCP tool: 'get_calibration_history' / 'trigger_recalibration'
    """
    __tablename__ = 'weight_calibration_history'

    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.customer_id'), nullable=False, index=True)

    calibration_type = db.Column(db.String(50), nullable=False)
    vertical = db.Column(db.String(50))

    previous_weights = db.Column(db.JSON, nullable=False)
    new_weights = db.Column(db.JSON, nullable=False)
    weight_deltas = db.Column(db.JSON)

    sample_size = db.Column(db.Integer)
    prediction_error_before = db.Column(db.Numeric(8, 4))
    prediction_error_after = db.Column(db.Numeric(8, 4))
    error_reduction_pct = db.Column(db.Numeric(5, 2))

    triggered_by = db.Column(db.String(50))
    approved = db.Column(db.Boolean, default=True)
    notes = db.Column(db.Text)

    calibrated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    created_at = db.Column(db.DateTime, server_default=db.func.now())

    __table_args__ = (
        db.Index('idx_calibration_customer_type', 'customer_id', 'calibration_type'),
        db.Index('idx_calibration_date', 'calibrated_at'),
    )

    def to_dict(self):
        return {
            'id': self.id,
            'customer_id': self.customer_id,
            'calibration_type': self.calibration_type,
            'vertical': self.vertical,
            'previous_weights': self.previous_weights,
            'new_weights': self.new_weights,
            'weight_deltas': self.weight_deltas,
            'sample_size': self.sample_size,
            'error_reduction_pct': float(self.error_reduction_pct) if self.error_reduction_pct else None,
            'triggered_by': self.triggered_by,
            'approved': self.approved,
            'calibrated_at': self.calibrated_at.isoformat() if self.calibrated_at else None,
        }


# ============================================================
# AUTO-UUID GENERATION — SQLAlchemy before_flush event
# ============================================================
# Ensures every Customer, Account, and User gets a UUID on insert,
# regardless of which code path creates the record. This eliminates
# the need to call ensure_uuid() manually in every creation point.

from sqlalchemy import event as sa_event


def _auto_generate_uuids(session, flush_context, instances):
    """
    SQLAlchemy before_flush listener that auto-generates UUIDs
    for Customer, Account, and User models if not already set.
    """
    try:
        from id_generator import generate_id
    except ImportError:
        return  # id_generator not available in test environments

    for obj in session.new:
        # Skip objects that don't have a uuid column
        if not hasattr(obj, 'uuid'):
            continue

        # Only process our core models
        class_name = obj.__class__.__name__
        if class_name not in ('Customer', 'Account', 'User'):
            continue

        # Skip if UUID already assigned
        if obj.uuid:
            continue

        # Determine vertical prefix
        vertical = getattr(obj, 'vertical', None) or 'dc'

        # Map class to entity type
        entity_map = {
            'Customer': 'customer',
            'Account': 'account',
            'User': 'user',
        }
        entity_type = entity_map.get(class_name, class_name.lower())

        # Generate and assign UUID
        obj.uuid = generate_id(vertical, entity_type)

        # For Account/User: propagate parent customer's UUID
        if class_name in ('Account', 'User') and hasattr(obj, 'customer_uuid'):
            if not obj.customer_uuid and obj.customer_id:
                # Look up parent customer's UUID
                parent = session.get(Customer, obj.customer_id)
                if parent and parent.uuid:
                    obj.customer_uuid = parent.uuid


sa_event.listen(db.session, 'before_flush', _auto_generate_uuids)


# ============================================================
# WIZARD MODELS — Run tracking, learnings, file references
# ============================================================

class WizardRun(db.Model):
    """Tracks each wizard run (data generation + training session)"""
    __tablename__ = 'wizard_runs'

    id = db.Column(db.Integer, primary_key=True)
    run_id = db.Column(db.String(50), unique=True, nullable=False, index=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.customer_id'), index=True)

    job_id = db.Column(db.String(100), index=True)
    status = db.Column(db.String(20), nullable=False, default='queued', index=True)
    current_phase = db.Column(db.String(50))
    progress = db.Column(db.JSON)

    config = db.Column(db.JSON, nullable=False)
    results = db.Column(db.JSON)
    error_message = db.Column(db.Text)

    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, index=True)
    started_at = db.Column(db.DateTime)
    completed_at = db.Column(db.DateTime)
    created_by = db.Column(db.String(100))

    learnings = db.relationship('WizardLearning', backref='source_run', lazy='dynamic')
    files = db.relationship('WizardFile', backref='run', lazy='dynamic')

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if not self.run_id:
            import uuid as _uuid
            self.run_id = f"wizard_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{_uuid.uuid4().hex[:8]}"

    def to_dict(self):
        return {
            'run_id': self.run_id,
            'customer_id': self.customer_id,
            'job_id': self.job_id,
            'status': self.status,
            'current_phase': self.current_phase,
            'progress': self.progress,
            'config': self.config,
            'results': self.results,
            'error_message': self.error_message,
            'created_at': self.created_at.isoformat(),
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'created_by': self.created_by,
        }


class WizardLearning(db.Model):
    """Stores extracted learnings from wizard runs (Wizard B pattern analysis, etc.)"""
    __tablename__ = 'wizard_learnings'

    id = db.Column(db.Integer, primary_key=True)
    version = db.Column(db.String(20), nullable=False, index=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.customer_id'), nullable=True, index=True)

    source_runs = db.Column(db.JSON)
    run_id = db.Column(db.String(50), db.ForeignKey('wizard_runs.run_id'))

    learnings = db.Column(db.JSON, nullable=False)
    industry_benchmarks = db.Column(db.JSON)
    validation_rules = db.Column(db.JSON)
    edge_cases = db.Column(db.JSON)
    analysis_report = db.Column(db.Text)

    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, index=True)
    is_active = db.Column(db.Boolean, default=True, index=True)

    total_accounts_tested = db.Column(db.Integer)
    avg_accuracy = db.Column(db.Float)

    __table_args__ = (
        db.UniqueConstraint('customer_id', 'version', name='uq_wizard_learning_customer_version'),
    )

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if not self.version:
            # Auto-increment version scoped to customer
            query = WizardLearning.query
            if self.customer_id is not None:
                query = query.filter_by(customer_id=self.customer_id)
            latest = query.order_by(WizardLearning.created_at.desc()).first()
            if latest and latest.version:
                try:
                    num = float(latest.version.replace('v', ''))
                    self.version = f"v{num + 0.1:.1f}"
                except (ValueError, TypeError):
                    self.version = "v1.0"
            else:
                self.version = "v1.0"

    def activate(self):
        """Make this the active learning for this customer (deactivates others)."""
        WizardLearning.query.filter_by(
            customer_id=self.customer_id
        ).update({'is_active': False})
        self.is_active = True
        db.session.flush()

    @classmethod
    def get_active(cls, customer_id=None):
        """Get the currently active learning, optionally filtered by customer."""
        query = cls.query.filter_by(is_active=True)
        if customer_id is not None:
            query = query.filter_by(customer_id=customer_id)
        return query.first()

    def to_dict(self):
        return {
            'version': self.version,
            'customer_id': self.customer_id,
            'source_runs': self.source_runs,
            'learnings': self.learnings,
            'industry_benchmarks': self.industry_benchmarks,
            'validation_rules': self.validation_rules,
            'edge_cases': self.edge_cases,
            'analysis_report': self.analysis_report,
            'created_at': self.created_at.isoformat(),
            'is_active': self.is_active,
            'total_accounts_tested': self.total_accounts_tested,
            'avg_accuracy': self.avg_accuracy,
        }


class WizardFile(db.Model):
    """Tracks files generated by wizard runs"""
    __tablename__ = 'wizard_files'

    id = db.Column(db.Integer, primary_key=True)
    run_id = db.Column(db.String(50), db.ForeignKey('wizard_runs.run_id'), nullable=False, index=True)

    filename = db.Column(db.String(255), nullable=False)
    filepath = db.Column(db.String(500), nullable=False)
    file_type = db.Column(db.String(50))
    file_size = db.Column(db.Integer)

    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    description = db.Column(db.Text)

    def to_dict(self):
        return {
            'filename': self.filename,
            'filepath': self.filepath,
            'file_type': self.file_type,
            'file_size': self.file_size,
            'created_at': self.created_at.isoformat(),
            'description': self.description,
        }


class ROISnapshot(db.Model):
    """Persisted ROI calculation snapshots for audit trail and trending."""
    __tablename__ = 'roi_snapshots'

    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.customer_id'), nullable=False, index=True)
    snapshot_date = db.Column(db.Date, nullable=False, default=db.func.current_date())
    improvement_pct = db.Column(db.Float, nullable=False)

    # Historical ROI (realized)
    historical_roi_pct = db.Column(db.Float)
    historical_impact = db.Column(db.Float)
    historical_investment = db.Column(db.Float)

    # Forward ROI (projected)
    forward_roi_pct = db.Column(db.Float)
    forward_impact = db.Column(db.Float)
    forward_investment = db.Column(db.Float)

    # Combined
    combined_roi_pct = db.Column(db.Float)
    total_arr = db.Column(db.Float)

    # Per-metric detail (JSON blob for drill-down)
    metric_details = db.Column(db.JSON)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
        db.Index('ix_roi_snap_cust_date', 'customer_id', 'snapshot_date'),
    )


class JourneyData(db.Model):
    """
    Stores journey timeline data per account (replaces filesystem JSON files).
    Used by Journey Visualizer UI. Previously stored at:
    verticals/customer{X}-dc2_s/journey/wizard_a/outputs/account_{id}_journey.json
    """
    __tablename__ = 'journey_data'

    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, nullable=False, index=True)
    account_id = db.Column(db.Integer, nullable=False, index=True)
    journey_json = db.Column(db.JSON, nullable=False)
    total_weeks = db.Column(db.Integer)
    journey_pattern = db.Column(db.String(50))
    generator_version = db.Column(db.String(20), default='1.0')
    generated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint('customer_id', 'account_id', name='uq_journey_data_customer_account'),
    )
