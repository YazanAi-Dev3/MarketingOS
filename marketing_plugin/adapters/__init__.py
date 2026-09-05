"""Marketing OS Adapters.

Infrastructure, reasoning, and specialized source adapters:
- Antigravity / Gemini API reasoning adapter
- SearXNG metasearch adapter
- Crawl4AI / Direct HTTP acquisition router
- BaseSourceAdapter and specialized freelance adapters (Bahr, Mostaql, Khamsat)
"""
from marketing_plugin.adapters.acquisition_router import (
    AcquisitionMode,
    AcquisitionResult,
    AcquisitionRouter,
    compute_content_hash,
    is_ssrf_safe_url,
)
from marketing_plugin.adapters.antigravity_adapter import (
    AntigravityAdapter,
    ReasoningResult,
)
from marketing_plugin.adapters.bahr_adapter import BahrAdapter
from marketing_plugin.adapters.base import BaseSourceAdapter
from marketing_plugin.adapters.khamsat_adapter import KhamsatAdapter
from marketing_plugin.adapters.mostaql_adapter import MostaqlAdapter
from marketing_plugin.adapters.searxng_adapter import (
    SearXNGAdapter,
    normalize_url,
)

__all__ = [
    "AcquisitionMode",
    "AcquisitionResult",
    "AcquisitionRouter",
    "compute_content_hash",
    "is_ssrf_safe_url",
    "AntigravityAdapter",
    "ReasoningResult",
    "BaseSourceAdapter",
    "BahrAdapter",
    "KhamsatAdapter",
    "MostaqlAdapter",
    "SearXNGAdapter",
    "normalize_url",
]
