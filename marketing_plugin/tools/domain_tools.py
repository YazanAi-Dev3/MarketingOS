"""Marketing OS Domain Tools for Hermes Agent.

Provides the core domain tools registered with Hermes:
- scan_market: Intent & regional discovery across search and freelance adapters
- assess_lead: Deterministic qualification and scoring for company leads
- list_leads: Filter and inspect lead pipeline by status and country
- request_approval: Human gatekeeper requests for public/external actions (A-007)
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

from marketing_plugin.adapters.bahr_adapter import BahrAdapter
from marketing_plugin.adapters.base import BaseSourceAdapter
from marketing_plugin.adapters.khamsat_adapter import KhamsatAdapter
from marketing_plugin.adapters.mostaql_adapter import MostaqlAdapter
from marketing_plugin.adapters.postiz_adapter import PostizAdapter
from marketing_plugin.policies.query_planner import RegionalQueryPlanner
from marketing_plugin.repositories.approval_repo import ApprovalRepository
from marketing_plugin.repositories.company_repo import CompanyRepository
from marketing_plugin.repositories.database import Database
from marketing_plugin.repositories.evidence_repo import EvidenceRepository
from marketing_plugin.repositories.interaction_repo import InteractionRepository
from marketing_plugin.repositories.lead_repo import LeadRepository
from marketing_plugin.repositories.source_repo import SourceRepository
from marketing_plugin.services.content_engine import ContentEngine
from marketing_plugin.services.conversation_intake import ConversationIntakeService
from marketing_plugin.services.lead_scorer import LeadScorer, LeadScorerResult
from marketing_plugin.services.market_scanner import MarketScanner, ScanRunSummary
from marketing_plugin.services.publishing_service import PublishingService
from schemas.models import (
    Approval,
    ApprovalDecision,
    ContentIdeaObjective,
    FunnelType,
    Lead,
    LeadAssessment,
    LeadStatus,
    SourceStatus,
    utc_now,
)

logger = logging.getLogger(__name__)

_DEFAULT_DB_PATH = "data/marketing.db"


def _get_db(db: Optional[Database] = None) -> Database:
    if db is not None:
        return db
    return Database(_DEFAULT_DB_PATH)


def scan_market(
    country_code: str,
    query: Optional[str] = None,
    service_key: Optional[str] = None,
    db: Optional[Database] = None,
    planner: Optional[RegionalQueryPlanner] = None,
    searxng_adapter: Optional[Any] = None,
    acquisition_router: Optional[Any] = None,
    scanner: Optional[MarketScanner] = None,
    limit: Optional[int] = None,
    run_full_scanner: bool = False,
) -> Dict[str, Any]:
    """Scans regional market for lead/service discovery using search and freelance sources.

    Supports running both fast discovery checks and the full end-to-end MarketScanner
    pipeline with page acquisition, extraction, entity resolution, and SQLite storage.

    Args:
        country_code: Two-letter ISO country code (e.g. 'SA', 'AE').
        query: Market scan intent or search topic.
        service_key: Optional service key (e.g. 'ai_automation', 'software_dev').
        db: Optional Database manager for recording the run.
        planner: Optional query planner override.
        searxng_adapter: Optional SearXNG adapter instance.
        acquisition_router: Optional AcquisitionRouter instance.
        scanner: Optional pre-configured MarketScanner instance.
        limit: Optional limit on queries / discovered URLs.
        run_full_scanner: Whether to execute the full page acquisition and resolution pipeline.
    """
    country_code = country_code.strip().upper()
    active_service = service_key or "ai_automation"
    query_planner = planner or RegionalQueryPlanner()

    # If full scanner requested or explicit MarketScanner supplied or query omitted
    if run_full_scanner or scanner is not None or query is None:
        active_scanner = scanner or MarketScanner(
            db=db,
            planner=query_planner,
            searxng_adapter=searxng_adapter,
            acquisition_router=acquisition_router,
        )
        summary = active_scanner.scan(
            country_code=country_code,
            service_key=active_service,
            limit=limit,
            query=query,
        )
        return {
            "status": "success",
            "country_code": country_code,
            "service_key": active_service,
            "query": query,
            "scan_summary": summary.to_dict(),
            "created_companies": summary.created_companies,
            "merged_companies": summary.merged_companies,
            "saved_evidence": summary.saved_evidence,
            "acquired_pages": summary.acquired_pages,
            "discovered_urls": summary.discovered_urls,
            "queries_executed": summary.queries_executed,
            "errors": summary.errors,
        }

    # 1. Generate Regional Query Plan
    plan = query_planner.plan(
        country_code=country_code,
        service_key=active_service,
        intent="market_scan",
    )

    planned_queries = [query]
    for q in plan.queries:
        if q not in planned_queries:
            planned_queries.append(q)

    # 2. Collect specialized freelance candidate search URLs
    candidate_sources: List[Dict[str, str]] = []
    registered_sources: List[Dict[str, str]] = []

    adapter_instances: Dict[str, BaseSourceAdapter] = {
        "mostaql": MostaqlAdapter(),
        "khamsat": KhamsatAdapter(),
        "bahr": BahrAdapter(),
    }

    if db is not None:
        try:
            conn = db.connect()
            source_repo = SourceRepository(conn)
            all_sources = source_repo.list_sources(status=SourceStatus.TRUSTED)
            for src in all_sources:
                country_scopes = [c.strip().upper() for c in src.country_scope if isinstance(c, str)]
                if (
                    country_code in country_scopes
                    or (country_code in ("SA", "KSA") and any(c in ("SA", "KSA") for c in country_scopes))
                    or "ALL" in country_scopes
                ):
                    key = src.source_id.lower()
                    adapter = adapter_instances.get(key)
                    if not adapter:
                        for ak, av in adapter_instances.items():
                            if ak in src.domain_or_platform_key.lower():
                                key = ak
                                adapter = av
                                break
                    if adapter and not any(cs["source"] == key for cs in registered_sources):
                        registered_sources.append({
                            "source": key,
                            "url": adapter.build_search_url(query),
                        })
        except Exception as exc:
            logger.warning("Failed to retrieve sources from repository: %s", exc)

    if registered_sources:
        candidate_sources = registered_sources
    else:
        # Fallback to static list only when db is None or no matching sources in repository
        mostaql = adapter_instances["mostaql"]
        khamsat = adapter_instances["khamsat"]
        candidate_sources.append({"source": "mostaql", "url": mostaql.build_search_url(query)})
        candidate_sources.append({"source": "khamsat", "url": khamsat.build_search_url(query)})

        if country_code in ("SA", "KSA"):
            bahr = adapter_instances["bahr"]
            candidate_sources.append({"source": "bahr", "url": bahr.build_search_url(query)})

    # 3. If SearXNG adapter supplied, execute discovery queries
    results: List[Dict[str, Any]] = []
    if searxng_adapter is not None:
        for q in planned_queries[:3]:  # Top 3 queries
            try:
                search_res = searxng_adapter.search(query=q, country_code=country_code)
                for res in search_res:
                    results.append({
                        "url": res.url,
                        "title": res.title,
                        "snippet": res.snippet,
                        "engines": res.engine_sources,
                    })
            except Exception as exc:
                logger.warning("SearXNG search failed for '%s': %s", q, exc)

    return {
        "status": "success",
        "country_code": country_code,
        "query": query,
        "service_key": active_service,
        "planned_queries": planned_queries,
        "language_target": plan.language_target,
        "candidate_sources": candidate_sources,
        "results_count": len(results),
        "results": results,
    }


def assess_lead(
    company_id: str,
    context: Optional[Dict[str, Any]] = None,
    db: Optional[Database] = None,
    scorer: Optional[LeadScorer] = None,
) -> Dict[str, Any]:
    """Assesses a company entity and produces an append-only LeadAssessment snapshot.

    Uses LeadScorer for AI-assisted multi-factor scoring (M-01), academic integrity checks (A-008),
    and deterministic fallback behavior.

    Args:
        company_id: The ID of the company to evaluate.
        context: Optional evaluation context or override weights.
        db: Optional Database instance.
        scorer: Optional LeadScorer instance.
    """
    database = _get_db(db)
    active_scorer = scorer or LeadScorer(db=database)
    res = active_scorer.score_company(company_id=company_id, context=context)

    if not res.success:
        return {
            "status": "error",
            "error": res.error or f"Company '{company_id}' not found in registry",
        }

    return {
        "status": "success",
        "assessment_id": res.assessment_id,
        "company_id": res.company_id,
        "lead_id": res.lead_id,
        "fit_score": res.fit_score,
        "pain_score": res.pain_score,
        "urgency_score": res.urgency_score,
        "reachability_score": res.reachability_score,
        "final_score": res.final_score,
        "lead_status": res.status.value,
        "priority_bucket": res.priority_bucket,
        "reasoning_summary": res.reasoning_summary,
        "academic_integrity_passed": res.academic_integrity_passed,
        "confidence": res.confidence,
    }


def list_leads(
    status: Optional[str] = None,
    country_code: Optional[str] = None,
    limit: int = 50,
    db: Optional[Database] = None,
) -> List[Dict[str, Any]]:
    """Lists leads filtered by status and country code, ordered by priority bucket.

    Args:
        status: Optional filter by LeadStatus (e.g. 'qualified', 'discovered').
        country_code: Optional filter by country code (e.g. 'SA', 'AE').
        limit: Maximum number of leads to return (default 50).
        db: Optional Database instance.
    """
    database = _get_db(db)
    conn = database.connect()
    lead_repo = LeadRepository(conn)
    company_repo = CompanyRepository(conn)

    status_enum: Optional[LeadStatus] = None
    if status:
        try:
            status_enum = LeadStatus(status.strip().lower())
        except ValueError:
            logger.warning("Unrecognized lead status filter: %s", status)

    all_leads = lead_repo.list_leads(status=status_enum)

    results: List[Dict[str, Any]] = []
    target_country = country_code.strip().upper() if country_code else None

    for lead in all_leads:
        if target_country:
            comp = company_repo.get_company(lead.company_id)
            if not comp or comp.country_code.upper() != target_country:
                continue

        results.append({
            "lead_id": lead.lead_id,
            "company_id": lead.company_id,
            "funnel": lead.funnel.value,
            "status": lead.status.value,
            "priority_bucket": lead.priority_bucket,
            "recommended_service_key": lead.recommended_service_key,
            "owner": lead.owner,
            "next_action": lead.next_action,
            "created_at": lead.created_at.isoformat(),
            "updated_at": lead.updated_at.isoformat(),
        })
        if len(results) >= limit:
            break

    return results


def request_approval(
    action_type: str,
    target_type: str,
    target_id: str,
    notes: Optional[str] = None,
    db: Optional[Database] = None,
) -> Dict[str, Any]:
    """Creates a human approval request safeguarding public/external actions (Invariant A-007).

    Args:
        action_type: Type of action (e.g. 'publish_content', 'outreach_send').
        target_type: Entity type (e.g. 'content_asset', 'lead', 'interaction').
        target_id: ID of the entity subject to approval.
        notes: Optional context or explanation for human operator.
        db: Optional Database instance.
    """
    database = _get_db(db)
    conn = database.connect()
    approval_repo = ApprovalRepository(conn)

    approval_id = f"appr_{uuid.uuid4().hex[:12]}"
    approval = Approval(
        approval_id=approval_id,
        action_type=action_type.strip(),
        target_type=target_type.strip(),
        target_id=target_id.strip(),
        decision=ApprovalDecision.PENDING,
        notes=notes,
        requested_at=utc_now(),
    )
    approval_repo.create_request(approval)

    return {
        "status": "requested",
        "approval_id": approval_id,
        "action_type": approval.action_type,
        "target_type": approval.target_type,
        "target_id": approval.target_id,
        "decision": approval.decision.value,
        "requested_at": approval.requested_at.isoformat(),
        "notes": approval.notes,
    }


def generate_content(
    service_key: str = "ai_automation",
    topic: Optional[str] = None,
    country_code: Optional[str] = "SA",
    platforms: Optional[List[str]] = None,
    objective: str = "demand_capture",
    evidence_ids: Optional[List[str]] = None,
    count: int = 1,
    db: Optional[Database] = None,
) -> Dict[str, Any]:
    """Synthesizes grounded marketing ideas and drafts tailored multi-platform copy (Invariant A-028, A-007).

    Generates structured drafts for LinkedIn, X/Twitter, Instagram, and Telegram,
    placing all assets into 'awaiting_approval' status with persistent approval records.

    Args:
        service_key: Offering to promote ('ai_automation', 'software_systems', 'academic_mentoring').
        topic: Optional explicit custom topic to focus the drafts.
        country_code: Regional targeting code (e.g. 'SA', 'AE').
        platforms: List of target platforms (default: ['linkedin', 'twitter', 'instagram', 'telegram']).
        objective: Strategic objective ('demand_capture', 'case_style', 'education', 'trust', 'direct_offer').
        evidence_ids: Specific evidence IDs to cite and ground the narrative.
        count: Number of ideas to generate if topic is not provided.
        db: Optional Database instance.
    """
    database = _get_db(db)
    engine = ContentEngine(db=database)

    try:
        obj_enum = ContentIdeaObjective(objective.lower().strip())
    except (ValueError, AttributeError):
        obj_enum = ContentIdeaObjective.DEMAND_CAPTURE

    target_scope = [country_code.upper().strip()] if country_code else ["SA"]

    ideas = engine.generate_ideas(
        service_key=service_key,
        market_scope=target_scope,
        evidence_ids=evidence_ids,
        count=count,
        objective=obj_enum,
        custom_topic=topic,
    )

    if not ideas:
        return {
            "status": "error",
            "message": "No content ideas could be generated for the specified parameters.",
            "ideas": [],
            "assets": [],
        }

    primary_idea = ideas[0]
    drafted_assets = engine.draft_multiplatform_assets(
        idea_id=primary_idea.content_idea_id,
        platforms=platforms or ["linkedin", "twitter", "instagram", "telegram"],
        auto_request_approval=True,
    )

    return {
        "status": "success",
        "primary_idea": {
            "idea_id": primary_idea.content_idea_id,
            "topic": primary_idea.topic,
            "objective": primary_idea.objective.value,
            "service_key": primary_idea.service_key,
            "score": primary_idea.score,
            "source_evidence_ids": primary_idea.source_signal_ids,
        },
        "all_ideas_count": len(ideas),
        "assets_count": len(drafted_assets),
        "assets": [
            {
                "asset_id": a.content_asset_id,
                "platform": a.platform,
                "format": a.format,
                "status": a.status.value,
                "body_preview": a.body[:150] + "..." if len(a.body) > 150 else a.body,
                "cta": a.cta,
                "media_brief": a.media_brief,
            }
            for a in drafted_assets
        ],
        "approval_required": True,
        "policy_notice": "Assets created in 'awaiting_approval' status. Human approval required prior to publishing (A-007, I-02).",
    }


def publish_content(
    asset_id: str,
    scheduled_at: Optional[str] = None,
    force_manual: bool = False,
    db: Optional[Database] = None,
    postiz_adapter: Optional[PostizAdapter] = None,
) -> Dict[str, Any]:
    """Publishes or schedules an approved content asset to social channels (Invariants A-007, A-021, I-02).

    Enforces mandatory human gatekeeper approval. Connects to Postiz for social networks,
    direct Telegram dispatch, or provides a structured manual export package if Postiz is offline (R-04).

    Args:
        asset_id: Unique ID of the ContentAsset to publish.
        scheduled_at: Optional ISO 8601 timestamp string for scheduling.
        force_manual: Whether to force manual export even if automated publishing is available.
        db: Optional Database manager instance.
        postiz_adapter: Optional PostizAdapter override.
    """
    database = _get_db(db)
    service = PublishingService(
        db=database,
        postiz_adapter=postiz_adapter,
    )

    sched_dt: Optional[datetime] = None
    if scheduled_at:
        try:
            sched_dt = datetime.fromisoformat(scheduled_at)
        except Exception:
            pass

    try:
        res = service.dispatch_asset(
            content_asset_id=asset_id,
            scheduled_at=sched_dt,
            force_manual=force_manual,
        )
        return {
            "status": "success" if res.success else "failed",
            "asset_id": res.asset_id,
            "platform": res.platform,
            "publication_status": res.status,
            "dispatch_mode": res.dispatch_mode,
            "remote_id": res.remote_id,
            "scheduled_at": res.scheduled_at,
            "manual_export_package": res.manual_export_package,
            "error": res.error,
        }
    except PermissionError as exc:
        return {
            "status": "permission_denied",
            "asset_id": asset_id,
            "error": str(exc),
            "approval_required": True,
            "policy_violation": "A-007/I-02: External actions require human approval record with decision='approved'.",
        }
    except ValueError as exc:
        return {
            "status": "not_found",
            "asset_id": asset_id,
            "error": str(exc),
        }


def ingest_interaction(
    channel: str,
    sender_ref: str,
    message: str,
    country_code: Optional[str] = None,
    sender_name: Optional[str] = None,
    company_name: Optional[str] = None,
    auto_request_approval: bool = True,
    db: Optional[Database] = None,
) -> Dict[str, Any]:
    """Ingests an inbound interaction across channels (WhatsApp, Telegram, Email, Web).

    Performs secret scrubbing (A-018, I-05), checks academic integrity (A-008),
    resolves company and lead, generates a proposed AI reply draft (actor='agent_draft'),
    and registers human approval request if enabled (A-007, I-02, A-022).

    Args:
        channel: Channel key ('whatsapp', 'telegram', 'email', 'web').
        sender_ref: Contact identifier (phone, email, username).
        message: Raw incoming message text.
        country_code: Country ISO code (default: 'SA').
        sender_name: Optional sender name.
        company_name: Optional company name.
        auto_request_approval: Whether to generate an approval request for reply.
        db: Optional Database manager instance.
    """
    database = _get_db(db)
    service = ConversationIntakeService(db=database)
    outcome = service.ingest_message(
        channel=channel,
        external_party_ref=sender_ref,
        message_text=message,
        country_code=country_code,
        sender_name=sender_name,
        company_name=company_name,
        auto_request_approval=auto_request_approval,
    )
    return {
        "status": "success" if outcome.success else "failed",
        "interaction_id": outcome.interaction_id,
        "lead_id": outcome.lead_id,
        "company_id": outcome.company_id,
        "channel": outcome.channel,
        "funnel": outcome.funnel,
        "intent": outcome.intent,
        "is_academic_violation": outcome.is_academic_violation,
        "suggested_reply": outcome.suggested_reply,
        "approval_id": outcome.approval_id,
        "intake_status": outcome.status,
        "reasoning": outcome.reasoning,
    }


def list_interactions(
    lead_id: Optional[str] = None,
    channel: Optional[str] = None,
    limit: int = 50,
    db: Optional[Database] = None,
) -> List[Dict[str, Any]]:
    """Lists interactions filtered by lead ID or channel.

    Args:
        lead_id: Optional Lead ID filter.
        channel: Optional Channel filter.
        limit: Max interactions to return (default: 50).
        db: Optional Database manager instance.
    """
    database = _get_db(db)
    conn = database.connect()
    repo = InteractionRepository(conn)
    interactions = repo.list_interactions(
        lead_id=lead_id,
        channel=channel,
        limit=limit,
    )
    return [
        {
            "interaction_id": i.interaction_id,
            "lead_id": i.lead_id,
            "channel": i.channel,
            "external_party_ref": i.external_party_ref,
            "direction": i.direction.value if hasattr(i.direction, "value") else str(i.direction),
            "actor": i.actor.value if hasattr(i.actor, "value") else str(i.actor),
            "content_summary": i.content_summary,
            "outcome_tag": i.outcome_tag,
            "occurred_at": i.occurred_at.isoformat() if i.occurred_at else None,
        }
        for i in interactions
    ]


DOMAIN_TOOLS: List[Callable[..., Any]] = [
    scan_market,
    assess_lead,
    list_leads,
    request_approval,
    generate_content,
    publish_content,
    ingest_interaction,
    list_interactions,
]
