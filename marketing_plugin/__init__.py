"""Marketing OS Plugin Package for Hermes.

Provides domain tools, repositories, policies, and adapters for
Market Radar, Content Engine, and Conversation Intake.
"""
from marketing_plugin.repositories import InteractionRepository
from marketing_plugin.services import (
    ContentEngine,
    ConversationIntakeService,
    EntityResolver,
    MarketScanner,
    PublishingService,
)
from marketing_plugin.tools.domain_tools import (
    DOMAIN_TOOLS,
    assess_lead,
    generate_content,
    ingest_interaction,
    list_interactions,
    list_leads,
    publish_content,
    request_approval,
    scan_market,
)

__version__ = "0.1.0"

__all__ = [
    "__version__",
    "DOMAIN_TOOLS",
    "assess_lead",
    "generate_content",
    "publish_content",
    "ingest_interaction",
    "list_interactions",
    "list_leads",
    "request_approval",
    "scan_market",
    "ContentEngine",
    "ConversationIntakeService",
    "InteractionRepository",
    "PublishingService",
    "EntityResolver",
    "MarketScanner",
]

