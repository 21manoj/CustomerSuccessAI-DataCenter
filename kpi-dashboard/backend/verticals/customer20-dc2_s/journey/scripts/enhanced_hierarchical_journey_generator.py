#!/usr/bin/env python3
"""
Enhanced Hierarchical Journey Generator
========================================

The COMPLETE solution:
  ✅ KPIs (35 values) → Pillars (5 scores) → Health (1 score)
  ✅ Events (narrative) → Sentiment → CSM Actions
  ✅ Events impact KPIs, KPIs calculate health
  ✅ Qdrant-ready data structure

Flow:
  Events happen → KPIs change → Pillars calculated → Health calculated
  
Both quantitative (KPIs) and qualitative (events) preserved!
"""

import json
import random
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, asdict, field
from enum import Enum
from pathlib import Path

# Import components
from kpi_generator import KPIGenerator, AccountProfile, LifecycleStage
from robust_hierarchical_health_calculator import RobustHierarchicalHealthCalculator


# ============================================================================
# ENUMS
# ============================================================================

class JourneyPhase(Enum):
    """Journey phases"""
    HEALTHY = "healthy"
    CRISIS = "crisis"
    RECOVERY = "recovery"
    AT_RISK = "at_risk"
    MODERATE = "moderate"
    GROWTH = "growth"
    CHURNED = "churned"


class EventType(Enum):
    """Types of events"""
    QBR = "qbr"
    OUTAGE = "outage"
    MEETING = "meeting"
    EMAIL = "email"
    ESCALATION = "escalation"
    SUPPORT_TICKET = "support_ticket"
    BUDGET_REVIEW = "budget_review"
    CONTRACT_DISCUSSION = "contract_discussion"
    TECHNICAL_ISSUE = "technical_issue"
    CHAMPION_INTERACTION = "champion_interaction"
    EXECUTIVE_ENGAGEMENT = "executive_engagement"
    MILESTONE = "milestone"
    EXPANSION_DISCUSSION = "expansion_discussion"


class SentimentLevel(Enum):
    """Sentiment levels"""
    VERY_POSITIVE = "very_positive"
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"
    VERY_NEGATIVE = "very_negative"


class CSMActionType(Enum):
    """CSM action types"""
    STANDARD_CHECKIN = "standard_checkin"
    WAR_ROOM = "war_room"
    EXECUTIVE_SPONSOR = "executive_sponsor"
    ROOT_CAUSE_ANALYSIS = "root_cause_analysis"
    SUPPORT_ENGINEER_24_7 = "support_engineer_24_7"
    ENHANCED_MONITORING = "enhanced_monitoring"
    WEEKLY_EXEC_CALLS = "weekly_exec_calls"
    FLEXIBLE_PAYMENT_TERMS = "flexible_payment_terms"
    DISCOUNT_NEGOTIATION = "discount_negotiation"
    ROI_ANALYSIS = "roi_analysis"
    PROACTIVE_TRAINING = "proactive_training"
    EXPANSION_ENABLEMENT = "expansion_enablement"
    NO_ACTION = "no_action"


# ============================================================================
# DATA MODELS
# ============================================================================

@dataclass
class CSMAction:
    """CSM action taken"""
    action_type: CSMActionType
    description: str
    response_time_hours: float
    cost_estimate: float
    
    def to_dict(self) -> Dict:
        return {
            'action_type': self.action_type.value,
            'description': self.description,
            'response_time_hours': self.response_time_hours,
            'cost_estimate': self.cost_estimate
        }


@dataclass
class WeekEvent:
    """
    Single event in a week (narrative layer)
    
    Events EXPLAIN what happened, but don't directly calculate health.
    Instead, events IMPACT KPIs, which then calculate health.
    """
    event_type: EventType
    description: str
    sentiment: SentimentLevel
    sentiment_value: float  # -1.0 to +1.0
    csm_action: Optional[CSMAction]
    outcome: str
    
    # NEW: Link events to KPI impacts
    kpi_impacts: Dict[str, float] = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        return {
            'event_type': self.event_type.value,
            'description': self.description,
            'sentiment': self.sentiment.value,
            'sentiment_value': round(self.sentiment_value, 2),
            'csm_action': self.csm_action.to_dict() if self.csm_action else None,
            'outcome': self.outcome,
            'kpi_impacts': {k: round(v, 2) for k, v in self.kpi_impacts.items()}
        }


@dataclass
class WeekData:
    """
    Complete week data with BOTH calculation layer AND narrative layer
    
    Calculation Layer (Quantitative):
      - KPIs (35 values)
      - Pillars (5 scores) - calculated from KPIs
      - Health (1 score) - calculated from pillars
    
    Narrative Layer (Qualitative):
      - Events (what happened)
      - Sentiment (customer mood)
      - CSM Actions (what we did)
    
    This is Qdrant-ready: all fields designed for vector search + filtering
    """
    # Metadata
    week_number: int
    date: str
    phase: JourneyPhase
    
    # Calculation Layer
    kpis: Dict[str, float]          # 35 KPI values (0-100 scale)
    pillars: Dict[str, float]       # 5 pillar scores (calculated)
    health_score: float             # Overall health (calculated)
    
    # Narrative Layer
    events: List[WeekEvent]         # Events that happened this week
    
    # Quality Metrics
    data_quality: float             # % of expected KPIs available
    missing_kpis: List[str]         # KPIs not available this week
    
    # Derived metrics (for Qdrant filtering)
    health_change: Optional[float] = None  # vs previous week
    pillar_changes: Dict[str, float] = field(default_factory=dict)
    primary_event_type: Optional[str] = None  # Most significant event
    average_sentiment: float = 0.0
    total_csm_investment: float = 0.0
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON export"""
        return {
            'week_number': self.week_number,
            'date': self.date,
            'phase': self.phase.value,
            'health_score': round(self.health_score, 2),
            'health_change': round(self.health_change, 2) if self.health_change else None,
            'pillars': {k: round(v, 2) for k, v in self.pillars.items()},
            'pillar_changes': {k: round(v, 2) for k, v in self.pillar_changes.items()},
            'kpis': {k: round(v, 2) for k, v in self.kpis.items()},
            'events': [e.to_dict() for e in self.events],
            'average_sentiment': round(self.average_sentiment, 2),
            'total_csm_investment': round(self.total_csm_investment, 2),
            'data_quality': round(self.data_quality, 2),
            'missing_kpis': self.missing_kpis,
            'primary_event_type': self.primary_event_type
        }
    
    def get_qdrant_payload(self) -> Dict:
        """
        Get Qdrant-optimized payload for vector storage
        
        Key design decisions:
        - Flatten nested structures for efficient filtering
        - Include all searchable/filterable fields
        - Keep payload size reasonable (<100KB)
        """
        return {
            # Identifiers
            'week_number': self.week_number,
            'date': self.date,
            
            # Phase & Health (most common filters)
            'phase': self.phase.value,
            'health_score': round(self.health_score, 2),
            'health_change': round(self.health_change, 2) if self.health_change else 0.0,
            
            # Pillar scores (for pillar-based filtering)
            'P1_deployment_velocity': round(self.pillars.get('P1_deployment_velocity', 0), 2),
            'P2_operational_stability': round(self.pillars.get('P2_operational_stability', 0), 2),
            'P3_ai_workload_performance': round(self.pillars.get('P3_ai_workload_performance', 0), 2),
            'P4_channel_partner_health': round(self.pillars.get('P4_channel_partner_health', 0), 2),
            'P5_expansion_readiness': round(self.pillars.get('P5_expansion_readiness', 0), 2),
            
            # Top 10 most important KPIs (for KPI-based filtering)
            'rma_frequency_rate': round(self.kpis.get('rma_frequency_rate', 0), 2),
            'mtbf': round(self.kpis.get('mtbf', 0), 2),
            'gpu_utilization_rate': round(self.kpis.get('gpu_utilization_rate', 0), 2),
            'training_job_completion': round(self.kpis.get('training_job_completion', 0), 2),
            'critical_incident_rate': round(self.kpis.get('critical_incident_rate', 0), 2),
            'unplanned_downtime': round(self.kpis.get('unplanned_downtime', 0), 2),
            'partner_engagement_score': round(self.kpis.get('partner_engagement_score', 0), 2),
            'expansion_probability_90d': round(self.kpis.get('expansion_probability_90d', 0), 2),
            'capacity_utilization_trajectory': round(self.kpis.get('capacity_utilization_trajectory', 0), 2),
            'workload_growth_velocity': round(self.kpis.get('workload_growth_velocity', 0), 2),
            
            # Event metadata (for event-based filtering)
            'event_count': len(self.events),
            'event_types': [e.event_type.value for e in self.events],
            'primary_event_type': self.primary_event_type,
            'has_escalation': any(e.event_type == EventType.ESCALATION for e in self.events),
            'has_outage': any(e.event_type == EventType.OUTAGE for e in self.events),
            
            # Sentiment (for sentiment-based filtering)
            'average_sentiment': round(self.average_sentiment, 2),
            'has_negative_sentiment': self.average_sentiment < -0.3,
            
            # CSM investment (for cost-based filtering)
            'total_csm_investment': round(self.total_csm_investment, 2),
            'has_high_csm_cost': self.total_csm_investment > 10000,
            
            # Data quality (for quality-based filtering)
            'data_quality': round(self.data_quality, 2),
            'data_quality_level': 'high' if self.data_quality >= 0.9 else 'medium' if self.data_quality >= 0.7 else 'low',
            
            # Full data (for retrieval)
            'full_week_data': self.to_dict()
        }


@dataclass
class EnhancedJourney:
    """Complete journey with KPIs + Events"""
    account_id: str
    account_name: str
    pattern_type: str
    start_date: str
    end_date: str
    total_weeks: int
    
    # Week-by-week data (KPIs + Events)
    weekly_data: List[WeekData]
    
    # Summary statistics
    starting_health: float
    ending_health: float
    lowest_health: float
    highest_health: float
    avg_pillar_scores: Dict[str, float]
    
    # Event statistics
    total_events: int
    event_distribution: Dict[str, int]
    total_csm_investment: float
    average_sentiment: float
    
    # Summary
    summary: Dict
    
    def to_dict(self) -> Dict:
        return {
            'account_id': self.account_id,
            'account_name': self.account_name,
            'pattern_type': self.pattern_type,
            'start_date': self.start_date,
            'end_date': self.end_date,
            'total_weeks': self.total_weeks,
            'starting_health': round(self.starting_health, 2),
            'ending_health': round(self.ending_health, 2),
            'lowest_health': round(self.lowest_health, 2),
            'highest_health': round(self.highest_health, 2),
            'avg_pillar_scores': {k: round(v, 2) for k, v in self.avg_pillar_scores.items()},
            'total_events': self.total_events,
            'event_distribution': self.event_distribution,
            'total_csm_investment': round(self.total_csm_investment, 2),
            'average_sentiment': round(self.average_sentiment, 2),
            'summary': self.summary,
            'weekly_data': [w.to_dict() for w in self.weekly_data]
        }


# ============================================================================
# EVENT GENERATOR
# ============================================================================

class EventGenerator:
    """Generate realistic events based on phase and KPI changes"""
    
    def generate_crisis_events(self, kpi_changes: Dict[str, float]) -> List[WeekEvent]:
        """Generate events for crisis situation"""
        events = []
        
        # Major outage event
        if kpi_changes.get('rma_frequency_rate', 0) < -30:
            events.append(WeekEvent(
                event_type=EventType.OUTAGE,
                description="Major datacenter outage: Cooling system failure caused 15 server shutdowns",
                sentiment=SentimentLevel.VERY_NEGATIVE,
                sentiment_value=-0.9,
                csm_action=CSMAction(
                    action_type=CSMActionType.WAR_ROOM,
                    description="Emergency war room convened within 2 hours",
                    response_time_hours=2,
                    cost_estimate=15000
                ),
                outcome="Hardware replacement initiated, 24/7 monitoring deployed",
                kpi_impacts=kpi_changes
            ))
        
        # Escalation event
        events.append(WeekEvent(
            event_type=EventType.ESCALATION,
            description="Customer escalated to executive team due to ongoing stability issues",
            sentiment=SentimentLevel.NEGATIVE,
            sentiment_value=-0.7,
            csm_action=CSMAction(
                action_type=CSMActionType.EXECUTIVE_SPONSOR,
                description="VP assigned as executive sponsor, daily calls scheduled",
                response_time_hours=4,
                cost_estimate=25000
            ),
            outcome="Executive sponsor assigned, daily status calls with CTO initiated",
            kpi_impacts={}
        ))
        
        return events
    
    def generate_healthy_events(self) -> List[WeekEvent]:
        """Generate events for healthy period"""
        events = []
        
        if random.random() < 0.3:  # 30% chance of event
            events.append(WeekEvent(
                event_type=EventType.QBR,
                description="Quarterly Business Review conducted, reviewed AI workload performance",
                sentiment=SentimentLevel.POSITIVE,
                sentiment_value=0.6,
                csm_action=CSMAction(
                    action_type=CSMActionType.STANDARD_CHECKIN,
                    description="Standard quarterly review completed",
                    response_time_hours=168,
                    cost_estimate=500
                ),
                outcome="Customer satisfied with performance, exploring expansion opportunities",
                kpi_impacts={}
            ))
        
        return events
    
    def generate_growth_events(self) -> List[WeekEvent]:
        """Generate events for growth phase"""
        events = []
        
        if random.random() < 0.4:
            events.append(WeekEvent(
                event_type=EventType.EXPANSION_DISCUSSION,
                description="Expansion planning session: Customer interested in 40% capacity increase",
                sentiment=SentimentLevel.VERY_POSITIVE,
                sentiment_value=0.8,
                csm_action=CSMAction(
                    action_type=CSMActionType.EXPANSION_ENABLEMENT,
                    description="Expansion proposal prepared with ROI analysis",
                    response_time_hours=48,
                    cost_estimate=3000
                ),
                outcome="Expansion proposal submitted, decision expected in 2 weeks",
                kpi_impacts={'expansion_probability_90d': 15}
            ))
        
        return events


# ============================================================================
# ENHANCED GENERATOR
# ============================================================================

class EnhancedHierarchicalJourneyGenerator:
    """
    Generate journeys with BOTH KPIs and Events
    
    Key features:
    - TRUE hierarchical: KPIs → Pillars → Health
    - Events provide narrative context
    - Events impact KPIs
    - Qdrant-ready data structure
    """
    
    def __init__(self, bootstrap_weights_path: str):
        self.kpi_generator = KPIGenerator()
        self.health_calculator = RobustHierarchicalHealthCalculator(bootstrap_weights_path)
        self.event_generator = EventGenerator()
        
        print("✅ Enhanced Hierarchical Journey Generator initialized")
        print("   - KPI Layer: 35 KPIs → 5 Pillars → 1 Health")
        print("   - Event Layer: Events → Sentiment → CSM Actions")
        print("   - Qdrant-ready: Optimized payload structure")
    
    def _determine_phase(self, health: float) -> JourneyPhase:
        """Determine phase from health score"""
        if health >= 85:
            return JourneyPhase.GROWTH
        elif health >= 70:
            return JourneyPhase.HEALTHY
        elif health >= 50:
            return JourneyPhase.MODERATE
        elif health >= 30:
            return JourneyPhase.AT_RISK
        elif health >= 15:
            return JourneyPhase.CRISIS
        else:
            return JourneyPhase.CHURNED
    
    def generate_crisis_recovery_journey(
        self,
        account_id: str,
        account_name: str,
        start_date: datetime,
        total_weeks: int = 52
    ) -> EnhancedJourney:
        """Generate crisis → recovery → growth with KPIs + Events"""
        
        print(f"\nGenerating enhanced journey for {account_name}...")
        
        crisis_week = 5
        recovery_weeks = 20
        
        # Generate initial KPIs
        current_kpis = self.kpi_generator.generate_initial_kpis(
            profile=AccountProfile.ENTERPRISE,
            stage=LifecycleStage.MATURE,
            pattern_type='crisis_recovery'
        )
        
        weekly_data = []
        previous_week = None
        
        for week in range(1, total_weeks + 1):
            week_date = start_date + timedelta(weeks=week - 1)
            
            # Evolve KPIs (pattern-specific)
            if week > 1:
                kpi_changes_from_pattern = {}
                previous_kpis = current_kpis.copy()
                
                current_kpis = self.kpi_generator.evolve_kpis_crisis(
                    current_kpis, week, crisis_week, recovery_weeks
                )
                
                # Calculate what changed
                for kpi in current_kpis:
                    kpi_changes_from_pattern[kpi] = current_kpis[kpi] - previous_kpis[kpi]
            else:
                kpi_changes_from_pattern = {}
            
            # Generate events based on phase and KPI changes
            if week == crisis_week:
                events = self.event_generator.generate_crisis_events(kpi_changes_from_pattern)
            elif week > crisis_week and week < crisis_week + 10:
                events = []  # Recovery period, few events
            else:
                events = self.event_generator.generate_healthy_events()
            
            # Events can further impact KPIs
            for event in events:
                for kpi, impact in event.kpi_impacts.items():
                    if kpi in current_kpis:
                        current_kpis[kpi] = max(0, min(100, current_kpis[kpi] + impact))
            
            # Calculate health from KPIs
            health, pillars, calc_details = self.health_calculator.calculate_health_with_pillars(
                current_kpis
            )
            
            # Determine phase
            phase = self._determine_phase(health)
            
            # Calculate derived metrics
            health_change = health - previous_week.health_score if previous_week else 0
            pillar_changes = {
                p: pillars[p] - previous_week.pillars[p]
                for p in pillars
            } if previous_week else {}
            
            avg_sentiment = sum(e.sentiment_value for e in events) / len(events) if events else 0
            total_csm_cost = sum(e.csm_action.cost_estimate for e in events if e.csm_action) else 0
            primary_event = events[0].event_type.value if events else None
            
            # Create week data
            week_data = WeekData(
                week_number=week,
                date=week_date.strftime('%Y-%m-%d'),
                phase=phase,
                kpis=current_kpis.copy(),
                pillars=pillars,
                health_score=health,
                events=events,
                data_quality=calc_details.data_completeness,
                missing_kpis=list(calc_details.expected_kpis - set(current_kpis.keys())),
                health_change=health_change,
                pillar_changes=pillar_changes,
                average_sentiment=avg_sentiment,
                total_csm_investment=total_csm_cost,
                primary_event_type=primary_event
            )
            
            weekly_data.append(week_data)
            previous_week = week_data
        
        # Calculate summary statistics
        health_scores = [w.health_score for w in weekly_data]
        all_events = [e for w in weekly_data for e in w.events]
        
        avg_pillars = {}
        for pillar_name in weekly_data[0].pillars.keys():
            scores = [w.pillars[pillar_name] for w in weekly_data]
            avg_pillars[pillar_name] = sum(scores) / len(scores)
        
        event_dist = {}
        for event in all_events:
            event_type = event.event_type.value
            event_dist[event_type] = event_dist.get(event_type, 0) + 1
        
        journey = EnhancedJourney(
            account_id=account_id,
            account_name=account_name,
            pattern_type='crisis_recovery',
            start_date=start_date.strftime('%Y-%m-%d'),
            end_date=(start_date + timedelta(weeks=total_weeks-1)).strftime('%Y-%m-%d'),
            total_weeks=total_weeks,
            weekly_data=weekly_data,
            starting_health=weekly_data[0].health_score,
            ending_health=weekly_data[-1].health_score,
            lowest_health=min(health_scores),
            highest_health=max(health_scores),
            avg_pillar_scores=avg_pillars,
            total_events=len(all_events),
            event_distribution=event_dist,
            total_csm_investment=sum(w.total_csm_investment for w in weekly_data),
            average_sentiment=sum(e.sentiment_value for e in all_events) / len(all_events) if all_events else 0,
            summary={
                'pattern_type': 'crisis_recovery',
                'crisis_week': crisis_week,
                'lowest_health': min(health_scores),
                'recovery_amount': weekly_data[-1].health_score - min(health_scores)
            }
        )
        
        print(f"✅ Journey complete!")
        print(f"   Health: {journey.starting_health:.1f} → {journey.ending_health:.1f}")
        print(f"   Events: {journey.total_events}")
        print(f"   CSM Investment: ${journey.total_csm_investment:,.0f}")
        
        return journey


# ============================================================================
# EXPORT FUNCTIONS
# ============================================================================

def export_to_json(journey: EnhancedJourney, filepath: str):
    """Export to JSON"""
    with open(filepath, 'w') as f:
        json.dump(journey.to_dict(), f, indent=2)
    print(f"✅ Exported to JSON: {filepath}")


if __name__ == '__main__':
    generator = EnhancedHierarchicalJourneyGenerator('bootstrap_weights_config.json')
    
    journey = generator.generate_crisis_recovery_journey(
        account_id='ACCT001',
        account_name='Test Enhanced Journey',
        start_date=datetime(2024, 1, 1),
        total_weeks=52
    )
    
    export_to_json(journey, 'test_enhanced_journey.json')
    
    # Show sample week data
    crisis_week = journey.weekly_data[4]  # Week 5
    print("\n" + "="*70)
    print("SAMPLE WEEK DATA (Crisis Week):")
    print("="*70)
    print(f"Week: {crisis_week.week_number}")
    print(f"Health: {crisis_week.health_score:.1f}")
    print(f"Phase: {crisis_week.phase.value}")
    print(f"Events: {len(crisis_week.events)}")
    for event in crisis_week.events:
        print(f"  - {event.event_type.value}: {event.description}")
        print(f"    Sentiment: {event.sentiment.value} ({event.sentiment_value})")
        if event.csm_action:
            print(f"    CSM Action: {event.csm_action.action_type.value}")
