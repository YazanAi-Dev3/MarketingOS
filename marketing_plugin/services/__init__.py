"""Marketing OS Domain Services.

Exports core pipeline services:
- EntityResolver: Canonical root domain normalization and identity deduplication.
- MarketScanner: Regional discovery, acquisition, extraction, and lead ingestion.
"""
from marketing_plugin.services.entity_resolver import (
    EntityResolver,
    ResolutionOutcome,
)
from marketing_plugin.services.market_scanner import (
    MarketScanner,
    ScanRunSummary,
)

__all__ = [
    "EntityResolver",
    "ResolutionOutcome",
    "MarketScanner",
    "ScanRunSummary",
]
