#!/usr/bin/env python3
"""
Onboarding Logger
=================

Verbose step-by-step logging for onboarding process.
Creates dedicated log files per customer onboarding session.
"""

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any
import json
import os

# Log directory
LOG_DIR = Path(__file__).parent / "logs" / "onboarding"
LOG_DIR.mkdir(parents=True, exist_ok=True)

# Format for verbose onboarding logs
ONBOARDING_LOG_FORMAT = '%(asctime)s | %(levelname)-8s | %(step)-25s | %(message)s'
ONBOARDING_DATE_FORMAT = '%Y-%m-%d %H:%M:%S.%f'

class OnboardingLogger:
    """
    Verbose logger for onboarding process with step-by-step tracking
    """
    
    def __init__(self, customer_id: int, customer_name: Optional[str] = None):
        """
        Initialize onboarding logger for a customer
        
        Args:
            customer_id: Customer ID
            customer_name: Customer name (optional)
        """
        self.customer_id = customer_id
        self.customer_name = customer_name or f"Customer {customer_id}"
        self.session_id = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.log_file = LOG_DIR / f"onboarding_customer{customer_id}_{self.session_id}.log"
        
        # Create logger
        self.logger = logging.getLogger(f'onboarding_customer{customer_id}')
        self.logger.setLevel(logging.DEBUG)
        
        # Remove existing handlers
        self.logger.handlers.clear()
        
        # File handler with rotation (50MB max, keep 10 backups)
        file_handler = RotatingFileHandler(
            str(self.log_file),
            maxBytes=50*1024*1024,  # 50MB
            backupCount=10,
            encoding='utf-8'
        )
        file_handler.setLevel(logging.DEBUG)
        
        # Custom formatter
        formatter = logging.Formatter(ONBOARDING_LOG_FORMAT, datefmt=ONBOARDING_DATE_FORMAT)
        file_handler.setFormatter(formatter)
        self.logger.addHandler(file_handler)
        
        # Log session start
        self.log_session_start()
    
    def log_session_start(self):
        """Log onboarding session start"""
        self.logger.info(
            f"═══════════════════════════════════════════════════════════════",
            extra={'step': 'SESSION_START'}
        )
        self.logger.info(
            f"ONBOARDING SESSION STARTED",
            extra={'step': 'SESSION_START'}
        )
        self.logger.info(
            f"Customer ID: {self.customer_id} | Name: {self.customer_name}",
            extra={'step': 'SESSION_START'}
        )
        self.logger.info(
            f"Session ID: {self.session_id} | Log File: {self.log_file.name}",
            extra={'step': 'SESSION_START'}
        )
        self.logger.info(
            f"═══════════════════════════════════════════════════════════════",
            extra={'step': 'SESSION_START'}
        )
    
    def log_step(self, step_name: str, message: str, status: str = 'INFO', details: Optional[Dict[str, Any]] = None):
        """
        Log a step in the onboarding process
        
        Args:
            step_name: Name of the step (e.g., 'PROVISION', 'UPLOAD_ACCOUNTS')
            message: Log message
            status: Status level ('INFO', 'SUCCESS', 'WARNING', 'ERROR')
            details: Optional dictionary with additional details
        """
        level_map = {
            'INFO': logging.INFO,
            'SUCCESS': logging.INFO,
            'WARNING': logging.WARNING,
            'ERROR': logging.ERROR,
            'DEBUG': logging.DEBUG
        }
        
        level = level_map.get(status.upper(), logging.INFO)
        
        # Format message with details
        if details:
            details_str = json.dumps(details, indent=2, default=str)
            full_message = f"{message}\nDetails:\n{details_str}"
        else:
            full_message = message
        
        # Add status prefix
        if status == 'SUCCESS':
            full_message = f"✅ {full_message}"
        elif status == 'ERROR':
            full_message = f"❌ {full_message}"
        elif status == 'WARNING':
            full_message = f"⚠️  {full_message}"
        
        self.logger.log(level, full_message, extra={'step': step_name})
    
    def log_provision_start(self, customer_name: str, vertical: str):
        """Log provisioning start"""
        self.log_step(
            'PROVISION_START',
            f"Starting customer directory provisioning",
            'INFO',
            {'customer_name': customer_name, 'vertical': vertical}
        )
    
    def log_provision_complete(self, directory_path: str):
        """Log provisioning completion"""
        self.log_step(
            'PROVISION_COMPLETE',
            f"Customer directory provisioned successfully",
            'SUCCESS',
            {'directory': directory_path}
        )
    
    def log_provision_error(self, error: str):
        """Log provisioning error"""
        self.log_step(
            'PROVISION_ERROR',
            f"Provisioning failed: {error}",
            'ERROR',
            {'error': error}
        )
    
    def log_complete_start(self, company_name: str, admin_email: str):
        """Log onboarding completion start"""
        self.log_step(
            'COMPLETE_START',
            f"Starting onboarding completion",
            'INFO',
            {'company_name': company_name, 'admin_email': admin_email}
        )
    
    def log_complete_success(self, customer_id: int, user_id: int, team_count: int = 0):
        """Log onboarding completion success"""
        self.log_step(
            'COMPLETE_SUCCESS',
            f"Onboarding completion successful",
            'SUCCESS',
            {
                'customer_id': customer_id,
                'user_id': user_id,
                'team_members_created': team_count
            }
        )
    
    def log_upload_file(self, file_type: str, filename: str, file_path: str, file_size: int):
        """Log file upload"""
        self.log_step(
            f'UPLOAD_{file_type.upper()}',
            f"File uploaded: {filename}",
            'SUCCESS',
            {
                'file_type': file_type,
                'filename': filename,
                'file_path': file_path,
                'size_bytes': file_size
            }
        )
    
    def log_process_data_start(self, skip_validation: bool, skip_wizard_b: bool):
        """Log data processing start"""
        self.log_step(
            'PROCESS_DATA_START',
            f"Starting data processing pipeline",
            'INFO',
            {
                'skip_validation': skip_validation,
                'skip_wizard_b': skip_wizard_b
            }
        )
    
    def log_script_start(self, script_name: str, script_path: str):
        """Log script execution start"""
        self.log_step(
            f'SCRIPT_START_{script_name}',
            f"Executing script: {script_name}",
            'INFO',
            {'script_path': script_path}
        )
    
    def log_script_success(self, script_name: str, stdout: str, duration_seconds: Optional[float] = None):
        """Log script execution success"""
        details = {'stdout_preview': stdout[:500] if stdout else ''}
        if duration_seconds:
            details['duration_seconds'] = round(duration_seconds, 2)
        
        self.log_step(
            f'SCRIPT_SUCCESS_{script_name}',
            f"Script completed successfully: {script_name}",
            'SUCCESS',
            details
        )
    
    def log_script_error(self, script_name: str, stderr: str, duration_seconds: Optional[float] = None):
        """Log script execution error"""
        details = {'error': stderr}
        if duration_seconds:
            details['duration_seconds'] = round(duration_seconds, 2)
        
        self.log_step(
            f'SCRIPT_ERROR_{script_name}',
            f"Script failed: {script_name}",
            'ERROR',
            details
        )
    
    def log_process_data_complete(self, steps_completed: list, errors: list):
        """Log data processing completion"""
        self.log_step(
            'PROCESS_DATA_COMPLETE',
            f"Data processing pipeline completed",
            'SUCCESS' if not errors else 'WARNING',
            {
                'steps_completed': steps_completed,
                'errors': errors,
                'total_steps': len(steps_completed)
            }
        )
    
    def log_rollback(self, steps_completed: list, rollback_actions: list):
        """Log rollback operation"""
        self.log_step(
            'ROLLBACK',
            f"Rollback triggered for partial operations",
            'WARNING',
            {
                'steps_completed': steps_completed,
                'rollback_actions_needed': rollback_actions
            }
        )
    
    def log_journey_api_registration(self, blueprint_name: str, success: bool, error: Optional[str] = None):
        """Log journey API registration"""
        if success:
            self.log_step(
                'JOURNEY_API_REGISTER',
                f"Journey API registered: {blueprint_name}",
                'SUCCESS',
                {'blueprint_name': blueprint_name}
            )
        else:
            self.log_step(
                'JOURNEY_API_REGISTER',
                f"Journey API registration failed: {error}",
                'ERROR',
                {'error': error}
            )
    
    def log_session_end(self, overall_status: str = 'SUCCESS', summary: Optional[Dict[str, Any]] = None):
        """Log onboarding session end"""
        self.logger.info(
            f"═══════════════════════════════════════════════════════════════",
            extra={'step': 'SESSION_END'}
        )
        self.logger.info(
            f"ONBOARDING SESSION ENDED - Status: {overall_status}",
            extra={'step': 'SESSION_END'}
        )
        if summary:
            summary_str = json.dumps(summary, indent=2, default=str)
            self.logger.info(
                f"Summary:\n{summary_str}",
                extra={'step': 'SESSION_END'}
            )
        self.logger.info(
            f"Log file: {self.log_file}",
            extra={'step': 'SESSION_END'}
        )
        self.logger.info(
            f"═══════════════════════════════════════════════════════════════",
            extra={'step': 'SESSION_END'}
        )
    
    def get_log_file_path(self) -> str:
        """Get the log file path"""
        return str(self.log_file)


# Global registry to track active onboarding sessions
_active_sessions: Dict[int, OnboardingLogger] = {}


def get_onboarding_logger(customer_id: int, customer_name: Optional[str] = None) -> OnboardingLogger:
    """
    Get or create onboarding logger for a customer
    
    Args:
        customer_id: Customer ID
        customer_name: Customer name (optional)
    
    Returns:
        OnboardingLogger instance
    """
    if customer_id not in _active_sessions:
        _active_sessions[customer_id] = OnboardingLogger(customer_id, customer_name)
    
    return _active_sessions[customer_id]


def close_onboarding_session(customer_id: int, overall_status: str = 'SUCCESS', summary: Optional[Dict[str, Any]] = None):
    """
    Close onboarding session and log summary
    
    Args:
        customer_id: Customer ID
        overall_status: Overall status ('SUCCESS', 'ERROR', 'WARNING')
        summary: Optional summary dictionary
    """
    if customer_id in _active_sessions:
        logger = _active_sessions[customer_id]
        logger.log_session_end(overall_status, summary)
        # Keep in registry for reference, but mark as closed
        # Could remove if needed: del _active_sessions[customer_id]
