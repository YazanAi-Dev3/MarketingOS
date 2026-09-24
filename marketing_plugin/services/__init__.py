"""Marketing OS Domain Services.

Exports core pipeline services:
- EntityResolver: Canonical root domain normalization and identity deduplication.
- MarketScanner: Regional discovery, acquisition, extraction, and lead ingestion.
- LeadScorer: AI-assisted multi-factor lead qualification and scoring.
"""
from marketing_plugin.services.entity_resolver import (
    EntityResolver,
    ResolutionOutcome,
)
from marketing_plugin.services.market_scanner import (
    MarketScanner,
    ScanRunSummary,
)
from marketing_plugin.services.lead_scorer import (
    LeadScorer,
    LeadScorerResult,
)

__all__ = [
    "EntityResolver",
    "ResolutionOutcome",
    "MarketScanner",
    "ScanRunSummary",
    "LeadScorer",
    "LeadScorerResult",
]
