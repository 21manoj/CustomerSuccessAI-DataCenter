#!/usr/bin/env python3
"""
Updated WeekData with Complete Qdrant Payload Mapping
=====================================================

This file provides the corrected WeekData class with get_qdrant_payload()
method that properly maps to ALL 48 fields in the journey_weeks collection.

Use this to replace the WeekData class in enhanced_hierarchical_journey_generator.py
"""

from typing import Dict, List, Optional
from dataclasses import dataclass, field
from enum import Enum


# Import from existing files (or redefine if needed)
class JourneyPhase(Enum):
    HEALTHY = "healthy"
    CRISIS = "crisis"
    RECOVERY = "recovery"
    AT_RISK = "at_risk"
    MODERATE = "moderate"
    GROWTH = "growth"
    CHURNED = "churned"


class EventType(Enum):
    QBR = "qbr"
    OUTAGE = "outage"
    ESCALATION = "escalation"
    # ... (all event types)


@dataclass
class WeekEvent:
    """Event data"""
    event_type: EventType
    description: str
    sentiment: str
    sentiment_value: float
    csm_action: Optional[Dict]
    outcome: str
    kpi_impacts: Dict[str, float] = field(default_factory=dict)


@dataclass
class WeekData:
    """
    Complete week data with PERFECT Qdrant mapping
    
    Maps to ALL 48 fields in journey_weeks collection:
    - 3 Identifiers
    - 2 Health metrics
    - 5 Pillar scores
    - 5 Pillar changes
    - 12 Top KPIs
    - 7 Event metadata fields
    - 3 Sentiment fields
    - 3 CSM investment fields
    - 3 Data quality fields
    - 3 Pattern metadata fields
    - 1 Full data field (non-indexed)
    - 1 Phase field
    """
    
    # ========================================================================
    # CORE FIELDS
    # ========================================================================
    week_number: int
    date: str
    phase: JourneyPhase
    
    # Calculation layer
    kpis: Dict[str, float]  # Normalized KPIs (0-100) - for backwards compatibility
    pillars: Dict[str, float]
    health_score: float
    
    # NEW V2: Raw KPI values (optional for backwards compatibility)
    raw_kpis: Optional[Dict[str, tuple]] = None  # {kpi_name: (value, unit)}
    
    # Narrative layer
    events: List[WeekEvent]
    
    # Quality metrics
    data_quality: float
    missing_kpis: List[str]
    
    # ========================================================================
    # DERIVED METRICS (calculated in generator)
    # ========================================================================
    health_change: Optional[float] = None
    pillar_changes: Dict[str, float] = field(default_factory=dict)
    
    # Event metadata
    average_sentiment: float = 0.0
    total_csm_investment: float = 0.0
    primary_event_type: Optional[str] = None
    
    # Pattern metadata
    is_crisis_start: bool = False
    is_recovery_start: bool = False
    weeks_since_crisis: Optional[int] = None
    
    def get_qdrant_payload(self, account_id: str) -> Dict:
        """
        Generate Qdrant payload with ALL 48 fields properly mapped.
        
        This matches EXACTLY with qdrant_field_registry.py JOURNEY_WEEKS_FIELDS.
        
        Args:
            account_id: Account identifier (required for payload)
        
        Returns:
            Dict with all 48 fields for journey_weeks collection
        """
        
        # Calculate derived fields if not set
        event_types = [e.event_type.value for e in self.events]
        has_escalation = any(e.event_type == EventType.ESCALATION for e in self.events)
        has_outage = any(e.event_type == EventType.OUTAGE for e in self.events)
        has_qbr = any(e.event_type == EventType.QBR for e in self.events)
        has_expansion = any(e.event_type.value == 'expansion_discussion' for e in self.events)
        
        has_war_room = any(
            e.csm_action and e.csm_action.get('action_type') == 'war_room' 
            for e in self.events if e.csm_action
        )
        has_exec_sponsor = any(
            e.csm_action and e.csm_action.get('action_type') == 'executive_sponsor'
            for e in self.events if e.csm_action
        )
        
        data_quality_level = (
            'high' if self.data_quality >= 0.9 
            else 'medium' if self.data_quality >= 0.7 
            else 'low'
        )
        
        payload = {
            # ================================================================
            # IDENTIFIERS (3 fields)
            # ================================================================
            'account_id': account_id,
            'week_number': self.week_number,
            'date': self.date,
            
            # ================================================================
            # PHASE & HEALTH (3 fields)
            # ================================================================
            'phase': self.phase.value,
            'health_score': round(self.health_score, 2),
            'health_change': round(self.health_change, 2) if self.health_change is not None else 0.0,
            
            # ================================================================
            # PILLAR SCORES (5 fields)
            # ================================================================
            'P1_deployment_velocity': round(self.pillars.get('P1_deployment_velocity', 0), 2),
            'P2_operational_stability': round(self.pillars.get('P2_operational_stability', 0), 2),
            'P3_ai_workload_performance': round(self.pillars.get('P3_ai_workload_performance', 0), 2),
            'P4_channel_partner_health': round(self.pillars.get('P4_channel_partner_health', 0), 2),
            'P5_expansion_readiness': round(self.pillars.get('P5_expansion_readiness', 0), 2),
            
            # ================================================================
            # PILLAR CHANGES (5 fields)
            # ================================================================
            'P1_change': round(self.pillar_changes.get('P1_deployment_velocity', 0), 2),
            'P2_change': round(self.pillar_changes.get('P2_operational_stability', 0), 2),
            'P3_change': round(self.pillar_changes.get('P3_ai_workload_performance', 0), 2),
            'P4_change': round(self.pillar_changes.get('P4_channel_partner_health', 0), 2),
            'P5_change': round(self.pillar_changes.get('P5_expansion_readiness', 0), 2),
            
            # ================================================================
            # TOP 12 KPIs (12 fields)
            # Most frequently queried KPIs - critical for filtering
            # ================================================================
            # P2: Operational Stability (4 KPIs)
            'rma_frequency_rate': round(self.kpis.get('rma_frequency_rate', 0), 2),
            'mtbf': round(self.kpis.get('mtbf', 0), 2),
            'critical_incident_rate': round(self.kpis.get('critical_incident_rate', 0), 2),
            'unplanned_downtime': round(self.kpis.get('unplanned_downtime', 0), 2),
            
            # P3: AI Workload Performance (2 KPIs)
            'gpu_utilization_rate': round(self.kpis.get('gpu_utilization_rate', 0), 2),
            'training_job_completion': round(self.kpis.get('training_job_completion', 0), 2),
            
            # P4: Partner Health (1 KPI)
            'partner_engagement_score': round(self.kpis.get('partner_engagement_score', 0), 2),
            
            # P5: Expansion Readiness (3 KPIs)
            'expansion_probability_90d': round(self.kpis.get('expansion_probability_90d', 0), 2),
            'capacity_utilization_trajectory': round(self.kpis.get('capacity_utilization_trajectory', 0), 2),
            'workload_growth_velocity': round(self.kpis.get('workload_growth_velocity', 0), 2),
            
            # Additional high-value KPIs (2 KPIs)
            'support_ticket_velocity': round(self.kpis.get('support_ticket_velocity', 0), 2),
            'thermal_power_alerts': round(self.kpis.get('thermal_power_alerts', 0), 2),
            
            # ================================================================
            # EVENT METADATA (7 fields)
            # ================================================================
            'event_count': len(self.events),
            'primary_event_type': self.primary_event_type or (event_types[0] if event_types else None),
            'has_escalation': has_escalation,
            'has_outage': has_outage,
            'has_qbr': has_qbr,
            'has_expansion_discussion': has_expansion,
            'has_war_room': has_war_room,
            'has_exec_sponsor': has_exec_sponsor,
            
            # ================================================================
            # SENTIMENT (3 fields)
            # ================================================================
            'average_sentiment': round(self.average_sentiment, 2),
            'has_negative_sentiment': self.average_sentiment < -0.3,
            'has_very_negative_sentiment': self.average_sentiment < -0.7,
            
            # ================================================================
            # CSM INVESTMENT (2 fields) - has_war_room, has_exec_sponsor above
            # ================================================================
            'total_csm_investment': round(self.total_csm_investment, 2),
            'has_high_csm_cost': self.total_csm_investment > 10000,
            
            # ================================================================
            # DATA QUALITY (3 fields)
            # ================================================================
            'data_quality': round(self.data_quality, 2),
            'data_quality_level': data_quality_level,
            'missing_kpi_count': len(self.missing_kpis),
            
            # ================================================================
            # PATTERN METADATA (3 fields)
            # ================================================================
            'is_crisis_start': self.is_crisis_start,
            'is_recovery_start': self.is_recovery_start,
            'weeks_since_crisis': self.weeks_since_crisis if self.weeks_since_crisis is not None else 0,
            
            # ================================================================
            # FULL DATA (1 field - non-indexed, for retrieval)
            # ================================================================
            'full_week_data': self.to_dict()
        }
        
        return payload
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON export and full_week_data field"""
        base_dict = {
            'week_number': self.week_number,
            'date': self.date,
            'phase': self.phase.value,
            'health_score': round(self.health_score, 2),
            'health_change': round(self.health_change, 2) if self.health_change else None,
            'pillars': {k: round(v, 2) for k, v in self.pillars.items()},
            'pillar_changes': {k: round(v, 2) for k, v in self.pillar_changes.items()},
            'kpis': {k: round(v, 2) for k, v in self.kpis.items()},
            'events': [
                {
                    'event_type': e.event_type.value,
                    'description': e.description,
                    'sentiment': e.sentiment,
                    'sentiment_value': e.sentiment_value,
                    'csm_action': e.csm_action,
                    'outcome': e.outcome
                } 
                for e in self.events
            ],
            'average_sentiment': round(self.average_sentiment, 2),
            'total_csm_investment': round(self.total_csm_investment, 2),
            'data_quality': round(self.data_quality, 2),
            'missing_kpis': self.missing_kpis,
            'primary_event_type': self.primary_event_type,
            'is_crisis_start': self.is_crisis_start,
            'is_recovery_start': self.is_recovery_start,
            'weeks_since_crisis': self.weeks_since_crisis
        }
        
        # Add raw_kpis if available (V2 format)
        if self.raw_kpis:
            base_dict['raw_kpis'] = {
                k: {'value': v[0], 'unit': v[1]} 
                for k, v in self.raw_kpis.items()
            }
        
        return base_dict


# ============================================================================
# VALIDATION EXAMPLE
# ============================================================================

if __name__ == '__main__':
    from qdrant_field_registry import FieldRegistry
    
    print("="*70)
    print("QDRANT PAYLOAD VALIDATION")
    print("="*70)
    print()
    
    # Create sample week data
    sample_week = WeekData(
        week_number=5,
        date='2024-01-29',
        phase=JourneyPhase.CRISIS,
        kpis={
            'rma_frequency_rate': 30.0,
            'mtbf': 25.0,
            'critical_incident_rate': 25.0,
            'unplanned_downtime': 21.0,
            'gpu_utilization_rate': 35.0,
            'training_job_completion': 43.0,
            'partner_engagement_score': 70.0,
            'expansion_probability_90d': 12.0,
            'capacity_utilization_trajectory': 72.0,
            'workload_growth_velocity': 65.0,
            'support_ticket_velocity': 50.0,
            'thermal_power_alerts': 34.0
        },
        pillars={
            'P1_deployment_velocity': 82.6,
            'P2_operational_stability': 37.2,
            'P3_ai_workload_performance': 56.6,
            'P4_channel_partner_health': 75.2,
            'P5_expansion_readiness': 67.0
        },
        health_score=63.0,
        events=[],
        data_quality=0.875,
        missing_kpis=['workload_density_trend', 'cosell_activity'],
        health_change=-18.0,
        pillar_changes={
            'P1_deployment_velocity': 0.0,
            'P2_operational_stability': -46.4,
            'P3_ai_workload_performance': -25.3,
            'P4_channel_partner_health': -9.1,
            'P5_expansion_readiness': -9.8
        },
        average_sentiment=-0.8,
        total_csm_investment=40000.0,
        is_crisis_start=True
    )
    
    # Generate payload
    payload = sample_week.get_qdrant_payload(account_id='ACCT001')
    
    # Validate against registry
    errors = FieldRegistry.validate_payload('journey_weeks', payload)
    
    if errors:
        print("❌ VALIDATION ERRORS:")
        for error in errors:
            print(f"   - {error}")
    else:
        print("✅ PAYLOAD VALID!")
    
    print(f"\nPayload fields: {len(payload)}")
    print(f"Expected fields: {len(FieldRegistry.get_all_fields('journey_weeks'))}")
    
    print("\nField mapping:")
    for field_name in sorted(payload.keys()):
        print(f"  ✓ {field_name}: {payload[field_name]}")
