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