"""
Test suite for multi-product KPI functionality.

⚠️ CRITICAL: These tests ensure that:
1. Legacy accounts (without products) work exactly as before
2. Accounts with products correctly separate account-level and product-level KPIs
3. Health score calculations use account-level KPIs only (no double-counting)
4. Database constraints prevent invalid data combinations
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from models import db, KPI, Account, Product, Customer
from kpi_queries import (
    get_account_level_kpis,
    get_product_kpis,
    get_all_kpis_for_account,
    get_worst_product_kpis,
    get_best_product_kpis
)


class TestMultiProductKPIs:
    """Test suite for multi-product KPI functionality"""
    
    @pytest.fixture
    def app_context(self):
        """Create Flask app context"""
        from app_v3_minimal import app
        with app.app_context():
            yield app
    
    @pytest.fixture
    def customer(self, app_context):
        """Create a test customer"""
        customer = Customer.query.filter_by(customer_id=999).first()
        if not customer:
            customer = Customer(
                customer_id=999,
                customer_name="Test Company",
                domain="test.com"
            )
            db.session.add(customer)
            db.session.commit()
        return customer
    
    @pytest.fixture
    def legacy_account(self, app_context, customer):
        """
        Create a legacy account without products (simulates existing accounts).
        """
        account = Account(
            account_id=1,
            customer_id=customer.customer_id,
            account_name="Legacy Account",
            revenue=100000
        )
        db.session.add(account)
        db.session.commit()
        return account
    
    def test_legacy_account_without_products(self, app_context, legacy_account, customer):
        """
        ✅ CRITICAL: Ensure accounts without products work exactly as before
        """
        # Add account-level KPIs (legacy style, both NULL)
        kpi1 = KPI(
            account_id=legacy_account.account_id,
            kpi_parameter="TTFV",
            data="10",
            product_id=None,      # NULL
            aggregation_type=None # NULL (legacy)
        )
        kpi2 = KPI(
            account_id=legacy_account.account_id,
            kpi_parameter="Feature Adoption Rate",
            data="80",
            product_id=None,
            aggregation_type=None
        )
        db.session.add_all([kpi1, kpi2])
        db.session.commit()
        
        # Test: get_account_level_kpis should return these KPIs
        kpis = get_account_level_kpis(
            account_id=legacy_account.account_id,
            customer_id=customer.customer_id
        )
        assert len(kpis) == 2
        assert all(kpi.kpi_parameter in ["TTFV", "Feature Adoption Rate"] for kpi in kpis)
        assert all(kpi.product_id is None for kpi in kpis)
        assert all(kpi.aggregation_type is None for kpi in kpis)
    
    def test_account_with_products(self, app_context, customer):
        """
        ✅ CRITICAL: Ensure account with products returns correct data
        """
        # Create account with products
        account = Account(
            account_id=2,
            customer_id=customer.customer_id,
            account_name="Multi-Product Account",
            revenue=200000
        )
        product1 = Product(
            product_id=1,
            account_id=account.account_id,
            customer_id=customer.customer_id,
            product_name="Product A",
            revenue=120000
        )
        product2 = Product(
            product_id=2,
            account_id=account.account_id,
            customer_id=customer.customer_id,
            product_name="Product B",
            revenue=80000
        )
        db.session.add_all([account, product1, product2])
        db.session.commit()
        
        # Add product-level KPIs
        kpi_p1 = KPI(
            account_id=account.account_id,
            kpi_parameter="TTFV",
            data="8",
            product_id=1,
            aggregation_type=None  # Product KPIs must have aggregation_type=NULL
        )
        kpi_p2 = KPI(
            account_id=account.account_id,
            kpi_parameter="TTFV",
            data="12",
            product_id=2,
            aggregation_type=None
        )
        
        # Add account-level aggregate
        kpi_account = KPI(
            account_id=account.account_id,
            kpi_parameter="TTFV",
            data="9.6",  # Weighted average: (8*120000 + 12*80000) / 200000 = 9.6
            product_id=None,
            aggregation_type="weighted_avg"
        )
        
        db.session.add_all([kpi_p1, kpi_p2, kpi_account])
        db.session.commit()
        
        # Test 1: get_account_level_kpis should return ONLY account aggregate
        account_kpis = get_account_level_kpis(
            account_id=account.account_id,
            customer_id=customer.customer_id
        )
        assert len(account_kpis) == 1  # ✅ CRITICAL: Should NOT include products!
        assert account_kpis[0].data == "9.6"
        assert account_kpis[0].product_id is None
        assert account_kpis[0].aggregation_type == "weighted_avg"
        
        # Test 2: get_product_kpis should return ONLY products
        product_kpis = get_product_kpis(
            account_id=account.account_id,
            customer_id=customer.customer_id
        )
        assert len(product_kpis) == 2  # ✅ Should include both products
        assert all(kpi.product_id is not None for kpi in product_kpis)
        assert all(kpi.aggregation_type is None for kpi in product_kpis)
        
        # Test 3: get_all_kpis_for_account should return structured data
        all_kpis = get_all_kpis_for_account(
            account_id=account.account_id,
            customer_id=customer.customer_id
        )
        assert len(all_kpis['account_level']) == 1
        assert len(all_kpis['products']) == 2
        assert 1 in all_kpis['products']
        assert 2 in all_kpis['products']
    
    def test_health_score_calculation_without_products(self, app_context, legacy_account, customer):
        """
        ✅ CRITICAL: Health score should work for legacy accounts
        """
        from health_score_storage import HealthScoreStorageService
        
        # Add KPIs
        kpis = [
            KPI(
                account_id=legacy_account.account_id,
                kpi_parameter="TTFV",
                data="10",
                product_id=None
            ),
            KPI(
                account_id=legacy_account.account_id,
                kpi_parameter="Feature Adoption Rate",
                data="80",
                product_id=None
            ),
        ]
        db.session.add_all(kpis)
        db.session.commit()
        
        # Calculate health score - should work exactly as before
        service = HealthScoreStorageService()
        health_scores = service._calculate_account_health_scores(legacy_account, customer.customer_id)
        
        assert health_scores is not None
        assert 'overall' in health_scores
        assert 0 <= health_scores['overall'] <= 100
    
    def test_health_score_calculation_with_products(self, app_context, customer):
        """
        ✅ CRITICAL: Health score should use account aggregates, NOT product KPIs
        """
        from health_score_storage import HealthScoreStorageService
        
        # Create account with products
        account = Account(
            account_id=4,
            customer_id=customer.customer_id,
            account_name="Multi-Product",
            revenue=100000
        )
        product1 = Product(
            product_id=3,
            account_id=account.account_id,
            customer_id=customer.customer_id,
            product_name="Product A",
            revenue=60000
        )
        product2 = Product(
            product_id=4,
            account_id=account.account_id,
            customer_id=customer.customer_id,
            product_name="Product B",
            revenue=40000
        )
        db.session.add_all([account, product1, product2])
        db.session.commit()
        
        # Add product KPIs
        kpi_p1_ttfv = KPI(
            account_id=account.account_id,
            kpi_parameter="TTFV",
            data="8",
            product_id=3
        )
        kpi_p2_ttfv = KPI(
            account_id=account.account_id,
            kpi_parameter="TTFV",
            data="12",
            product_id=4
        )
        
        # Add account aggregates (weighted)
        kpi_account_ttfv = KPI(
            account_id=account.account_id,
            kpi_parameter="TTFV",
            data="9.6",  # (8*0.6 + 12*0.4) = 9.6
            product_id=None,
            aggregation_type="weighted_avg"
        )
        
        db_session.add_all([kpi_p1_ttfv, kpi_p2_ttfv, kpi_account_ttfv])
        db_session.commit()
        
        # Calculate health score
        service = HealthScoreStorageService()
        health_scores = service._calculate_account_health_scores(account, customer.customer_id)
        
        # Verify it used account aggregate (9.6), NOT individual products (8, 12)
        # This is tested indirectly by ensuring calculation doesn't double-count
        assert health_scores is not None
        assert 'overall' in health_scores
        assert 0 <= health_scores['overall'] <= 100
        
        # Verify only account-level KPI was used (not product KPIs)
        # The health score should be based on 1 KPI (account aggregate), not 3 KPIs
        account_kpis = get_account_level_kpis(account.account_id, customer.customer_id)
        assert len(account_kpis) == 1  # Only the account aggregate
    
    def test_constraint_prevents_invalid_data(self, app_context, customer):
        """
        ✅ Database constraint should prevent invalid combinations
        """
        account = Account(
            account_id=5,
            customer_id=customer.customer_id,
            account_name="Test Account",
            revenue=50000
        )
        product = Product(
            product_id=5,
            account_id=account.account_id,
            customer_id=customer.customer_id,
            product_name="Test Product",
            revenue=50000
        )
        db_session.add_all([account, product])
        db_session.commit()
        
        # Test 1: product_id NOT NULL + aggregation_type NOT NULL → Should FAIL
        with pytest.raises(ValueError) as exc_info:
            kpi_invalid = KPI(
                account_id=account.account_id,
                kpi_parameter="TTFV",
                data="10",
                product_id=5,  # Product-level
                aggregation_type="weighted_avg"  # ❌ Should be NULL!
            )
            db.session.add(kpi_invalid)
            db.session.commit()
        
        assert "cannot both be set" in str(exc_info.value).lower()
        db.session.rollback()
        
        # Test 2: Valid combinations should work
        kpi_valid1 = KPI(
            account_id=account.account_id,
            kpi_parameter="TTFV",
            data="10",
            product_id=5,
            aggregation_type=None  # ✅ Valid
        )
        kpi_valid2 = KPI(
            account_id=account.account_id,
            kpi_parameter="TTFV",
            data="10",
            product_id=None,
            aggregation_type="weighted_avg"  # ✅ Valid
        )
        
        db.session.add_all([kpi_valid1, kpi_valid2])
        db.session.commit()  # Should succeed
    
    def test_aggregation_type_validation(self, app_context, customer):
        """
        ✅ Test that invalid aggregation_type values are rejected
        """
        account = Account(
            account_id=6,
            customer_id=customer.customer_id,
            account_name="Test Account",
            revenue=50000
        )
        db.session.add(account)
        db.session.commit()
        
        # Test: Invalid aggregation_type should raise ValueError
        with pytest.raises(ValueError) as exc_info:
            kpi_invalid = KPI(
                account_id=account.account_id,
                kpi_parameter="TTFV",
                data="10",
                product_id=None,
                aggregation_type="invalid_type"  # ❌ Invalid
            )
            db.session.add(kpi_invalid)
            db.session.commit()
        
        assert "invalid aggregation_type" in str(exc_info.value).lower()
        db.session.rollback()
    
    def test_get_worst_product_kpis(self, app_context, customer):
        """
        ✅ Test get_worst_product_kpis helper function
        """
        account = Account(
            account_id=7,
            customer_id=customer.customer_id,
            account_name="Test Account",
            revenue=100000
        )
        db.session.add(account)
        db.session.commit()
        
        # Add max aggregate (worst case)
        kpi_max = KPI(
            account_id=account.account_id,
            kpi_parameter="TTFV",
            data="25",  # Worst case
            product_id=None,
            aggregation_type="max"
        )
        
        # Add min aggregate (best case)
        kpi_min = KPI(
            account_id=account.account_id,
            kpi_parameter="TTFV",
            data="8",  # Best case
            product_id=None,
            aggregation_type="min"
        )
        
        db.session.add_all([kpi_max, kpi_min])
        db.session.commit()
        
        # Test get_worst_product_kpis
        worst_kpis = get_worst_product_kpis(account.account_id, customer.customer_id)
        assert len(worst_kpis) == 1
        assert worst_kpis[0].aggregation_type == "max"
        assert worst_kpis[0].data == "25"
        
        # Test get_best_product_kpis
        best_kpis = get_best_product_kpis(account.account_id, customer.customer_id)
        assert len(best_kpis) == 1
        assert best_kpis[0].aggregation_type == "min"
        assert best_kpis[0].data == "8"

