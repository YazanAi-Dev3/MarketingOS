"""Marketing OS Domain Schemas.

Pydantic models representing domain entities according to docs/02-technical-design-spec.md.
"""
from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class FunnelType(str, Enum):
    B2B = "b2b"
    ACADEMIC = "academic"


class PriorityClass(str, Enum):
    PRIMARY = "primary"
    SECONDARY = "secondary"
    TERTIARY = "tertiary"


class SourceStatus(str, Enum):
    CANDIDATE = "candidate"
    TRUSTED = "trusted"
    DEGRADED = "degraded"
    BLOCKED = "blocked"
    DEAD = "dead"


class AccessMode(str, Enum):
    PUBLIC = "public"
    AUTHORIZED_CONNECTOR = "authorized_connector"
    MANUAL = "manual"


class ExtractorType(str, Enum):
    DETERMINISTIC = "deterministic"
    MODEL_ASSISTED = "model_assisted"
    MANUAL = "manual"


class LeadStatus(str, Enum):
    DISCOVERED = "discovered"
    QUALIFIED = "qualified"
    REJECTED = "rejected"
    OUTREACH_READY = "outreach_ready"
    CONTACTED = "contacted"
    REPLIED = "replied"
    MEETING = "meeting"
    PROPOSAL = "proposal"
    WON = "won"
    LOST = "lost"
    DORMANT = "dormant"


class ContentIdeaObjective(str, Enum):
    TRUST = "trust"
    EDUCATION = "education"
    DEMAND_CAPTURE = "demand_capture"
    DIRECT_OFFER = "direct_offer"
    CASE_STYLE = "case_style"


class ContentAssetStatus(str, Enum):
    DRAFT = "draft"
    AWAITING_APPROVAL = "awaiting_approval"
    APPROVED = "approved"
    REJECTED = "rejected"
    SCHEDULED = "scheduled"
    PUBLISHED = "published"
    FAILED = "failed"


class ApprovalDecision(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    REWRITE_REQUESTED = "rewrite_requested"


class InteractionDirection(str, Enum):
    INBOUND = "inbound"
    OUTBOUND = "outbound"


# --- Core Domain Models ---

class CountryProfile(BaseModel):
    country_code: str = Field(..., max_length=5)
    name: str
    languages: List[str] = Field(default_factory=list)
    enabled: bool = True
    manual_weight: Optional[float] = None
    query_lexicon_version: str = "1.0"
    source_policy_version: str = "1.0"
    updated_at: datetime = Field(default_factory=utc_now)
    updated_by: str = "system"


class ServiceProfile(BaseModel):
    service_key: str
    priority_class: PriorityClass
    enabled: bool = True
    allowed_funnels: List[FunnelType] = Field(default_factory=lambda: [FunnelType.B2B])
    offer_summary: str
    qualification_policy_version: str = "1.0"


class Source(BaseModel):
    source_id: str
    domain_or_platform_key: str
    country_scope: List[str] = Field(default_factory=list)
    source_family: str
    languages: List[str] = Field(default_factory=list)
    status: SourceStatus = SourceStatus.CANDIDATE
    first_seen_at: datetime = Field(default_factory=utc_now)
    last_seen_at: datetime = Field(default_factory=utc_now)
    last_success_at: Optional[datetime] = None
    access_mode: AccessMode = AccessMode.PUBLIC
    metadata_json: Dict[str, Any] = Field(default_factory=dict)


class SourceCapabilityScore(BaseModel):
    source_id: str
    capability: str
    score: float = 0.0
    sample_count: int = 0
    last_updated_at: datetime = Field(default_factory=utc_now)
    score_version: str = "1.0"


class SearchRun(BaseModel):
    search_run_id: str
    intent: str
    country_code: str
    service_key: Optional[str] = None
    query_plan_json: Dict[str, Any] = Field(default_factory=dict)
    engine_profile: str = "default"
    config_snapshot_hash: str = ""
    started_at: datetime = Field(default_factory=utc_now)
    finished_at: Optional[datetime] = None
    status: str = "pending"
    result_count: int = 0
    error_summary: Optional[str] = None


class SearchResult(BaseModel):
    search_result_id: str
    search_run_id: str
    url: str
    normalized_url: str
    title: str
    snippet: str
    rank: int
    engine_sources: List[str] = Field(default_factory=list)
    discovered_at: datetime = Field(default_factory=utc_now)


class Company(BaseModel):
    company_id: str
    canonical_name: str
    primary_domain: Optional[str] = None
    country_code: str
    city: Optional[str] = None
    sector: Optional[str] = None
    public_contacts_json: Dict[str, Any] = Field(default_factory=dict)
    funnel: FunnelType = FunnelType.B2B
    entity_confidence: float = 1.0
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class Evidence(BaseModel):
    evidence_id: str
    company_id: Optional[str] = None
    source_id: str
    url: str
    artifact_path: Optional[str] = None
    observed_at: datetime = Field(default_factory=utc_now)
    published_at: Optional[datetime] = None
    fact_type: str
    fact_text: str
    extractor: ExtractorType = ExtractorType.DETERMINISTIC
    content_hash: str
    confidence: float = 1.0


class Signal(BaseModel):
    signal_id: str
    company_id: str
    type: str
    summary: str
    evidence_ids: List[str] = Field(default_factory=list)
    confidence: float = 1.0
    model_or_rule_identity: str
    created_at: datetime = Field(default_factory=utc_now)
    valid_until: Optional[datetime] = None


class Lead(BaseModel):
    lead_id: str
    company_id: str
    funnel: FunnelType = FunnelType.B2B
    status: LeadStatus = LeadStatus.DISCOVERED
    priority_bucket: int = 3
    recommended_service_key: Optional[str] = None
    owner: Optional[str] = None
    next_action: Optional[str] = None
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class LeadAssessment(BaseModel):
    assessment_id: str
    lead_id: str
    assessment_version: str = "1.0"
    fit_score: float = 0.0
    pain_score: float = 0.0
    urgency_score: float = 0.0
    reachability_score: float = 0.0
    final_score: float = 0.0
    confidence: float = 1.0
    recommended_service_key: Optional[str] = None
    evidence_ids: List[str] = Field(default_factory=list)
    reasoning_summary: str
    provider_identity: str = "antigravity"
    prompt_contract_version: str = "1.0"
    created_at: datetime = Field(default_factory=utc_now)


class ContentIdea(BaseModel):
    content_idea_id: str
    funnel: FunnelType = FunnelType.B2B
    market_scope: List[str] = Field(default_factory=list)
    service_key: str
    source_signal_ids: List[str] = Field(default_factory=list)
    topic: str
    objective: ContentIdeaObjective = ContentIdeaObjective.DEMAND_CAPTURE
    score: float = 0.0
    status: str = "proposed"


class ContentAsset(BaseModel):
    content_asset_id: str
    idea_id: str
    master_content: str
    platform: str
    format: str
    body: str
    media_brief: Optional[str] = None
    cta: str
    status: ContentAssetStatus = ContentAssetStatus.DRAFT
    version: int = 1


class Approval(BaseModel):
    approval_id: str
    action_type: str
    target_type: str
    target_id: str
    requested_at: datetime = Field(default_factory=utc_now)
    resolved_at: Optional[datetime] = None
    actor_id: Optional[str] = None
    decision: ApprovalDecision = ApprovalDecision.PENDING
    notes: Optional[str] = None


class ActorType(str, Enum):
    HUMAN = "human"
    AGENT_DRAFT = "agent_draft"
    EXTERNAL = "external"


class Interaction(BaseModel):
    interaction_id: str
    lead_id: Optional[str] = None
    channel: str
    external_party_ref: Optional[str] = None
    direction: InteractionDirection = InteractionDirection.OUTBOUND
    actor: ActorType = ActorType.HUMAN
    content_summary: str
    outcome_tag: Optional[str] = None
    raw_content_path: Optional[str] = None
    occurred_at: datetime = Field(default_factory=utc_now)


class AgentRun(BaseModel):
    agent_run_id: str
    task_type: str
    provider_path: str
    model_identity: Optional[str] = None
    input_refs: List[str] = Field(default_factory=list)
    input_size_estimate: int = 0
    output_contract_version: str = "1.0"
    started_at: datetime = Field(default_factory=utc_now)
    finished_at: Optional[datetime] = None
    status: str = "started"
    error_class: Optional[str] = None
    approval_required: bool = False

