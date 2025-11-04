#!/usr/bin/env python3
"""
Customer Management API for MVP
Handles customer creation, data upload, and knowledge base management
"""

from flask import Blueprint, request, jsonify
from auth_middleware import get_current_customer_id, get_current_user_id
from models import db, Customer, CustomerConfig, Account, KPIUpload
from enhanced_rag_qdrant import get_qdrant_rag_system
import json
from datetime import datetime

customer_management_api = Blueprint('customer_management_api', __name__)

@customer_management_api.route('/api/customers', methods=['POST'])
def create_customer():
    """Create a new customer"""
    try:
        data = request.json
        customer_name = data.get('customer_name')
        email = data.get('email')
        phone = data.get('phone')
        
        if not customer_name:
            return jsonify({'error': 'Customer name is required'}), 400
        
        # Check if customer already exists
        existing_customer = Customer.query.filter_by(email=email).first() if email else None
        if existing_customer:
            return jsonify({'error': 'Customer with this email already exists'}), 400
        
        # Create customer
        customer = Customer(
            customer_name=customer_name,
            email=email,
            phone=phone
        )
        db.session.add(customer)
        db.session.flush()  # Get the customer_id
        
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
            }),
            master_file_name=None
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
                'phone': customer.phone,
                'created_at': customer.customer_id  # Using customer_id as placeholder
            }
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Failed to create customer: {str(e)}'}), 500

@customer_management_api.route('/api/customers', methods=['GET'])
def list_customers():
    """List all customers"""
    try:
        customers = Customer.query.all()
        customer_list = []
        
        for customer in customers:
            # Get data counts
            account_count = Account.query.filter_by(customer_id=customer.customer_id).count()
            kpi_count = KPIUpload.query.filter_by(customer_id=customer.customer_id).count()
            
            # Simple knowledge base check - if customer has data, assume it can be built
            has_data = bool(account_count) or bool(kpi_count)
            
            customer_list.append({
                'customer_id': customer.customer_id,
                'customer_name': customer.customer_name,
                'email': customer.email,
                'phone': customer.phone,
                'account_count': account_count,
                'kpi_count': kpi_count,
                'has_data': has_data,
                'knowledge_base_ready': has_data
            })
        
        return jsonify({
            'status': 'success',
            'customers': customer_list,
            'total_customers': len(customer_list)
        })
        
    except Exception as e:
        return jsonify({'error': f'Failed to list customers: {str(e)}'}), 500

@customer_management_api.route('/api/customers/<int:customer_id>/knowledge-base/status', methods=['GET'])
def get_customer_kb_status(customer_id):
    """Get knowledge base status for a specific customer"""
    try:
        # Check if customer exists
        customer = Customer.query.get(customer_id)
        if not customer:
            return jsonify({'error': 'Customer not found'}), 404
        
        # Get RAG system and check status
        try:
            rag_system = get_qdrant_rag_system(customer_id)
            collection_info = rag_system.get_collection_info()
            vectors_count = collection_info.get('vectors_count', 0)
            indexed_vectors_count = collection_info.get('indexed_vectors_count', 0)
            is_built = vectors_count is not None and vectors_count > 0
        except:
            vectors_count = 0
            indexed_vectors_count = 0
            is_built = False
        
        # Get data counts
        account_count = Account.query.filter_by(customer_id=customer_id).count()
        kpi_count = KPIUpload.query.filter_by(customer_id=customer_id).count()
        
        return jsonify({
            'customer_id': customer_id,
            'customer_name': customer.customer_name,
            'is_built': is_built,
            'vectors_count': vectors_count,
            'indexed_vectors_count': indexed_vectors_count,
            'account_count': account_count,
            'kpi_count': kpi_count,
            'status': 'ready' if is_built else 'not_built'
        })
        
    except Exception as e:
        return jsonify({'error': f'Failed to get knowledge base status: {str(e)}'}), 500

@customer_management_api.route('/api/customers/<int:customer_id>/knowledge-base/build', methods=['POST'])
def build_customer_knowledge_base(customer_id):
    """Build knowledge base for a specific customer"""
    try:
        # Check if customer exists
        customer = Customer.query.get(customer_id)
        if not customer:
            return jsonify({'error': 'Customer not found'}), 404
        
        # Check if customer has data
        account_count = Account.query.filter_by(customer_id=customer_id).count()
        kpi_count = KPIUpload.query.filter_by(customer_id=customer_id).count()
        
        if account_count == 0 and kpi_count == 0:
            return jsonify({'error': 'No data found for this customer. Please upload data first.'}), 400
        
        # Build knowledge base
        rag_system = get_qdrant_rag_system(customer_id)
        rag_system.build_knowledge_base(customer_id)
        
        # Get updated status
        collection_info = rag_system.get_collection_info()
        
        return jsonify({
            'status': 'success',
            'message': f'Knowledge base built successfully for customer {customer_id}',
            'customer_id': customer_id,
            'customer_name': customer.customer_name,
            'vectors_count': collection_info.get('vectors_count', 0),
            'account_count': account_count,
            'kpi_count': kpi_count
        })
        
    except Exception as e:
        return jsonify({'error': f'Failed to build knowledge base: {str(e)}'}), 500

@customer_management_api.route('/api/customers/<int:customer_id>/data-summary', methods=['GET'])
def get_customer_data_summary(customer_id):
    """Get data summary for a specific customer"""
    try:
        # Check if customer exists
        customer = Customer.query.get(customer_id)
        if not customer:
            return jsonify({'error': 'Customer not found'}), 404
        
        # Get data counts
        accounts = Account.query.filter_by(customer_id=customer_id).all()
        kpi_uploads = KPIUpload.query.filter_by(customer_id=customer_id).all()
        
        # Calculate total revenue
        total_revenue = sum(account.revenue or 0 for account in accounts)
        
        # Get industries
        industries = list(set(account.industry for account in accounts if account.industry))
        
        # Get regions
        regions = list(set(account.region for account in accounts if account.region))
        
        return jsonify({
            'customer_id': customer_id,
            'customer_name': customer.customer_name,
            'data_summary': {
                'account_count': len(accounts),
                'kpi_upload_count': len(kpi_uploads),
                'total_revenue': float(total_revenue),
                'industries': industries,
                'regions': regions,
                'last_upload': max([upload.uploaded_at for upload in kpi_uploads]) if kpi_uploads else None
            }
        })
        
    except Exception as e:
        return jsonify({'error': f'Failed to get data summary: {str(e)}'}), 500
