#!/usr/bin/env python3
"""
Feature Toggle API
Provides endpoints for managing feature toggles from the React UI
"""

from flask import Blueprint, request, jsonify
from auth_middleware import get_current_customer_id, get_current_user_id
import os
import sys

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from feature_toggles import feature_toggles, FeatureToggle

feature_toggle_api = Blueprint('feature_toggle_api', __name__)

@feature_toggle_api.route('/api/feature-status', methods=['GET'])
def get_feature_status():
    """Get current feature toggle status"""
    try:
        status = feature_toggles.get_feature_status()
        validation = feature_toggles.validate_dependencies()
        
        return jsonify({
            'features': status,
            'dependencies': validation,
            'status': 'success'
        })
    except Exception as e:
        return jsonify({
            'error': f'Failed to get feature status: {str(e)}',
            'status': 'error'
        }), 500

@feature_toggle_api.route('/api/feature-toggle', methods=['POST'])
def toggle_feature():
    """Toggle a feature on/off"""
    try:
        data = request.get_json()
        feature_name = data.get('feature')
        enabled = data.get('enabled', False)
        
        if not feature_name:
            return jsonify({
                'error': 'Feature name is required',
                'status': 'error'
            }), 400
        
        # Convert string to FeatureToggle enum
        try:
            feature_enum = FeatureToggle(feature_name)
        except ValueError:
            return jsonify({
                'error': f'Invalid feature name: {feature_name}',
                'status': 'error'
            }), 400
        
        # Toggle the feature
        if enabled:
            feature_toggles.enable_feature(feature_enum)
        else:
            feature_toggles.disable_feature(feature_enum)
        
        # Update environment variable
        env_var = f'FEATURE_{feature_name.upper()}'
        os.environ[env_var] = 'true' if enabled else 'false'
        
        return jsonify({
            'feature': feature_name,
            'enabled': enabled,
            'message': f'Feature {feature_name} {"enabled" if enabled else "disabled"} successfully',
            'status': 'success'
        })
        
    except Exception as e:
        return jsonify({
            'error': f'Failed to toggle feature: {str(e)}',
            'status': 'error'
        }), 500

@feature_toggle_api.route('/api/feature-toggle/<feature_name>', methods=['GET'])
def get_feature_status_single(feature_name):
    """Get status of a single feature"""
    try:
        # Convert string to FeatureToggle enum
        try:
            feature_enum = FeatureToggle(feature_name)
        except ValueError:
            return jsonify({
                'error': f'Invalid feature name: {feature_name}',
                'status': 'error'
            }), 400
        
        status = feature_toggles.get_feature_status()
        feature_status = status.get(feature_name)
        
        if not feature_status:
            return jsonify({
                'error': f'Feature {feature_name} not found',
                'status': 'error'
            }), 404
        
        return jsonify({
            'feature': feature_name,
            'status': feature_status,
            'status': 'success'
        })
        
    except Exception as e:
        return jsonify({
            'error': f'Failed to get feature status: {str(e)}',
            'status': 'error'
        }), 500

@feature_toggle_api.route('/api/feature-toggle/<feature_name>', methods=['PUT'])
def update_feature_status(feature_name):
    """Update status of a single feature"""
    try:
        data = request.get_json()
        enabled = data.get('enabled', False)
        
        # Convert string to FeatureToggle enum
        try:
            feature_enum = FeatureToggle(feature_name)
        except ValueError:
            return jsonify({
                'error': f'Invalid feature name: {feature_name}',
                'status': 'error'
            }), 400
        
        # Update the feature
        if enabled:
            feature_toggles.enable_feature(feature_enum)
        else:
            feature_toggles.disable_feature(feature_enum)
        
        # Update environment variable
        env_var = f'FEATURE_{feature_name.upper()}'
        os.environ[env_var] = 'true' if enabled else 'false'
        
        return jsonify({
            'feature': feature_name,
            'enabled': enabled,
            'message': f'Feature {feature_name} {"enabled" if enabled else "disabled"} successfully',
            'status': 'success'
        })
        
    except Exception as e:
        return jsonify({
            'error': f'Failed to update feature status: {str(e)}',
            'status': 'error'
        }), 500

@feature_toggle_api.route('/api/feature-toggle/reset', methods=['POST'])
def reset_all_features():
    """Reset all features to default state"""
    try:
        # Reset all features to disabled
        for feature in FeatureToggle:
            feature_toggles.disable_feature(feature)
            env_var = f'FEATURE_{feature.value.upper()}'
            os.environ[env_var] = 'false'
        
        return jsonify({
            'message': 'All features reset to disabled state',
            'status': 'success'
        })
        
    except Exception as e:
        return jsonify({
            'error': f'Failed to reset features: {str(e)}',
            'status': 'error'
        }), 500

@feature_toggle_api.route('/api/feature-toggle/validate', methods=['GET'])
def validate_dependencies():
    """Validate feature dependencies"""
    try:
        validation = feature_toggles.validate_dependencies()
        
        return jsonify({
            'validation': validation,
            'status': 'success'
        })
        
    except Exception as e:
        return jsonify({
            'error': f'Failed to validate dependencies: {str(e)}',
            'status': 'error'
        }), 500

# ============================================
# MCP Integration Feature Toggle
# ============================================



@feature_toggle_api.route('/api/features/mcp', methods=['GET'])
def get_mcp_status():
    """Get MCP integration status for customer"""
    try:
        from models import FeatureToggle as FTModel, db
        
        customer_id = get_current_customer_id()
        
        toggle = FTModel.query.filter_by(
            customer_id=customer_id,
            feature_name='mcp_integration'
        ).first()
        
        if toggle:
            config = toggle.config or {}
            return jsonify({
                'enabled': toggle.enabled,
                'salesforce_enabled': config.get('salesforce', False),
                'servicenow_enabled': config.get('servicenow', False),
                'surveys_enabled': config.get('surveys', False),
                'description': toggle.description,
                'updated_at': toggle.updated_at.isoformat() if toggle.updated_at else None,
                'status': 'success'
            })
        else:
            # Default: disabled
            return jsonify({
                'enabled': False,
                'salesforce_enabled': False,
                'servicenow_enabled': False,
                'surveys_enabled': False,
                'description': 'MCP integration not configured',
                'status': 'success'
            })
        
    except Exception as e:
        return jsonify({
            'error': f'Failed to get MCP status: {str(e)}',
            'status': 'error'
        }), 500

@feature_toggle_api.route('/api/features/mcp', methods=['POST'])
def toggle_mcp():
    """Toggle MCP integration on/off"""
    try:
        from models import FeatureToggle as FTModel, db
        from datetime import datetime
        
        customer_id = get_current_customer_id()
        data = request.json
        
        # Get or create toggle
        toggle = FTModel.query.filter_by(
            customer_id=customer_id,
            feature_name='mcp_integration'
        ).first()
        
        if not toggle:
            toggle = FTModel(
                customer_id=customer_id,
                feature_name='mcp_integration',
                enabled=False,
                config={},
                description='MCP external system integration (Salesforce, ServiceNow, Surveys)'
            )
            db.session.add(toggle)
        
        # Update toggle
        toggle.enabled = data.get('enabled', False)
        toggle.config = {
            'salesforce': data.get('salesforce_enabled', False),
            'servicenow': data.get('servicenow_enabled', False),
            'surveys': data.get('surveys_enabled', False)
        }
        toggle.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'message': f"MCP integration {'enabled' if toggle.enabled else 'disabled'}",
            'enabled': toggle.enabled,
            'config': toggle.config
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'error': f'Failed to toggle MCP: {str(e)}',
            'status': 'error'
        }), 500

@feature_toggle_api.route('/api/features/mcp/status', methods=['GET'])
def get_mcp_connection_status():
    """Get real-time MCP connection status"""
    try:
        from mcp_integration import is_mcp_enabled, get_mcp_config
        
        customer_id = get_current_customer_id()
        
        enabled = is_mcp_enabled(customer_id)
        config = get_mcp_config(customer_id)
        
        # Check MCP SDK availability
        try:
            import mcp
            mcp_available = True
        except ImportError:
            mcp_available = False
        
        return jsonify({
            'enabled': enabled,
            'systems': config,
            'mcp_sdk_installed': mcp_available,
            'ready_to_use': enabled and mcp_available,
            'status': 'success'
        })
        
    except Exception as e:
        return jsonify({
            'error': f'Failed to get connection status: {str(e)}',
            'status': 'error'
        }), 500

# Example usage
if __name__ == "__main__":
    print("🔧 Feature Toggle API")
    print("=" * 50)
    print("Available endpoints:")
    print("  GET  /api/feature-status - Get all feature status")
    print("  POST /api/feature-toggle - Toggle a feature")
    print("  GET  /api/feature-toggle/<name> - Get single feature status")
    print("  PUT  /api/feature-toggle/<name> - Update single feature")
    print("  POST /api/feature-toggle/reset - Reset all features")
    print("  GET  /api/feature-toggle/validate - Validate dependencies")
