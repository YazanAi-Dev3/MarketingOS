"""Marketing OS Domain Tools for Hermes.

Exposes domain capabilities (scan_market, assess_lead, list_leads, request_approval)
to the Hermes agent loop.
"""
from marketing_plugin.tools.domain_tools import (
    DOMAIN_TOOLS,
    assess_lead,
    list_leads,
    request_approval,
    scan_market,
)

__all__ = [
    "DOMAIN_TOOLS",
    "assess_lead",
    "list_leads",
    "request_approval",
    "scan_market",
]
