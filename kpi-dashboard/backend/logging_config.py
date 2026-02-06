#!/usr/bin/env python3
"""
Centralized Logging Configuration
Provides consistent timestamped logging across the backend
"""

import logging
import sys
from logging.handlers import RotatingFileHandler
import os

# Standard logging format with timestamp (to seconds level)
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
LOG_DATE_FORMAT = '%Y-%m-%d %H:%M:%S'

def configure_logging(
    level=logging.INFO,
    log_file=None,
    console=True,
    file_handler=True
):
    """
    Configure logging for the backend application
    
    Args:
        level: Logging level (default: INFO)
        log_file: Path to log file (optional)
        console: Whether to log to console (default: True)
        file_handler: Whether to use file handler (default: True)
    """
    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    
    # Remove existing handlers to avoid duplicates
    root_logger.handlers.clear()
    
    # Console handler
    if console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)
        console_formatter = logging.Formatter(LOG_FORMAT, datefmt=LOG_DATE_FORMAT)
        console_handler.setFormatter(console_formatter)
        root_logger.addHandler(console_handler)
    
    # File handler (if log file specified)
    if file_handler and log_file:
        # Create logs directory if it doesn't exist
        log_dir = os.path.dirname(log_file) if os.path.dirname(log_file) else '.'
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir, exist_ok=True)
        
        # Use rotating file handler (10MB max, keep 5 backups)
        file_handler_obj = RotatingFileHandler(
            log_file,
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5
        )
        file_handler_obj.setLevel(level)
        file_formatter = logging.Formatter(LOG_FORMAT, datefmt=LOG_DATE_FORMAT)
        file_handler_obj.setFormatter(file_formatter)
        root_logger.addHandler(file_handler_obj)
    
    return root_logger

def get_logger(name):
    """
    Get a logger instance with the configured format
    
    Args:
        name: Logger name (typically __name__)
    
    Returns:
        Logger instance
    """
    return logging.getLogger(name)

# Default configuration on import
configure_logging(level=logging.INFO)
