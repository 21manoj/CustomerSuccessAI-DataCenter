#!/usr/bin/env python3
"""
OpenAI API Key Management API

Allows customers to set/update their OpenAI API key without server restart.
"""

from flask import Blueprint, request, jsonify
from auth_middleware import get_current_customer_id, get_current_user_id
from openai_key_utils import get_openai_api_key, set_openai_api_key, has_openai_api_key
from models import db
from activity_logging import activity_logger
import os

openai_key_api = Blueprint('openai_key_api', __name__)


@openai_key_api.route('/api/openai-key', methods=['GET'])
def get_openai_key_status():
    """Get OpenAI API key status (without exposing the key)"""
    customer_id = get_current_customer_id()
    
    if not customer_id:
        return jsonify({
            'status': 'error',
            'error': 'Authentication required'
        }), 401
    
    try:
        has_key = has_openai_api_key(customer_id)
        
        return jsonify({
            'status': 'success',
            'has_key': has_key,
            'message': 'OpenAI API key is configured' if has_key else 'OpenAI API key is not configured'
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'error': str(e)
        }), 500


@openai_key_api.route('/api/openai-key', methods=['POST'])
def set_openai_key():
    """Set or update OpenAI API key for the current customer"""
    customer_id = get_current_customer_id()
    
    if not customer_id:
        return jsonify({
            'status': 'error',
            'error': 'Authentication required'
        }), 401
    
    try:
        data = request.json
        api_key = data.get('api_key')
        
        if not api_key:
            return jsonify({
                'status': 'error',
                'error': 'API key is required'
            }), 400
        
        # Validate API key format (basic check)
        if not api_key.startswith('sk-'):
            return jsonify({
                'status': 'error',
                'error': 'Invalid API key format. OpenAI API keys should start with "sk-"'
            }), 400
        
        # Get before value (check if key exists)
        has_existing_key = has_openai_api_key(customer_id)
        
        # Store the key (encrypted)
        success = set_openai_api_key(customer_id, api_key)
        
        if success:
            # Log settings change
            try:
                user_id = get_current_user_id()
                activity_logger.log_settings_change(
                    customer_id=customer_id,
                    user_id=user_id,
                    setting_type='openai_key',
                    changed_fields=['openai_api_key'],
                    before_values={'has_key': has_existing_key},
                    after_values={'has_key': True},
                    status='success'
                )
            except Exception as log_error:
                print(f"Warning: Failed to log OpenAI key update: {log_error}")
            
            return jsonify({
                'status': 'success',
                'message': 'OpenAI API key updated successfully. Changes take effect immediately - no server restart needed!'
            })
        else:
            # Determine specific error message
            error_message = 'Failed to save API key'
            try:
                # Check if it's a model configuration issue
                from models import CustomerConfig
                if not hasattr(CustomerConfig, 'openai_api_key_encrypted'):
                    error_message = 'OpenAI API key support not configured. Please contact administrator to update the backend.'
                elif not os.getenv('ENCRYPTION_KEY'):
                    error_message = 'Server configuration error: ENCRYPTION_KEY not set. Please contact administrator.'
            except:
                pass
            
            # Log failed update
            try:
                user_id = get_current_user_id()
                activity_logger.log_settings_change(
                    customer_id=customer_id,
                    user_id=user_id,
                    setting_type='openai_key',
                    changed_fields=['openai_api_key'],
                    before_values={'has_key': has_existing_key},
                    after_values={'has_key': False},
                    status='failure',
                    error_message=error_message
                )
            except:
                pass
            
            return jsonify({
                'status': 'error',
                'error': error_message
            }), 500
            
    except Exception as e:
        return jsonify({
            'status': 'error',
            'error': str(e)
        }), 500


@openai_key_api.route('/api/openai-key', methods=['DELETE'])
def delete_openai_key():
    """Remove OpenAI API key for the current customer"""
    customer_id = get_current_customer_id()
    
    if not customer_id:
        return jsonify({
            'status': 'error',
            'error': 'Authentication required'
        }), 401
    
    try:
        from models import CustomerConfig
        
        # Check if key exists before deletion
        had_key = has_openai_api_key(customer_id)
        
        config = CustomerConfig.query.filter_by(customer_id=customer_id).first()
        if config:
            config.openai_api_key_encrypted = None
            config.openai_api_key_updated_at = None
            db.session.commit()
        
        # Log settings change
        try:
            user_id = get_current_user_id()
            activity_logger.log_settings_change(
                customer_id=customer_id,
                user_id=user_id,
                setting_type='openai_key',
                changed_fields=['openai_api_key'],
                before_values={'has_key': had_key},
                after_values={'has_key': False},
                status='success'
            )
        except Exception as log_error:
            print(f"Warning: Failed to log OpenAI key deletion: {log_error}")
        
        return jsonify({
            'status': 'success',
            'message': 'OpenAI API key removed successfully'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'status': 'error',
            'error': str(e)
        }), 500

