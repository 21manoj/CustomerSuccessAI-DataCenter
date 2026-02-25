"""Base scenario class for all load test scenarios"""

import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class BaseScenario(ABC):
    """
    Abstract base class for all load test scenarios

    Subclasses must implement run() method
    """

    def __init__(self, client, args=None):
        """
        Initialize scenario

        Args:
            client: CSPulseClient instance (authenticated)
            args: argparse.Namespace with CLI arguments
        """
        self.client = client
        self.args = args or {}
        self.start_time = None
        self.end_time = None
        self.duration_seconds = None

    @abstractmethod
    def run(self) -> Dict[str, Any]:
        """
        Execute scenario and return results

        Must be implemented by subclasses

        Returns:
            Dict with keys:
            - status: 'success' or 'failure'
            - message: Human-readable summary
            - api_calls: Count of API calls made
            - errors: List of errors encountered
            - duration_seconds: Total execution time
            - details: Scenario-specific data
        """
        pass

    def _record_api_call(self, method: str, endpoint: str, status: str):
        """Record an API call for metrics"""
        logger.debug(f"  {method} {endpoint} [{status}]")

    def _format_duration(self, seconds: float) -> str:
        """Format duration as human-readable string"""
        if seconds < 1:
            return f"{seconds*1000:.0f}ms"
        elif seconds < 60:
            return f"{seconds:.1f}s"
        else:
            minutes = seconds / 60
            return f"{minutes:.1f}m"

    def start_timer(self):
        """Start execution timer"""
        self.start_time = datetime.now()

    def stop_timer(self):
        """Stop execution timer"""
        self.end_time = datetime.now()
        self.duration_seconds = (self.end_time - self.start_time).total_seconds()

    def success(self, message: str, details: Optional[Dict[str, Any]] = None, **kwargs) -> Dict[str, Any]:
        """Return success result"""
        self.stop_timer()
        return {
            'status': 'success',
            'message': message,
            'duration_seconds': self.duration_seconds,
            'details': details or {},
            **kwargs
        }

    def failure(self, message: str, error: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        """Return failure result"""
        self.stop_timer()
        return {
            'status': 'failure',
            'message': message,
            'error': error,
            'duration_seconds': self.duration_seconds,
            **kwargs
        }
