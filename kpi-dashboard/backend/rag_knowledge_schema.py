#!/usr/bin/env python3
"""
RAG Knowledge Base Schema and Prerequisites
Defines the comprehensive data schema needed for a robust RAG system
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, Float, JSON, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from extensions import db

Base = declarative_base()

class RAGKnowledgeBase(db.Model):
    """Comprehensive knowledge base for RAG system"""
    __tablename__ = 'rag_knowledge_base'
    
    id = db.Column(db.Integer, primary_key=True)
    knowledge_type = db.Column(db.String(50), nullable=False)  # kpi_analysis, financial_projection, best_practice, etc.
    content = db.Column(Text, nullable=False)
    knowledge_metadata = db.Column(JSON)  # Structured metadata
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.customer_id'), nullable=False)
    account_id = db.Column(db.Integer, db.ForeignKey('accounts.account_id'), nullable=True)
    kpi_id = db.Column(db.Integer, db.ForeignKey('kpis.kpi_id'), nullable=True)
    created_at = db.Column(db.DateTime, server_default=db.func.now())
    updated_at = db.Column(db.DateTime, server_default=db.func.now(), onupdate=db.func.now())
    
    # Indexes for efficient querying
    __table_args__ = (
        db.Index('idx_knowledge_type', 'knowledge_type'),
        db.Index('idx_customer_id', 'customer_id'),
        db.Index('idx_created_at', 'created_at'),
    )

class FinancialProjection(db.Model):
    """Financial projections tied to KPI changes"""
    __tablename__ = 'financial_projections'
    
    id = db.Column(db.Integer, primary_key=True)
    account_id = db.Column(db.Integer, db.ForeignKey('accounts.account_id'), nullable=False)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.customer_id'), nullable=False)
    projection_date = db.Column(db.DateTime, nullable=False)
    months_ahead = db.Column(db.Integer, nullable=False)  # 3, 6, 12 months
    
    # KPI Category Projections
    product_usage_projected = db.Column(db.Float)
    support_projected = db.Column(db.Float)
    customer_sentiment_projected = db.Column(db.Float)
    business_outcomes_projected = db.Column(db.Float)
    relationship_strength_projected = db.Column(db.Float)
    overall_projected = db.Column(db.Float)
    
    # Financial Impact Projections
    revenue_impact = db.Column(db.Float)
    cost_savings = db.Column(db.Float)
    retention_improvement = db.Column(db.Float)
    total_financial_impact = db.Column(db.Float)
    roi_percentage = db.Column(db.Float)
    
    # Confidence and Methodology
    confidence_level = db.Column(db.String(20))  # high, medium, low
    methodology_notes = db.Column(Text)
    
    created_at = db.Column(db.DateTime, server_default=db.func.now())
    updated_at = db.Column(db.DateTime, server_default=db.func.now(), onupdate=db.func.now())

class KPIBestPractices(db.Model):
    """Best practices and recommendations for KPIs"""
    __tablename__ = 'kpi_best_practices'
    
    id = db.Column(db.Integer, primary_key=True)
    kpi_name = db.Column(db.String(200), nullable=False)
    category = db.Column(db.String(100), nullable=False)
    
    # Best Practice Content
    title = db.Column(db.String(300), nullable=False)
    description = db.Column(Text, nullable=False)
    implementation_steps = db.Column(JSON)  # Array of steps
    expected_impact = db.Column(Text)
    
    # Performance Metrics
    typical_improvement_percentage = db.Column(db.Float)
    implementation_timeframe = db.Column(db.String(50))  # weeks, months
    difficulty_level = db.Column(db.String(20))  # low, medium, high
    cost_estimate = db.Column(db.String(100))  # low, medium, high, specific amount
    
    # Industry Context
    industry_applicability = db.Column(JSON)  # Array of industries
    company_size_applicability = db.Column(JSON)  # startup, smb, enterprise
    
    created_at = db.Column(db.DateTime, server_default=db.func.now())
    updated_at = db.Column(db.DateTime, server_default=db.func.now(), onupdate=db.func.now())

class IndustryBenchmarks(db.Model):
    """Industry benchmarks for KPIs"""
    __tablename__ = 'industry_benchmarks'
    
    id = db.Column(db.Integer, primary_key=True)
    kpi_name = db.Column(db.String(200), nullable=False)
    industry = db.Column(db.String(100), nullable=False)
    company_size = db.Column(db.String(50))  # startup, smb, enterprise
    
    # Benchmark Values
    percentile_25 = db.Column(db.Float)
    percentile_50 = db.Column(db.Float)  # median
    percentile_75 = db.Column(db.Float)
    percentile_90 = db.Column(db.Float)
    
    # Sample Information
    sample_size = db.Column(db.Integer)
    data_source = db.Column(db.String(200))
    last_updated = db.Column(db.DateTime)
    
    created_at = db.Column(db.DateTime, server_default=db.func.now())

class CustomerInsights(db.Model):
    """Customer-specific insights and patterns"""
    __tablename__ = 'customer_insights'
    
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.customer_id'), nullable=False)
    account_id = db.Column(db.Integer, db.ForeignKey('accounts.account_id'), nullable=True)
    
    # Insight Content
    insight_type = db.Column(db.String(50), nullable=False)  # trend, anomaly, recommendation
    title = db.Column(db.String(300), nullable=False)
    description = db.Column(Text, nullable=False)
    severity = db.Column(db.String(20))  # low, medium, high, critical
    
    # Associated Data
    affected_kpis = db.Column(JSON)  # Array of KPI names
    financial_impact = db.Column(db.Float)
    confidence_score = db.Column(db.Float)  # 0-1
    
    # Actions and Status
    recommended_actions = db.Column(JSON)  # Array of actions
    status = db.Column(db.String(20), default='active')  # active, resolved, dismissed
    
    created_at = db.Column(db.DateTime, server_default=db.func.now())
    updated_at = db.Column(db.DateTime, server_default=db.func.now(), onupdate=db.func.now())

class RAGQueryLog(db.Model):
    """Log of RAG queries for improvement and analytics"""
    __tablename__ = 'rag_query_log'
    
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.customer_id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=True)
    
    # Query Information
    query_text = db.Column(Text, nullable=False)
    query_type = db.Column(db.String(50))  # financial, kpi_analysis, best_practice, etc.
    
    # Response Information
    response_text = db.Column(Text)
    response_quality_score = db.Column(db.Float)  # 0-1, user feedback
    sources_used = db.Column(JSON)  # Array of source IDs
    
    # Performance Metrics
    response_time_ms = db.Column(db.Integer)
    tokens_used = db.Column(db.Integer)
    
    created_at = db.Column(db.DateTime, server_default=db.func.now())

# RAG Knowledge Base Prerequisites Documentation
RAG_PREREQUISITES = {
    "data_requirements": {
        "time_series_data": {
            "description": "Historical KPI data over multiple time periods",
            "minimum_period": "6 months",
            "recommended_period": "2+ years",
            "granularity": "Monthly or weekly",
            "status": "✅ Implemented - KPITimeSeries table with 7 months of data"
        },
        "financial_projections": {
            "description": "Financial impact calculations tied to KPI changes",
            "requirements": [
                "Revenue impact coefficients per KPI category",
                "Cost savings calculations",
                "ROI projections",
                "Confidence levels"
            ],
            "status": "✅ Implemented - FinancialProjection model and API"
        },
        "industry_benchmarks": {
            "description": "Industry-specific KPI benchmarks and comparisons",
            "requirements": [
                "Percentile-based benchmarks (25th, 50th, 75th, 90th)",
                "Industry segmentation",
                "Company size considerations",
                "Regular updates"
            ],
            "status": "⚠️ Partially implemented - Schema ready, needs data population"
        },
        "best_practices_library": {
            "description": "Curated best practices and recommendations for KPI improvement",
            "requirements": [
                "Implementation steps",
                "Expected impact metrics",
                "Difficulty and cost estimates",
                "Industry applicability"
            ],
            "status": "⚠️ Schema ready, needs content creation"
        },
        "customer_insights": {
            "description": "Customer-specific insights, trends, and recommendations",
            "requirements": [
                "Anomaly detection",
                "Trend analysis",
                "Personalized recommendations",
                "Action tracking"
            ],
            "status": "⚠️ Schema ready, needs AI-powered insight generation"
        }
    },
    
    "technical_requirements": {
        "vector_database": {
            "description": "Vector database for semantic search",
            "options": ["Pinecone", "Weaviate", "Qdrant", "Chroma", "Milvus"],
            "current_status": "⚠️ Basic ChromaDB setup exists, needs enhancement",
            "requirements": [
                "Embedding model integration",
                "Vector indexing",
                "Similarity search",
                "Scalability"
            ]
        },
        "embedding_model": {
            "description": "LLM-powered embeddings for semantic understanding",
            "current_status": "⚠️ Basic SentenceTransformer setup exists",
            "requirements": [
                "Domain-specific fine-tuning",
                "Multi-modal capabilities",
                "Context awareness",
                "Performance optimization"
            ]
        },
        "llm_integration": {
            "description": "Large Language Model for response generation",
            "current_status": "❌ Not implemented - using rule-based responses",
            "requirements": [
                "API integration (OpenAI, Anthropic, etc.)",
                "Prompt engineering",
                "Context management",
                "Response validation"
            ]
        },
        "rag_pipeline": {
            "description": "End-to-end RAG pipeline implementation",
            "current_status": "⚠️ Basic TF-IDF implementation exists",
            "requirements": [
                "Retrieval optimization",
                "Context ranking",
                "Response synthesis",
                "Quality assessment"
            ]
        }
    },
    
    "data_quality_requirements": {
        "data_validation": {
            "description": "Data quality and validation mechanisms",
            "requirements": [
                "Outlier detection",
                "Data completeness checks",
                "Consistency validation",
                "Automated data cleaning"
            ],
            "status": "⚠️ Basic validation exists, needs enhancement"
        },
        "data_enrichment": {
            "description": "Data enrichment and augmentation",
            "requirements": [
                "External data integration",
                "Market data feeds",
                "Industry reports",
                "Competitive intelligence"
            ],
            "status": "❌ Not implemented"
        }
    },
    
    "user_experience_requirements": {
        "query_interface": {
            "description": "Natural language query interface",
            "requirements": [
                "Intent recognition",
                "Query expansion",
                "Context awareness",
                "Multi-turn conversations"
            ],
            "status": "⚠️ Basic interface exists, needs enhancement"
        },
        "response_formatting": {
            "description": "Intelligent response formatting",
            "requirements": [
                "Structured data presentation",
                "Visual charts and graphs",
                "Actionable recommendations",
                "Source attribution"
            ],
            "status": "⚠️ Basic formatting exists"
        }
    }
}

def get_rag_readiness_assessment():
    """Assess current RAG system readiness"""
    total_requirements = 0
    implemented_requirements = 0
    
    for category, requirements in RAG_PREREQUISITES.items():
        for req_name, req_data in requirements.items():
            if isinstance(req_data, dict) and 'status' in req_data:
                total_requirements += 1
                if req_data['status'].startswith('✅'):
                    implemented_requirements += 1
    
    readiness_percentage = (implemented_requirements / total_requirements) * 100
    
    return {
        'readiness_percentage': readiness_percentage,
        'implemented_requirements': implemented_requirements,
        'total_requirements': total_requirements,
        'next_priorities': [
            'Implement LLM integration for response generation',
            'Enhance vector database with proper embeddings',
            'Populate industry benchmarks database',
            'Create best practices content library',
            'Implement customer insights generation'
        ]
    }
