from extensions import db

class Customer(db.Model):
    __tablename__ = 'customers'
    customer_id = db.Column(db.Integer, primary_key=True)
    customer_name = db.Column(db.String, nullable=False)
    email = db.Column(db.String, unique=True)
    phone = db.Column(db.String)

class CustomerConfig(db.Model):
    __tablename__ = 'customer_configs'
    config_id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.customer_id'), unique=True)
    kpi_upload_mode = db.Column(db.String, default='corporate')  # 'corporate' or 'account_rollup'
    category_weights = db.Column(db.Text)  # JSON string of category weights
    master_file_name = db.Column(db.String)  # Name of uploaded master file
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
    created_at = db.Column(db.DateTime, server_default=db.func.now())
    updated_at = db.Column(db.DateTime, server_default=db.func.now(), onupdate=db.func.now())

class User(db.Model):
    __tablename__ = 'users'
    user_id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.customer_id'))
    user_name = db.Column(db.String, nullable=False)
    email = db.Column(db.String)
    password_hash = db.Column(db.String(128))

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
    kpi_name = db.Column(db.String, nullable=False, unique=True)
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
    
    # Metadata
    created_at = db.Column(db.DateTime, server_default=db.func.now())
    updated_at = db.Column(db.DateTime, server_default=db.func.now(), onupdate=db.func.now())
    created_by = db.Column(db.Integer, db.ForeignKey('users.user_id'))
    updated_by = db.Column(db.Integer, db.ForeignKey('users.user_id'))

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