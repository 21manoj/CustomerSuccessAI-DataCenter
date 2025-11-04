#!/usr/bin/env python3
"""
Test API
"""

from flask import Blueprint, request, jsonify
from auth_middleware import get_current_customer_id, get_current_user_id
from models import db, Customer, Account, KPIUpload

test_api = Blueprint('test_api', __name__)

@test_api.route('/api/test-customers', methods=['GET'])
def test_customers():
    """Test customer listing"""
    try:
        customers = Customer.query.all()
        customer_list = []
        
        for customer in customers:
            account_count = Account.query.filter_by(customer_id=customer.customer_id).count()
            kpi_count = KPIUpload.query.filter_by(customer_id=customer.customer_id).count()
            
            customer_list.append({
                'customer_id': customer.customer_id,
                'customer_name': customer.customer_name,
                'email': customer.email,
                'phone': customer.phone,
                'account_count': account_count,
                'kpi_count': kpi_count
            })
        
        return jsonify({
            'status': 'success',
            'customers': customer_list,
            'total_customers': len(customer_list)
        })
        
    except Exception as e:
        return jsonify({'error': f'Failed to list customers: {str(e)}'}), 500
