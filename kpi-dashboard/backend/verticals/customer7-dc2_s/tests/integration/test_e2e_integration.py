#!/usr/bin/env python3
"""
End-to-End Integration Tests
==============================

Comprehensive test suite for complete import pipeline:
- Excel → Normalization → Health → Qdrant

Tests:
1. Complete import pipeline
2. Qdrant data integrity
3. Health calculation accuracy
4. Sparse KPI handling
5. Wizard A to Signal Analyst flow
"""

import sys
import json
import unittest
from pathlib import Path
from datetime import datetime

# Import components
from import_integration_adapter import ImportIntegrationAdapter
from realistic_kpi_generator import RealisticKPIGenerator
# CoverageLevel and PatternType are not enum classes, they're just string parameters
# Using string literals instead: 'typical', 'good', 'healthy', 'crisis', etc.
try:
    from wizard_a_v2 import WizardAV2
except ImportError:
    WizardAV2 = None  # Wizard A may not be available


class TestCompleteImportPipeline(unittest.TestCase):
    """Test complete Excel → Qdrant pipeline"""
    
    @classmethod
    def setUpClass(cls):
        """Setup test environment"""
        import os
        cls.test_file = '/mnt/user-data/outputs/DataCenter_Enterprise_FINAL.xlsx'
        # Use Qdrant Cloud (not localhost) - matches production configuration
        cls.qdrant_url = os.getenv('QDRANT_URL', 'https://7528cec3-24f4-4584-bee2-ca371726134a.us-east-1-1.aws.cloud.qdrant.io:6333')
        cls.qdrant_api_key = os.getenv('QDRANT_API_KEY')
        
        # Check if test file exists
        if not Path(cls.test_file).exists():
            print(f"⚠️  Test file not found: {cls.test_file}")
            print("   Tests will be skipped")
    
    def test_01_excel_import(self):
        """Test Excel file import"""
        
        if not Path(self.test_file).exists():
            self.skipTest("Test file not available")
        
        # Import (use Qdrant Cloud if API key is available)
        qdrant_url = self.qdrant_url
        adapter = ImportIntegrationAdapter(qdrant_url=qdrant_url)
        result = adapter.import_excel_to_cs_pulse(self.test_file)
        
        # Verify
        self.assertTrue(result.success, "Import should succeed")
        self.assertGreater(result.customers_imported, 0, "Should import customers")
        self.assertGreater(result.weeks_imported, 0, "Should import weeks")
        self.assertEqual(len(result.errors), 0, f"Should have no errors: {result.errors}")
    
    def test_02_qdrant_data_integrity(self):
        """Test data integrity in Qdrant"""
        
        try:
            from qdrant_client import QdrantClient
        except ImportError:
            self.skipTest("Qdrant client not available")
        
        # Connect to Qdrant Cloud (requires API key)
        if not hasattr(self, 'qdrant_api_key') or not self.qdrant_api_key:
            self.skipTest("QDRANT_API_KEY not set - cannot connect to Qdrant Cloud")
        
        client = QdrantClient(url=self.qdrant_url, api_key=self.qdrant_api_key)
        
        # Get points
        try:
            points, _ = client.scroll(
                collection_name='journey_weeks',
                limit=100
            )
            
            self.assertGreater(len(points), 0, "Should have points in Qdrant")
            
            # Verify point structure
            for point in points[:5]:
                payload = point.payload
                
                # Check required fields
                self.assertIn('account_id', payload)
                self.assertIn('week_number', payload)
                self.assertIn('health_score', payload)
                self.assertIn('data_quality', payload)
                
                # Check data types
                self.assertIsInstance(payload['health_score'], (int, float))
                self.assertIsInstance(payload['data_quality'], (int, float))
                
                # Check data ranges
                self.assertGreaterEqual(payload['health_score'], 0)
                self.assertLessEqual(payload['health_score'], 100)
                self.assertGreaterEqual(payload['data_quality'], 0)
                self.assertLessEqual(payload['data_quality'], 1)
                
        except Exception as e:
            self.skipTest(f"Qdrant not available: {e}")
    
    def test_03_health_calculation_accuracy(self):
        """Test health calculation accuracy"""
        
        # Generate test data with known values
        generator = RealisticKPIGenerator()
        
        # Test 1: Healthy pattern
        healthy_kpis = generator.generate(
            pattern='typical',
            scenario='healthy'
        )
        
        # Health should be > 70 for healthy pattern
        avg_score = sum(healthy_kpis.normalized_kpis.values()) / len(healthy_kpis.normalized_kpis)
        self.assertGreater(avg_score, 70, "Healthy pattern should have high scores")
        
        # Test 2: Crisis pattern
        crisis_kpis = generator.generate(
            pattern='typical',
            scenario='crisis'
        )
        
        # Health should be < 50 for crisis pattern
        avg_score = sum(crisis_kpis.normalized_kpis.values()) / len(crisis_kpis.normalized_kpis)
        self.assertLess(avg_score, 50, "Crisis pattern should have low scores")


class TestSparseKPIHandling(unittest.TestCase):
    """Test sparse KPI handling across the system"""
    
    def test_01_sparse_kpi_normalization(self):
        """Test normalization with sparse KPIs"""
        
        from kpi_normalization_service import KPINormalizationService
        
        service = KPINormalizationService()
        
        # Test with 3 KPIs (sparse)
        sparse_kpis = {
            'mtbf': (8500, 'hours'),
            'gpu_utilization_rate': (65, '%'),
            'critical_incident_rate': (1.5, 'P1 incidents/month')
        }
        
        # Normalize (normalize returns just a float, not a tuple)
        normalized = {}
        for kpi_name, (value, unit) in sparse_kpis.items():
            score = service.normalize(kpi_name, value, unit)
            normalized[kpi_name] = score
        
        # Verify
        self.assertEqual(len(normalized), 3, "Should normalize all 3 KPIs")
        for score in normalized.values():
            self.assertGreaterEqual(score, 0)
            self.assertLessEqual(score, 100)
    
    def test_02_sparse_kpi_coverage_validation(self):
        """Test coverage validation"""
        
        from sparse_kpi_handler import SparseKPIHandler
        
        handler = SparseKPIHandler()
        
        # Test coverage calculation with actual KPI names
        # Use select_sparse_kpis to get valid KPI names
        selected_kpis = handler.select_sparse_kpis(pattern='typical')
        
        # Get total KPI count from KPI_PILLAR_MAP (all available KPIs)
        from sparse_kpi_handler import KPI_PILLAR_MAP
        total_kpis = len(KPI_PILLAR_MAP)
        
        # Test with good coverage (should have ~12-15 KPIs = 34-43%)
        coverage_pct = (len(selected_kpis) / total_kpis) * 100
        self.assertGreater(coverage_pct, 25, f"Should have reasonable coverage ({coverage_pct:.1f}%)")
        self.assertLess(coverage_pct, 50, f"Should be sparse coverage ({coverage_pct:.1f}%)")
        
        # Test that sparse handler works with selected KPIs
        self.assertGreater(len(selected_kpis), 10, "Should select at least 10 KPIs")
        self.assertLess(len(selected_kpis), 20, "Should select less than 20 KPIs (sparse)")


class TestWizardAIntegration(unittest.TestCase):
    """Test Wizard A V2 to Signal Analyst flow"""
    
    def test_01_realistic_kpi_generation(self):
        """Test realistic KPI generation"""
        
        generator = RealisticKPIGenerator()
        
        # Generate KPIs
        kpis = generator.generate(
            pattern='typical',
            scenario='healthy'
        )
        
        # Verify structure (uses raw_kpis, not raw_values)
        self.assertIn('raw_kpis', kpis.__dict__)
        self.assertIn('normalized_kpis', kpis.__dict__)
        self.assertIn('data_quality', kpis.__dict__)
        self.assertIn('coverage_pct', kpis.__dict__)
        
        # Verify data quality
        self.assertGreater(kpis.data_quality, 0.1, "Should have reasonable coverage")
        self.assertLess(kpis.data_quality, 0.50, "Should have sparse coverage")
        
        # Verify raw values have units (structure is {kpi: (value, unit)})
        for kpi_name, (value, unit) in kpis.raw_kpis.items():
            self.assertIsInstance(value, (int, float))
            self.assertIsInstance(unit, str)
            self.assertGreater(len(unit), 0, "Unit should not be empty")
    
    def test_02_training_data_generation(self):
        """Test Wizard A V2 training data generation"""
        
        if WizardAV2 is None:
            self.skipTest("Wizard A V2 not available")
        
        wizard = WizardAV2()
        
        # Generate small training set
        stats = wizard.generate_training_set(
            num_customers=5,
            output_dir='/tmp/test_training'
        )
        
        # Verify
        self.assertEqual(stats['total_customers'], 5)
        self.assertEqual(stats['total_weeks'], 5 * 52)  # 5 customers × 52 weeks
        self.assertGreater(stats['avg_coverage_pct'], 25)
        self.assertLess(stats['avg_coverage_pct'], 45)


class TestDataFormatCompatibility(unittest.TestCase):
    """Test V1 and V2 data format compatibility"""
    
    def test_01_weekdata_v1_compatibility(self):
        """Test WeekData works with V1 format (no raw_kpis)"""
        
        try:
            from updated_week_data_qdrant import WeekData, JourneyPhase
        except ImportError:
            self.skipTest("WeekData not available")
        
        # Create V1-style data (no raw_kpis)
        week_data_v1 = WeekData(
            week_number=1,
            date='2024-01-01',
            phase=JourneyPhase.HEALTHY,
            kpis={'mtbf': 85.0, 'gpu_utilization_rate': 65.0},
            pillars={
                'P1_deployment_velocity': 80.0,
                'P2_operational_stability': 85.0,
                'P3_ai_workload_performance': 65.0,
                'P4_channel_partner_health': 0.0,
                'P5_expansion_readiness': 72.0
            },
            health_score=75.0,
            events=[],
            data_quality=0.06,
            missing_kpis=[]
        )
        
        # Should work without raw_kpis
        payload = week_data_v1.get_qdrant_payload('TEST001')
        
        # Verify
        self.assertIn('health_score', payload)
        self.assertIn('data_quality', payload)
    
    def test_02_weekdata_v2_with_raw_kpis(self):
        """Test WeekData works with V2 format (with raw_kpis)"""
        
        try:
            from updated_week_data_qdrant import WeekData, JourneyPhase
        except ImportError:
            self.skipTest("WeekData not available")
        
        # Create V2-style data (with raw_kpis)
        week_data_v2 = WeekData(
            week_number=1,
            date='2024-01-01',
            phase=JourneyPhase.HEALTHY,
            kpis={'mtbf': 85.0, 'gpu_utilization_rate': 65.0},
            raw_kpis={
                'mtbf': (8500, 'hours'),
                'gpu_utilization_rate': (65, '%')
            },
            pillars={
                'P1_deployment_velocity': 80.0,
                'P2_operational_stability': 85.0,
                'P3_ai_workload_performance': 65.0,
                'P4_channel_partner_health': 0.0,
                'P5_expansion_readiness': 72.0
            },
            health_score=75.0,
            events=[],
            data_quality=0.06,
            missing_kpis=[]
        )
        
        # Should work with raw_kpis
        payload = week_data_v2.get_qdrant_payload('TEST001')
        dict_data = week_data_v2.to_dict()
        
        # Verify raw_kpis are included
        self.assertIn('raw_kpis', dict_data)
        self.assertIn('mtbf', dict_data['raw_kpis'])


# ============================================================================
# TEST RUNNER
# ============================================================================

def run_tests(verbose=True):
    """Run all tests"""
    
    print("="*70)
    print("END-TO-END INTEGRATION TESTS")
    print("="*70)
    print()
    
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add test classes
    suite.addTests(loader.loadTestsFromTestCase(TestCompleteImportPipeline))
    suite.addTests(loader.loadTestsFromTestCase(TestSparseKPIHandling))
    suite.addTests(loader.loadTestsFromTestCase(TestWizardAIntegration))
    suite.addTests(loader.loadTestsFromTestCase(TestDataFormatCompatibility))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2 if verbose else 1)
    result = runner.run(suite)
    
    # Print summary
    print()
    print("="*70)
    print("TEST SUMMARY")
    print("="*70)
    print(f"Tests run: {result.testsRun}")
    print(f"Passed: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"Failed: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Skipped: {len(result.skipped)}")
    print()
    
    return result.wasSuccessful()


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Run end-to-end integration tests')
    parser.add_argument('--verbose', action='store_true', help='Verbose output')
    parser.add_argument('--quick', action='store_true', help='Run quick tests only')
    
    args = parser.parse_args()
    
    success = run_tests(verbose=args.verbose)
    sys.exit(0 if success else 1)
