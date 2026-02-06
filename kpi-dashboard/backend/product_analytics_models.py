#!/usr/bin/env python3
"""
Product Analytics Database Models
Master product catalog, product trends, and aggregate product trends
"""

from extensions import db
from datetime import datetime

class ProductCatalog(db.Model):
    """Master product catalog - normalized product names across all accounts"""
    __tablename__ = 'product_catalog'
    
    product_id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.customer_id'), nullable=False, index=True)
    product_name = db.Column(db.String(255), nullable=False)  # Normalized/canonical name
    product_sku = db.Column(db.String(100))
    product_type = db.Column(db.String(100))
    status = db.Column(db.String(50), default='active')
    created_at = db.Column(db.DateTime, server_default=db.func.now())
    updated_at = db.Column(db.DateTime, server_default=db.func.now(), onupdate=db.func.now())
    
    __table_args__ = (
        db.UniqueConstraint('customer_id', 'product_name', name='unique_customer_product_name'),
        db.Index('idx_product_catalog_customer', 'customer_id'),
        db.Index('idx_product_catalog_name', 'product_name'),
    )
    
    def __repr__(self):
        return f'<ProductCatalog {self.product_id}: {self.product_name} (Customer {self.customer_id})>'


class ProductTrend(db.Model):
    """Product health trends per account-product combination (monthly tracking)"""
    __tablename__ = 'product_trends'
    
    trend_id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('product_catalog.product_id'), nullable=False, index=True)
    account_id = db.Column(db.Integer, db.ForeignKey('accounts.account_id'), nullable=False, index=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.customer_id'), nullable=False, index=True)
    month = db.Column(db.Integer, nullable=False, index=True)  # 1-12
    year = db.Column(db.Integer, nullable=False, index=True)
    
    # Health Scores (0.00-100.00)
    overall_health_score = db.Column(db.Numeric(5, 2), nullable=False)
    product_usage_score = db.Column(db.Numeric(5, 2))
    support_score = db.Column(db.Numeric(5, 2))
    customer_sentiment_score = db.Column(db.Numeric(5, 2))
    business_outcomes_score = db.Column(db.Numeric(5, 2))
    relationship_strength_score = db.Column(db.Numeric(5, 2))
    
    # KPI Statistics
    total_kpis = db.Column(db.Integer, default=0)
    valid_kpis = db.Column(db.Integer, default=0)
    product_level_kpis = db.Column(db.Integer, default=0)  # KPIs with product_id set
    account_level_kpis = db.Column(db.Integer, default=0)  # Account-level KPIs used for this product
    
    # Revenue (from account at time of calculation)
    revenue = db.Column(db.Numeric(15, 2))
    
    created_at = db.Column(db.DateTime, server_default=db.func.now(), index=True)
    updated_at = db.Column(db.DateTime, server_default=db.func.now(), onupdate=db.func.now())
    
    __table_args__ = (
        db.UniqueConstraint('product_id', 'account_id', 'month', 'year', name='unique_product_account_month_year'),
        db.Index('idx_product_trend_product_date', 'product_id', 'year', 'month'),
        db.Index('idx_product_trend_account_date', 'account_id', 'year', 'month'),
        db.Index('idx_product_trend_customer_date', 'customer_id', 'year', 'month'),
        db.Index('idx_product_trend_product_account', 'product_id', 'account_id'),
    )
    
    def __repr__(self):
        return f'<ProductTrend Product {self.product_id} @ Account {self.account_id} ({self.year}-{self.month:02d}): {self.overall_health_score}>'


class ProductAggregateTrend(db.Model):
    """Aggregate product health trends across all accounts using the product"""
    __tablename__ = 'product_aggregate_trends'
    
    aggregate_trend_id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('product_catalog.product_id'), nullable=False, index=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.customer_id'), nullable=False, index=True)
    month = db.Column(db.Integer, nullable=False, index=True)  # 1-12
    year = db.Column(db.Integer, nullable=False, index=True)
    
    # Aggregate Health Scores (weighted average across accounts)
    overall_health_score = db.Column(db.Numeric(5, 2), nullable=False)
    product_usage_score = db.Column(db.Numeric(5, 2))
    support_score = db.Column(db.Numeric(5, 2))
    customer_sentiment_score = db.Column(db.Numeric(5, 2))
    business_outcomes_score = db.Column(db.Numeric(5, 2))
    relationship_strength_score = db.Column(db.Numeric(5, 2))
    
    # Aggregate Statistics
    total_accounts = db.Column(db.Integer, default=0)  # Number of accounts using this product
    total_revenue = db.Column(db.Numeric(15, 2))  # Sum of revenue from all accounts
    average_revenue_per_account = db.Column(db.Numeric(15, 2))
    total_kpis = db.Column(db.Integer, default=0)
    valid_kpis = db.Column(db.Integer, default=0)
    
    created_at = db.Column(db.DateTime, server_default=db.func.now(), index=True)
    updated_at = db.Column(db.DateTime, server_default=db.func.now(), onupdate=db.func.now())
    
    __table_args__ = (
        db.UniqueConstraint('product_id', 'month', 'year', name='unique_product_aggregate_month_year'),
        db.Index('idx_product_aggregate_product_date', 'product_id', 'year', 'month'),
        db.Index('idx_product_aggregate_customer_date', 'customer_id', 'year', 'month'),
    )
    
    def __repr__(self):
        return f'<ProductAggregateTrend Product {self.product_id} ({self.year}-{self.month:02d}): {self.overall_health_score} ({self.total_accounts} accounts)>'
