#!/usr/bin/env python3
"""
Journey Pattern Generator - Phase 3: KPI Integration
====================================================

Adds 35 KPIs per week for each account, correlating with health trajectory and events.

KPI Categories:
1. Performance & Utilization (8 KPIs)
2. Cost Efficiency (7 KPIs)
3. Scalability & Growth (7 KPIs)
4. Support & Reliability (6 KPIs)
5. Business Value (7 KPIs)
"""

import random
from typing import Dict, List
from dataclasses import dataclass
from enum import Enum


# ============================================================================
# KPI DEFINITIONS
# ============================================================================

class KPICategory(Enum):
    """KPI categories"""
    PERFORMANCE = "Performance & Utilization"
    COST = "Cost Efficiency"
    SCALABILITY = "Scalability & Growth"
    SUPPORT = "Support & Reliability"
    BUSINESS = "Business Value"


@dataclass
class KPIDefinition:
    """Definition of a KPI"""
    kpi_id: str
    name: str
    category: KPICategory
    unit: str
    good_range: tuple  # (min, max) for good performance
    bad_range: tuple   # (min, max) for bad performance
    inverse: bool = False  # True if lower is better (e.g., cost, downtime)


# All 35 KPIs
KPI_DEFINITIONS = {
    # Performance & Utilization (8 KPIs)
    'P1': KPIDefinition('P1', 'Workload Running', KPICategory.PERFORMANCE, 'count', (15, 25), (3, 8)),
    'P2': KPIDefinition('P2', 'GPU Utilization', KPICategory.PERFORMANCE, '%', (75, 95), (30, 50), False),
    'P3': KPIDefinition('P3', 'Active Users', KPICategory.PERFORMANCE, 'count', (25, 40), (5, 15)),
    'P4': KPIDefinition('P4', 'Training Jobs Completed', KPICategory.PERFORMANCE, 'count', (40, 60), (10, 25)),
    'P5': KPIDefinition('P5', 'Inference Requests', KPICategory.PERFORMANCE, 'millions', (5.0, 10.0), (0.5, 2.0)),
    'P6': KPIDefinition('P6', 'Model Accuracy', KPICategory.PERFORMANCE, '%', (92, 98), (70, 85)),
    'P7': KPIDefinition('P7', 'Data Processing Throughput', KPICategory.PERFORMANCE, 'TB/day', (8, 15), (2, 5)),
    'P8': KPIDefinition('P8', 'API Response Time', KPICategory.PERFORMANCE, 'ms', (50, 150), (400, 800), True),
    
    # Cost Efficiency (7 KPIs)
    'C1': KPIDefinition('C1', 'Cost per Training Job', KPICategory.COST, '$', (50, 150), (300, 600), True),
    'C2': KPIDefinition('C2', 'Cost per 1M Inferences', KPICategory.COST, '$', (10, 30), (80, 150), True),
    'C3': KPIDefinition('C3', 'Idle GPU Time', KPICategory.COST, '%', (2, 8), (25, 45), True),
    'C4': KPIDefinition('C4', 'Storage Cost Efficiency', KPICategory.COST, '$/TB', (30, 60), (120, 200), True),
    'C5': KPIDefinition('C5', 'Compute ROI', KPICategory.COST, 'ratio', (4.0, 8.0), (1.2, 2.0)),
    'C6': KPIDefinition('C6', 'Budget Utilization', KPICategory.COST, '%', (70, 90), (40, 55)),
    'C7': KPIDefinition('C7', 'Cost Predictability', KPICategory.COST, 'score', (85, 98), (50, 70)),
    
    # Scalability & Growth (7 KPIs)
    'S1': KPIDefinition('S1', 'Capacity Utilization', KPICategory.SCALABILITY, '%', (75, 90), (35, 55)),
    'S2': KPIDefinition('S2', 'Workload Growth Rate', KPICategory.SCALABILITY, '%', (15, 35), (-5, 5)),
    'S3': KPIDefinition('S3', 'New Use Cases Deployed', KPICategory.SCALABILITY, 'count', (2, 5), (0, 1)),
    'S4': KPIDefinition('S4', 'Time to Scale', KPICategory.SCALABILITY, 'hours', (2, 8), (48, 96), True),
    'S5': KPIDefinition('S5', 'Resource Elasticity', KPICategory.SCALABILITY, 'score', (85, 98), (50, 70)),
    'S6': KPIDefinition('S6', 'Peak Load Handling', KPICategory.SCALABILITY, '%', (90, 99), (65, 80)),
    'S7': KPIDefinition('S7', 'Expansion Readiness', KPICategory.SCALABILITY, 'score', (80, 95), (40, 60)),
    
    # Support & Reliability (6 KPIs)
    'R1': KPIDefinition('R1', 'System Uptime', KPICategory.SUPPORT, '%', (99.5, 99.99), (95.0, 98.0)),
    'R2': KPIDefinition('R2', 'Support Ticket Volume', KPICategory.SUPPORT, 'count', (2, 8), (18, 35), True),
    'R3': KPIDefinition('R3', 'Mean Time to Resolution', KPICategory.SUPPORT, 'hours', (2, 8), (24, 72), True),
    'R4': KPIDefinition('R4', 'Critical Incidents', KPICategory.SUPPORT, 'count', (0, 1), (4, 8), True),
    'R5': KPIDefinition('R5', 'Support Satisfaction', KPICategory.SUPPORT, 'score', (4.5, 5.0), (2.5, 3.5)),
    'R6': KPIDefinition('R6', 'Documentation Usage', KPICategory.SUPPORT, 'score', (75, 95), (30, 50)),
    
    # Business Value (7 KPIs)
    'B1': KPIDefinition('B1', 'Business Value Score', KPICategory.BUSINESS, 'score', (85, 98), (50, 70)),
    'B2': KPIDefinition('B2', 'User Satisfaction (NPS)', KPICategory.BUSINESS, 'score', (50, 80), (0, 25)),
    'B3': KPIDefinition('B3', 'Feature Adoption', KPICategory.BUSINESS, '%', (70, 90), (30, 50)),
    'B4': KPIDefinition('B4', 'Time to Value', KPICategory.BUSINESS, 'days', (7, 21), (60, 120), True),
    'B5': KPIDefinition('B5', 'Strategic Alignment', KPICategory.BUSINESS, 'score', (80, 95), (45, 65)),
    'B6': KPIDefinition('B6', 'Executive Engagement', KPICategory.BUSINESS, 'score', (75, 95), (35, 55)),
    'B7': KPIDefinition('B7', 'Competitive Position', KPICategory.BUSINESS, 'score', (80, 95), (40, 60)),
}


# ============================================================================
# KPI GENERATION ENGINE
# ============================================================================

class KPIGenerator:
    """Generates KPI values based on health score and events"""
    
    def __init__(self, account_id: str, account_name: str):
        self.account_id = account_id
        self.account_name = account_name
        self.kpi_definitions = KPI_DEFINITIONS
    
    def generate_weekly_kpis(self, 
                            week_number: int,
                            date: str,
                            health_score: float,
                            phase: str,
                            events: List[Dict]) -> Dict[str, any]:
        """
        Generate all 35 KPIs for a given week
        
        Args:
            week_number: Week number (1-52)
            date: Date string (YYYY-MM-DD)
            health_score: Current health score (0-100)
            phase: Current phase (healthy, crisis, at_risk, etc.)
            events: List of events that occurred this week
        
        Returns:
            Dict with all KPI values
        """
        kpis = {
            'week_number': week_number,
            'date': date,
            'health_score': health_score,
            'phase': phase
        }
        
        # Generate each KPI
        for kpi_id, definition in self.kpi_definitions.items():
            value = self._generate_kpi_value(
                definition, 
                health_score, 
                phase, 
                events
            )
            kpis[kpi_id] = value
        
        return kpis
    
    def _generate_kpi_value(self,
                           definition: KPIDefinition,
                           health_score: float,
                           phase: str,
                           events: List[Dict]) -> float:
        """
        Generate a single KPI value based on health and events
        
        Logic:
        - High health (85-100) → Good range values
        - Medium health (60-85) → Middle values
        - Low health (0-60) → Bad range values
        - Modified by specific events (outages, escalations, etc.)
        """
        # Base value from health score
        if health_score >= 85:
            # Healthy: Use good range
            base_value = random.uniform(
                definition.good_range[0],
                definition.good_range[1]
            )
        elif health_score >= 60:
            # Moderate: Interpolate between good and bad
            health_pct = (health_score - 60) / 25  # 0-1 scale
            base_value = (
                definition.bad_range[1] + 
                health_pct * (definition.good_range[0] - definition.bad_range[1])
            )
        else:
            # At-risk/Crisis: Use bad range
            base_value = random.uniform(
                definition.bad_range[0],
                definition.bad_range[1]
            )
        
        # Apply event-based modifications
        for event in events:
            base_value = self._apply_event_impact(
                base_value,
                definition,
                event
            )
        
        # Apply phase-specific adjustments
        base_value = self._apply_phase_adjustments(
            base_value,
            definition,
            phase
        )
        
        # Add noise (±5%)
        noise = random.uniform(-0.05, 0.05)
        final_value = base_value * (1 + noise)
        
        # Round based on unit type
        if definition.unit in ['count', 'days', 'hours']:
            final_value = max(0, int(round(final_value)))
        elif definition.unit in ['%', 'score', 'ratio']:
            final_value = round(max(0, min(100, final_value)), 2)
        else:
            final_value = round(max(0, final_value), 2)
        
        return final_value
    
    def _apply_event_impact(self,
                          value: float,
                          definition: KPIDefinition,
                          event: Dict) -> float:
        """Apply event-specific impact to KPI value"""
        event_type = event.get('event_type', '')
        sentiment = event.get('sentiment_value', 0)
        
        # Outage events
        if event_type == 'outage':
            if definition.kpi_id == 'R1':  # System Uptime
                value *= 0.95  # 5% reduction
            elif definition.kpi_id == 'P2':  # GPU Utilization
                value *= 0.6   # 40% reduction during outage
            elif definition.kpi_id == 'R4':  # Critical Incidents
                value += 1     # Add incident
            elif definition.kpi_id in ['B1', 'B2']:  # Business value, NPS
                value *= 0.85  # 15% reduction
        
        # Escalation events
        elif event_type == 'escalation':
            if definition.kpi_id == 'R2':  # Support Tickets
                value += random.randint(3, 8)
            elif definition.kpi_id == 'R5':  # Support Satisfaction
                value *= 0.75  # 25% reduction
            elif definition.kpi_id == 'B2':  # NPS
                value *= 0.7   # 30% reduction
        
        # Positive events (expansion, milestone)
        elif event_type in ['milestone', 'expansion_discussion']:
            if sentiment > 0.7:
                if definition.kpi_id in ['B1', 'B2', 'B3']:  # Business metrics
                    value *= 1.15  # 15% boost
                elif definition.kpi_id in ['S1', 'S2']:  # Growth metrics
                    value *= 1.20  # 20% boost
        
        return value
    
    def _apply_phase_adjustments(self,
                                value: float,
                                definition: KPIDefinition,
                                phase: str) -> float:
        """Apply phase-specific adjustments"""
        
        # Crisis phase
        if phase == 'crisis':
            if definition.category == KPICategory.PERFORMANCE:
                value *= 0.60  # 40% reduction in performance
            elif definition.category == KPICategory.SUPPORT:
                if definition.inverse:  # Bad metrics go up
                    value *= 2.5
                else:  # Good metrics go down
                    value *= 0.60
        
        # Growth phase
        elif phase == 'growth':
            if definition.category == KPICategory.SCALABILITY:
                value *= 1.25  # 25% boost in scalability
            elif definition.category == KPICategory.BUSINESS:
                value *= 1.15  # 15% boost in business value
        
        # Churned phase
        elif phase == 'churned':
            # All metrics degraded
            if not definition.inverse:
                value *= 0.40  # 60% reduction
            else:
                value *= 3.0   # 3x worse for inverse metrics
        
        return value


# ============================================================================
# DATA EXPORT FUNCTIONS
# ============================================================================

def export_kpis_to_csv(kpis_data: List[Dict], filename: str):
    """Export KPI data to CSV"""
    import csv
    
    if not kpis_data:
        return
    
    # Get all KPI IDs for header
    kpi_ids = list(KPI_DEFINITIONS.keys())
    header = ['account_id', 'account_name', 'week_number', 'date', 'health_score', 'phase'] + kpi_ids
    
    with open(filename, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=header)
        writer.writeheader()
        writer.writerows(kpis_data)
    
    print(f"✅ Exported {len(kpis_data)} weeks of KPI data to {filename}")


def generate_kpi_metadata():
    """Generate KPI metadata for documentation"""
    metadata = []
    
    for kpi_id, definition in KPI_DEFINITIONS.items():
        metadata.append({
            'kpi_id': kpi_id,
            'name': definition.name,
            'category': definition.category.value,
            'unit': definition.unit,
            'good_range': f"{definition.good_range[0]}-{definition.good_range[1]}",
            'bad_range': f"{definition.bad_range[0]}-{definition.bad_range[1]}",
            'inverse': 'Yes' if definition.inverse else 'No'
        })
    
    return metadata


# ============================================================================
# INTEGRATION WITH JOURNEY GENERATOR
# ============================================================================

def add_kpis_to_journey(journey_data: Dict) -> Dict:
    """
    Add KPI data to existing journey data
    
    Args:
        journey_data: Existing journey data from Phase 1/2
    
    Returns:
        Enhanced journey data with KPI information
    """
    account_id = journey_data['account_id']
    account_name = journey_data['account_name']
    
    generator = KPIGenerator(account_id, account_name)
    
    # Generate KPIs for each week
    kpi_data = []
    for event in journey_data['events']:
        week_number = event['week_number']
        date = event['date']
        health_score = event['health_score_after']
        phase = event['phase']
        
        # Get events for this week
        week_events = [e for e in journey_data['events'] 
                      if e['week_number'] == week_number]
        
        # Generate KPIs
        kpis = generator.generate_weekly_kpis(
            week_number,
            date,
            health_score,
            phase,
            week_events
        )
        
        # Add account info
        kpis['account_id'] = account_id
        kpis['account_name'] = account_name
        
        kpi_data.append(kpis)
    
    # Add to journey data
    journey_data['kpis'] = kpi_data
    
    return journey_data


# ============================================================================
# MAIN EXECUTION
# ============================================================================

if __name__ == "__main__":
    print("="*70)
    print("KPI GENERATOR - PHASE 3")
    print("="*70)
    print()
    
    # Display KPI definitions
    print("📊 KPI DEFINITIONS (35 Total)")
    print("-" * 70)
    
    by_category = {}
    for kpi_id, definition in KPI_DEFINITIONS.items():
        category = definition.category.value
        if category not in by_category:
            by_category[category] = []
        by_category[category].append((kpi_id, definition))
    
    for category, kpis in by_category.items():
        print(f"\n{category} ({len(kpis)} KPIs):")
        for kpi_id, definition in kpis:
            inverse_marker = " (↓)" if definition.inverse else " (↑)"
            print(f"  {kpi_id}: {definition.name} [{definition.unit}]{inverse_marker}")
            print(f"      Good: {definition.good_range}, Bad: {definition.bad_range}")
    
    print()
    print("="*70)
    print("Ready to integrate with journey generator!")
    print("="*70)
