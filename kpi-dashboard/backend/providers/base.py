"""
Provider Base Class — Abstract interface for all action providers.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, Optional


class ProviderError(Exception):
    """Raised when a provider action fails."""
    def __init__(self, message: str, provider: str = '', retriable: bool = False):
        super().__init__(message)
        self.provider = provider
        self.retriable = retriable


@dataclass
class ProviderResult:
    """Standardized result from any provider action."""
    success: bool
    provider: str
    action_name: str
    response_data: Dict[str, Any] = field(default_factory=dict)
    external_id: Optional[str] = None     # Ticket ID, message ID, etc.
    external_url: Optional[str] = None    # Link to the created resource
    error_message: Optional[str] = None
    duration_ms: int = 0

    def to_dict(self) -> Dict:
        return {
            'success': self.success,
            'provider': self.provider,
            'action_name': self.action_name,
            'external_id': self.external_id,
            'external_url': self.external_url,
            'error_message': self.error_message,
            'duration_ms': self.duration_ms,
        }


class ProviderBase(ABC):
    """
    Abstract base class for provider adapters.

    Each provider must implement:
      - execute(action_name, params, credentials) → ProviderResult
      - validate_config(config) → bool
    """

    PROVIDER_NAME: str = 'base'

    @abstractmethod
    def execute(
        self,
        action_name: str,
        params: Dict[str, Any],
        credentials: Optional[Dict[str, Any]] = None,
        config: Optional[Dict[str, Any]] = None,
    ) -> ProviderResult:
        """Execute an action and return a standardized result."""
        ...

    @abstractmethod
    def validate_config(self, config: Dict[str, Any]) -> bool:
        """Validate that the provider config is complete and correct."""
        ...

    def health_check(self, credentials: Dict[str, Any]) -> bool:
        """Optional: verify that credentials are valid and service is reachable."""
        return True
