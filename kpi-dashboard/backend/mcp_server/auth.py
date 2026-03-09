"""
MCP Server Authentication — API key validation for HTTP transport.

For stdio transport (Claude Desktop, Claude Code), auth is implicit (local process).
For Streamable HTTP transport (Copilot Studio, ChatGPT), Bearer token auth is required.
"""

import os
from functools import wraps


# API key for HTTP transport — set via environment variable
MCP_SERVER_API_KEY = os.environ.get("MCP_SERVER_API_KEY", "")


def validate_api_key(api_key: str) -> bool:
    """Validate an API key against the configured server key."""
    if not MCP_SERVER_API_KEY:
        # No key configured — reject all HTTP requests
        return False
    return api_key == MCP_SERVER_API_KEY


def require_api_key(func):
    """Decorator to require API key for HTTP-transported tool calls.

    Only enforced when MCP_SERVER_API_KEY is set. If not set, all
    HTTP requests are rejected (stdio is always allowed).
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        # In stdio mode, this decorator is a no-op
        transport = os.environ.get("MCP_TRANSPORT", "stdio")
        if transport == "stdio":
            return func(*args, **kwargs)

        # For HTTP, check the API key
        api_key = os.environ.get("_MCP_CURRENT_API_KEY", "")
        if not validate_api_key(api_key):
            raise PermissionError("Invalid or missing MCP API key")
        return func(*args, **kwargs)

    return wrapper
