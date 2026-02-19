"""
Provider Registry — maps provider names to adapter instances.
"""

from typing import Dict, Optional
from providers.base import ProviderBase

# Lazy-loaded registry
_registry: Dict[str, ProviderBase] = {}


def _init_registry():
    """Initialize the provider registry on first access."""
    if _registry:
        return

    from providers.internal_provider import InternalProvider
    from providers.jira_provider import JiraProvider
    from providers.slack_provider import SlackProvider
    from providers.salesforce_provider import SalesforceProvider
    from providers.email_provider import EmailProvider

    _registry['cs_pulse_internal'] = InternalProvider()
    _registry['jira'] = JiraProvider()
    _registry['slack'] = SlackProvider()
    _registry['salesforce'] = SalesforceProvider()
    _registry['email'] = EmailProvider()


def get_provider(provider_name: str) -> Optional[ProviderBase]:
    """Get a provider adapter by name. Returns None if unknown."""
    _init_registry()
    return _registry.get(provider_name)


def PROVIDER_REGISTRY() -> Dict[str, ProviderBase]:
    """Return the full provider registry."""
    _init_registry()
    return dict(_registry)
