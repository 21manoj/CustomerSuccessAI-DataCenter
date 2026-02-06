#!/usr/bin/env python3
"""
RAG Logging Utilities
Provides timestamped logging functions for RAG system
"""

from datetime import datetime
from typing import Any
import sys

def get_timestamp() -> str:
    """Get current timestamp formatted as YYYY-MM-DD HH:MM:SS"""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def log_print(*args: Any, **kwargs: Any) -> None:
    """Print with timestamp prefix"""
    timestamp = get_timestamp()
    print(f"[{timestamp}]", *args, **kwargs)

def log_info(message: str) -> None:
    """Log info message with timestamp"""
    timestamp = get_timestamp()
    print(f"[{timestamp}] ℹ️  {message}", file=sys.stdout)

def log_success(message: str) -> None:
    """Log success message with timestamp"""
    timestamp = get_timestamp()
    print(f"[{timestamp}] ✅ {message}", file=sys.stdout)

def log_warning(message: str) -> None:
    """Log warning message with timestamp"""
    timestamp = get_timestamp()
    print(f"[{timestamp}] ⚠️  {message}", file=sys.stderr)

def log_error(message: str) -> None:
    """Log error message with timestamp"""
    timestamp = get_timestamp()
    print(f"[{timestamp}] ❌ {message}", file=sys.stderr)

def log_debug(message: str) -> None:
    """Log debug message with timestamp"""
    timestamp = get_timestamp()
    print(f"[{timestamp}] 🔍 {message}", file=sys.stdout)

def log_build(message: str) -> None:
    """Log build/construction message with timestamp"""
    timestamp = get_timestamp()
    print(f"[{timestamp}] 🔧 {message}", file=sys.stdout)

def log_data(message: str) -> None:
    """Log data-related message with timestamp"""
    timestamp = get_timestamp()
    print(f"[{timestamp}] 📊 {message}", file=sys.stdout)

def log_security(message: str) -> None:
    """Log security-related message with timestamp"""
    timestamp = get_timestamp()
    print(f"[{timestamp}] 🔒 {message}", file=sys.stdout)
