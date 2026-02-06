"""
Phase 4: PostgreSQL Schema for Journey Training Data
====================================================

NEW TABLES (won't touch production):
- journey_accounts     - Training account metadata
- journey_events       - 187 events from journey patterns
- journey_kpis         - 3,220 KPI data points
- journey_health       - Weekly health snapshots
- journey_metadata     - Pattern information

All tables prefixed with 'journey_' to keep separate from production.
"""

from sqlalchemy import create_engine, Column, Integer, String, Numeric, DateTime, Text, JSON, Boolean, ForeignKey, Index, UniqueConstraint
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()


# ============================================================================
# JOURNEY TRAINING TABLES
# ============================================================================

class JourneyAccount(Base):
    """
    Training account data - references production accounts table
    Stores generated journey pattern metadata
    """
    __tablename__ = 'journey_accounts'
    
    # Primary Key
    journey_account_id = Column(Integer, primary_key=True)
    
    # Link to production account (optional - can work standalone)
    account_id = Column(Integer, ForeignKey('accounts.account_id'), nullable=True, index=True)
    
    # Account Details (duplicated for standalone testing)
    account_name = Column(String(200), nullable=False)
    external_account_id = Column(String(50), nullable=False, unique=True, index=True)  # e.g., '15007'
    
    # Journey Pattern Metadata
    pattern_type = Column(String(50), nullable=False, index=True)  # crisis_recovery, ignored_churn, proactive_growth
    pattern_description = Column(Text)
    
    # Financial
    arr = Column(Numeric(15, 2), nullable=False)
    
    # Journey Stats
    journey_start_date = Column(DateTime, nullable=False)
    journey_end_date = Column(DateTime)
    total_weeks = Column(Integer)
    total_events = Column(Integer)
    starting_health = Column(Numeric(5, 2))
    ending_health = Column(Numeric(5, 2))
    health_change = Column(Numeric(5, 2))
    
    # Outcome
    final_outcome = Column(String(50))  # expanded, churned, renewed, stable
    outcome_arr_impact = Column(Numeric(15, 2))  # Positive or negative ARR change
    total_csm_investment = Column(Numeric(12, 2))  # Total CSM costs
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    events = relationship('JourneyEvent', back_populates='account', cascade='all, delete-orphan')
    kpis = relationship('JourneyKPI', back_populates='account', cascade='all, delete-orphan')
    health_snapshots = relationship('JourneyHealth', back_populates='account', cascade='all, delete-orphan')
    
    # Indexes
    __table_args__ = (
        Index('idx_journey_account_pattern', 'pattern_type'),
        Index('idx_journey_account_external', 'external_account_id'),
    )


class JourneyEvent(Base):
    """
    Journey events - all 187 events from generated patterns
    Compatible with Signal Analyst qualitative signals
    """
    __tablename__ = 'journey_events'
    
    # Primary Key
    event_id = Column(Integer, primary_key=True)
    
    # Account Reference
    journey_account_id = Column(Integer, ForeignKey('journey_accounts.journey_account_id', ondelete='CASCADE'), nullable=False, index=True)
    
    # Event Details
    week_number = Column(Integer, nullable=False, index=True)
    event_date = Column(DateTime, nullable=False, index=True)
    event_type = Column(String(50), nullable=False, index=True)  # outage, escalation, qbr, etc.
    
    # Event Content
    description = Column(Text, nullable=False)
    phase = Column(String(50), nullable=False, index=True)  # healthy, crisis, recovery, at_risk, etc.
    
    # Sentiment
    sentiment_level = Column(String(20))  # very_positive, positive, neutral, negative, very_negative
    sentiment_value = Column(Numeric(4, 2))  # -1.0 to +1.0
    
    # Health Impact
    health_score_before = Column(Numeric(5, 2))
    health_score_after = Column(Numeric(5, 2))
    health_impact = Column(Numeric(5, 2))  # Change in health
    
    # CSM Action
    csm_action_type = Column(String(50), index=True)  # war_room, executive_sponsor, etc.
    csm_response_time_hours = Column(Integer)
    csm_action_cost = Column(Numeric(10, 2))
    csm_action_description = Column(Text)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationship
    account = relationship('JourneyAccount', back_populates='events')
    
    # Indexes
    __table_args__ = (
        Index('idx_journey_event_account_week', 'journey_account_id', 'week_number'),
        Index('idx_journey_event_account_date', 'journey_account_id', 'event_date'),
        Index('idx_journey_event_phase', 'phase'),
        Index('idx_journey_event_sentiment', 'sentiment_level'),
    )


class JourneyKPI(Base):
    """
    Journey KPIs - all 3,220 KPI data points
    Compatible with dc2s_kpis table structure
    """
    __tablename__ = 'journey_kpis'
    
    # Primary Key
    journey_kpi_id = Column(Integer, primary_key=True)
    
    # Account Reference
    journey_account_id = Column(Integer, ForeignKey('journey_accounts.journey_account_id', ondelete='CASCADE'), nullable=False, index=True)
    
    # Time Period
    week_number = Column(Integer, nullable=False, index=True)
    measurement_date = Column(DateTime, nullable=False, index=True)
    
    # KPI Identification (matches Phase 3 KPI generator)
    kpi_code = Column(String(10), nullable=False, index=True)  # P1, P2, C1, S1, R1, B1, etc.
    kpi_name = Column(String(100), nullable=False)
    category = Column(String(50), nullable=False, index=True)  # Performance, Cost, Scalability, Support, Business
    
    # KPI Value
    value = Column(Numeric(10, 2), nullable=False)
    unit = Column(String(20))
    
    # Ranges (from KPI definitions)
    good_range_min = Column(Numeric(10, 2))
    good_range_max = Column(Numeric(10, 2))
    bad_range_min = Column(Numeric(10, 2))
    bad_range_max = Column(Numeric(10, 2))
    
    # Status
    status = Column(String(20))  # good, at_risk, critical
    
    # Context
    health_score = Column(Numeric(5, 2))  # Health score at this time
    phase = Column(String(50))  # Phase at this time
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationship
    account = relationship('JourneyAccount', back_populates='kpis')
    
    # Indexes and Constraints
    __table_args__ = (
        UniqueConstraint('journey_account_id', 'week_number', 'kpi_code', name='unique_journey_kpi'),
        Index('idx_journey_kpi_account_week', 'journey_account_id', 'week_number'),
        Index('idx_journey_kpi_account_code', 'journey_account_id', 'kpi_code'),
        Index('idx_journey_kpi_category', 'category'),
    )


class JourneyHealth(Base):
    """
    Weekly health snapshots for journey accounts
    Compatible with health_trends table
    """
    __tablename__ = 'journey_health'
    
    # Primary Key
    health_id = Column(Integer, primary_key=True)
    
    # Account Reference
    journey_account_id = Column(Integer, ForeignKey('journey_accounts.journey_account_id', ondelete='CASCADE'), nullable=False, index=True)
    
    # Time Period
    week_number = Column(Integer, nullable=False, index=True)
    snapshot_date = Column(DateTime, nullable=False, index=True)
    
    # Overall Health
    overall_health_score = Column(Numeric(5, 2), nullable=False)
    health_status = Column(String(20))  # excellent, good, at_risk, critical
    
    # Phase
    phase = Column(String(50), nullable=False, index=True)
    
    # Pillar Scores (if using bootstrap weights)
    p1_deployment_score = Column(Numeric(5, 2))
    p2_operational_score = Column(Numeric(5, 2))
    p3_performance_score = Column(Numeric(5, 2))
    p4_channel_score = Column(Numeric(5, 2))
    p5_expansion_score = Column(Numeric(5, 2))
    
    # Event Summary for this week
    events_this_week = Column(Integer, default=0)
    csm_actions_this_week = Column(Integer, default=0)
    total_csm_cost_this_week = Column(Numeric(10, 2))
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationship
    account = relationship('JourneyAccount', back_populates='health_snapshots')
    
    # Indexes and Constraints
    __table_args__ = (
        UniqueConstraint('journey_account_id', 'week_number', name='unique_journey_health'),
        Index('idx_journey_health_account_week', 'journey_account_id', 'week_number'),
        Index('idx_journey_health_account_date', 'journey_account_id', 'snapshot_date'),
        Index('idx_journey_health_phase', 'phase'),
    )


class JourneyMetadata(Base):
    """
    Metadata about journey generation
    Tracks what was generated when and with what parameters
    """
    __tablename__ = 'journey_metadata'
    
    # Primary Key
    metadata_id = Column(Integer, primary_key=True)
    
    # Generation Info
    generation_phase = Column(String(20), nullable=False)  # phase1, phase2, phase3
    generation_date = Column(DateTime, nullable=False, default=datetime.utcnow)
    generator_version = Column(String(20))
    
    # Statistics
    accounts_generated = Column(Integer)
    events_generated = Column(Integer)
    kpis_generated = Column(Integer)
    
    # Configuration
    parameters = Column(JSON)  # Generation parameters
    patterns = Column(JSON)  # List of patterns generated
    
    # File References
    source_files = Column(JSON)  # List of source JSON/CSV files
    
    # Notes
    notes = Column(Text)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def create_journey_tables(engine):
    """Create all journey training tables"""
    Base.metadata.create_all(engine)
    print("✅ Journey training tables created successfully!")


def drop_journey_tables(engine):
    """Drop all journey training tables (useful for testing)"""
    Base.metadata.drop_all(engine)
    print("✅ Journey training tables dropped!")


# ============================================================================
# EXAMPLE USAGE
# ============================================================================

if __name__ == "__main__":
    print("="*70)
    print("JOURNEY TRAINING SCHEMA - Phase 4")
    print("="*70)
    print()
    print("📋 TABLES TO BE CREATED:")
    print("-" * 70)
    print("  1. journey_accounts      - Account metadata & pattern info")
    print("  2. journey_events        - 187 events from patterns")
    print("  3. journey_kpis          - 3,220 KPI data points")
    print("  4. journey_health        - Weekly health snapshots")
    print("  5. journey_metadata      - Generation tracking")
    print()
    print("🔒 SAFETY:")
    print("-" * 70)
    print("  ✅ All tables prefixed with 'journey_'")
    print("  ✅ No modifications to production tables")
    print("  ✅ Optional FK to production accounts table")
    print("  ✅ Can be dropped anytime without affecting SaaS")
    print()
    print("🔗 INTEGRATION:")
    print("-" * 70)
    print("  ✅ Compatible with existing naming conventions")
    print("  ✅ Matches dc2s_kpis structure for KPIs")
    print("  ✅ Matches health_trends structure for health")
    print("  ✅ Can reference production accounts table")
    print()
    print("="*70)
    print("Ready to create migration scripts!")
    print("="*70)
