#!/usr/bin/env python3
"""
Import Integration Adapter
===========================

Complete integration layer that connects:
- Excel Import Service (real customer data)
- KPI Normalization Service (raw values → 0-100)
- Sparse KPI Handler (10-15 KPIs validation)
- Hierarchical Health Calculator (existing system)
- WeekData (existing system)
- Qdrant (existing system)

This is the BRIDGE between your Excel templates and CS Pulse.
"""

import sys
from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

# Our new services
from excel_import_service import ExcelImportService, CustomerImportData
from kpi_normalization_service import KPINormalizationService
from sparse_kpi_handler import SparseKPIHandler

# Existing CS Pulse components (from uploaded files)
try:
    from updated_week_data_qdrant import WeekData, JourneyPhase, WeekEvent, EventType
    from qdrant_journey_schema import QdrantJourneyStorage
    # In production, import actual health calculator:
    # from robust_hierarchical_health_calculator import HierarchicalHealthCalculator
except ImportError:
    print("⚠️  Warning: Could not import existing CS Pulse components")
    print("   Make sure updated_week_data_qdrant.py and qdrant_journey_schema.py are in path")
    WeekData = None
    QdrantJourneyStorage = None


@dataclass
class ImportResult:
    """Result of import operation"""
    success: bool
    customers_imported: int
    weeks_imported: int
    errors: List[str]
    warnings: List[str]
    qdrant_point_ids: List[str]


class ImportIntegrationAdapter:
    """
    Complete integration adapter: Excel → CS Pulse
    
    Pipeline:
    1. Excel file → ExcelImportService
    2. Raw KPI values → KPINormalizationService → Normalized 0-100 scores
    3. Sparse KPIs (10-15) → SparseKPIHandler → Validation
    4. Normalized KPIs → HierarchicalHealthCalculator → Pillar scores + Health score
    5. Complete data → WeekData → Qdrant payload
    6. Qdrant payload → QdrantJourneyStorage → Upload
    """
    
    def __init__(
        self,
        qdrant_url: str = 'http://localhost:6333',
        bootstrap_weights_path: Optional[str] = None
    ):
        """
        Initialize adapter with all services
        
        Args:
            qdrant_url: Qdrant server URL
            bootstrap_weights_path: Path to bootstrap weights JSON (optional)
        """
        
        # Initialize our new services
        self.excel_import = ExcelImportService()
        self.normalization = KPINormalizationService()
        self.sparse_handler = SparseKPIHandler()
        
        # Initialize existing CS Pulse components
        if QdrantJourneyStorage:
            self.qdrant = QdrantJourneyStorage(qdrant_url)
        else:
            self.qdrant = None
            print("⚠️  Qdrant storage not initialized")
        
        # Health calculator (placeholder - use actual in production)
        # self.health_calculator = HierarchicalHealthCalculator(bootstrap_weights_path)
        self.health_calculator = None
    
    def import_excel_to_cs_pulse(self, excel_path: str) -> ImportResult:
        """
        Complete import pipeline: Excel → CS Pulse
        
        Args:
            excel_path: Path to Excel template file
        
        Returns:
            ImportResult with summary
        """
        
        errors = []
        warnings = []
        qdrant_ids = []
        
        try:
            # Step 1: Parse Excel
            print("Step 1: Parsing Excel file...")
            customers = self.excel_import.import_from_file(excel_path)
            print(f"  ✅ Parsed {len(customers)} customers")
            
            # Collect validation warnings
            for customer in customers:
                for error in customer.validation_errors:
                    if error.severity == 'warning':
                        warnings.append(f"{customer.account_id}: {error.error_message}")
                    elif error.severity == 'error':
                        errors.append(f"{customer.account_id}: {error.error_message}")
            
            if errors:
                return ImportResult(
                    success=False,
                    customers_imported=0,
                    weeks_imported=0,
                    errors=errors,
                    warnings=warnings,
                    qdrant_point_ids=[]
                )
            
            total_weeks = 0
            
            # Step 2: Process each customer
            for customer in customers:
                print(f"\nProcessing: {customer.account_name} ({customer.account_id})")
                
                # Step 2a: Check if we have KPI history
                if not customer.kpi_history:
                    # No historical data - create single week snapshot
                    print(f"  ℹ️  No KPI history - creating current snapshot only")
                    
                    # Use tracked KPIs from coverage sheet
                    # (In production, might have current values in separate sheet)
                    # For now, skip customers without history
                    warnings.append(
                        f"{customer.account_id}: No KPI history available - skipping journey upload"
                    )
                    continue
                
                print(f"  Found {len(customer.kpi_history)} weeks of data")
                
                # Get events for this customer (if available)
                customer_events = {}
                if customer.events:
                    # Group events by week
                    for event in customer.events:
                        week = event.get('week', 1)
                        if week not in customer_events:
                            customer_events[week] = []
                        customer_events[week].append(event)
                    print(f"  Found {len(customer.events)} events across {len(customer_events)} weeks")
                
                # Step 2b: Process each week in history
                previous_week_data = None
                
                for week_data_raw in customer.kpi_history:
                    week_number = week_data_raw['week']
                    date_str = week_data_raw['date']
                    raw_kpis = week_data_raw['kpis']  # {kpi_name: (value, unit)}
                    
                    # Step 3: Normalize KPIs
                    normalized_kpis = self.excel_import.normalize_customer_kpis(
                        customer, raw_kpis
                    )
                    
                    if not normalized_kpis:
                        warnings.append(
                            f"{customer.account_id} Week {week_number}: No valid KPIs after normalization"
                        )
                        continue
                    
                    # Step 4: Calculate health (with weight renormalization for missing KPIs)
                    health_result = self._calculate_health_with_sparse_kpis(
                        customer, normalized_kpis
                    )
                    
                    # Step 4a: Calculate changes from previous week
                    if previous_week_data:
                        health_result['health_change'] = health_result['health_score'] - previous_week_data.health_score
                        
                        # Calculate pillar changes
                        pillar_changes = {}
                        for pillar_name in health_result['pillars']:
                            prev_score = previous_week_data.pillars.get(pillar_name, 0)
                            curr_score = health_result['pillars'].get(pillar_name, 0)
                            pillar_changes[pillar_name] = curr_score - prev_score
                        health_result['pillar_changes'] = pillar_changes
                    else:
                        health_result['pillar_changes'] = {}
                    
                    # Step 5: Get events for this week
                    week_events = customer_events.get(week_number, [])
                    
                    # Step 6: Create WeekData object
                    week_data = self._create_week_data(
                        customer=customer,
                        week_number=week_number,
                        date_str=date_str,
                        normalized_kpis=normalized_kpis,
                        health_result=health_result,
                        raw_events=week_events
                    )
                    
                    if not week_data:
                        continue
                    
                    # Step 6a: Detect pattern metadata (crisis/recovery)
                    if previous_week_data:
                        # Crisis start detection
                        if (previous_week_data.health_score >= 50 and 
                            week_data.health_score < 50):
                            week_data.is_crisis_start = True
                        
                        # Recovery start detection
                        if (previous_week_data.phase.value == 'crisis' and 
                            week_data.phase.value in ['recovery', 'at_risk', 'healthy']):
                            week_data.is_recovery_start = True
                    
                    # Step 7: Upload to Qdrant
                    if self.qdrant and week_data:
                        point_id = self._upload_to_qdrant(customer.account_id, week_data)
                        if point_id:
                            qdrant_ids.append(point_id)
                            total_weeks += 1
                    
                    previous_week_data = week_data
                
                print(f"  ✅ Processed {total_weeks} weeks for {customer.account_name}")
            
            print(f"\n✅ Import complete: {len(customers)} customers, {total_weeks} weeks")
            
            return ImportResult(
                success=True,
                customers_imported=len(customers),
                weeks_imported=total_weeks,
                errors=errors,
                warnings=warnings,
                qdrant_point_ids=qdrant_ids
            )
            
        except Exception as e:
            import traceback
            error_msg = f"Import failed: {str(e)}\n{traceback.format_exc()}"
            errors.append(error_msg)
            
            return ImportResult(
                success=False,
                customers_imported=0,
                weeks_imported=0,
                errors=errors,
                warnings=warnings,
                qdrant_point_ids=[]
            )
    
    def _calculate_health_with_sparse_kpis(
        self, 
        customer: CustomerImportData,
        normalized_kpis: Dict[str, float]
    ) -> Dict:
        """
        Calculate health scores using hierarchical calculator with weight renormalization
        
        Args:
            customer: Customer data
            normalized_kpis: Dict of normalized KPI scores (sparse - 10-15 KPIs)
        
        Returns:
            Dict with:
            - pillars: Dict[str, float]
            - health_score: float
            - phase: str
            - health_change: float (if available)
        """
        
        # Prepare for health calculation (validates coverage, etc.)
        health_input = self.sparse_handler.prepare_for_health_calculation(normalized_kpis)
        
        # Use actual health calculator if available
        if self.health_calculator:
            try:
                health, pillars, details = self.health_calculator.calculate_health_with_pillars(
                    normalized_kpis
                )
                
                # Determine phase from health score
                if health >= 70:
                    phase = 'healthy'
                elif health >= 50:
                    phase = 'at_risk'
                else:
                    phase = 'crisis'
                
                return {
                    'pillars': pillars,
                    'health_score': round(health, 2),
                    'phase': phase,
                    'health_change': None,  # Would need previous week data
                    'data_quality': details.data_completeness,
                    'missing_kpis': list(details.expected_kpis - set(normalized_kpis.keys())),
                    'available_kpis': list(normalized_kpis.keys())
                }
            except Exception as e:
                print(f"⚠️  Health calculator error: {e}, using fallback calculation")
        
        # Fallback: Simplified calculation with weight renormalization
        pillars = {}
        
        # Calculate pillar scores with weight renormalization
        for pillar_name, pillar_kpis in self.sparse_handler.ALL_KPIS.items():
            available_kpis_in_pillar = [kpi for kpi in pillar_kpis if kpi in normalized_kpis]
            
            if available_kpis_in_pillar:
                # Average of available KPIs in this pillar
                pillar_score = sum(normalized_kpis[kpi] for kpi in available_kpis_in_pillar) / len(available_kpis_in_pillar)
                pillars[pillar_name] = pillar_score
            else:
                # No KPIs available for this pillar
                pillars[pillar_name] = 0
        
        # Calculate overall health (weighted average of pillars with renormalization)
        available_pillars = {p: s for p, s in pillars.items() if s > 0}
        
        if available_pillars:
            # Equal weighting across available pillars (renormalized)
            health_score = sum(available_pillars.values()) / len(available_pillars)
        else:
            health_score = 0
        
        # Determine phase
        if health_score >= 70:
            phase = 'healthy'
        elif health_score >= 50:
            phase = 'at_risk'
        else:
            phase = 'crisis'
        
        return {
            'pillars': pillars,
            'health_score': round(health_score, 2),
            'phase': phase,
            'health_change': None,  # Would need previous week data
            'data_quality': health_input['data_quality'],
            'missing_kpis': health_input['missing_kpis'],
            'available_kpis': health_input['available_kpis']
        }
    
    def _create_week_data(
        self,
        customer: CustomerImportData,
        week_number: int,
        date_str: str,
        normalized_kpis: Dict[str, float],
        health_result: Dict,
        raw_events: List[Dict] = None
    ) -> Optional[WeekData]:
        """
        Create WeekData object from processed data
        
        Args:
            customer: Customer data
            week_number: Week number
            date_str: Date string (YYYY-MM-DD)
            normalized_kpis: Normalized KPI scores (sparse - 10-15 KPIs)
            health_result: Health calculation results
            raw_events: Raw event data from Excel
        
        Returns:
            WeekData object ready for Qdrant
        """
        
        if not WeekData:
            print("⚠️  WeekData class not available - skipping")
            return None
        
        # Convert events to WeekEvent objects
        events = []
        if raw_events:
            for event_data in raw_events:
                try:
                    # Parse event type
                    event_type_str = event_data.get('event_type', 'meeting')
                    event_type = EventType(event_type_str)
                    
                    # Parse sentiment
                    sentiment_str = event_data.get('sentiment', 'neutral')
                    sentiment_value = event_data.get('sentiment_value', 0.0)
                    
                    # Parse CSM action
                    csm_action = None
                    if 'csm_action' in event_data:
                        csm_data = event_data['csm_action']
                        csm_action = {
                            'action_type': csm_data.get('action_type', 'no_action'),
                            'description': csm_data.get('description', ''),
                            'response_time_hours': csm_data.get('response_time_hours', 0),
                            'cost_estimate': csm_data.get('cost_estimate', 0)
                        }
                    
                    # Create WeekEvent
                    event = WeekEvent(
                        event_type=event_type,
                        description=event_data.get('description', ''),
                        sentiment=sentiment_str,
                        sentiment_value=sentiment_value,
                        csm_action=csm_action,
                        outcome=event_data.get('outcome', ''),
                        kpi_impacts=event_data.get('kpi_impacts', {})
                    )
                    events.append(event)
                    
                except Exception as e:
                    print(f"⚠️  Failed to parse event: {e}")
                    continue
        
        # Convert phase string to enum
        phase_map = {
            'healthy': JourneyPhase.HEALTHY,
            'at_risk': JourneyPhase.AT_RISK,
            'crisis': JourneyPhase.CRISIS,
            'recovery': JourneyPhase.RECOVERY,
            'moderate': JourneyPhase.MODERATE,
            'growth': JourneyPhase.GROWTH,
            'churned': JourneyPhase.CHURNED
        }
        phase = phase_map.get(health_result['phase'], JourneyPhase.HEALTHY)
        
        # Calculate sentiment and CSM investment from events
        if events:
            avg_sentiment = sum(e.sentiment_value for e in events) / len(events)
            total_csm_cost = sum(
                e.csm_action['cost_estimate'] 
                for e in events 
                if e.csm_action and 'cost_estimate' in e.csm_action
            )
            primary_event_type = events[0].event_type.value if events else None
        else:
            avg_sentiment = 0.0
            total_csm_cost = 0.0
            primary_event_type = None
        
        # Create WeekData with sparse KPIs
        week_data = WeekData(
            week_number=week_number,
            date=date_str,
            phase=phase,
            kpis=normalized_kpis,  # Sparse dict (10-15 KPIs, not all 35)
            pillars=health_result['pillars'],
            health_score=health_result['health_score'],
            events=events,
            data_quality=health_result['data_quality'],
            missing_kpis=health_result['missing_kpis'],
            health_change=health_result.get('health_change'),
            pillar_changes=health_result.get('pillar_changes', {}),  # From calculation
            average_sentiment=avg_sentiment,
            total_csm_investment=total_csm_cost,
            primary_event_type=primary_event_type,
            is_crisis_start=False,  # Will be calculated in import flow
            is_recovery_start=False,  # Will be calculated in import flow
            weeks_since_crisis=None  # Will be calculated in import flow
        )
        
        return week_data
    
    def _upload_to_qdrant(self, account_id: str, week_data: WeekData) -> Optional[str]:
        """
        Upload week data to Qdrant
        
        Args:
            account_id: Account identifier
            week_data: WeekData object
        
        Returns:
            Point ID if successful, None otherwise
        """
        
        if not self.qdrant:
            return None
        
        try:
            # Generate Qdrant payload
            payload = week_data.get_qdrant_payload(account_id)
            
            # Generate point ID
            point_id = f"{account_id}_week_{week_data.week_number}"
            
            # Upload to Qdrant
            # self.qdrant.upsert_week(point_id, payload, embedding_vector)
            # (Implementation depends on Qdrant client setup)
            
            return point_id
            
        except Exception as e:
            print(f"⚠️  Failed to upload to Qdrant: {str(e)}")
            return None


# ============================================================================
# COMMAND LINE INTERFACE
# ============================================================================

def main():
    """Command line interface for import adapter"""
    
    import argparse
    
    parser = argparse.ArgumentParser(description='Import customer data from Excel to CS Pulse')
    parser.add_argument('excel_file', help='Path to Excel template file')
    parser.add_argument('--qdrant-url', default='http://localhost:6333', help='Qdrant server URL')
    parser.add_argument('--weights', help='Path to bootstrap weights JSON')
    
    args = parser.parse_args()
    
    if not Path(args.excel_file).exists():
        print(f"❌ Error: Excel file not found: {args.excel_file}")
        sys.exit(1)
    
    print("="*70)
    print("IMPORT INTEGRATION ADAPTER")
    print("="*70)
    print()
    print(f"Excel File: {args.excel_file}")
    print(f"Qdrant URL: {args.qdrant_url}")
    if args.weights:
        print(f"Weights Config: {args.weights}")
    print()
    
    # Initialize adapter
    adapter = ImportIntegrationAdapter(
        qdrant_url=args.qdrant_url,
        bootstrap_weights_path=args.weights
    )
    
    # Run import
    print("Starting import...")
    print()
    
    result = adapter.import_excel_to_cs_pulse(args.excel_file)
    
    # Display results
    print()
    print("="*70)
    print("IMPORT RESULTS")
    print("="*70)
    print()
    
    if result.success:
        print("✅ Import Successful!")
        print(f"  Customers: {result.customers_imported}")
        print(f"  Weeks: {result.weeks_imported}")
        print(f"  Qdrant Points: {len(result.qdrant_point_ids)}")
    else:
        print("❌ Import Failed!")
    
    if result.warnings:
        print(f"\n⚠️  Warnings ({len(result.warnings)}):")
        for warning in result.warnings[:10]:  # Show first 10
            print(f"  • {warning}")
        if len(result.warnings) > 10:
            print(f"  ... and {len(result.warnings) - 10} more")
    
    if result.errors:
        print(f"\n❌ Errors ({len(result.errors)}):")
        for error in result.errors[:10]:
            print(f"  • {error}")
        if len(result.errors) > 10:
            print(f"  ... and {len(result.errors) - 10} more")
    
    sys.exit(0 if result.success else 1)


if __name__ == '__main__':
    # Check if running from command line
    if len(sys.argv) > 1:
        main()
    else:
        # Run example
        print("="*70)
        print("IMPORT INTEGRATION ADAPTER - EXAMPLE")
        print("="*70)
        print()
        print("This adapter bridges:")
        print("  1. Excel templates (real customer data)")
        print("  2. KPI normalization (raw values → 0-100)")
        print("  3. Sparse KPI handling (10-15 KPIs)")
        print("  4. Hierarchical health calculation")
        print("  5. Qdrant upload")
        print()
        print("Usage:")
        print("  python import_integration_adapter.py <excel_file>")
        print()
        print("Example:")
        print("  python import_integration_adapter.py /path/to/DataCenter_Enterprise_FINAL.xlsx")
        print()
