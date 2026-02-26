#!/usr/bin/env python3
"""
Test Bootstrap Weights Integration
==================================

Tests that bootstrap weights are properly loaded and integrated
with the Signal Analyst system.

Usage:
    python3 test_bootstrap_weights.py
    python3 test_bootstrap_weights.py --verbose
"""

import os
import sys
import argparse

# Colors
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
RESET = '\033[0m'

def print_ok(msg): print(f"{GREEN}✅ {msg}{RESET}")
def print_fail(msg): print(f"{RED}❌ {msg}{RESET}")
def print_warn(msg): print(f"{YELLOW}⚠️  {msg}{RESET}")
def print_header(msg): print(f"\n{'='*60}\n{msg}\n{'='*60}")


def test_bootstrap_loader(verbose=False):
    """Test bootstrap weights loader"""
    print_header("TEST 1: Bootstrap Weights Loader")
    
    try:
        from bootstrap_weights_loader import get_bootstrap_weights, reset_bootstrap_weights
        
        # Reset singleton for clean test
        reset_bootstrap_weights()
        
        # Load weights
        manager = get_bootstrap_weights()
        
        # Verify loaded
        assert manager.is_loaded, "Weights not loaded"
        print_ok("Weights loaded successfully")
        
        # Check pillar weights
        pillar_weights = manager.get_pillar_weights()
        assert len(pillar_weights) >= 5, f"Expected 5 pillars, got {len(pillar_weights)}"
        print_ok(f"Pillar weights loaded: {len(pillar_weights)} pillars")
        
        if verbose:
            for pillar, weight in pillar_weights.items():
                print(f"    {pillar}: {weight:.2f}")
        
        # Check weights sum to ~1.0
        total = sum(pillar_weights.values())
        assert 0.95 <= total <= 1.05, f"Pillar weights should sum to ~1.0, got {total}"
        print_ok(f"Pillar weights sum to {total:.2f}")
        
        # Check thresholds
        thresholds = manager.get_thresholds()
        assert 'healthy' in thresholds, "Missing healthy threshold"
        assert 'at_risk' in thresholds, "Missing at_risk threshold"
        assert 'crisis' in thresholds, "Missing crisis threshold"
        print_ok("Thresholds configured")
        
        # Check critical KPIs
        critical = manager.get_critical_kpis()
        assert len(critical) >= 3, f"Expected 3+ critical KPIs, got {len(critical)}"
        print_ok(f"Critical KPIs defined: {len(critical)}")
        
        if verbose:
            print(f"    Critical: {critical}")
        
        return True
        
    except Exception as e:
        print_fail(f"Bootstrap loader test failed: {e}")
        return False


def test_weighted_health_calculation(verbose=False):
    """Test weighted health calculation"""
    print_header("TEST 2: Weighted Health Calculation")
    
    try:
        from bootstrap_weights_loader import get_bootstrap_weights
        
        manager = get_bootstrap_weights()
        
        # Test case 1: Healthy scores
        healthy_scores = {
            'P1_deployment': 85,
            'P2_stability': 80,
            'P3_performance': 78,
            'P4_channel': 90,
            'P5_expansion': 82
        }
        
        health = manager.calculate_weighted_health(healthy_scores)
        classification = manager.classify_health(health)
        
        assert 70 <= health <= 100, f"Healthy scores should give health 70-100, got {health}"
        assert classification == 'healthy', f"Should classify as healthy, got {classification}"
        print_ok(f"Healthy case: score={health:.1f}, class={classification}")
        
        # Test case 2: At-risk scores
        at_risk_scores = {
            'P1_deployment': 65,
            'P2_stability': 55,
            'P3_performance': 50,
            'P4_channel': 60,
            'P5_expansion': 45
        }
        
        health = manager.calculate_weighted_health(at_risk_scores)
        classification = manager.classify_health(health)
        
        assert 40 <= health <= 70, f"At-risk scores should give health 40-70, got {health}"
        assert classification == 'at_risk', f"Should classify as at_risk, got {classification}"
        print_ok(f"At-risk case: score={health:.1f}, class={classification}")
        
        # Test case 3: Crisis scores
        crisis_scores = {
            'P1_deployment': 30,
            'P2_stability': 25,
            'P3_performance': 35,
            'P4_channel': 40,
            'P5_expansion': 20
        }
        
        health = manager.calculate_weighted_health(crisis_scores)
        classification = manager.classify_health(health)
        
        assert health < 40, f"Crisis scores should give health <40, got {health}"
        assert classification == 'crisis', f"Should classify as crisis, got {classification}"
        print_ok(f"Crisis case: score={health:.1f}, class={classification}")
        
        return True
        
    except Exception as e:
        print_fail(f"Weighted health test failed: {e}")
        return False


def test_kpi_weights(verbose=False):
    """Test KPI weights within pillars"""
    print_header("TEST 3: KPI Weights Within Pillars")
    
    try:
        from bootstrap_weights_loader import get_bootstrap_weights
        
        manager = get_bootstrap_weights()
        
        all_kpi_weights = manager.get_all_kpi_weights()
        
        for pillar, kpi_weights in all_kpi_weights.items():
            # Check weights exist
            assert len(kpi_weights) >= 2, f"{pillar} should have 2+ KPIs"
            
            # Check weights sum to ~1.0
            total = sum(kpi_weights.values())
            assert 0.95 <= total <= 1.05, f"{pillar} KPI weights should sum to ~1.0, got {total}"
            
            print_ok(f"{pillar}: {len(kpi_weights)} KPIs, sum={total:.2f}")
            
            if verbose:
                for kpi, weight in kpi_weights.items():
                    print(f"      {kpi}: {weight:.2f}")
        
        return True
        
    except Exception as e:
        print_fail(f"KPI weights test failed: {e}")
        return False


def test_integration_with_services(verbose=False):
    """Test integration with KPI normalization service"""
    print_header("TEST 4: Integration with KPI Services")
    
    try:
        from bootstrap_weights_loader import get_bootstrap_weights
        from kpi_normalization_service import get_normalization_service
        from sparse_kpi_handler import get_sparse_handler
        
        bootstrap = get_bootstrap_weights()
        norm_service = get_normalization_service()
        sparse_handler = get_sparse_handler()
        
        # Get critical KPIs from bootstrap
        critical_kpis = bootstrap.get_critical_kpis()
        
        # Verify critical KPIs exist in normalization service
        all_kpis = set(norm_service.get_all_kpi_codes())
        
        for kpi in critical_kpis:
            if kpi in all_kpis:
                print_ok(f"Critical KPI '{kpi}' found in normalization service")
            else:
                print_warn(f"Critical KPI '{kpi}' not in normalization service")
        
        # Test sparse selection with bootstrap weights
        selected = sparse_handler.select_sparse_kpis('typical')
        
        # Check that critical KPIs are likely included
        critical_included = sum(1 for kpi in critical_kpis if kpi in selected)
        print_ok(f"Sparse selection includes {critical_included}/{len(critical_kpis)} critical KPIs")
        
        return True
        
    except Exception as e:
        print_fail(f"Integration test failed: {e}")
        return False


def test_config_file_loading(verbose=False):
    """Test loading from actual config files"""
    print_header("TEST 5: Config File Loading")
    
    # Find config directory
    base_dir = os.environ.get('BASE_DIR', 
        os.path.expanduser('~/CustomerSuccessAI-DataCenter/kpi-dashboard/backend/verticals/customer24-dc2_s'))
    config_dir = os.path.join(base_dir, 'journey', 'config')
    
    print(f"Config directory: {config_dir}")
    
    # Check files exist
    weights_file = os.path.join(config_dir, 'bootstrap_weights_config.json')
    mapping_file = os.path.join(config_dir, 'kpi_mapping_config.json')
    
    if os.path.exists(weights_file):
        print_ok(f"Found: bootstrap_weights_config.json")
        if verbose:
            import json
            with open(weights_file) as f:
                data = json.load(f)
                print(f"    Version: {data.get('version', 'unknown')}")
                print(f"    Keys: {list(data.keys())}")
    else:
        print_warn(f"Not found: {weights_file}")
    
    if os.path.exists(mapping_file):
        print_ok(f"Found: kpi_mapping_config.json")
        if verbose:
            import json
            with open(mapping_file) as f:
                data = json.load(f)
                print(f"    Keys: {list(data.keys())}")
    else:
        print_warn(f"Not found: {mapping_file}")
    
    return True


def main():
    parser = argparse.ArgumentParser(description='Test Bootstrap Weights Integration')
    parser.add_argument('--verbose', '-v', action='store_true', help='Show detailed output')
    args = parser.parse_args()
    
    # Add services to path
    base_dir = os.environ.get('BASE_DIR',
        os.path.expanduser('~/CustomerSuccessAI-DataCenter/kpi-dashboard/backend/verticals/customer24-dc2_s'))
    services_dir = os.path.join(base_dir, 'services')
    sys.path.insert(0, services_dir)
    
    print("=" * 60)
    print("BOOTSTRAP WEIGHTS INTEGRATION TESTS")
    print("=" * 60)
    
    results = []
    
    results.append(('Config Files', test_config_file_loading(args.verbose)))
    results.append(('Bootstrap Loader', test_bootstrap_loader(args.verbose)))
    results.append(('Weighted Health', test_weighted_health_calculation(args.verbose)))
    results.append(('KPI Weights', test_kpi_weights(args.verbose)))
    results.append(('Service Integration', test_integration_with_services(args.verbose)))
    
    # Summary
    print_header("SUMMARY")
    
    passed = sum(1 for _, r in results if r)
    total = len(results)
    
    for name, result in results:
        status = f"{GREEN}PASS{RESET}" if result else f"{RED}FAIL{RESET}"
        print(f"  {name}: {status}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print_ok("All bootstrap weights tests passed!")
        return 0
    else:
        print_fail(f"{total - passed} test(s) failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
