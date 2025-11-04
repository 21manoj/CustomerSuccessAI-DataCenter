#!/usr/bin/env python3
"""
Simple Customer Management API for MVP
"""

from flask import Blueprint, request, jsonify
from auth_middleware import get_current_customer_id, get_current_user_id
from models import db, Customer, CustomerConfig, Account, KPIUpload
import json

simple_customer_api = Blueprint('simple_customer_api', __name__)

@simple_customer_api.route('/api/customers', methods=['GET'])
def list_customers():
    """List all customers"""
    try:
        customers = Customer.query.all()
        customer_list = []
        
        for customer in customers:
            # Get data counts
            account_count = Account.query.filter_by(customer_id=customer.customer_id).count()
            kpi_count = KPIUpload.query.filter_by(customer_id=customer.customer_id).count()
            
            customer_list.append({
                'customer_id': customer.customer_id,
                'customer_name': customer.customer_name,
                'email': customer.email,
                'phone': customer.phone,
                'account_count': account_count,
                'kpi_count': kpi_count,
                'has_data': account_count > 0 or kpi_count > 0
            })
        
        return jsonify({
            'status': 'success',
            'customers': customer_list,
            'total_customers': len(customer_list)
        })
        
    except Exception as e:
        return jsonify({'error': f'Failed to list customers: {str(e)}'}), 500

@simple_customer_api.route('/api/customers', methods=['POST'])
def create_customer():
    """Create a new customer"""
    try:
        data = request.json
        customer_name = data.get('customer_name')
        email = data.get('email')
        phone = data.get('phone')
        
        if not customer_name:
            return jsonify({'error': 'Customer name is required'}), 400
        
        # Create customer
        customer = Customer(
            customer_name=customer_name,
            email=email,
            phone=phone
        )
        db.session.add(customer)
        db.session.flush()
        
        # Create default customer config
        config = CustomerConfig(
            customer_id=customer.customer_id,
            kpi_upload_mode='corporate',
            category_weights=json.dumps({
                'Product Usage KPI': 0.3,
                'Support KPI': 0.2,
                'Customer Sentiment KPI': 0.2,
                'Business Outcomes KPI': 0.15,
                'Relationship Strength KPI': 0.15
            })
        )
        db.session.add(config)
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'message': 'Customer created successfully',
            'customer': {
                'customer_id': customer.customer_id,
                'customer_name': customer.customer_name,
                'email': customer.email,
                'phone': customer.phone
            }
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Failed to create customer: {str(e)}'}), 500
