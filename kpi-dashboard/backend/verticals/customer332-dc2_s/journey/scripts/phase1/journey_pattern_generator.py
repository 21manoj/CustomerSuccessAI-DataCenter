#!/usr/bin/env python3
"""
Journey Pattern Generator - Phase 1: Foundation
===============================================

Generates realistic customer journey data based on archetype patterns.
Focuses on health trajectory simulation and event generation.

Based on: CX_JOURNEY_MAPS_MONTHWISE.md
"""

import json
import random
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum


# ============================================================================
# ENUMS & CONSTANTS
# ============================================================================

class JourneyPhase(Enum):
    """Journey phases that dictate event types and patterns"""
    HEALTHY = "healthy"
    CRISIS = "crisis"
    RECOVERY = "recovery"
    AT_RISK = "at_risk"
    MODERATE = "moderate"
    GROWTH = "growth"
    CHURNED = "churned"


class EventType(Enum):
    """Types of events that can occur"""
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
    """Sentiment levels for events"""
    VERY_POSITIVE = "very_positive"  # 😊
    POSITIVE = "positive"            # 🙂
    NEUTRAL = "neutral"              # 😐
    NEGATIVE = "negative"            # 😟
    VERY_NEGATIVE = "very_negative"  # 😡


class CSMActionType(Enum):
    """Types of CSM interventions"""
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
    PERFORMANCE_REPORTING = "performance_reporting"
    PROACTIVE_TRAINING = "proactive_training"
    NEW_USE_CASE_SUPPORT = "new_use_case_support"
    RENEWAL_PLANNING = "renewal_planning"
    RENEWAL_EXECUTION = "renewal_execution"
    EXPANSION_ENABLEMENT = "expansion_enablement"
    STRATEGIC_PLANNING = "strategic_planning"
    MARKETING_COLLABORATION = "marketing_collaboration"
    MULTI_YEAR_PLANNING = "multi_year_planning"
    DEAL_STRUCTURING = "deal_structuring"
    CONTRACT_EXECUTION = "contract_execution"
    NO_ACTION = "no_action"


# ============================================================================
# DATA MODELS
# ============================================================================

@dataclass
class EventTemplate:
    """Template for generating events"""
    event_type: EventType
    sentiment: SentimentLevel
    sentiment_value: float  # -1.0 to +1.0
    description: str
    health_impact: float  # Expected change in health score
    probability: float  # Chance this event occurs in this phase
    
    def to_dict(self) -> Dict:
        return {
            'event_type': self.event_type.value,
            'sentiment': self.sentiment.value,
            'sentiment_value': self.sentiment_value,
            'description': self.description,
            'health_impact': self.health_impact,
            'probability': self.probability
        }


@dataclass
class CSMAction:
    """CSM intervention action"""
    action_type: CSMActionType
    description: str
    response_time_hours: float  # How quickly CSM responded
    cost_estimate: float  # Investment in this action
    
    def to_dict(self) -> Dict:
        return {
            'action_type': self.action_type.value,
            'description': self.description,
            'response_time_hours': self.response_time_hours,
            'cost_estimate': self.cost_estimate
        }


@dataclass
class JourneyEvent:
    """A single event in the customer journey"""
    week_number: int
    date: str
    phase: JourneyPhase
    event_type: EventType
    description: str
    sentiment: SentimentLevel
    sentiment_value: float
    health_score_before: float
    health_score_after: float
    csm_action: Optional[CSMAction]
    outcome: str
    
    def to_dict(self) -> Dict:
        result = {
            'week_number': self.week_number,
            'date': self.date,
            'phase': self.phase.value,
            'event_type': self.event_type.value,
            'description': self.description,
            'sentiment': self.sentiment.value,
            'sentiment_value': self.sentiment_value,
            'health_score_before': round(self.health_score_before, 2),
            'health_score_after': round(self.health_score_after, 2),
            'outcome': self.outcome
        }
        if self.csm_action:
            result['csm_action'] = self.csm_action.to_dict()
        return result


@dataclass
class AccountJourney:
    """Complete journey for an account"""
    account_id: str
    account_name: str
    pattern_type: str
    start_date: str
    end_date: str
    starting_health: float
    ending_health: float
    lowest_health: float
    highest_health: float
    total_weeks: int
    events: List[JourneyEvent]
    summary: Dict
    
    def to_dict(self) -> Dict:
        return {
            'account_id': self.account_id,
            'account_name': self.account_name,
            'pattern_type': self.pattern_type,
            'start_date': self.start_date,
            'end_date': self.end_date,
            'starting_health': round(self.starting_health, 2),
            'ending_health': round(self.ending_health, 2),
            'lowest_health': round(self.lowest_health, 2),
            'highest_health': round(self.highest_health, 2),
            'total_weeks': self.total_weeks,
            'events': [e.to_dict() for e in self.events],
            'summary': self.summary
        }


# ============================================================================
# EVENT TEMPLATE LIBRARY
# ============================================================================

class EventTemplateLibrary:
    """Library of event templates organized by journey phase"""
    
    def __init__(self):
        self.templates = self._build_template_library()
    
    def _build_template_library(self) -> Dict[JourneyPhase, List[EventTemplate]]:
        """Build comprehensive event template library"""
        
        return {
            # ================================================================
            # HEALTHY PHASE
            # ================================================================
            JourneyPhase.HEALTHY: [
                EventTemplate(
                    EventType.QBR,
                    SentimentLevel.VERY_POSITIVE,
                    0.9,
                    "Outstanding QBR - All metrics exceeding targets",
                    2.0,
                    0.8
                ),
                EventTemplate(
                    EventType.CHAMPION_INTERACTION,
                    SentimentLevel.VERY_POSITIVE,
                    0.85,
                    "Champion promoted to CTO - Strong executive buy-in",
                    3.0,
                    0.3
                ),
                EventTemplate(
                    EventType.EXPANSION_DISCUSSION,
                    SentimentLevel.VERY_POSITIVE,
                    0.9,
                    "Board approval for expansion - Budget allocated",
                    2.5,
                    0.4
                ),
                EventTemplate(
                    EventType.MEETING,
                    SentimentLevel.POSITIVE,
                    0.7,
                    "Regular check-in - All systems performing well",
                    0.5,
                    0.9
                ),
                EventTemplate(
                    EventType.MILESTONE,
                    SentimentLevel.VERY_POSITIVE,
                    0.95,
                    "Reference customer agreement - Willing to advocate",
                    2.0,
                    0.2
                ),
            ],
            
            # ================================================================
            # CRISIS PHASE
            # ================================================================
            JourneyPhase.CRISIS: [
                EventTemplate(
                    EventType.OUTAGE,
                    SentimentLevel.VERY_NEGATIVE,
                    -0.95,
                    "14-HOUR OUTAGE - Complete production stoppage",
                    -55.0,
                    0.9  # High probability this is THE crisis
                ),
                EventTemplate(
                    EventType.ESCALATION,
                    SentimentLevel.VERY_NEGATIVE,
                    -0.9,
                    "CEO threatening to change vendors - Trust destroyed",
                    -5.0,
                    0.8
                ),
                EventTemplate(
                    EventType.EXECUTIVE_ENGAGEMENT,
                    SentimentLevel.VERY_NEGATIVE,
                    -0.85,
                    "Board questioning infrastructure decision",
                    -3.0,
                    0.6
                ),
                EventTemplate(
                    EventType.SUPPORT_TICKET,
                    SentimentLevel.VERY_NEGATIVE,
                    -0.9,
                    "Critical support ticket - Production loss quantified",
                    -2.0,
                    0.9
                ),
                EventTemplate(
                    EventType.BUDGET_REVIEW,
                    SentimentLevel.VERY_NEGATIVE,
                    -0.85,
                    "Emergency budget meeting - Damages being calculated",
                    -4.0,
                    0.7
                ),
            ],
            
            # ================================================================
            # RECOVERY PHASE (Early)
            # ================================================================
            JourneyPhase.RECOVERY: [
                EventTemplate(
                    EventType.MEETING,
                    SentimentLevel.NEGATIVE,
                    -0.5,
                    "Competitor (AWS) being evaluated - Active shopping",
                    -2.0,
                    0.7
                ),
                EventTemplate(
                    EventType.TECHNICAL_ISSUE,
                    SentimentLevel.NEUTRAL,
                    0.1,
                    "Firmware patch deployed - First step to stability",
                    5.0,
                    0.9
                ),
                EventTemplate(
                    EventType.MILESTONE,
                    SentimentLevel.NEUTRAL,
                    0.3,
                    "30-day uptime milestone achieved - Trust rebuilding begins",
                    8.0,
                    0.8
                ),
                EventTemplate(
                    EventType.MEETING,
                    SentimentLevel.NEGATIVE,
                    -0.4,
                    "CFO calculating damages - Still very fragile relationship",
                    -1.0,
                    0.6
                ),
                EventTemplate(
                    EventType.SUPPORT_TICKET,
                    SentimentLevel.NEUTRAL,
                    0.2,
                    "Enhanced monitoring showing improved metrics",
                    3.0,
                    0.7
                ),
            ],
            
            # ================================================================
            # AT-RISK PHASE
            # ================================================================
            JourneyPhase.AT_RISK: [
                EventTemplate(
                    EventType.BUDGET_REVIEW,
                    SentimentLevel.NEGATIVE,
                    -0.6,
                    "CFO: 'Should we switch providers?' - Budget under review",
                    -3.0,
                    0.8
                ),
                EventTemplate(
                    EventType.CONTRACT_DISCUSSION,
                    SentimentLevel.NEGATIVE,
                    -0.5,
                    "Budget review: $2.1M contract questioned by finance",
                    -2.0,
                    0.7
                ),
                EventTemplate(
                    EventType.MILESTONE,
                    SentimentLevel.NEUTRAL,
                    0.2,
                    "60-day uptime milestone - Slow progress, cautious optimism",
                    5.0,
                    0.6
                ),
                EventTemplate(
                    EventType.CONTRACT_DISCUSSION,
                    SentimentLevel.POSITIVE,
                    0.5,
                    "Pricing compromise reached - 12% discount negotiated",
                    7.0,
                    0.8
                ),
            ],
            
            # ================================================================
            # MODERATE PHASE (Stabilizing)
            # ================================================================
            JourneyPhase.MODERATE: [
                EventTemplate(
                    EventType.MILESTONE,
                    SentimentLevel.POSITIVE,
                    0.6,
                    "90-day uptime milestone - Confidence returning",
                    8.0,
                    0.9
                ),
                EventTemplate(
                    EventType.MEETING,
                    SentimentLevel.POSITIVE,
                    0.5,
                    "Board: 'Cautiously positive' - Sentiment improving",
                    5.0,
                    0.7
                ),
                EventTemplate(
                    EventType.TECHNICAL_ISSUE,
                    SentimentLevel.POSITIVE,
                    0.6,
                    "Quality metrics: 42% improvement shown",
                    6.0,
                    0.8
                ),
                EventTemplate(
                    EventType.MEETING,
                    SentimentLevel.NEUTRAL,
                    0.2,
                    "Expansion still frozen - Wait and see approach",
                    0.0,
                    0.5
                ),
                EventTemplate(
                    EventType.CHAMPION_INTERACTION,
                    SentimentLevel.POSITIVE,
                    0.7,
                    "New champion emerges (VP Operations) - Fresh perspective",
                    8.0,
                    0.4
                ),
            ],
            
            # ================================================================
            # GROWTH PHASE
            # ================================================================
            JourneyPhase.GROWTH: [
                EventTemplate(
                    EventType.EXPANSION_DISCUSSION,
                    SentimentLevel.VERY_POSITIVE,
                    0.85,
                    "Robotics expansion interest - New use cases identified",
                    5.0,
                    0.7
                ),
                EventTemplate(
                    EventType.CONTRACT_DISCUSSION,
                    SentimentLevel.VERY_POSITIVE,
                    0.9,
                    "Early renewal discussion - Multi-year interest expressed",
                    8.0,
                    0.8
                ),
                EventTemplate(
                    EventType.MILESTONE,
                    SentimentLevel.VERY_POSITIVE,
                    0.95,
                    "150-day uptime milestone - Complete trust restored",
                    3.0,
                    0.9
                ),
                EventTemplate(
                    EventType.CONTRACT_DISCUSSION,
                    SentimentLevel.VERY_POSITIVE,
                    0.95,
                    "2-year renewal signed - $2.25M/yr commitment",
                    5.0,
                    0.6
                ),
                EventTemplate(
                    EventType.CHAMPION_INTERACTION,
                    SentimentLevel.VERY_POSITIVE,
                    0.9,
                    "Offered to be reference customer - Full advocacy",
                    3.0,
                    0.5
                ),
                EventTemplate(
                    EventType.MILESTONE,
                    SentimentLevel.VERY_POSITIVE,
                    0.95,
                    "200-day uptime milestone - Exceptional performance",
                    2.0,
                    0.6
                ),
                EventTemplate(
                    EventType.EXPANSION_DISCUSSION,
                    SentimentLevel.VERY_POSITIVE,
                    0.9,
                    "2025 budget approved ($800K) - Major expansion planned",
                    5.0,
                    0.4
                ),
            ],
        }
    
    def get_templates_for_phase(self, phase: JourneyPhase) -> List[EventTemplate]:
        """Get all templates for a specific phase"""
        return self.templates.get(phase, [])
    
    def get_random_event(self, phase: JourneyPhase) -> Optional[EventTemplate]:
        """Get a random event based on phase and probabilities"""
        templates = self.get_templates_for_phase(phase)
        if not templates:
            return None
        
        # Weight by probability
        weights = [t.probability for t in templates]
        return random.choices(templates, weights=weights, k=1)[0]


# ============================================================================
# HEALTH TRAJECTORY SIMULATOR
# ============================================================================

class HealthTrajectorySimulator:
    """Simulates health score progression over time"""
    
    def __init__(self, pattern_config: Dict):
        """
        Initialize with pattern configuration
        
        pattern_config example:
        {
            'start_health': 90,
            'crisis_week': 5,
            'crisis_depth': -55,
            'recovery_weeks': 20,
            'end_health': 93,
            'volatility': 0.15
        }
        """
        self.config = pattern_config
        self.validate_config()
    
    def validate_config(self):
        """Validate configuration parameters"""
        required = ['start_health', 'crisis_week', 'crisis_depth', 
                   'recovery_weeks', 'end_health']
        for key in required:
            if key not in self.config:
                raise ValueError(f"Missing required config: {key}")
    
    def simulate_trajectory(self, total_weeks: int) -> List[Tuple[int, float, JourneyPhase]]:
        """
        Simulate health score trajectory
        
        Returns: List of (week_number, health_score, phase) tuples
        """
        trajectory = []
        
        # Extract config
        start_health = self.config['start_health']
        crisis_week = self.config['crisis_week']
        crisis_depth = self.config['crisis_depth']
        recovery_weeks = self.config['recovery_weeks']
        end_health = self.config['end_health']
        volatility = self.config.get('volatility', 0.1)
        
        current_health = start_health
        
        for week in range(1, total_weeks + 1):
            # Determine phase and health change
            if week < crisis_week:
                # Pre-crisis: Healthy and stable
                phase = JourneyPhase.HEALTHY
                weekly_change = random.uniform(-1, 1) * volatility
                
            elif week == crisis_week:
                # Crisis week: Dramatic drop
                phase = JourneyPhase.CRISIS
                weekly_change = crisis_depth
                
            elif week < crisis_week + 4:
                # Immediate post-crisis: Still critical, slow recovery
                phase = JourneyPhase.CRISIS
                weekly_change = abs(crisis_depth) * 0.08 + random.uniform(-2, 2)
                
            elif week < crisis_week + recovery_weeks // 2:
                # Early recovery: At-risk, gradual improvement
                phase = JourneyPhase.AT_RISK
                remaining = (crisis_week + recovery_weeks) - week
                target_gain = (end_health - current_health)
                weekly_change = (target_gain / remaining) * 0.8 + random.uniform(-1, 3)
                
            elif week < crisis_week + recovery_weeks:
                # Mid-recovery: Moderate, steady gains
                phase = JourneyPhase.MODERATE
                remaining = (crisis_week + recovery_weeks) - week
                target_gain = (end_health - current_health)
                weekly_change = (target_gain / remaining) * 1.0 + random.uniform(0, 2)
                
            else:
                # Post-recovery: Growth and stabilization
                phase = JourneyPhase.GROWTH
                # Small positive gains toward target
                gap = end_health - current_health
                if gap > 5:
                    weekly_change = random.uniform(0.5, 2.0)
                else:
                    weekly_change = random.uniform(-0.5, 0.5)
            
            # Apply change and clamp
            current_health = max(0, min(100, current_health + weekly_change))
            
            trajectory.append((week, current_health, phase))
        
        return trajectory


# ============================================================================
# CSM ACTION GENERATOR
# ============================================================================

class CSMActionGenerator:
    """Generates CSM actions based on health scores and phases"""
    
    def __init__(self):
        self.action_library = self._build_action_library()
    
    def _build_action_library(self) -> Dict[JourneyPhase, List[Tuple[CSMActionType, str, float, float]]]:
        """
        Build library of CSM actions by phase
        
        Returns: Dict[phase] -> List[(action_type, description, response_hours, cost)]
        """
        return {
            JourneyPhase.HEALTHY: [
                (CSMActionType.STANDARD_CHECKIN, "Standard quarterly check-in", 168, 500),
            ],
            
            JourneyPhase.CRISIS: [
                (CSMActionType.WAR_ROOM, "Emergency war room convened (Day 0)", 2, 15000),
                (CSMActionType.EXECUTIVE_SPONSOR, "Executive sponsor assigned immediately", 2, 25000),
                (CSMActionType.ROOT_CAUSE_ANALYSIS, "Root cause analysis initiated", 4, 10000),
            ],
            
            JourneyPhase.RECOVERY: [
                (CSMActionType.SUPPORT_ENGINEER_24_7, "24/7 dedicated support engineer assigned", 0, 20000),
                (CSMActionType.ENHANCED_MONITORING, "Enhanced monitoring infrastructure deployed", 24, 8000),
                (CSMActionType.WEEKLY_EXEC_CALLS, "Weekly executive status calls scheduled", 168, 2000),
            ],
            
            JourneyPhase.AT_RISK: [
                (CSMActionType.FLEXIBLE_PAYMENT_TERMS, "Flexible payment terms offered", 72, 5000),
                (CSMActionType.DISCOUNT_NEGOTIATION, "12% discount negotiated with finance", 96, 3000),
                (CSMActionType.ROI_ANALYSIS, "Detailed ROI analysis prepared", 48, 4000),
            ],
            
            JourneyPhase.MODERATE: [
                (CSMActionType.PERFORMANCE_REPORTING, "Performance dashboard and reporting", 72, 2000),
                (CSMActionType.PROACTIVE_TRAINING, "Proactive team training sessions (15 engineers)", 120, 5000),
                (CSMActionType.NEW_USE_CASE_SUPPORT, "New use case support and enablement", 48, 3000),
            ],
            
            JourneyPhase.GROWTH: [
                (CSMActionType.RENEWAL_PLANNING, "Renewal planning and strategy", 168, 2000),
                (CSMActionType.RENEWAL_EXECUTION, "Contract renewal execution", 72, 3000),
                (CSMActionType.EXPANSION_ENABLEMENT, "Expansion enablement and POC support", 96, 8000),
                (CSMActionType.STRATEGIC_PLANNING, "Strategic multi-year planning", 120, 5000),
                (CSMActionType.MARKETING_COLLABORATION, "Marketing collaboration and case study", 200, 2000),
            ],
        }
    
    def generate_action(self, phase: JourneyPhase, health_before: float, 
                       health_after: float) -> Optional[CSMAction]:
        """Generate appropriate CSM action based on context"""
        
        # No action needed for minor changes in healthy state
        if phase == JourneyPhase.HEALTHY and abs(health_after - health_before) < 3:
            if random.random() > 0.3:  # 70% chance of no action
                return None
        
        # Crisis always triggers action
        if phase == JourneyPhase.CRISIS:
            actions = self.action_library[phase]
            action_data = random.choice(actions)
            return CSMAction(*action_data)
        
        # Other phases: probabilistic
        if phase in self.action_library:
            if random.random() < 0.7:  # 70% chance of action
                actions = self.action_library[phase]
                action_data = random.choice(actions)
                return CSMAction(*action_data)
        
        return None


# ============================================================================
# JOURNEY PATTERN GENERATOR (Main Class)
# ============================================================================

class JourneyPatternGenerator:
    """Main generator for customer journey patterns"""
    
    def __init__(self):
        self.event_library = EventTemplateLibrary()
        self.action_generator = CSMActionGenerator()
    
    def generate_crisis_recovery_journey(
        self,
        account_id: str,
        account_name: str,
        start_date: datetime,
        total_weeks: int = 52
    ) -> AccountJourney:
        """
        Generate Account 1007-style crisis → recovery → growth journey
        
        Pattern:
        - Starts healthy (90)
        - Week 5: Major crisis drops to 35
        - Weeks 6-25: Recovery to 78
        - Weeks 26-52: Growth to 93
        """
        
        # Define trajectory pattern
        pattern_config = {
            'start_health': 90,
            'crisis_week': 5,
            'crisis_depth': -55,
            'recovery_weeks': 20,
            'end_health': 93,
            'volatility': 0.15
        }
        
        # Simulate health trajectory
        simulator = HealthTrajectorySimulator(pattern_config)
        trajectory = simulator.simulate_trajectory(total_weeks)
        
        # Generate events for each week
        events = []
        previous_health = pattern_config['start_health']
        total_csm_investment = 0.0
        
        for week_num, health, phase in trajectory:
            week_date = start_date + timedelta(weeks=week_num - 1)
            
            # Determine number of events this week based on phase
            if phase == JourneyPhase.CRISIS:
                num_events = random.randint(3, 5)  # High activity during crisis
            elif phase == JourneyPhase.RECOVERY:
                num_events = random.randint(2, 3)
            elif phase in [JourneyPhase.AT_RISK, JourneyPhase.MODERATE]:
                num_events = random.randint(1, 2)
            elif phase == JourneyPhase.GROWTH:
                num_events = random.randint(1, 3)
            else:  # HEALTHY
                num_events = 1 if random.random() < 0.3 else 0  # Occasional check-ins
            
            # Generate events for this week
            for _ in range(num_events):
                event_template = self.event_library.get_random_event(phase)
                if not event_template:
                    continue
                
                # Generate CSM action
                csm_action = self.action_generator.generate_action(
                    phase, previous_health, health
                )
                
                if csm_action:
                    total_csm_investment += csm_action.cost_estimate
                
                # Create outcome description
                outcome = self._generate_outcome(phase, health, previous_health)
                
                # Create journey event
                event = JourneyEvent(
                    week_number=week_num,
                    date=week_date.strftime('%Y-%m-%d'),
                    phase=phase,
                    event_type=event_template.event_type,
                    description=event_template.description,
                    sentiment=event_template.sentiment,
                    sentiment_value=event_template.sentiment_value,
                    health_score_before=previous_health,
                    health_score_after=health,
                    csm_action=csm_action,
                    outcome=outcome
                )
                
                events.append(event)
            
            previous_health = health
        
        # Calculate summary statistics
        health_scores = [h for _, h, _ in trajectory]
        summary = {
            'pattern_type': 'crisis_recovery',
            'total_events': len(events),
            'crisis_week': pattern_config['crisis_week'],
            'lowest_health_week': trajectory[
                health_scores.index(min(health_scores))
            ][0],
            'recovery_duration_weeks': pattern_config['recovery_weeks'],
            'total_csm_investment': round(total_csm_investment, 2),
            'health_recovered': round(trajectory[-1][1] - min(health_scores), 2),
            'financial_impact': '40% ARR expansion',
            'key_success_factors': [
                'Immediate crisis response (< 2 hours)',
                'Executive sponsor assignment (Day 1)',
                'Over-communication (weekly exec calls)',
                'Technical excellence (150+ days uptime)',
                'Commercial flexibility (12% discount)',
                'New champion cultivation'
            ]
        }
        
        # Create account journey
        journey = AccountJourney(
            account_id=account_id,
            account_name=account_name,
            pattern_type='crisis_recovery',
            start_date=start_date.strftime('%Y-%m-%d'),
            end_date=(start_date + timedelta(weeks=total_weeks)).strftime('%Y-%m-%d'),
            starting_health=trajectory[0][1],
            ending_health=trajectory[-1][1],
            lowest_health=min(health_scores),
            highest_health=max(health_scores),
            total_weeks=total_weeks,
            events=events,
            summary=summary
        )
        
        return journey
    
    def generate_ignored_churn_journey(
        self,
        account_id: str,
        account_name: str,
        start_date: datetime,
        total_weeks: int = 52
    ) -> AccountJourney:
        """
        Generate ignored churn journey pattern
        
        Pattern:
        - Starts moderate (70)
        - Steady decline due to neglect
        - Minimal CSM intervention
        - Ends in churn (20)
        """
        
        # Define trajectory pattern for churn
        pattern_config = {
            'start_health': 70,
            'decline_rate': -1.0,  # Steady decline
            'end_health': 20,
            'volatility': 0.1
        }
        
        # Simulate declining health trajectory
        trajectory = []
        current_health = pattern_config['start_health']
        decline_per_week = (pattern_config['end_health'] - pattern_config['start_health']) / total_weeks
        
        for week_num in range(1, total_weeks + 1):
            # Determine phase based on health
            if current_health >= 70:
                phase = JourneyPhase.MODERATE
            elif current_health >= 50:
                phase = JourneyPhase.AT_RISK
            elif current_health >= 30:
                phase = JourneyPhase.CRISIS
            else:
                phase = JourneyPhase.CHURNED
            
            trajectory.append((week_num, current_health, phase))
            
            # Decline with some randomness
            current_health += decline_per_week + random.uniform(-2, 1)
            current_health = max(15, current_health)  # Floor at 15
        
        # Generate events for each week
        events = []
        previous_health = pattern_config['start_health']
        total_csm_investment = 0.0
        
        for week_num, health, phase in trajectory:
            week_date = start_date + timedelta(weeks=week_num - 1)
            
            # Fewer events - this account is being ignored!
            if phase == JourneyPhase.CHURNED:
                num_events = random.randint(1, 2)
            elif phase == JourneyPhase.CRISIS:
                num_events = random.randint(1, 2)
            elif phase == JourneyPhase.AT_RISK:
                num_events = random.randint(0, 1)
            else:  # MODERATE
                num_events = 1 if random.random() < 0.2 else 0
            
            # Generate events for this week
            for _ in range(num_events):
                event_template = self.event_library.get_random_event(phase)
                if not event_template:
                    continue
                
                # Minimal or no CSM action for churn pattern
                csm_action = None
                if phase == JourneyPhase.CRISIS and random.random() < 0.3:
                    csm_action = self.action_generator.generate_action(
                        phase, previous_health, health
                    )
                    if csm_action:
                        total_csm_investment += csm_action.cost_estimate
                
                # Create outcome description
                outcome = self._generate_outcome(phase, health, previous_health)
                
                # Create journey event
                event = JourneyEvent(
                    week_number=week_num,
                    date=week_date.strftime('%Y-%m-%d'),
                    phase=phase,
                    event_type=event_template.event_type,
                    description=event_template.description,
                    sentiment=event_template.sentiment,
                    sentiment_value=event_template.sentiment_value,
                    health_score_before=previous_health,
                    health_score_after=health,
                    csm_action=csm_action,
                    outcome=outcome
                )
                
                events.append(event)
            
            previous_health = health
        
        # Calculate summary statistics
        health_scores = [h for _, h, _ in trajectory]
        summary = {
            'pattern_type': 'ignored_churn',
            'total_events': len(events),
            'lowest_health_week': trajectory[
                health_scores.index(min(health_scores))
            ][0],
            'total_csm_investment': round(total_csm_investment, 2),
            'health_decline': round(trajectory[0][1] - trajectory[-1][1], 2),
            'financial_impact': '100% ARR lost - churn',
            'key_failure_factors': [
                'Ignored early warning signs',
                'Minimal CSM engagement',
                'No proactive outreach',
                'Late intervention attempts',
                'Lost account to competition'
            ]
        }
        
        # Create account journey
        journey = AccountJourney(
            account_id=account_id,
            account_name=account_name,
            pattern_type='ignored_churn',
            start_date=start_date.strftime('%Y-%m-%d'),
            end_date=(start_date + timedelta(weeks=total_weeks)).strftime('%Y-%m-%d'),
            starting_health=trajectory[0][1],
            ending_health=trajectory[-1][1],
            lowest_health=min(health_scores),
            highest_health=max(health_scores),
            total_weeks=total_weeks,
            events=events,
            summary=summary
        )
        
        return journey

    def generate_proactive_growth_journey(
        self,
        account_id: str,
        account_name: str,
        start_date: datetime,
        total_weeks: int = 52
    ) -> AccountJourney:
        """
        Generate proactive growth journey pattern
        
        Pattern:
        - Starts good (75)
        - Steady improvement with proactive CSM
        - Regular engagement
        - Ends excellent (92)
        """
        
        # Define trajectory pattern for growth
        pattern_config = {
            'start_health': 75,
            'growth_rate': 0.35,
            'end_health': 92,
            'volatility': 0.08
        }
        
        # Simulate growing health trajectory
        trajectory = []
        current_health = pattern_config['start_health']
        growth_per_week = (pattern_config['end_health'] - pattern_config['start_health']) / total_weeks
        
        for week_num in range(1, total_weeks + 1):
            # Determine phase based on health
            if current_health >= 85:
                phase = JourneyPhase.GROWTH
            elif current_health >= 70:
                phase = JourneyPhase.HEALTHY
            else:
                phase = JourneyPhase.MODERATE
            
            trajectory.append((week_num, current_health, phase))
            
            # Growth with some randomness
            current_health += growth_per_week + random.uniform(-1, 2)
            current_health = min(98, current_health)  # Cap at 98
        
        # Generate events for each week
        events = []
        previous_health = pattern_config['start_health']
        total_csm_investment = 0.0
        
        for week_num, health, phase in trajectory:
            week_date = start_date + timedelta(weeks=week_num - 1)
            
            # Regular proactive engagement
            if phase == JourneyPhase.GROWTH:
                num_events = random.randint(2, 4)
            elif phase == JourneyPhase.HEALTHY:
                num_events = random.randint(1, 3)
            else:  # MODERATE
                num_events = random.randint(1, 2)
            
            # Generate events for this week
            for _ in range(num_events):
                event_template = self.event_library.get_random_event(phase)
                if not event_template:
                    continue
                
                # Proactive CSM action
                csm_action = self.action_generator.generate_action(
                    phase, previous_health, health
                )
                
                if csm_action:
                    total_csm_investment += csm_action.cost_estimate
                
                # Create outcome description
                outcome = self._generate_outcome(phase, health, previous_health)
                
                # Create journey event
                event = JourneyEvent(
                    week_number=week_num,
                    date=week_date.strftime('%Y-%m-%d'),
                    phase=phase,
                    event_type=event_template.event_type,
                    description=event_template.description,
                    sentiment=event_template.sentiment,
                    sentiment_value=event_template.sentiment_value,
                    health_score_before=previous_health,
                    health_score_after=health,
                    csm_action=csm_action,
                    outcome=outcome
                )
                
                events.append(event)
            
            previous_health = health
        
        # Calculate summary statistics
        health_scores = [h for _, h, _ in trajectory]
        summary = {
            'pattern_type': 'proactive_growth',
            'total_events': len(events),
            'highest_health_week': trajectory[
                health_scores.index(max(health_scores))
            ][0],
            'total_csm_investment': round(total_csm_investment, 2),
            'health_growth': round(trajectory[-1][1] - trajectory[0][1], 2),
            'financial_impact': '40% ARR expansion',
            'key_success_factors': [
                'Proactive regular engagement',
                'Quarterly business reviews',
                'Executive alignment',
                'Strategic planning sessions',
                'Early expansion discussions',
                'Strong partnership foundation'
            ]
        }
        
        # Create account journey
        journey = AccountJourney(
            account_id=account_id,
            account_name=account_name,
            pattern_type='proactive_growth',
            start_date=start_date.strftime('%Y-%m-%d'),
            end_date=(start_date + timedelta(weeks=total_weeks)).strftime('%Y-%m-%d'),
            starting_health=trajectory[0][1],
            ending_health=trajectory[-1][1],
            lowest_health=min(health_scores),
            highest_health=max(health_scores),
            total_weeks=total_weeks,
            events=events,
            summary=summary
        )
        
        return journey
    def _generate_outcome(self, phase: JourneyPhase, health: float, 
                         previous_health: float) -> str:
        """Generate outcome description based on phase and health change"""
        
        health_delta = health - previous_health
        
        if phase == JourneyPhase.CRISIS:
            if health_delta < -30:
                return "Production stopped, CEO furious, trust destroyed"
            else:
                return "Crisis mitigation in progress, situation critical"
        
        elif phase == JourneyPhase.RECOVERY:
            if health_delta > 5:
                return "Trust rebuilding, progress visible"
            else:
                return "Still fragile, slow progress"
        
        elif phase == JourneyPhase.AT_RISK:
            if health_delta > 5:
                return "Budget pressure eased, retention secured"
            else:
                return "Financial concerns remain, cautious"
        
        elif phase == JourneyPhase.MODERATE:
            if health_delta > 3:
                return "Confidence returning, team re-engaging"
            else:
                return "Stable, expansion still frozen"
        
        elif phase == JourneyPhase.GROWTH:
            if health_delta > 2:
                return "Growth accelerating, strategic partnership"
            else:
                return "Sustained growth, advocacy unlocked"
        
        else:  # HEALTHY
            return "Perfect metrics, expansion opportunities"


# ============================================================================
# EXPORT FUNCTIONS
# ============================================================================

def export_journey_to_json(journey: AccountJourney, filepath: str):
    """Export journey to JSON file"""
    with open(filepath, 'w') as f:
        json.dump(journey.to_dict(), f, indent=2)
    print(f"✅ Exported journey to: {filepath}")


def export_journey_to_csv(journey: AccountJourney, filepath: str):
    """Export journey events to CSV file"""
    import csv
    
    with open(filepath, 'w', newline='') as f:
        if not journey.events:
            return
        
        # Define fieldnames including flattened CSM action fields
        fieldnames = [
            'week_number', 'date', 'phase', 'event_type', 'description',
            'sentiment', 'sentiment_value', 'health_score_before', 
            'health_score_after', 'outcome',
            'csm_action_type', 'csm_action_desc', 'csm_response_hours', 'csm_cost'
        ]
        
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        
        for event in journey.events:
            event_dict = event.to_dict()
            
            # Flatten CSM action if present
            if 'csm_action' in event_dict and event_dict['csm_action']:
                action = event_dict.pop('csm_action')
                event_dict['csm_action_type'] = action['action_type']
                event_dict['csm_action_desc'] = action['description']
                event_dict['csm_response_hours'] = action['response_time_hours']
                event_dict['csm_cost'] = action['cost_estimate']
            else:
                # No CSM action for this event
                event_dict['csm_action_type'] = None
                event_dict['csm_action_desc'] = None
                event_dict['csm_response_hours'] = None
                event_dict['csm_cost'] = None
            
            writer.writerow(event_dict)
    
    print(f"✅ Exported journey to: {filepath}")


def generate_journey_report(journey: AccountJourney, filepath: str):
    """Generate markdown report of the journey"""
    
    report = f"""# Customer Journey Report: {journey.account_name}

## Account Overview
- **Account ID:** {journey.account_id}
- **Pattern Type:** {journey.pattern_type}
- **Duration:** {journey.start_date} to {journey.end_date} ({journey.total_weeks} weeks)

## Health Score Summary
- **Starting Health:** {journey.starting_health:.1f}
- **Ending Health:** {journey.ending_health:.1f}
- **Lowest Health:** {journey.lowest_health:.1f} (Week {journey.summary.get('lowest_health_week', 'N/A')})
- **Highest Health:** {journey.highest_health:.1f}
- **Net Change:** {journey.ending_health - journey.starting_health:+.1f} points

## Journey Statistics
- **Total Events:** {len(journey.events)}
- **Crisis Week:** {journey.summary.get('crisis_week', 'N/A')}
- **Recovery Duration:** {journey.summary.get('recovery_duration_weeks', 'N/A')} weeks
- **Total CSM Investment:** ${journey.summary.get('total_csm_investment', 0):,.2f}
- **Financial Impact:** {journey.summary.get('financial_impact', 'N/A')}

## Key Success Factors
"""
    
    for factor in journey.summary.get('key_success_factors', []):
        report += f"- {factor}\n"
    
    report += "\n## Week-by-Week Journey\n\n"
    report += "| Week | Date | Phase | Health | Event | Sentiment | CSM Action |\n"
    report += "|------|------|-------|--------|-------|-----------|------------|\n"
    
    for event in journey.events:
        csm = event.csm_action.action_type.value if event.csm_action else "None"
        report += f"| {event.week_number} | {event.date} | {event.phase.value} | "
        report += f"{event.health_score_after:.1f} | {event.event_type.value} | "
        report += f"{event.sentiment.value} | {csm} |\n"
    
    with open(filepath, 'w') as f:
        f.write(report)
    
    print(f"✅ Generated journey report: {filepath}")


# ============================================================================
# MAIN EXECUTION
# ============================================================================

if __name__ == "__main__":
    print("="*70)
    print("JOURNEY PATTERN GENERATOR - PHASE 1: FOUNDATION")
    print("="*70)
    print()
    
    # Initialize generator
    generator = JourneyPatternGenerator()
    
    # Generate Account 1007 (Crisis-Recovery pattern)
    print("Generating Account 1007: Legacy Manufacturing (Crisis → Recovery)")
    print("-" * 70)
    
    start_date = datetime(2024, 1, 1)
    
    journey = generator.generate_crisis_recovery_journey(
        account_id="10007",
        account_name="Legacy Manufacturing Corp",
        start_date=start_date,
        total_weeks=52
    )
    
    print(f"\n✅ Journey Generated Successfully!")
    print(f"   - Account: {journey.account_name} ({journey.account_id})")
    print(f"   - Duration: {journey.total_weeks} weeks")
    print(f"   - Events: {len(journey.events)}")
    print(f"   - Health: {journey.starting_health:.1f} → {journey.ending_health:.1f}")
    print(f"   - Lowest: {journey.lowest_health:.1f}")
    print(f"   - CSM Investment: ${journey.summary['total_csm_investment']:,.2f}")
    
    # Export to files
    print("\n" + "-" * 70)
    print("Exporting journey data...")
    print("-" * 70)
    
    export_journey_to_json(journey, "/home/claude/account_10007_journey.json")
    export_journey_to_csv(journey, "/home/claude/account_10007_events.csv")
    generate_journey_report(journey, "/home/claude/account_10007_report.md")
    
    print("\n" + "="*70)
    print("PHASE 1 COMPLETE! ✅")
    print("="*70)
    print("\nNext: Phase 2 will add Account 1003 (Churn) and Account 1001 (Growth)")
