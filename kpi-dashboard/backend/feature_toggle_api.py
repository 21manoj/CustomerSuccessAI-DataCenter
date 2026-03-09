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

@feature_toggle_api.route('/api/features/customer-toggle', methods=['POST'])
def set_customer_feature_toggle():
    """Create or update a per-customer feature toggle in the DB.

    Body: {"feature_name": "revenue_intelligence", "enabled": true}

    Uses the authenticated user's customer_id.
    """
    try:
        from models import FeatureToggle as FTModel, db

        customer_id = get_current_customer_id()
        if not customer_id:
            return jsonify({'error': 'Authentication required'}), 401

        data = request.get_json() or {}
        feature_name = data.get('feature_name')
        enabled = data.get('enabled', True)

        if not feature_name:
            return jsonify({'error': 'feature_name is required', 'status': 'error'}), 400

        toggle = FTModel.query.filter_by(
            customer_id=customer_id,
            feature_name=feature_name
        ).first()

        if toggle:
            toggle.enabled = enabled
        else:
            toggle = FTModel(
                customer_id=customer_id,
                feature_name=feature_name,
                enabled=enabled,
                description=data.get('description', f'{feature_name} toggle')
            )
            db.session.add(toggle)

        db.session.commit()

        return jsonify({
            'status': 'success',
            'customer_id': customer_id,
            'feature_name': feature_name,
            'enabled': enabled,
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e), 'status': 'error'}), 500


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

# ============================================
# Context Graph Feature Toggle
# ============================================
# Per-customer toggle with sub-toggles for
# incremental rollout of context graph features.
# Follows same pattern as MCP integration toggle.
# ============================================

from feature_toggles import (
    CONTEXT_GRAPH_DEFAULT_CONFIG,
    is_context_graph_enabled,
    get_context_graph_config,
)


@feature_toggle_api.route('/api/features/context-graph', methods=['GET'])
def get_context_graph_status():
    """Get context graph feature status for current customer"""
    try:
        from models import FeatureToggle as FTModel

        customer_id = get_current_customer_id()

        # Check global platform toggle
        global_enabled = feature_toggles.is_enabled(
            FeatureToggle.CONTEXT_GRAPH
        )

        # Check per-customer toggle
        toggle = FTModel.query.filter_by(
            customer_id=customer_id,
            feature_name='context_graph'
        ).first()

        if toggle:
            config = toggle.config or {}
            return jsonify({
                'global_enabled': global_enabled,
                'customer_enabled': toggle.enabled,
                'active': global_enabled and toggle.enabled,
                'sub_toggles': {
                    'story_arcs': config.get('story_arcs', False),
                    'signal_edges': config.get('signal_edges', False),
                    'stakeholder_tracking': config.get('stakeholder_tracking', False),
                    'decision_lifecycle': config.get('decision_lifecycle', False),
                    'outcome_economics': config.get('outcome_economics', False),
                    'industry_benchmarks': config.get('industry_benchmarks', False),
                },
                'description': toggle.description,
                'updated_at': toggle.updated_at.isoformat() if toggle.updated_at else None,
                'status': 'success'
            })
        else:
            return jsonify({
                'global_enabled': global_enabled,
                'customer_enabled': False,
                'active': False,
                'sub_toggles': dict(CONTEXT_GRAPH_DEFAULT_CONFIG),
                'description': 'Context graph not configured for this customer',
                'status': 'success'
            })

    except Exception as e:
        return jsonify({
            'error': f'Failed to get context graph status: {str(e)}',
            'status': 'error'
        }), 500


@feature_toggle_api.route('/api/features/context-graph', methods=['POST'])
def toggle_context_graph():
    """Toggle context graph on/off for current customer with sub-toggles"""
    try:
        from models import FeatureToggle as FTModel, db
        from datetime import datetime

        customer_id = get_current_customer_id()
        data = request.json

        # Get or create per-customer toggle
        toggle = FTModel.query.filter_by(
            customer_id=customer_id,
            feature_name='context_graph'
        ).first()

        if not toggle:
            toggle = FTModel(
                customer_id=customer_id,
                feature_name='context_graph',
                enabled=False,
                config=dict(CONTEXT_GRAPH_DEFAULT_CONFIG),
                description='Context graph intelligence: causal signal edges, '
                            'stakeholder tracking, decision lifecycle, '
                            'outcome economics, story arcs'
            )
            db.session.add(toggle)

        # Update master enable
        toggle.enabled = data.get('enabled', toggle.enabled)

        # Update sub-toggles (merge with existing)
        sub_toggles = data.get('sub_toggles', {})
        current_config = toggle.config or dict(CONTEXT_GRAPH_DEFAULT_CONFIG)
        for key in CONTEXT_GRAPH_DEFAULT_CONFIG:
            if key in sub_toggles:
                current_config[key] = bool(sub_toggles[key])
        toggle.config = current_config

        toggle.updated_at = datetime.utcnow()

        # Force SQLAlchemy to detect JSONB mutation
        from sqlalchemy.orm.attributes import flag_modified
        flag_modified(toggle, 'config')

        db.session.commit()

        # Check effective state (global AND customer)
        global_enabled = feature_toggles.is_enabled(
            FeatureToggle.CONTEXT_GRAPH
        )

        return jsonify({
            'status': 'success',
            'message': f"Context graph {'enabled' if toggle.enabled else 'disabled'} "
                       f"for customer {customer_id}",
            'active': global_enabled and toggle.enabled,
            'global_enabled': global_enabled,
            'customer_enabled': toggle.enabled,
            'sub_toggles': current_config,
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({
            'error': f'Failed to toggle context graph: {str(e)}',
            'status': 'error'
        }), 500


@feature_toggle_api.route('/api/features/context-graph/sub-toggle', methods=['PUT'])
def update_context_graph_sub_toggle():
    """Update a single context graph sub-toggle without touching others"""
    try:
        from models import FeatureToggle as FTModel, db
        from datetime import datetime

        customer_id = get_current_customer_id()
        data = request.json

        sub_toggle_name = data.get('name')
        sub_toggle_value = data.get('enabled', False)

        if sub_toggle_name not in CONTEXT_GRAPH_DEFAULT_CONFIG:
            return jsonify({
                'error': f'Invalid sub-toggle: {sub_toggle_name}. '
                         f'Valid: {list(CONTEXT_GRAPH_DEFAULT_CONFIG.keys())}',
                'status': 'error'
            }), 400

        toggle = FTModel.query.filter_by(
            customer_id=customer_id,
            feature_name='context_graph'
        ).first()

        if not toggle:
            return jsonify({
                'error': 'Context graph not configured for this customer. '
                         'Enable context graph first via POST /api/features/context-graph',
                'status': 'error'
            }), 404

        current_config = toggle.config or dict(CONTEXT_GRAPH_DEFAULT_CONFIG)
        current_config[sub_toggle_name] = bool(sub_toggle_value)
        toggle.config = current_config
        toggle.updated_at = datetime.utcnow()

        # Force SQLAlchemy to detect JSONB change
        from sqlalchemy.orm.attributes import flag_modified
        flag_modified(toggle, 'config')

        db.session.commit()

        return jsonify({
            'status': 'success',
            'message': f"Sub-toggle '{sub_toggle_name}' "
                       f"{'enabled' if sub_toggle_value else 'disabled'}",
            'sub_toggles': current_config,
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({
            'error': f'Failed to update sub-toggle: {str(e)}',
            'status': 'error'
        }), 500


# Example usage
if __name__ == "__main__":
    print("Feature Toggle API")
    print("=" * 50)
    print("Available endpoints:")
    print("  GET  /api/feature-status - Get all feature status")
    print("  POST /api/feature-toggle - Toggle a feature")
    print("  GET  /api/feature-toggle/<name> - Get single feature status")
    print("  PUT  /api/feature-toggle/<name> - Update single feature")
    print("  POST /api/feature-toggle/reset - Reset all features")
    print("  GET  /api/feature-toggle/validate - Validate dependencies")
    print()
    print("Context Graph endpoints:")
    print("  GET  /api/features/context-graph - Get context graph status")
    print("  POST /api/features/context-graph - Toggle context graph on/off")
    print("  PUT  /api/features/context-graph/sub-toggle - Update single sub-toggle")
