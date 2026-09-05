"""Marketing OS Plugin Package for Hermes.

Provides domain tools, repositories, policies, and adapters for
Market Radar, Content Engine, and Conversation Intake.
"""
from marketing_plugin.tools.domain_tools import (
    DOMAIN_TOOLS,
    assess_lead,
    list_leads,
    request_approval,
    scan_market,
)

__version__ = "0.1.0"

__all__ = [
    "__version__",
    "DOMAIN_TOOLS",
    "assess_lead",
    "list_leads",
    "request_approval",
    "scan_market",
]
