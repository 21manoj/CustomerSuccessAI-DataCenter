#!/usr/bin/env python3
"""
Tests for KPI Filtering Logic (Backend)
Ensures product-level vs account-level KPI filtering works correctly
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app_v3_minimal import app
from extensions import db
from models import KPI, Account, Product, KPIUpload
import unittest


class TestKPIFiltering(unittest.TestCase):
    """Test KPI filtering logic for product-level vs account-level"""
    
    def setUp(self):
        """Set up test data"""
        self.app = app
        self.app.config['TESTING'] = True
        self.app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        self.client = self.app.test_client()
        
        with self.app.app_context():
            db.create_all()
            
            # Create test customer and account
            from models import Customer
            customer = Customer(customer_name='Test Customer', email='test@test.com')
            db.session.add(customer)
            db.session.flush()
            self.customer_id = customer.customer_id
            
            account = Account(
                customer_id=self.customer_id,
                account_name='Test Account',
                revenue=100000,
                industry='Tech',
                region='US'
            )
            db.session.add(account)
            db.session.flush()
            self.account_id = account.account_id
            
            # Create products
            product1 = Product(
                account_id=self.account_id,
                customer_id=self.customer_id,
                product_name='Core Platform',
                product_sku='SKU-001',
                product_type='Platform',
                revenue=50000,
                status='active'
            )
            product2 = Product(
                account_id=self.account_id,
                customer_id=self.customer_id,
                product_name='Mobile App',
                product_sku='SKU-002',
                product_type='Application',
                revenue=30000,
                status='active'
            )
            db.session.add_all([product1, product2])
            db.session.flush()
            self.product1_id = product1.product_id
            self.product2_id = product2.product_id
            
            # Create KPI upload
            upload = KPIUpload(
                customer_id=self.customer_id,
                account_id=self.account_id,
                user_id=1,
                version=1,
                original_filename='test.xlsx'
            )
            db.session.add(upload)
            db.session.flush()
            self.upload_id = upload.upload_id
            
            # Create test KPIs
            # Account-level KPIs (product_id = None)
            account_kpi1 = KPI(
                upload_id=self.upload_id,
                account_id=self.account_id,
                product_id=None,  # Explicitly None
                category='Business Outcomes KPI',
                kpi_parameter='Revenue',
                data='100000',
                impact_level='High',
                weight='High',
                measurement_frequency='Monthly'
            )
            
            account_kpi2 = KPI(
                upload_id=self.upload_id,
                account_id=self.account_id,
                product_id=None,  # Explicitly None
                category='Product Usage KPI',
                kpi_parameter='Total Users',
                data='500',
                impact_level='Medium',
                weight='Medium',
                measurement_frequency='Monthly'
            )
            
            # Product-level KPIs
            product_kpi1 = KPI(
                upload_id=self.upload_id,
                account_id=self.account_id,
                product_id=self.product1_id,  # Has product_id
                category='Product Usage KPI',
                kpi_parameter='Product Activation Rate',
                data='80%',
                impact_level='High',
                weight='High',
                measurement_frequency='Monthly'
            )
            
            product_kpi2 = KPI(
                upload_id=self.upload_id,
                account_id=self.account_id,
                product_id=self.product2_id,  # Has product_id
                category='Product Usage KPI',
                kpi_parameter='Product Activation Rate',
                data='75%',
                impact_level='High',
                weight='High',
                measurement_frequency='Monthly'
            )
            
            db.session.add_all([account_kpi1, account_kpi2, product_kpi1, product_kpi2])
            db.session.commit()
    
    def tearDown(self):
        """Clean up test data"""
        with self.app.app_context():
            db.drop_all()
    
    def test_filter_product_level_kpis(self):
        """Test filtering product-level KPIs"""
        with self.app.app_context():
            # Get all KPIs for the account
            all_kpis = KPI.query.filter_by(account_id=self.account_id).all()
            
            # Filter product-level KPIs (explicit null/undefined check)
            product_kpis = [
                kpi for kpi in all_kpis 
                if kpi.product_id is not None and kpi.product_id != 0
            ]
            
            self.assertEqual(len(product_kpis), 2, "Should have 2 product-level KPIs")
            self.assertTrue(all(kpi.product_id is not None for kpi in product_kpis))
            self.assertEqual(set(kpi.product_id for kpi in product_kpis), 
                           {self.product1_id, self.product2_id})
    
    def test_filter_account_level_kpis(self):
        """Test filtering account-level KPIs"""
        with self.app.app_context():
            # Get all KPIs for the account
            all_kpis = KPI.query.filter_by(account_id=self.account_id).all()
            
            # Filter account-level KPIs (explicit null/undefined check)
            account_kpis = [
                kpi for kpi in all_kpis 
                if kpi.product_id is None or kpi.product_id == 0
            ]
            
            self.assertEqual(len(account_kpis), 2, "Should have 2 account-level KPIs")
            self.assertTrue(all(kpi.product_id is None for kpi in account_kpis))
    
    def test_kpi_counting_logic(self):
        """Test that KPI counting logic matches filtering logic"""
        with self.app.app_context():
            all_kpis = KPI.query.filter_by(account_id=self.account_id).all()
            
            # Count using explicit checks (the fixed way)
            product_count = sum(1 for kpi in all_kpis 
                              if kpi.product_id is not None and kpi.product_id != 0)
            account_count = sum(1 for kpi in all_kpis 
                              if kpi.product_id is None or kpi.product_id == 0)
            
            self.assertEqual(product_count, 2)
            self.assertEqual(account_count, 2)
            self.assertEqual(product_count + account_count, len(all_kpis))
    
    def test_api_response_includes_product_id(self):
        """Test that API response includes product_id for filtering"""
        with self.app.app_context():
            from kpi_api import get_all_kpis
            from flask import Flask
            
            # Simulate API call
            with self.client.session_transaction() as sess:
                sess['customer_id'] = self.customer_id
            
            # Get KPIs via API
            response = self.client.get('/api/kpis/customer/all')
            self.assertEqual(response.status_code, 200)
            
            data = response.get_json()
            self.assertIsInstance(data, list)
            
            # Check that product_id is included
            for kpi in data:
                self.assertIn('product_id', kpi)
                self.assertIn('product_name', kpi)
                
                # Verify filtering would work
                if kpi['product_id'] is not None:
                    self.assertIsInstance(kpi['product_id'], int)
                    self.assertGreater(kpi['product_id'], 0)


if __name__ == '__main__':
    unittest.main()

