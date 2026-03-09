#!/usr/bin/env python3
"""
Agent Provider Factory — Provider-Agnostic Agent Creation
==========================================================
Extends the existing create_signal_analyst_agent() factory in
claude_signal_analyst_agent.py to support:
  - OpenAI  (GPT-4o, GPT-4-turbo)
  - Anthropic (Claude Opus 4.6, Sonnet 4.5, Haiku 4.5)
  - Azure OpenAI (same models via Azure endpoint)

Auto-detects provider from available API keys if not specified.
Supports per-customer provider preferences (future: from CustomerConfig).
"""

import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)


PROVIDER_CONFIGS = {
    'openai': {
        'env_key': 'OPENAI_API_KEY',
        'default_model': 'gpt-4o',
        'agent_module': 'agents.signal_analyst_agent',
        'agent_class': 'SignalAnalystAgent',
        'init_key_param': 'openai_api_key',
    },
    'anthropic': {
        'env_key': 'ANTHROPIC_API_KEY',
        'default_model': 'claude-sonnet-4-5-20250929',
        'agent_module': 'agents.claude_signal_analyst_agent',
        'agent_class': 'ClaudeSignalAnalystAgent',
        'init_key_param': 'anthropic_api_key',
    },
    'claude': {
        # Alias for 'anthropic'
        'env_key': 'ANTHROPIC_API_KEY',
        'default_model': 'claude-sonnet-4-5-20250929',
        'agent_module': 'agents.claude_signal_analyst_agent',
        'agent_class': 'ClaudeSignalAnalystAgent',
        'init_key_param': 'anthropic_api_key',
    },
    'azure': {
        'env_key': 'AZURE_OPENAI_API_KEY',
        'default_model': 'gpt-4o',
        'agent_module': 'agents.signal_analyst_agent',
        'agent_class': 'SignalAnalystAgent',
        'init_key_param': 'openai_api_key',
    },
}


class AgentProviderFactory:
    """
    Factory for creating AI agents with any supported provider.

    Usage:
        agent = AgentProviderFactory.create(customer_id=1, account_id='acct-123')
        agent = AgentProviderFactory.create(provider='anthropic', customer_id=1)
        agent = AgentProviderFactory.create(provider='openai', model='gpt-4-turbo', customer_id=1)
    """

    @classmethod
    def create(
        cls,
        provider: Optional[str] = None,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        customer_id: Optional[int] = None,
        account_id: Optional[str] = None,
    ):
        """
        Create an agent using the specified (or auto-detected) provider.

        Args:
            provider:    'openai' | 'anthropic' | 'claude' | 'azure' | None (auto-detect)
            api_key:     Provider API key (falls back to env var)
            model:       Model override (defaults per provider)
            customer_id: Customer ID for cost tracking
            account_id:  Account ID for cost tracking

        Returns:
            SignalAnalystAgent or ClaudeSignalAnalystAgent instance
        """
        # Auto-detect provider if not specified
        if not provider:
            provider = cls.detect_provider()

        provider = provider.lower()

        config = PROVIDER_CONFIGS.get(provider)
        if not config:
            raise ValueError(
                f"Unknown provider '{provider}'. "
                f"Supported: {list(PROVIDER_CONFIGS.keys())}"
            )

        # Resolve API key
        key = api_key or os.getenv(config['env_key'])
        if not key:
            raise ValueError(
                f"{config['env_key']} environment variable required for "
                f"provider '{provider}'"
            )

        # Resolve model
        model = model or config['default_model']

        logger.info(
            f"AgentProviderFactory: creating {provider} agent "
            f"(model={model}, customer={customer_id})"
        )

        # Use the existing factory function for simplicity
        from .claude_signal_analyst_agent import create_signal_analyst_agent
        return create_signal_analyst_agent(
            provider=provider,
            api_key=key,
            model=model,
            customer_id=customer_id,
            account_id=account_id,
        )

    @classmethod
    def detect_provider(cls) -> str:
        """
        Auto-detect the best available provider from environment variables.

        Priority: Anthropic > OpenAI > Azure
        (Anthropic preferred for cost-effective reasoning)
        """
        if os.getenv('ANTHROPIC_API_KEY'):
            return 'anthropic'
        if os.getenv('OPENAI_API_KEY'):
            return 'openai'
        if os.getenv('AZURE_OPENAI_API_KEY'):
            return 'azure'
        raise ValueError(
            "No AI provider API key found. Set one of: "
            "ANTHROPIC_API_KEY, OPENAI_API_KEY, AZURE_OPENAI_API_KEY"
        )

    @classmethod
    def available_providers(cls) -> dict:
        """Return dict of provider → bool (is API key available)."""
        return {
            'openai': bool(os.getenv('OPENAI_API_KEY')),
            'anthropic': bool(os.getenv('ANTHROPIC_API_KEY')),
            'azure': bool(os.getenv('AZURE_OPENAI_API_KEY')),
        }
