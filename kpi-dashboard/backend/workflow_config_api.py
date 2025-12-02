"""
Blueprint handling per-customer workflow (n8n) configuration CRUD + connection testing.
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, Optional

import requests
from flask import Blueprint, jsonify, request

from auth_middleware import get_current_customer_id
from extensions import db
# Try to import CustomerWorkflowConfig, make it optional
try:
    from models import CustomerWorkflowConfig
    WORKFLOW_CONFIG_AVAILABLE = True
except ImportError:
    CustomerWorkflowConfig = None
    WORKFLOW_CONFIG_AVAILABLE = False
from security_utils import (
    encrypt_credential,
    decrypt_credential,
    generate_webhook_secret,
    generate_webhook_signature,
    rotate_webhook_secret,
)

workflow_config_api = Blueprint("workflow_config_api", __name__)
logger = logging.getLogger(__name__)


def _serialize_config(config: CustomerWorkflowConfig) -> Dict[str, Any]:
    if not WORKFLOW_CONFIG_AVAILABLE or config is None:
        return {}
    return {
        "customer_id": config.customer_id,
        "workflow_system": config.workflow_system,
        "n8n_instance_type": config.n8n_instance_type,
        "n8n_base_url": config.n8n_base_url,
        "n8n_webhook_url": config.n8n_webhook_url,
        "n8n_api_key_present": bool(config.n8n_api_key_encrypted),
        "enabled_playbooks": config.enabled_playbooks or [],
        "config": config.config or {},
        "webhook_last_rotated": config.webhook_secret_rotated_at.isoformat()
        if config.webhook_secret_rotated_at
        else None,
        "created_at": config.created_at.isoformat() if config.created_at else None,
        "updated_at": config.updated_at.isoformat() if config.updated_at else None,
    }


@workflow_config_api.route("/api/workflow/config", methods=["GET"])
def get_workflow_config():
    try:
        customer_id = get_current_customer_id()
        if not customer_id:
            return jsonify({
                "error": "Authentication required",
                "message": "Please log in to access this resource"
            }), 401
        
        if not WORKFLOW_CONFIG_AVAILABLE:
            return jsonify({"configured": False, "config": None, "message": "Workflow config not available"})
        
        config = CustomerWorkflowConfig.query.filter_by(customer_id=customer_id).first()
        if not config:
            return jsonify({"configured": False, "config": None})
        return jsonify({"configured": True, "config": _serialize_config(config)})
    except Exception as e:
        import traceback
        logger.error(f"Error in get_workflow_config: {e}\n{traceback.format_exc()}")
        return jsonify({
            "error": "Internal server error",
            "message": str(e)
        }), 500


@workflow_config_api.route("/api/workflow/config", methods=["POST"])
def upsert_workflow_config():
    try:
        customer_id = get_current_customer_id()
        if not customer_id:
            return jsonify({
                "error": "Authentication required",
                "message": "Please log in to access this resource"
            }), 401
        
        if not WORKFLOW_CONFIG_AVAILABLE:
            return jsonify({"error": "Workflow config not available"}), 503
        
        payload = request.json or {}

        config = CustomerWorkflowConfig.query.filter_by(customer_id=customer_id).first()
        if not config:
            config = CustomerWorkflowConfig(customer_id=customer_id)
            db.session.add(config)

        # validate + assign
        config.workflow_system = payload.get("workflow_system") or config.workflow_system
        config.n8n_instance_type = payload.get("n8n_instance_type") or config.n8n_instance_type
        config.n8n_base_url = payload.get("n8n_base_url") or config.n8n_base_url
        config.n8n_webhook_url = payload.get("n8n_webhook_url") or config.n8n_webhook_url
        config.config = payload.get("config") or config.config or {}

        # Capture before values for activity log
        before_values = {
            'workflow_system': config.workflow_system,
            'n8n_instance_type': config.n8n_instance_type,
            'n8n_base_url': config.n8n_base_url,
            'n8n_webhook_url': config.n8n_webhook_url,
            'enabled_playbooks': config.enabled_playbooks,
            'config': config.config,
        }
        changed_fields = []
        
        enabled_playbooks = payload.get("enabled_playbooks")
        if enabled_playbooks is not None:
            if config.enabled_playbooks != enabled_playbooks:
                changed_fields.append('enabled_playbooks')
            config.enabled_playbooks = enabled_playbooks

        if payload.get("n8n_api_key"):
            changed_fields.append('n8n_api_key')
            config.n8n_api_key_encrypted = encrypt_credential(payload["n8n_api_key"])
            config.n8n_api_key_updated_at = datetime.utcnow()

        # Capture after values
        after_values = {
            'workflow_system': config.workflow_system,
            'n8n_instance_type': config.n8n_instance_type,
            'n8n_base_url': config.n8n_base_url,
            'n8n_webhook_url': config.n8n_webhook_url,
            'enabled_playbooks': config.enabled_playbooks,
            'config': config.config,
        }
        
        # Always generate a new secret if one doesn't exist
        if not config.webhook_secret_encrypted:
            secret = generate_webhook_secret()
            config.webhook_secret_encrypted = encrypt_credential(secret)
            config.webhook_secret_rotated_at = datetime.utcnow()
            changed_fields.append('webhook_secret')
        
        try:
            db.session.commit()
            
            # Log activity if there were changes
            if changed_fields:
                try:
                    from activity_logging import activity_logger
                    from auth_middleware import get_current_user_id
                    user_id = get_current_user_id()
                    activity_logger.log_settings_change(
                        customer_id=customer_id,
                        user_id=user_id,
                        setting_type='workflow_config',
                        changed_fields=changed_fields,
                        before_values=before_values,
                        after_values=after_values,
                        status='success'
                    )
                except Exception as e:
                    logger.error(f"Failed to log workflow config activity: {e}")
            
            # Return the secret so user can copy it (only on first creation)
            response = _serialize_config(config)
            if not config.webhook_secret_encrypted:
                response["webhook_secret"] = secret  # show once for customer to save
            return jsonify(response), 201
        except Exception as e:
            db.session.rollback()
            # Log failed activity
            if changed_fields:
                try:
                    from activity_logging import activity_logger
                    from auth_middleware import get_current_user_id
                    user_id = get_current_user_id()
                    activity_logger.log_settings_change(
                        customer_id=customer_id,
                        user_id=user_id,
                        setting_type='workflow_config',
                        changed_fields=changed_fields,
                        before_values=before_values,
                        after_values=after_values,
                        status='failure',
                        error_message=str(e)
                    )
                except:
                    pass
            raise
    except Exception as e:
        import traceback
        logger.error(f"Error in upsert_workflow_config: {e}\n{traceback.format_exc()}")
        return jsonify({
            "error": "Internal server error",
            "message": str(e)
        }), 500


@workflow_config_api.route("/api/workflow/config/rotate-secret", methods=["POST"])
def rotate_secret():
    customer_id = get_current_customer_id()
    if not WORKFLOW_CONFIG_AVAILABLE:
        return jsonify({"error": "Workflow config not available"}), 503
    
    config = CustomerWorkflowConfig.query.filter_by(customer_id=customer_id).first()
    if not config:
        return jsonify({"error": "Workflow config not found"}), 404

    secret = rotate_webhook_secret(config)
    return jsonify(
        {
            "message": "Webhook secret rotated. Please update your n8n workflow.",
            "webhook_secret": secret,
            "grace_period_until": config.webhook_secret_grace_period_until.isoformat()
            if config.webhook_secret_grace_period_until
            else None,
        }
    )


@workflow_config_api.route("/api/workflow/config/test", methods=["POST"])
def test_connection():
    try:
        customer_id = get_current_customer_id()
        if not customer_id:
            return jsonify({
                "success": False,
                "error": "Authentication required",
                "message": "Please log in to test the connection"
            }), 401
        
        payload = request.json or {}

        webhook_url = payload.get("n8n_webhook_url")
        if not webhook_url:
            return jsonify({
                "success": False,
                "error": "n8n_webhook_url is required"
            }), 400

        # Allow HTTP for localhost development, require HTTPS for production
        if not webhook_url.startswith("https://") and not webhook_url.startswith("http://localhost"):
            return jsonify({
                "success": False,
                "error": "HTTPS is required for webhook URL (or use localhost for development)"
            }), 400

        secret = payload.get("webhook_secret") or generate_webhook_secret()
        body = {
            "test": True,
            "customer_id": customer_id,
            "timestamp": datetime.utcnow().isoformat(),
        }
        signature = generate_webhook_signature(body, secret)

        try:
            response = requests.post(
                webhook_url,
                json=body,
                headers={
                    "Content-Type": "application/json",
                    "X-GrowthPulse-Signature": signature,
                },
                timeout=10,
            )
            response.raise_for_status()
            
            # Try to get response body if available
            response_data = {}
            try:
                if response.content:
                    response_data = response.json()
            except:
                pass
            
            return jsonify({
                "success": True,
                "webhook_secret": secret,
                "n8n_response": response_data,
                "status_code": response.status_code
            })
        except requests.exceptions.Timeout:
            return jsonify({
                "success": False,
                "error": "Connection timeout. n8n webhook did not respond within 10 seconds."
            }), 400
        except requests.exceptions.ConnectionError as e:
            return jsonify({
                "success": False,
                "error": f"Could not connect to n8n webhook. Is n8n running? Error: {str(e)}"
            }), 400
        except requests.exceptions.HTTPError as e:
            return jsonify({
                "success": False,
                "error": f"n8n webhook returned error: {e.response.status_code} - {e.response.text[:200] if e.response.text else str(e)}"
            }), 400
        except requests.RequestException as exc:
            logger.warning("Workflow connection test failed: %s", exc)
            return jsonify({
                "success": False,
                "error": f"Connection test failed: {str(exc)}"
            }), 400
    except Exception as e:
        import traceback
        logger.error(f"Error in test_connection: {e}\n{traceback.format_exc()}")
        return jsonify({
            "success": False,
            "error": f"Internal server error: {str(e)}"
        }), 500

