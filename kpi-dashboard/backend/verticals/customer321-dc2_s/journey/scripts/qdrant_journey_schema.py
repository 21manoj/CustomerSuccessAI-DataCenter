#!/usr/bin/env python3
"""
Qdrant Schema & Integration for Journey Data
=============================================

Defines Qdrant collections for:
1. journey_weeks - Week-by-week journey data with KPIs + Events
2. events - Individual events (optional denormalization)
3. accounts - Account-level summaries

Key design decisions:
- Vector embeddings of week summaries for semantic search
- Extensive payload indexing for fast filtering
- Optimized for common query patterns
"""

from typing import List, Dict, Optional
from dataclasses import dataclass
from qdrant_client import QdrantClient
from qdrant_client.models import (
    VectorParams, Distance, PointStruct,
    PayloadSchemaType, PayloadIndexParams,
    FieldCondition, Filter, Range, MatchValue
)
import json


# ============================================================================
# QDRANT SCHEMA DEFINITIONS
# ============================================================================

# Vector dimensions (adjust based on embedding model)
VECTOR_DIMENSION = 768  # OpenAI text-embedding-ada-002 or similar
# VECTOR_DIMENSION = 384  # sentence-transformers/all-MiniLM-L6-v2

QDRANT_COLLECTIONS = {
    
    # ========================================================================
    # Collection 1: journey_weeks
    # ========================================================================
    # Main collection for week-by-week journey data
    # Each point = one week of one account's journey
    #
    # Vector: Embedding of week summary (events + KPI changes + sentiment)
    # Use cases:
    #   - "Find similar crisis situations"
    #   - "Find weeks with similar recovery patterns"
    #   - "Find accounts in similar phases"
    # ========================================================================
    
    'journey_weeks': {
        'description': 'Week-by-week journey data with KPIs, pillars, and events',
        'vector_params': VectorParams(
            size=VECTOR_DIMENSION,
            distance=Distance.COSINE
        ),
        
        # Indexed fields for fast filtering
        'indexed_fields': {
            # Identifiers
            'account_id': PayloadSchemaType.KEYWORD,
            'week_number': PayloadSchemaType.INTEGER,
            'date': PayloadSchemaType.KEYWORD,
            
            # Phase & Health (most common filters)
            'phase': PayloadSchemaType.KEYWORD,  # healthy, crisis, recovery, etc.
            'health_score': PayloadSchemaType.FLOAT,
            'health_change': PayloadSchemaType.FLOAT,
            
            # Pillar scores (for pillar-based queries)
            'P1_deployment_velocity': PayloadSchemaType.FLOAT,
            'P2_operational_stability': PayloadSchemaType.FLOAT,
            'P3_ai_workload_performance': PayloadSchemaType.FLOAT,
            'P4_channel_partner_health': PayloadSchemaType.FLOAT,
            'P5_expansion_readiness': PayloadSchemaType.FLOAT,
            
            # Top KPIs (most frequently queried)
            'rma_frequency_rate': PayloadSchemaType.FLOAT,
            'mtbf': PayloadSchemaType.FLOAT,
            'gpu_utilization_rate': PayloadSchemaType.FLOAT,
            'training_job_completion': PayloadSchemaType.FLOAT,
            'critical_incident_rate': PayloadSchemaType.FLOAT,
            'unplanned_downtime': PayloadSchemaType.FLOAT,
            'partner_engagement_score': PayloadSchemaType.FLOAT,
            'expansion_probability_90d': PayloadSchemaType.FLOAT,
            
            # Event metadata
            'event_count': PayloadSchemaType.INTEGER,
            'primary_event_type': PayloadSchemaType.KEYWORD,
            'has_escalation': PayloadSchemaType.BOOL,
            'has_outage': PayloadSchemaType.BOOL,
            
            # Sentiment
            'average_sentiment': PayloadSchemaType.FLOAT,
            'has_negative_sentiment': PayloadSchemaType.BOOL,
            
            # CSM investment
            'total_csm_investment': PayloadSchemaType.FLOAT,
            'has_high_csm_cost': PayloadSchemaType.BOOL,
            
            # Data quality
            'data_quality': PayloadSchemaType.FLOAT,
            'data_quality_level': PayloadSchemaType.KEYWORD  # high, medium, low
        },
        
        # Example queries this enables:
        'example_queries': [
            "Find all crisis weeks (phase=crisis)",
            "Find weeks with health drop >20 points (health_change < -20)",
            "Find weeks with RMA issues (rma_frequency_rate < 50)",
            "Find weeks with high CSM investment (total_csm_investment > 10000)",
            "Find similar crisis recovery patterns (vector search)",
            "Find weeks with escalations (has_escalation=true)",
            "Find weeks with negative sentiment (average_sentiment < -0.3)"
        ]
    },
    
    # ========================================================================
    # Collection 2: events
    # ========================================================================
    # Individual events (denormalized from journey_weeks)
    # Each point = one event
    #
    # Vector: Embedding of event description + outcome
    # Use cases:
    #   - "Find similar outage events"
    #   - "Find events with similar CSM responses"
    #   - "Analyze event patterns across accounts"
    # ========================================================================
    
    'events': {
        'description': 'Individual journey events with descriptions and outcomes',
        'vector_params': VectorParams(
            size=VECTOR_DIMENSION,
            distance=Distance.COSINE
        ),
        
        'indexed_fields': {
            # Identifiers
            'account_id': PayloadSchemaType.KEYWORD,
            'week_number': PayloadSchemaType.INTEGER,
            'date': PayloadSchemaType.KEYWORD,
            
            # Event details
            'event_type': PayloadSchemaType.KEYWORD,  # outage, escalation, qbr, etc.
            'sentiment': PayloadSchemaType.KEYWORD,  # very_positive, positive, etc.
            'sentiment_value': PayloadSchemaType.FLOAT,
            
            # CSM action
            'csm_action_type': PayloadSchemaType.KEYWORD,
            'csm_response_hours': PayloadSchemaType.FLOAT,
            'csm_cost': PayloadSchemaType.FLOAT,
            
            # Context
            'week_health_score': PayloadSchemaType.FLOAT,
            'week_phase': PayloadSchemaType.KEYWORD
        },
        
        'example_queries': [
            "Find all outage events (event_type=outage)",
            "Find events with very negative sentiment (sentiment=very_negative)",
            "Find expensive CSM responses (csm_cost > 15000)",
            "Find similar event descriptions (vector search)",
            "Find fast CSM responses (csm_response_hours < 4)",
            "Find events during crisis (week_phase=crisis)"
        ]
    },
    
    # ========================================================================
    # Collection 3: accounts
    # ========================================================================
    # Account-level journey summaries
    # Each point = one account's complete journey
    #
    # Vector: Embedding of account journey summary
    # Use cases:
    #   - "Find accounts with similar journeys"
    #   - "Find accounts with similar outcomes"
    #   - "Benchmark against similar accounts"
    # ========================================================================
    
    'accounts': {
        'description': 'Account-level journey summaries',
        'vector_params': VectorParams(
            size=VECTOR_DIMENSION,
            distance=Distance.COSINE
        ),
        
        'indexed_fields': {
            # Identifiers
            'account_id': PayloadSchemaType.KEYWORD,
            'account_name': PayloadSchemaType.KEYWORD,
            'pattern_type': PayloadSchemaType.KEYWORD,  # crisis_recovery, proactive_growth, etc.
            
            # Health trajectory
            'starting_health': PayloadSchemaType.FLOAT,
            'ending_health': PayloadSchemaType.FLOAT,
            'lowest_health': PayloadSchemaType.FLOAT,
            'highest_health': PayloadSchemaType.FLOAT,
            'health_volatility': PayloadSchemaType.FLOAT,  # Standard deviation
            
            # Pillar averages
            'avg_P1': PayloadSchemaType.FLOAT,
            'avg_P2': PayloadSchemaType.FLOAT,
            'avg_P3': PayloadSchemaType.FLOAT,
            'avg_P4': PayloadSchemaType.FLOAT,
            'avg_P5': PayloadSchemaType.FLOAT,
            
            # Event statistics
            'total_events': PayloadSchemaType.INTEGER,
            'total_escalations': PayloadSchemaType.INTEGER,
            'total_outages': PayloadSchemaType.INTEGER,
            'total_csm_investment': PayloadSchemaType.FLOAT,
            'average_sentiment': PayloadSchemaType.FLOAT,
            
            # Outcome
            'had_crisis': PayloadSchemaType.BOOL,
            'recovered': PayloadSchemaType.BOOL,
            'churned': PayloadSchemaType.BOOL,
            'expanded': PayloadSchemaType.BOOL
        },
        
        'example_queries': [
            "Find accounts with crisis recovery pattern (pattern_type=crisis_recovery)",
            "Find accounts that recovered from crisis (had_crisis=true AND recovered=true)",
            "Find accounts with high CSM investment (total_csm_investment > 50000)",
            "Find similar account journeys (vector search)",
            "Find accounts with similar ending health (ending_health 80-90)",
            "Find accounts with many escalations (total_escalations > 3)"
        ]
    }
}


# ============================================================================
# QDRANT CLIENT & SETUP
# ============================================================================

class QdrantJourneyStorage:
    """
    Qdrant storage manager for journey data
    
    Handles:
    - Collection creation with proper schema
    - Data upload with vector embeddings
    - Query interface for common patterns
    """
    
    def __init__(self, qdrant_url: str = "http://localhost:6333"):
        """
        Initialize Qdrant client
        
        Args:
            qdrant_url: Qdrant server URL
        """
        self.client = QdrantClient(url=qdrant_url)
        print(f"✅ Connected to Qdrant at {qdrant_url}")
    
    def create_collections(self):
        """Create all journey collections with proper schema"""
        
        for collection_name, config in QDRANT_COLLECTIONS.items():
            print(f"\n📦 Creating collection: {collection_name}")
            print(f"   {config['description']}")
            
            # Create collection
            self.client.recreate_collection(
                collection_name=collection_name,
                vectors_config=config['vector_params']
            )
            
            # Create payload indexes
            for field_name, field_type in config['indexed_fields'].items():
                self.client.create_payload_index(
                    collection_name=collection_name,
                    field_name=field_name,
                    field_schema=field_type
                )
                print(f"   ✅ Indexed: {field_name} ({field_type})")
        
        print(f"\n✅ All collections created!")
    
    def upload_journey(
        self,
        journey_data: Dict,
        embedding_function: callable
    ):
        """
        Upload journey to Qdrant
        
        Args:
            journey_data: Journey dictionary from EnhancedJourney.to_dict()
            embedding_function: Function to generate embeddings (text -> vector)
        """
        
        account_id = journey_data['account_id']
        print(f"\n📤 Uploading journey for {account_id}...")
        
        # ====================================================================
        # Upload to journey_weeks collection
        # ====================================================================
        
        week_points = []
        event_points = []
        
        for week_data in journey_data['weekly_data']:
            # Generate embedding for this week
            week_text = self._create_week_embedding_text(week_data)
            week_vector = embedding_function(week_text)
            
            # Create point for journey_weeks collection
            point_id = f"{account_id}_week_{week_data['week_number']}"
            
            week_points.append(PointStruct(
                id=point_id,
                vector=week_vector,
                payload=week_data  # Use get_qdrant_payload() in real implementation
            ))
            
            # ================================================================
            # Extract events for events collection
            # ================================================================
            
            for event in week_data.get('events', []):
                # Generate embedding for this event
                event_text = f"{event['description']} {event['outcome']}"
                event_vector = embedding_function(event_text)
                
                # Create point for events collection
                event_id = f"{account_id}_week_{week_data['week_number']}_event_{event['event_type']}"
                
                event_points.append(PointStruct(
                    id=event_id,
                    vector=event_vector,
                    payload={
                        'account_id': account_id,
                        'week_number': week_data['week_number'],
                        'date': week_data['date'],
                        'event_type': event['event_type'],
                        'description': event['description'],
                        'sentiment': event['sentiment'],
                        'sentiment_value': event['sentiment_value'],
                        'csm_action_type': event['csm_action']['action_type'] if event['csm_action'] else None,
                        'csm_response_hours': event['csm_action']['response_time_hours'] if event['csm_action'] else None,
                        'csm_cost': event['csm_action']['cost_estimate'] if event['csm_action'] else None,
                        'outcome': event['outcome'],
                        'week_health_score': week_data['health_score'],
                        'week_phase': week_data['phase']
                    }
                ))
        
        # Upload weeks
        if week_points:
            self.client.upsert(
                collection_name='journey_weeks',
                points=week_points
            )
            print(f"   ✅ Uploaded {len(week_points)} weeks to journey_weeks")
        
        # Upload events
        if event_points:
            self.client.upsert(
                collection_name='events',
                points=event_points
            )
            print(f"   ✅ Uploaded {len(event_points)} events to events")
        
        # ====================================================================
        # Upload to accounts collection
        # ====================================================================
        
        # Generate embedding for account summary
        account_text = self._create_account_embedding_text(journey_data)
        account_vector = embedding_function(account_text)
        
        # Calculate additional metrics
        health_scores = [w['health_score'] for w in journey_data['weekly_data']]
        health_volatility = self._calculate_std_dev(health_scores)
        
        account_payload = {
            'account_id': account_id,
            'account_name': journey_data['account_name'],
            'pattern_type': journey_data['pattern_type'],
            'starting_health': journey_data['starting_health'],
            'ending_health': journey_data['ending_health'],
            'lowest_health': journey_data['lowest_health'],
            'highest_health': journey_data['highest_health'],
            'health_volatility': health_volatility,
            'avg_P1': journey_data['avg_pillar_scores']['P1_deployment_velocity'],
            'avg_P2': journey_data['avg_pillar_scores']['P2_operational_stability'],
            'avg_P3': journey_data['avg_pillar_scores']['P3_ai_workload_performance'],
            'avg_P4': journey_data['avg_pillar_scores']['P4_channel_partner_health'],
            'avg_P5': journey_data['avg_pillar_scores']['P5_expansion_readiness'],
            'total_events': journey_data['total_events'],
            'total_escalations': journey_data['event_distribution'].get('escalation', 0),
            'total_outages': journey_data['event_distribution'].get('outage', 0),
            'total_csm_investment': journey_data['total_csm_investment'],
            'average_sentiment': journey_data['average_sentiment'],
            'had_crisis': journey_data['lowest_health'] < 40,
            'recovered': journey_data['ending_health'] > journey_data['lowest_health'] + 20,
            'churned': journey_data['ending_health'] < 30,
            'expanded': journey_data['event_distribution'].get('expansion_discussion', 0) > 0
        }
        
        self.client.upsert(
            collection_name='accounts',
            points=[PointStruct(
                id=account_id,
                vector=account_vector,
                payload=account_payload
            )]
        )
        print(f"   ✅ Uploaded account summary to accounts")
    
    def _create_week_embedding_text(self, week_data: Dict) -> str:
        """Create text for week embedding"""
        parts = [
            f"Week {week_data['week_number']}",
            f"Phase: {week_data['phase']}",
            f"Health: {week_data['health_score']:.1f}",
            f"P2 Stability: {week_data.get('P2_operational_stability', 0):.1f}",
            f"P3 Performance: {week_data.get('P3_ai_workload_performance', 0):.1f}"
        ]
        
        # Add event descriptions
        for event in week_data.get('events', []):
            parts.append(f"{event['event_type']}: {event['description']}")
        
        return " | ".join(parts)
    
    def _create_account_embedding_text(self, journey_data: Dict) -> str:
        """Create text for account embedding"""
        return (
            f"Account journey: {journey_data['pattern_type']} pattern. "
            f"Health: {journey_data['starting_health']:.1f} to {journey_data['ending_health']:.1f}. "
            f"Total events: {journey_data['total_events']}. "
            f"Average sentiment: {journey_data['average_sentiment']:.2f}."
        )
    
    def _calculate_std_dev(self, values: List[float]) -> float:
        """Calculate standard deviation"""
        mean = sum(values) / len(values)
        variance = sum((x - mean) ** 2 for x in values) / len(values)
        return variance ** 0.5
    
    # ========================================================================
    # QUERY METHODS
    # ========================================================================
    
    def find_similar_crisis_weeks(
        self,
        reference_week_id: str,
        limit: int = 10
    ):
        """Find weeks with similar crisis patterns"""
        return self.client.search(
            collection_name='journey_weeks',
            query_vector=self.client.retrieve(
                collection_name='journey_weeks',
                ids=[reference_week_id]
            )[0].vector,
            query_filter=Filter(
                must=[FieldCondition(key='phase', match=MatchValue(value='crisis'))]
            ),
            limit=limit
        )
    
    def find_weeks_with_health_drop(
        self,
        min_drop: float = -20,
        limit: int = 50
    ):
        """Find weeks with significant health drops"""
        return self.client.scroll(
            collection_name='journey_weeks',
            scroll_filter=Filter(
                must=[FieldCondition(
                    key='health_change',
                    range=Range(lt=min_drop)
                )]
            ),
            limit=limit
        )
    
    def find_high_csm_investment_weeks(
        self,
        min_investment: float = 10000,
        limit: int = 50
    ):
        """Find weeks with high CSM investment"""
        return self.client.scroll(
            collection_name='journey_weeks',
            scroll_filter=Filter(
                must=[FieldCondition(key='has_high_csm_cost', match=MatchValue(value=True))]
            ),
            limit=limit
        )


# ============================================================================
# EXAMPLE USAGE
# ============================================================================

if __name__ == '__main__':
    print("="*70)
    print("QDRANT SCHEMA FOR JOURNEY DATA")
    print("="*70)
    print()
    
    # Print schema summary
    for collection_name, config in QDRANT_COLLECTIONS.items():
        print(f"\n📦 {collection_name.upper()}")
        print(f"   {config['description']}")
        print(f"   Vector dimension: {config['vector_params'].size}")
        print(f"   Indexed fields: {len(config['indexed_fields'])}")
        print(f"\n   Example queries:")
        for query in config['example_queries']:
            print(f"     • {query}")
    
    print("\n" + "="*70)
    print("FIELD REFERENCE")
    print("="*70)
    
    print("\n🔍 journey_weeks collection:")
    for field_name in QDRANT_COLLECTIONS['journey_weeks']['indexed_fields'].keys():
        print(f"   • {field_name}")
    
    print("\n✅ Schema defined and ready for implementation!")
