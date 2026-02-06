#!/usr/bin/env python3
"""
CS Pulse DC2_S Integration Tests
================================

Tests each phase of the integration.

Usage:
    python3 test_integration.py --phase 2
    python3 test_integration.py --all
    python3 test_integration.py --safety  # Verify SaaS not modified
"""

import os
import sys
import argparse
from pathlib import Path


# Colors for output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
RESET = '\033[0m'


def print_ok(msg): print(f"{GREEN}✅ {msg}{RESET}")
def print_fail(msg): print(f"{RED}❌ {msg}{RESET}")
def print_warn(msg): print(f"{YELLOW}⚠️  {msg}{RESET}")
def print_header(msg): print(f"\n{'='*60}\n{msg}\n{'='*60}")


class IntegrationTester:
    def __init__(self, base_dir: str = None):
        self.base_dir = Path(base_dir or os.environ.get(
            'BASE_DIR', 
            os.path.expanduser('~/CustomerSuccessAI-DataCenter/kpi-dashboard/backend/verticals/customer{CUSTOMER_ID}-dc2_s')
        ))
        self.results = {}
    
    def test_phase_1_files(self) -> bool:
        """Phase 1: Verify file structure"""
        print_header("PHASE 1: File Structure")
        
        required_dirs = [
            'journey/scripts',
            'journey/data/phase1',
            'journey/data/phase2', 
            'journey/data/phase3',
            'journey/config',
            'agents/signal_analyst',
            'services',
            'api/blueprints',
            'tests/integration',
        ]
        
        required_files = [
            'journey/scripts/enhanced_hierarchical_journey_generator.py',
            'journey/config/bootstrap_weights_config.json',
            'agents/signal_analyst/test_signal_analyst_v4_smart_override.py',
            'services/excel_import_service.py',
            'api/blueprints/import_blueprint.py',
        ]
        
        all_ok = True
        
        # Check directories
        for dir_path in required_dirs:
            full_path = self.base_dir / dir_path
            if full_path.exists():
                print_ok(f"Directory exists: {dir_path}")
            else:
                print_fail(f"Missing directory: {dir_path}")
                all_ok = False
        
        # Check files
        for file_path in required_files:
            full_path = self.base_dir / file_path
            if full_path.exists():
                print_ok(f"File exists: {file_path}")
            else:
                print_fail(f"Missing file: {file_path}")
                all_ok = False
        
        self.results['phase_1'] = all_ok
        return all_ok
    
    def test_phase_2_services(self) -> bool:
        """Phase 2: Test Python services"""
        print_header("PHASE 2: Python Services")
        
        # Add services to path
        services_dir = self.base_dir / 'services'
        sys.path.insert(0, str(services_dir))
        
        all_ok = True
        
        # Test KPI Normalization Service
        try:
            from kpi_normalization_service import get_normalization_service
            service = get_normalization_service()
            
            # Test normalization
            score = service.normalize('mtbf', 8500, 'hours')
            assert 80 <= score <= 90, f"MTBF 8500h should be ~85, got {score}"
            
            # Test denormalization
            raw, unit = service.denormalize('mtbf', 85.0)
            assert 8000 <= raw <= 9000, f"Score 85 should be ~8500h, got {raw}"
            
            # Test KPI count
            kpis = service.get_all_kpi_codes()
            assert len(kpis) >= 30, f"Should have 30+ KPIs, got {len(kpis)}"
            
            print_ok(f"KPI Normalization Service: {len(kpis)} KPIs defined")
        except Exception as e:
            print_fail(f"KPI Normalization Service: {e}")
            all_ok = False
        
        # Test Sparse KPI Handler
        try:
            from sparse_kpi_handler import get_sparse_handler
            handler = get_sparse_handler()
            
            # Test sparse selection
            selected = handler.select_sparse_kpis('typical')
            assert 10 <= len(selected) <= 20, f"Typical should select 10-20 KPIs, got {len(selected)}"
            
            print_ok(f"Sparse KPI Handler: selected {len(selected)} KPIs")
        except Exception as e:
            print_fail(f"Sparse KPI Handler: {e}")
            all_ok = False
        
        # Test Realistic KPI Generator
        try:
            from realistic_kpi_generator import get_realistic_generator
            gen = get_realistic_generator()
            
            # Test generation
            result = gen.generate('typical', 'healthy')
            # Allow wider range due to randomness in sparse KPI selection
            assert 10 <= result.coverage_pct <= 60, f"Coverage should be 10-60%, got {result.coverage_pct}"
            assert len(result.raw_kpis) > 0, "Should generate raw KPIs"
            
            # Verify raw values have units
            for kpi, (val, unit) in result.raw_kpis.items():
                assert unit, f"KPI {kpi} missing unit"
            
            print_ok(f"Realistic KPI Generator: {result.coverage_pct}% coverage")
        except Exception as e:
            print_fail(f"Realistic KPI Generator: {e}")
            all_ok = False
        
        self.results['phase_2'] = all_ok
        return all_ok
    
    def test_phase_3_database(self) -> bool:
        """Phase 3: Test database schema"""
        print_header("PHASE 3: Database Schema")
        
        try:
            import psycopg2
            
            db_url = os.environ.get('DATABASE_URL', 
                'postgresql://dcuser:dcpass123@localhost:5432/cs_pulse_datacenter')
            
            conn = psycopg2.connect(db_url)
            cur = conn.cursor()
            
            # Check dc2s tables exist
            dc2s_tables = [
                'dc2s_kpis',
                'dc2s_journey_weeks',
                'dc2s_journey_events',
                'dc2s_milestones',
                'dc2s_predictions',
            ]
            
            all_ok = True
            for table in dc2s_tables:
                cur.execute(f"SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = '{table}')")
                exists = cur.fetchone()[0]
                if exists:
                    print_ok(f"Table exists: {table}")
                else:
                    print_warn(f"Table not found: {table} (may need to run init_database_schema.py)")
                    all_ok = False
            
            conn.close()
            self.results['phase_3'] = all_ok
            return all_ok
            
        except Exception as e:
            print_fail(f"Database connection: {e}")
            self.results['phase_3'] = False
            return False
    
    def test_phase_4_qdrant(self) -> bool:
        """Phase 4: Test Qdrant collections"""
        print_header("PHASE 4: Qdrant Collections")
        
        try:
            from qdrant_client import QdrantClient
            from dotenv import load_dotenv
            
            # Load environment variables from .env file
            env_path = os.path.join(os.path.dirname(__file__), '../../../../.env')
            if os.path.exists(env_path):
                load_dotenv(env_path)
            
            url = os.environ.get('QDRANT_URL')
            api_key = os.environ.get('QDRANT_API_KEY')
            
            if not url or not api_key:
                print_warn("QDRANT_URL or QDRANT_API_KEY not set")
                self.results['phase_4'] = False
                return False
            
            client = QdrantClient(url=url, api_key=api_key)
            collections = [c.name for c in client.get_collections().collections]
            
            # Required collections for DC2_S
            required = [
                'kpi_dashboard_vectors_customer_{CUSTOMER_ID}',
            ]
            
            optional = [
                'journey_weeks_customer_{CUSTOMER_ID}',
                'journey_signals_customer_{CUSTOMER_ID}',
                'journey_training_customer_{CUSTOMER_ID}',
            ]
            
            all_ok = True
            for coll in required:
                if coll in collections:
                    print_ok(f"Collection exists: {coll}")
                else:
                    print_fail(f"Missing collection: {coll}")
                    all_ok = False
            
            for coll in optional:
                if coll in collections:
                    print_ok(f"Collection exists: {coll}")
                else:
                    print_warn(f"Optional collection not found: {coll}")
            
            self.results['phase_4'] = all_ok
            return all_ok
            
        except Exception as e:
            print_fail(f"Qdrant connection: {e}")
            self.results['phase_4'] = False
            return False
    
    def test_phase_5_data(self) -> bool:
        """Phase 5: Test data loading"""
        print_header("PHASE 5: Data Loading")
        
        # Check data files exist (check both raw/ and direct paths)
        data_files = [
            ('journey/data/raw/phase1/account_10007_events.csv', 'journey/data/phase1/account_10007_events.csv'),
            ('journey/data/raw/phase2/account_10001_events.csv', 'journey/data/phase2/account_10001_events.csv'),
            ('journey/data/raw/phase2/account_10003_events.csv', 'journey/data/phase2/account_10003_events.csv'),
            ('journey/data/raw/phase3/all_accounts_kpis.csv', 'journey/data/phase3/all_accounts_kpis.csv'),
        ]
        
        all_ok = True
        for raw_path, direct_path in data_files:
            # Check both raw/ path and direct path
            full_path = self.base_dir / raw_path
            file_path_to_show = raw_path
            if not full_path.exists():
                full_path = self.base_dir / direct_path
                file_path_to_show = direct_path
            
            if full_path.exists():
                # Check file has content
                size = full_path.stat().st_size
                print_ok(f"Data file: {file_path_to_show} ({size:,} bytes)")
            else:
                print_fail(f"Missing data: {raw_path} or {direct_path}")
                all_ok = False
        
        self.results['phase_5'] = all_ok
        return all_ok
    
    def test_phase_6_signal_analyst(self) -> bool:
        """Phase 6: Test Signal Analyst"""
        print_header("PHASE 6: Signal Analyst")
        
        agent_dir = self.base_dir / 'agents/signal_analyst'
        
        if not (agent_dir / 'test_signal_analyst_v4_smart_override.py').exists():
            print_fail("Signal Analyst V4 not found")
            self.results['phase_6'] = False
            return False
        
        # Just verify file exists and has content
        file_size = (agent_dir / 'test_signal_analyst_v4_smart_override.py').stat().st_size
        if file_size > 10000:  # Should be ~37KB
            print_ok(f"Signal Analyst V4 exists ({file_size:,} bytes)")
            self.results['phase_6'] = True
            return True
        else:
            print_fail(f"Signal Analyst V4 too small ({file_size} bytes)")
            self.results['phase_6'] = False
            return False
    
    def test_safety_saas(self) -> bool:
        """Safety check: Verify SaaS data not modified"""
        print_header("SAFETY CHECK: SaaS Data")
        
        try:
            import psycopg2
            
            db_url = os.environ.get('DATABASE_URL',
                'postgresql://dcuser:dcpass123@localhost:5432/cs_pulse_datacenter')
            
            conn = psycopg2.connect(db_url)
            cur = conn.cursor()
            
            # Check Customer 1 (Syntara) accounts unchanged
            cur.execute("SELECT COUNT(*) FROM accounts WHERE customer_id = 1")
            saas_accounts = cur.fetchone()[0]
            
            # Check SaaS KPIs unchanged
            cur.execute("SELECT COUNT(*) FROM kpis")
            saas_kpis = cur.fetchone()[0]
            
            conn.close()
            
            # Expected values (from original state)
            expected_accounts = 36
            expected_kpis = 2088
            
            all_ok = True
            if saas_accounts == expected_accounts:
                print_ok(f"SaaS accounts unchanged: {saas_accounts}")
            else:
                print_fail(f"SaaS accounts changed! Expected {expected_accounts}, got {saas_accounts}")
                all_ok = False
            
            if saas_kpis == expected_kpis:
                print_ok(f"SaaS KPIs unchanged: {saas_kpis}")
            else:
                print_fail(f"SaaS KPIs changed! Expected {expected_kpis}, got {saas_kpis}")
                all_ok = False
            
            return all_ok
            
        except Exception as e:
            print_fail(f"Safety check failed: {e}")
            return False
    
    def run_all(self):
        """Run all tests"""
        print_header("CS PULSE DC2_S INTEGRATION TESTS")
        
        self.test_phase_1_files()
        self.test_phase_2_services()
        self.test_phase_3_database()
        self.test_phase_4_qdrant()
        self.test_phase_5_data()
        self.test_phase_6_signal_analyst()
        self.test_safety_saas()
        
        # Summary
        print_header("SUMMARY")
        total = len(self.results)
        passed = sum(1 for v in self.results.values() if v)
        
        for phase, result in self.results.items():
            status = f"{GREEN}PASS{RESET}" if result else f"{RED}FAIL{RESET}"
            print(f"  {phase}: {status}")
        
        print(f"\nTotal: {passed}/{total} phases passed")
        
        if passed == total:
            print_ok("All tests passed!")
            return True
        else:
            print_fail(f"{total - passed} phase(s) failed")
            return False


def main():
    parser = argparse.ArgumentParser(description='CS Pulse DC2_S Integration Tests')
    parser.add_argument('--phase', type=int, help='Run specific phase (1-6)')
    parser.add_argument('--all', action='store_true', help='Run all tests')
    parser.add_argument('--safety', action='store_true', help='Run safety check only')
    parser.add_argument('--base-dir', type=str, help='Base directory for DC2_S')
    
    args = parser.parse_args()
    
    tester = IntegrationTester(args.base_dir)
    
    if args.safety:
        tester.test_safety_saas()
    elif args.phase:
        phase_tests = {
            1: tester.test_phase_1_files,
            2: tester.test_phase_2_services,
            3: tester.test_phase_3_database,
            4: tester.test_phase_4_qdrant,
            5: tester.test_phase_5_data,
            6: tester.test_phase_6_signal_analyst,
        }
        if args.phase in phase_tests:
            phase_tests[args.phase]()
        else:
            print(f"Invalid phase: {args.phase}. Choose 1-6.")
    else:
        tester.run_all()


if __name__ == "__main__":
    main()
