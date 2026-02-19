"""
Provider Adapters — Phase 3
============================
Abstract base + concrete providers for the Action Interface.
Each provider implements execute() and returns a standardized result.
"""

from providers.base import ProviderBase, ProviderResult, ProviderError
from providers.registry import PROVIDER_REGISTRY, get_provider

__all__ = [
    'ProviderBase', 'ProviderResult', 'ProviderError',
    'PROVIDER_REGISTRY', 'get_provider',
]
