#!/usr/bin/env python3
"""
Master File API
Handles upload and processing of master KPI framework files
"""

import pandas as pd
import json
from datetime import datetime
from flask import Blueprint, request, jsonify, current_app
from auth_middleware import get_current_customer_id, get_current_user_id
from werkzeug.utils import secure_filename
import os
from models import db, Customer, CustomerConfig
from extensions import get_customer_id

master_file_api = Blueprint('master_file_api', __name__)

def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in {'xlsx', 'xls'}

def extract_category_weights_from_master_file(file_path):
    """
    Extract category weights from the master KPI framework file
    Returns dict of category weights
    """
    try:
        # Read the Health Score Components sheet
        df = pd.read_excel(file_path, sheet_name='Health Score Components')
        
        # Find the rows with category weights
        category_weights = {}
        
        for index, row in df.iterrows():
            component = str(row.iloc[0]).strip() if pd.notna(row.iloc[0]) else ""
            weight = row.iloc[1] if pd.notna(row.iloc[1]) else None
            
            # Map component names to our category names
            if component == "Product Usage":
                category_weights["Product Usage KPI"] = float(weight) if weight is not None else 0.0
            elif component == "Support Engagement":
                category_weights["Support KPI"] = float(weight) if weight is not None else 0.0
            elif component == "Customer Sentiment":
                category_weights["Customer Sentiment KPI"] = float(weight) if weight is not None else 0.0
            elif component == "Business Outcomes":
                category_weights["Business Outcomes KPI"] = float(weight) if weight is not None else 0.0
            elif component == "Relationship Strength":
                category_weights["Relationship Strength KPI"] = float(weight) if weight is not None else 0.0
        
        return category_weights
        
    except Exception as e:
        current_app.logger.error(f"Error extracting category weights: {str(e)}")
        return {}

@master_file_api.route('/api/master-file/upload', methods=['POST'])
def upload_master_file():
    """Upload and process master KPI framework file"""
    customer_id = get_current_customer_id()
    
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    if not allowed_file(file.filename):
        return jsonify({'error': 'Invalid file type. Please upload Excel files (.xlsx, .xls)'}), 400
    
    try:
        # Save the file temporarily
        filename = secure_filename(file.filename)
        temp_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
        file.save(temp_path)
        
        # Extract category weights
        category_weights = extract_category_weights_from_master_file(temp_path)
        
        if not category_weights:
            return jsonify({'error': 'Could not extract category weights from file'}), 400
        
        # Store category weights in customer config
        config = CustomerConfig.query.filter_by(customer_id=customer_id).first()
        if not config:
            config = CustomerConfig(customer_id=customer_id)
            db.session.add(config)
        
        # Store the category weights as JSON
        config.category_weights = json.dumps(category_weights)
        config.master_file_name = filename
        db.session.commit()
        
        # Clean up temporary file
        os.remove(temp_path)
        
        return jsonify({
            'status': 'success',
            'message': 'Master file uploaded and processed successfully',
            'category_weights': category_weights,
            'filename': filename
        })
        
    except Exception as e:
        current_app.logger.error(f"Error processing master file: {str(e)}")
        return jsonify({'error': f'Error processing file: {str(e)}'}), 500

@master_file_api.route('/api/master-file/weights', methods=['GET'])
def get_category_weights():
    """Get current category weights for the customer"""
    try:
        customer_id = get_current_customer_id()
        
        # Get customer configuration
        config = CustomerConfig.query.filter_by(customer_id=customer_id).first()
        
        if config and config.category_weights:
            # Parse stored weights
            weights = json.loads(config.category_weights)
            return jsonify({
                'category_weights': weights,
                'source': 'customer_config'
            })
        else:
            # Return default weights if no config
            default_weights = {
                "Relationship Strength": 0.20,
                "Adoption & Engagement": 0.25,
                "Support & Experience": 0.20,
                "Product Value": 0.20,
                "Business Outcomes": 0.15
            }
            return jsonify({
                'category_weights': default_weights,
                'source': 'default'
            })
    except Exception as e:
        # Fallback to default on error
        default_weights = {
            "Relationship Strength": 0.20,
            "Adoption & Engagement": 0.25,
            "Support & Experience": 0.20,
            "Product Value": 0.20,
            "Business Outcomes": 0.15
        }
        return jsonify({
            'category_weights': default_weights,
            'source': 'default',
            'error': str(e)
        })

@master_file_api.route('/api/master-file/test', methods=['GET'])
def test_master_file_api():
    """Test endpoint for master file API"""
    return jsonify({
        'status': 'success',
        'message': 'Master file API is working',
        'timestamp': datetime.now().isoformat()
    })
