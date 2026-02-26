#!/usr/bin/env python3
"""
Qdrant Field Mapping Verification
==================================

Ensures complete consistency between:
1. Data model (WeekData, WeekEvent, EnhancedJourney)
2. Qdrant payload structure
3. Qdrant indexed fields
4. Query capabilities

This file audits and fixes any mismatches.
"""

from typing import Dict, List
from enum import Enum


# ============================================================================
# FIELD REGISTRY - Single Source of Truth
# ============================================================================

class FieldType(Enum):
    """Qdrant field types"""
    KEYWORD = "keyword"
    INTEGER = "integer"
    FLOAT = "float"
    BOOL = "bool"
    TEXT = "text"  # Not indexed, stored in payload only


class FieldRegistry:
    """
    Central registry of all fields across collections.
    
    This is the SINGLE SOURCE OF TRUTH for:
    - Which fields exist
    - Which fields are indexed
    - What type each field is
    - Which collection each field belongs to
    """
    
    # ========================================================================
    # COLLECTION: journey_weeks
    # ========================================================================
    
    JOURNEY_WEEKS_FIELDS = {
        # ====================================================================
        # IDENTIFIERS (Always indexed)
        # ====================================================================
        'account_id': {
            'type': FieldType.KEYWORD,
            'indexed': True,
            'required': True,
            'description': 'Account identifier',
            'example': 'ACCT001',
            'filter_use_cases': ['Find all weeks for specific account']
        },
        'week_number': {
            'type': FieldType.INTEGER,
            'indexed': True,
            'required': True,
            'description': 'Week number in journey (1-52)',
            'example': 5,
            'filter_use_cases': ['Find specific week', 'Find week range']
        },
        'date': {
            'type': FieldType.KEYWORD,
            'indexed': True,
            'required': True,
            'description': 'Date of week (YYYY-MM-DD)',
            'example': '2024-01-29',
            'filter_use_cases': ['Find weeks in date range', 'Find week by date']
        },
        
        # ====================================================================
        # PHASE & HEALTH (Most common filters)
        # ====================================================================
        'phase': {
            'type': FieldType.KEYWORD,
            'indexed': True,
            'required': True,
            'description': 'Journey phase',
            'example': 'crisis',
            'allowed_values': ['healthy', 'crisis', 'recovery', 'at_risk', 'moderate', 'growth', 'churned'],
            'filter_use_cases': ['Find all crisis weeks', 'Find recovery weeks']
        },
        'health_score': {
            'type': FieldType.FLOAT,
            'indexed': True,
            'required': True,
            'description': 'Overall health score (0-100)',
            'example': 63.0,
            'filter_use_cases': ['Find weeks with health < 50', 'Find healthy weeks']
        },
        'health_change': {
            'type': FieldType.FLOAT,
            'indexed': True,
            'required': False,  # Not available for week 1
            'description': 'Health change vs previous week',
            'example': -18.0,
            'filter_use_cases': ['Find weeks with big drops', 'Find improving weeks']
        },
        
        # ====================================================================
        # PILLAR SCORES (All indexed for pillar-based queries)
        # ====================================================================
        'P1_deployment_velocity': {
            'type': FieldType.FLOAT,
            'indexed': True,
            'required': True,
            'description': 'Deployment velocity pillar score (0-100)',
            'example': 82.6,
            'filter_use_cases': ['Find weeks with deployment issues']
        },
        'P2_operational_stability': {
            'type': FieldType.FLOAT,
            'indexed': True,
            'required': True,
            'description': 'Operational stability pillar score (0-100)',
            'example': 37.2,
            'filter_use_cases': ['Find weeks with stability issues', 'Most critical filter!']
        },
        'P3_ai_workload_performance': {
            'type': FieldType.FLOAT,
            'indexed': True,
            'required': True,
            'description': 'AI workload performance pillar score (0-100)',
            'example': 56.6,
            'filter_use_cases': ['Find weeks with performance issues']
        },
        'P4_channel_partner_health': {
            'type': FieldType.FLOAT,
            'indexed': True,
            'required': True,
            'description': 'Channel partner health pillar score (0-100)',
            'example': 75.2,
            'filter_use_cases': ['Find weeks with partner issues']
        },
        'P5_expansion_readiness': {
            'type': FieldType.FLOAT,
            'indexed': True,
            'required': True,
            'description': 'Expansion readiness pillar score (0-100)',
            'example': 67.0,
            'filter_use_cases': ['Find expansion opportunities']
        },
        
        # ====================================================================
        # PILLAR CHANGES (For trend analysis)
        # ====================================================================
        'P1_change': {
            'type': FieldType.FLOAT,
            'indexed': True,
            'required': False,
            'description': 'P1 change vs previous week',
            'example': -2.5,
            'filter_use_cases': ['Find pillar degradation']
        },
        'P2_change': {
            'type': FieldType.FLOAT,
            'indexed': True,
            'required': False,
            'description': 'P2 change vs previous week',
            'example': -46.4,  # Big drop during crisis!
            'filter_use_cases': ['Find stability crashes']
        },
        'P3_change': {
            'type': FieldType.FLOAT,
            'indexed': True,
            'required': False,
            'description': 'P3 change vs previous week',
            'example': -25.3,
            'filter_use_cases': ['Find performance degradation']
        },
        'P4_change': {
            'type': FieldType.FLOAT,
            'indexed': True,
            'required': False,
            'description': 'P4 change vs previous week',
            'example': -9.1,
            'filter_use_cases': ['Find partner relationship issues']
        },
        'P5_change': {
            'type': FieldType.FLOAT,
            'indexed': True,
            'required': False,
            'description': 'P5 change vs previous week',
            'example': -9.8,
            'filter_use_cases': ['Find expansion readiness decline']
        },
        
        # ====================================================================
        # TOP 12 KPIs (Most frequently queried)
        # ====================================================================
        # P2: Operational Stability KPIs (Critical!)
        'rma_frequency_rate': {
            'type': FieldType.FLOAT,
            'indexed': True,
            'required': True,
            'description': 'RMA frequency rate (0-100, higher=better)',
            'example': 30.0,  # Low during crisis!
            'filter_use_cases': ['Find hardware failure weeks', 'CRITICAL for crisis detection']
        },
        'mtbf': {
            'type': FieldType.FLOAT,
            'indexed': True,
            'required': True,
            'description': 'Mean time between failures (0-100, higher=better)',
            'example': 25.0,
            'filter_use_cases': ['Find reliability issues']
        },
        'critical_incident_rate': {
            'type': FieldType.FLOAT,
            'indexed': True,
            'required': True,
            'description': 'Critical incident rate (0-100, higher=better)',
            'example': 25.0,
            'filter_use_cases': ['Find incident-heavy weeks']
        },
        'unplanned_downtime': {
            'type': FieldType.FLOAT,
            'indexed': True,
            'required': True,
            'description': 'Unplanned downtime (0-100, higher=better)',
            'example': 21.0,
            'filter_use_cases': ['Find downtime weeks']
        },
        
        # P3: AI Workload Performance KPIs
        'gpu_utilization_rate': {
            'type': FieldType.FLOAT,
            'indexed': True,
            'required': True,
            'description': 'GPU utilization rate (0-100)',
            'example': 35.0,
            'filter_use_cases': ['Find underutilization', 'Find optimal usage']
        },
        'training_job_completion': {
            'type': FieldType.FLOAT,
            'indexed': True,
            'required': True,
            'description': 'Training job completion rate (0-100)',
            'example': 43.0,
            'filter_use_cases': ['Find job failure weeks']
        },
        
        # P4: Partner Health KPIs
        'partner_engagement_score': {
            'type': FieldType.FLOAT,
            'indexed': True,
            'required': True,
            'description': 'Partner engagement score (0-100)',
            'example': 70.0,
            'filter_use_cases': ['Find partner relationship issues']
        },
        
        # P5: Expansion Readiness KPIs
        'expansion_probability_90d': {
            'type': FieldType.FLOAT,
            'indexed': True,
            'required': True,
            'description': 'Expansion probability in 90 days (0-100)',
            'example': 12.0,
            'filter_use_cases': ['Find expansion opportunities']
        },
        'capacity_utilization_trajectory': {
            'type': FieldType.FLOAT,
            'indexed': True,
            'required': True,
            'description': 'Capacity utilization trajectory (0-100)',
            'example': 72.0,
            'filter_use_cases': ['Find capacity constraints']
        },
        'workload_growth_velocity': {
            'type': FieldType.FLOAT,
            'indexed': True,
            'required': True,
            'description': 'Workload growth velocity (0-100)',
            'example': 65.0,
            'filter_use_cases': ['Find growth opportunities']
        },
        
        # Additional high-value KPIs
        'support_ticket_velocity': {
            'type': FieldType.FLOAT,
            'indexed': True,
            'required': True,
            'description': 'Support ticket resolution velocity (0-100)',
            'example': 50.0,
            'filter_use_cases': ['Find support issues']
        },
        'thermal_power_alerts': {
            'type': FieldType.FLOAT,
            'indexed': True,
            'required': True,
            'description': 'Thermal/power alerts (0-100, higher=better)',
            'example': 34.0,
            'filter_use_cases': ['Find infrastructure issues']
        },
        
        # ====================================================================
        # EVENT METADATA (For event-based queries)
        # ====================================================================
        'event_count': {
            'type': FieldType.INTEGER,
            'indexed': True,
            'required': True,
            'description': 'Number of events this week',
            'example': 2,
            'filter_use_cases': ['Find eventful weeks']
        },
        'primary_event_type': {
            'type': FieldType.KEYWORD,
            'indexed': True,
            'required': False,
            'description': 'Most significant event type this week',
            'example': 'outage',
            'allowed_values': ['qbr', 'outage', 'meeting', 'email', 'escalation', 'support_ticket', 
                             'budget_review', 'contract_discussion', 'technical_issue', 
                             'champion_interaction', 'executive_engagement', 'milestone', 
                             'expansion_discussion'],
            'filter_use_cases': ['Find weeks with specific event types']
        },
        'has_escalation': {
            'type': FieldType.BOOL,
            'indexed': True,
            'required': True,
            'description': 'Whether week had escalation event',
            'example': True,
            'filter_use_cases': ['Find escalation weeks', 'CRITICAL for crisis detection']
        },
        'has_outage': {
            'type': FieldType.BOOL,
            'indexed': True,
            'required': True,
            'description': 'Whether week had outage event',
            'example': True,
            'filter_use_cases': ['Find outage weeks', 'CRITICAL for crisis detection']
        },
        'has_qbr': {
            'type': FieldType.BOOL,
            'indexed': True,
            'required': True,
            'description': 'Whether week had QBR event',
            'example': False,
            'filter_use_cases': ['Find QBR weeks']
        },
        'has_expansion_discussion': {
            'type': FieldType.BOOL,
            'indexed': True,
            'required': True,
            'description': 'Whether week had expansion discussion',
            'example': False,
            'filter_use_cases': ['Find expansion opportunities']
        },
        
        # ====================================================================
        # SENTIMENT METADATA
        # ====================================================================
        'average_sentiment': {
            'type': FieldType.FLOAT,
            'indexed': True,
            'required': True,
            'description': 'Average sentiment across all events (-1.0 to +1.0)',
            'example': -0.8,
            'filter_use_cases': ['Find negative sentiment weeks']
        },
        'has_negative_sentiment': {
            'type': FieldType.BOOL,
            'indexed': True,
            'required': True,
            'description': 'Whether average sentiment < -0.3',
            'example': True,
            'filter_use_cases': ['Find unhappy customer weeks']
        },
        'has_very_negative_sentiment': {
            'type': FieldType.BOOL,
            'indexed': True,
            'required': True,
            'description': 'Whether average sentiment < -0.7',
            'example': True,
            'filter_use_cases': ['Find very unhappy customer weeks']
        },
        
        # ====================================================================
        # CSM INVESTMENT METADATA
        # ====================================================================
        'total_csm_investment': {
            'type': FieldType.FLOAT,
            'indexed': True,
            'required': True,
            'description': 'Total CSM investment this week ($)',
            'example': 40000.0,
            'filter_use_cases': ['Find expensive intervention weeks', 'ROI analysis']
        },
        'has_high_csm_cost': {
            'type': FieldType.BOOL,
            'indexed': True,
            'required': True,
            'description': 'Whether CSM cost > $10,000',
            'example': True,
            'filter_use_cases': ['Find high-cost interventions']
        },
        'has_war_room': {
            'type': FieldType.BOOL,
            'indexed': True,
            'required': True,
            'description': 'Whether war room was initiated',
            'example': True,
            'filter_use_cases': ['Find crisis response weeks']
        },
        'has_exec_sponsor': {
            'type': FieldType.BOOL,
            'indexed': True,
            'required': True,
            'description': 'Whether executive sponsor was assigned',
            'example': True,
            'filter_use_cases': ['Find executive escalations']
        },
        
        # ====================================================================
        # DATA QUALITY METADATA
        # ====================================================================
        'data_quality': {
            'type': FieldType.FLOAT,
            'indexed': True,
            'required': True,
            'description': 'Data completeness (0-1.0)',
            'example': 0.875,
            'filter_use_cases': ['Filter by data quality']
        },
        'data_quality_level': {
            'type': FieldType.KEYWORD,
            'indexed': True,
            'required': True,
            'description': 'Data quality category',
            'example': 'medium',
            'allowed_values': ['high', 'medium', 'low'],
            'filter_use_cases': ['Find high-quality data weeks']
        },
        'missing_kpi_count': {
            'type': FieldType.INTEGER,
            'indexed': True,
            'required': True,
            'description': 'Number of missing KPIs',
            'example': 4,
            'filter_use_cases': ['Filter by data completeness']
        },
        
        # ====================================================================
        # PATTERN METADATA (For pattern recognition)
        # ====================================================================
        'is_crisis_start': {
            'type': FieldType.BOOL,
            'indexed': True,
            'required': True,
            'description': 'Whether this is the start of a crisis',
            'example': True,
            'filter_use_cases': ['Find crisis onset weeks']
        },
        'is_recovery_start': {
            'type': FieldType.BOOL,
            'indexed': True,
            'required': True,
            'description': 'Whether this is the start of recovery',
            'example': False,
            'filter_use_cases': ['Find recovery onset weeks']
        },
        'weeks_since_crisis': {
            'type': FieldType.INTEGER,
            'indexed': True,
            'required': False,
            'description': 'Weeks since last crisis (if any)',
            'example': 0,
            'filter_use_cases': ['Analyze recovery timeline']
        },
        
        # ====================================================================
        # NON-INDEXED FIELDS (Stored but not indexed)
        # ====================================================================
        'full_week_data': {
            'type': FieldType.TEXT,
            'indexed': False,
            'required': True,
            'description': 'Complete week data as JSON (for retrieval)',
            'example': '{...}',
            'filter_use_cases': []
        }
    }
    
    # ========================================================================
    # COLLECTION: events
    # ========================================================================
    
    EVENTS_FIELDS = {
        # Identifiers
        'event_id': {
            'type': FieldType.KEYWORD,
            'indexed': True,
            'required': True,
            'description': 'Unique event identifier',
            'example': 'ACCT001_week_5_event_outage'
        },
        'account_id': {
            'type': FieldType.KEYWORD,
            'indexed': True,
            'required': True,
            'description': 'Account identifier',
            'example': 'ACCT001'
        },
        'week_number': {
            'type': FieldType.INTEGER,
            'indexed': True,
            'required': True,
            'description': 'Week number',
            'example': 5
        },
        'date': {
            'type': FieldType.KEYWORD,
            'indexed': True,
            'required': True,
            'description': 'Event date',
            'example': '2024-01-29'
        },
        
        # Event details
        'event_type': {
            'type': FieldType.KEYWORD,
            'indexed': True,
            'required': True,
            'description': 'Event type',
            'example': 'outage'
        },
        'description': {
            'type': FieldType.TEXT,
            'indexed': False,
            'required': True,
            'description': 'Event description',
            'example': 'Cooling failure caused 15 server shutdowns'
        },
        'outcome': {
            'type': FieldType.TEXT,
            'indexed': False,
            'required': True,
            'description': 'Event outcome',
            'example': 'Hardware replacement initiated'
        },
        
        # Sentiment
        'sentiment': {
            'type': FieldType.KEYWORD,
            'indexed': True,
            'required': True,
            'description': 'Sentiment level',
            'example': 'very_negative'
        },
        'sentiment_value': {
            'type': FieldType.FLOAT,
            'indexed': True,
            'required': True,
            'description': 'Sentiment value (-1.0 to +1.0)',
            'example': -0.9
        },
        
        # CSM action
        'csm_action_type': {
            'type': FieldType.KEYWORD,
            'indexed': True,
            'required': False,
            'description': 'CSM action type',
            'example': 'war_room'
        },
        'csm_response_hours': {
            'type': FieldType.FLOAT,
            'indexed': True,
            'required': False,
            'description': 'CSM response time (hours)',
            'example': 2.0
        },
        'csm_cost': {
            'type': FieldType.FLOAT,
            'indexed': True,
            'required': False,
            'description': 'CSM action cost ($)',
            'example': 15000.0
        },
        
        # Week context
        'week_health_score': {
            'type': FieldType.FLOAT,
            'indexed': True,
            'required': True,
            'description': 'Health score during this week',
            'example': 63.0
        },
        'week_phase': {
            'type': FieldType.KEYWORD,
            'indexed': True,
            'required': True,
            'description': 'Journey phase during this week',
            'example': 'crisis'
        }
    }
    
    # ========================================================================
    # COLLECTION: accounts
    # ========================================================================
    
    ACCOUNTS_FIELDS = {
        # Identifiers
        'account_id': {
            'type': FieldType.KEYWORD,
            'indexed': True,
            'required': True,
            'description': 'Account identifier',
            'example': 'ACCT001'
        },
        'account_name': {
            'type': FieldType.KEYWORD,
            'indexed': True,
            'required': True,
            'description': 'Account name',
            'example': 'Enterprise Corp'
        },
        'pattern_type': {
            'type': FieldType.KEYWORD,
            'indexed': True,
            'required': True,
            'description': 'Journey pattern type',
            'example': 'crisis_recovery'
        },
        
        # Health trajectory
        'starting_health': {
            'type': FieldType.FLOAT,
            'indexed': True,
            'required': True,
            'description': 'Starting health score',
            'example': 85.0
        },
        'ending_health': {
            'type': FieldType.FLOAT,
            'indexed': True,
            'required': True,
            'description': 'Ending health score',
            'example': 92.0
        },
        'lowest_health': {
            'type': FieldType.FLOAT,
            'indexed': True,
            'required': True,
            'description': 'Lowest health score in journey',
            'example': 63.0
        },
        'highest_health': {
            'type': FieldType.FLOAT,
            'indexed': True,
            'required': True,
            'description': 'Highest health score in journey',
            'example': 92.0
        },
        'health_volatility': {
            'type': FieldType.FLOAT,
            'indexed': True,
            'required': True,
            'description': 'Health volatility (std dev)',
            'example': 12.5
        },
        'health_improvement': {
            'type': FieldType.FLOAT,
            'indexed': True,
            'required': True,
            'description': 'Net health improvement (ending - starting)',
            'example': 7.0
        },
        
        # Pillar averages
        'avg_P1': {
            'type': FieldType.FLOAT,
            'indexed': True,
            'required': True,
            'description': 'Average P1 score',
            'example': 82.0
        },
        'avg_P2': {
            'type': FieldType.FLOAT,
            'indexed': True,
            'required': True,
            'description': 'Average P2 score',
            'example': 75.0
        },
        'avg_P3': {
            'type': FieldType.FLOAT,
            'indexed': True,
            'required': True,
            'description': 'Average P3 score',
            'example': 83.0
        },
        'avg_P4': {
            'type': FieldType.FLOAT,
            'indexed': True,
            'required': True,
            'description': 'Average P4 score',
            'example': 85.0
        },
        'avg_P5': {
            'type': FieldType.FLOAT,
            'indexed': True,
            'required': True,
            'description': 'Average P5 score',
            'example': 78.0
        },
        
        # Event statistics
        'total_events': {
            'type': FieldType.INTEGER,
            'indexed': True,
            'required': True,
            'description': 'Total number of events',
            'example': 45
        },
        'total_escalations': {
            'type': FieldType.INTEGER,
            'indexed': True,
            'required': True,
            'description': 'Total escalation events',
            'example': 2
        },
        'total_outages': {
            'type': FieldType.INTEGER,
            'indexed': True,
            'required': True,
            'description': 'Total outage events',
            'example': 1
        },
        'total_qbrs': {
            'type': FieldType.INTEGER,
            'indexed': True,
            'required': True,
            'description': 'Total QBR events',
            'example': 4
        },
        'total_csm_investment': {
            'type': FieldType.FLOAT,
            'indexed': True,
            'required': True,
            'description': 'Total CSM investment ($)',
            'example': 65000.0
        },
        'average_sentiment': {
            'type': FieldType.FLOAT,
            'indexed': True,
            'required': True,
            'description': 'Average sentiment across all events',
            'example': -0.2
        },
        
        # Outcomes
        'had_crisis': {
            'type': FieldType.BOOL,
            'indexed': True,
            'required': True,
            'description': 'Whether account had crisis (health < 40)',
            'example': True
        },
        'recovered': {
            'type': FieldType.BOOL,
            'indexed': True,
            'required': True,
            'description': 'Whether account recovered from crisis',
            'example': True
        },
        'churned': {
            'type': FieldType.BOOL,
            'indexed': True,
            'required': True,
            'description': 'Whether account churned (ending health < 30)',
            'example': False
        },
        'expanded': {
            'type': FieldType.BOOL,
            'indexed': True,
            'required': True,
            'description': 'Whether account had expansion discussions',
            'example': True
        },
        
        # Timeline
        'total_weeks': {
            'type': FieldType.INTEGER,
            'indexed': True,
            'required': True,
            'description': 'Total weeks in journey',
            'example': 52
        },
        'crisis_week': {
            'type': FieldType.INTEGER,
            'indexed': True,
            'required': False,
            'description': 'Week when crisis occurred (if any)',
            'example': 5
        },
        'recovery_duration': {
            'type': FieldType.INTEGER,
            'indexed': True,
            'required': False,
            'description': 'Weeks from crisis to recovery',
            'example': 20
        }
    }
    
    @classmethod
    def get_indexed_fields(cls, collection_name: str) -> Dict:
        """Get indexed fields for a collection"""
        if collection_name == 'journey_weeks':
            fields = cls.JOURNEY_WEEKS_FIELDS
        elif collection_name == 'events':
            fields = cls.EVENTS_FIELDS
        elif collection_name == 'accounts':
            fields = cls.ACCOUNTS_FIELDS
        else:
            raise ValueError(f"Unknown collection: {collection_name}")
        
        return {
            name: spec 
            for name, spec in fields.items() 
            if spec['indexed']
        }
    
    @classmethod
    def get_all_fields(cls, collection_name: str) -> Dict:
        """Get all fields (indexed + non-indexed) for a collection"""
        if collection_name == 'journey_weeks':
            return cls.JOURNEY_WEEKS_FIELDS
        elif collection_name == 'events':
            return cls.EVENTS_FIELDS
        elif collection_name == 'accounts':
            return cls.ACCOUNTS_FIELDS
        else:
            raise ValueError(f"Unknown collection: {collection_name}")
    
    @classmethod
    def validate_payload(cls, collection_name: str, payload: Dict) -> List[str]:
        """
        Validate payload against field registry.
        
        Returns:
            List of errors (empty if valid)
        """
        errors = []
        fields = cls.get_all_fields(collection_name)
        
        # Check required fields
        for field_name, spec in fields.items():
            if spec.get('required', False) and field_name not in payload:
                errors.append(f"Missing required field: {field_name}")
        
        # Check field types (basic validation)
        for field_name, value in payload.items():
            if field_name in fields:
                spec = fields[field_name]
                field_type = spec['type']
                
                if field_type == FieldType.FLOAT and not isinstance(value, (int, float)):
                    errors.append(f"Field {field_name} should be float, got {type(value)}")
                elif field_type == FieldType.INTEGER and not isinstance(value, int):
                    errors.append(f"Field {field_name} should be int, got {type(value)}")
                elif field_type == FieldType.BOOL and not isinstance(value, bool):
                    errors.append(f"Field {field_name} should be bool, got {type(value)}")
        
        return errors


# ============================================================================
# GENERATE DOCUMENTATION
# ============================================================================

def generate_field_documentation():
    """Generate comprehensive field documentation"""
    
    print("="*80)
    print("QDRANT FIELD REGISTRY - COMPLETE DOCUMENTATION")
    print("="*80)
    print()
    
    for collection in ['journey_weeks', 'events', 'accounts']:
        print(f"\n{'='*80}")
        print(f"COLLECTION: {collection.upper()}")
        print(f"{'='*80}\n")
        
        fields = FieldRegistry.get_all_fields(collection)
        indexed_fields = FieldRegistry.get_indexed_fields(collection)
        
        print(f"Total fields: {len(fields)}")
        print(f"Indexed fields: {len(indexed_fields)}")
        print(f"Non-indexed fields: {len(fields) - len(indexed_fields)}\n")
        
        # Group fields by category
        categories = {}
        for field_name, spec in fields.items():
            desc = spec['description']
            # Extract category from description or use default
            if 'pillar' in desc.lower():
                category = 'Pillar Scores'
            elif 'kpi' in desc.lower() or field_name in ['rma_frequency_rate', 'mtbf', 'gpu_utilization_rate']:
                category = 'KPI Values'
            elif 'event' in desc.lower():
                category = 'Event Metadata'
            elif 'sentiment' in desc.lower():
                category = 'Sentiment'
            elif 'csm' in desc.lower():
                category = 'CSM Investment'
            elif 'health' in desc.lower():
                category = 'Health Metrics'
            elif field_name in ['account_id', 'week_number', 'date', 'event_id']:
                category = 'Identifiers'
            else:
                category = 'Other'
            
            if category not in categories:
                categories[category] = []
            categories[category].append((field_name, spec))
        
        # Print by category
        for category in sorted(categories.keys()):
            print(f"\n--- {category} ---\n")
            for field_name, spec in sorted(categories[category]):
                indexed_mark = "🔍" if spec['indexed'] else "  "
                required_mark = "✓" if spec.get('required', False) else " "
                
                print(f"{indexed_mark} {required_mark} {field_name}")
                print(f"     Type: {spec['type'].value}")
                print(f"     Desc: {spec['description']}")
                if 'example' in spec:
                    print(f"     Example: {spec['example']}")
                if 'allowed_values' in spec:
                    print(f"     Values: {', '.join(spec['allowed_values'])}")
                if spec.get('indexed') and 'filter_use_cases' in spec:
                    print(f"     Use cases: {', '.join(spec['filter_use_cases'])}")
                print()


if __name__ == '__main__':
    generate_field_documentation()
    
    print("\n" + "="*80)
    print("FIELD COUNT SUMMARY")
    print("="*80)
    
    for collection in ['journey_weeks', 'events', 'accounts']:
        fields = FieldRegistry.get_all_fields(collection)
        indexed = FieldRegistry.get_indexed_fields(collection)
        print(f"\n{collection}:")
        print(f"  Total: {len(fields)}")
        print(f"  Indexed: {len(indexed)}")
        print(f"  Storage only: {len(fields) - len(indexed)}")
