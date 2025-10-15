#!/usr/bin/env python3
"""Test customer database"""

from app import app
from models import Customer, Account, KPIUpload

with app.app_context():
    customers = Customer.query.all()
    print(f"Total customers: {len(customers)}")
    
    for customer in customers:
        account_count = Account.query.filter_by(customer_id=customer.customer_id).count()
        kpi_count = KPIUpload.query.filter_by(customer_id=customer.customer_id).count()
        print(f"Customer {customer.customer_id}: {customer.customer_name}, Accounts: {account_count}, KPIs: {kpi_count}")
