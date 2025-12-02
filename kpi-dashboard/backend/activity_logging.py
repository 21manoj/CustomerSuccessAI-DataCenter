#!/usr/bin/env python3
"""
Activity Logging Utility
Comprehensive logging for all user actions and system changes
"""

from flask import request, session, g
from datetime import datetime
from typing import Optional, Dict, Any, List
from extensions import db
import json
import logging

# Try to import ActivityLog, but make it optional
try:
    from models import ActivityLog
    ACTIVITY_LOG_AVAILABLE = True
except ImportError:
    ActivityLog = None
    ACTIVITY_LOG_AVAILABLE = False

logger = logging.getLogger(__name__)

class ActivityLogger:
    """Utility class for logging user activities"""
    
    ACTION_CATEGORIES = {
        'authentication': ['login', 'logout', 'session_expired', 'password_change', 'password_reset'],
        'data_modification': ['kpi_edit', 'kpi_create', 'kpi_delete', 'account_create', 'account_update', 
                             'account_delete', 'product_create', 'product_update', 'product_delete'],
        'configuration': ['settings_update', 'workflow_config_update', 'openai_key_update', 
                         'n8n_config_update', 'kpi_range_update', 'category_weight_update'],
        'export': ['export_excel', 'export_csv', 'export_pdf'],
        'upload': ['kpi_upload', 'file_upload'],
        'playbook': ['playbook_execute', 'playbook_start', 'playbook_complete', 'playbook_cancel'],
        'system': ['rag_rebuild', 'data_migration', 'backup', 'restore'],
        'query': ['rag_query', 'direct_query'],  # RAG queries are logged separately but can be cross-referenced
    }
    
    @staticmethod
    def get_action_category(action_type: str) -> str:
        """Determine action category from action type"""
        for category, actions in ActivityLogger.ACTION_CATEGORIES.items():
            if action_type in actions:
                return category
        return 'system'  # Default to system
    
    @staticmethod
    def get_client_info() -> Dict[str, Optional[str]]:
        """Extract client information from request (works with or without request context)"""
        try:
            from flask import has_request_context, request as flask_request
            if has_request_context():
                return {
                    'ip_address': flask_request.remote_addr or flask_request.headers.get('X-Forwarded-For', '').split(',')[0].strip(),
                    'user_agent': flask_request.headers.get('User-Agent', ''),
                    'session_id': session.get('_id') if session else None,
                }
        except:
            pass
        
        # Fallback for non-request contexts (system actions, background jobs, etc.)
        return {
            'ip_address': None,
            'user_agent': None,
            'session_id': None,
        }
    
    @staticmethod
    def log_activity(
        customer_id: int,
        action_type: str,
        action_description: str,
        user_id: Optional[int] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        changed_fields: Optional[List[str]] = None,
        before_values: Optional[Dict[str, Any]] = None,
        after_values: Optional[Dict[str, Any]] = None,
        status: str = 'success',
        error_message: Optional[str] = None,
    ) -> Optional[int]:
        """
        Log an activity
        
        Args:
            customer_id: Customer ID performing the action
            action_type: Type of action (e.g., 'login', 'kpi_edit', 'settings_update')
            action_description: Human-readable description
            user_id: User ID (optional, can be None for system actions)
            resource_type: Type of resource affected (e.g., 'kpi', 'account', 'settings')
            resource_id: ID of resource affected
            details: Additional structured data
            changed_fields: List of field names that changed
            before_values: Dictionary of values before change
            after_values: Dictionary of values after change
            status: 'success', 'failure', or 'partial'
            error_message: Error message if status is 'failure'
        
        Returns:
            Activity log ID if successful, None otherwise
        """
        if not ACTIVITY_LOG_AVAILABLE or ActivityLog is None:
            # ActivityLog model not available, skip logging
            logger.debug(f"ActivityLog model not available, skipping log for {action_type}")
            return None
            
        try:
            # Get client info
            client_info = ActivityLogger.get_client_info()
            
            # Determine action category
            action_category = ActivityLogger.get_action_category(action_type)
            
            # Create activity log entry
            activity_log = ActivityLog(
                customer_id=customer_id,
                user_id=user_id,
                action_type=action_type,
                action_category=action_category,
                resource_type=resource_type,
                resource_id=str(resource_id) if resource_id else None,
                action_description=action_description,
                details=details or {},
                changed_fields=changed_fields or [],
                before_values=before_values or {},
                after_values=after_values or {},
                ip_address=client_info['ip_address'],
                user_agent=client_info['user_agent'],
                session_id=client_info['session_id'],
                status=status,
                error_message=error_message,
            )
            
            db.session.add(activity_log)
            db.session.commit()
            
            return activity_log.id
            
        except Exception as e:
            # Log error but don't fail the request
            logger.error(f"Failed to log activity: {e}", exc_info=True)
            try:
                db.session.rollback()
            except:
                pass
            return None
    
    @staticmethod
    def log_kpi_edit(
        customer_id: int,
        user_id: int,
        kpi_id: int,
        changed_fields: List[str],
        before_values: Dict[str, Any],
        after_values: Dict[str, Any],
        status: str = 'success',
        error_message: Optional[str] = None,
    ) -> Optional[int]:
        """Log KPI edit activity"""
        description = f"KPI #{kpi_id} edited: {', '.join(changed_fields)}"
        return ActivityLogger.log_activity(
            customer_id=customer_id,
            action_type='kpi_edit',
            action_description=description,
            user_id=user_id,
            resource_type='kpi',
            resource_id=str(kpi_id),
            changed_fields=changed_fields,
            before_values=before_values,
            after_values=after_values,
            status=status,
            error_message=error_message,
        )
    
    @staticmethod
    def log_account_update(
        customer_id: int,
        user_id: int,
        account_id: int,
        changed_fields: List[str],
        before_values: Dict[str, Any],
        after_values: Dict[str, Any],
        status: str = 'success',
        error_message: Optional[str] = None,
    ) -> Optional[int]:
        """Log account update activity"""
        description = f"Account #{account_id} updated: {', '.join(changed_fields)}"
        return ActivityLogger.log_activity(
            customer_id=customer_id,
            action_type='account_update',
            action_description=description,
            user_id=user_id,
            resource_type='account',
            resource_id=str(account_id),
            changed_fields=changed_fields,
            before_values=before_values,
            after_values=after_values,
            status=status,
            error_message=error_message,
        )
    
    @staticmethod
    def log_settings_change(
        customer_id: int,
        user_id: int,
        setting_type: str,
        changed_fields: List[str],
        before_values: Dict[str, Any],
        after_values: Dict[str, Any],
        status: str = 'success',
        error_message: Optional[str] = None,
    ) -> Optional[int]:
        """Log settings change activity"""
        description = f"{setting_type} settings updated: {', '.join(changed_fields)}"
        return ActivityLogger.log_activity(
            customer_id=customer_id,
            action_type='settings_update',
            action_description=description,
            user_id=user_id,
            resource_type='settings',
            resource_id=setting_type,
            changed_fields=changed_fields,
            before_values=before_values,
            after_values=after_values,
            status=status,
            error_message=error_message,
        )
    
    @staticmethod
    def log_login(
        customer_id: int,
        user_id: int,
        status: str = 'success',
        error_message: Optional[str] = None,
    ) -> Optional[int]:
        """Log user login"""
        description = f"User #{user_id} logged in" if status == 'success' else f"Login failed for user #{user_id}"
        return ActivityLogger.log_activity(
            customer_id=customer_id,
            action_type='login',
            action_description=description,
            user_id=user_id,
            status=status,
            error_message=error_message,
        )
    
    @staticmethod
    def log_logout(
        customer_id: int,
        user_id: int,
    ) -> Optional[int]:
        """Log user logout"""
        description = f"User #{user_id} logged out"
        return ActivityLogger.log_activity(
            customer_id=customer_id,
            action_type='logout',
            action_description=description,
            user_id=user_id,
        )
    
    @staticmethod
    def log_export(
        customer_id: int,
        user_id: int,
        export_type: str,
        filename: str,
        status: str = 'success',
        error_message: Optional[str] = None,
    ) -> Optional[int]:
        """Log export activity"""
        description = f"Exported {export_type} to {filename}"
        return ActivityLogger.log_activity(
            customer_id=customer_id,
            action_type='export_excel' if export_type == 'excel' else 'export_csv',
            action_description=description,
            user_id=user_id,
            resource_type='export',
            details={'export_type': export_type, 'filename': filename},
            status=status,
            error_message=error_message,
        )
    
    @staticmethod
    def log_upload(
        customer_id: int,
        user_id: int,
        upload_type: str,
        filename: str,
        upload_id: Optional[int] = None,
        status: str = 'success',
        error_message: Optional[str] = None,
    ) -> Optional[int]:
        """Log upload activity"""
        description = f"Uploaded {upload_type} file: {filename}"
        return ActivityLogger.log_activity(
            customer_id=customer_id,
            action_type='kpi_upload' if upload_type == 'kpi' else 'file_upload',
            action_description=description,
            user_id=user_id,
            resource_type='upload',
            resource_id=str(upload_id) if upload_id else None,
            details={'upload_type': upload_type, 'filename': filename},
            status=status,
            error_message=error_message,
        )
    
    @staticmethod
    def log_playbook_execution(
        customer_id: int,
        user_id: Optional[int],
        playbook_id: str,
        execution_id: str,
        account_id: Optional[int] = None,
        status: str = 'success',
        error_message: Optional[str] = None,
    ) -> Optional[int]:
        """Log playbook execution"""
        description = f"Playbook '{playbook_id}' executed (Execution ID: {execution_id})"
        return ActivityLogger.log_activity(
            customer_id=customer_id,
            action_type='playbook_execute',
            action_description=description,
            user_id=user_id,
            resource_type='playbook',
            resource_id=execution_id,
            details={'playbook_id': playbook_id, 'account_id': account_id},
            status=status,
            error_message=error_message,
        )


# Global instance
activity_logger = ActivityLogger()

