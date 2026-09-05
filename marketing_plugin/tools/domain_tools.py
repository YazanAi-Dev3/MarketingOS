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
from marketing_plugin.policies.query_planner import RegionalQueryPlanner
from marketing_plugin.repositories.approval_repo import ApprovalRepository
from marketing_plugin.repositories.company_repo import CompanyRepository
from marketing_plugin.repositories.database import Database
from marketing_plugin.repositories.evidence_repo import EvidenceRepository
from marketing_plugin.repositories.lead_repo import LeadRepository
from marketing_plugin.repositories.source_repo import SourceRepository
from schemas.models import (
    Approval,
    ApprovalDecision,
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
    query: str,
    service_key: Optional[str] = None,
    db: Optional[Database] = None,
    planner: Optional[RegionalQueryPlanner] = None,
    searxng_adapter: Optional[Any] = None,
) -> Dict[str, Any]:
    """Scans regional market for lead/service discovery using search and freelance sources.

    Args:
        country_code: Two-letter ISO country code (e.g. 'SA', 'AE').
        query: Market scan intent or search topic.
        service_key: Optional service key (e.g. 'ai_automation', 'software_dev').
        db: Optional Database manager for recording the run.
        planner: Optional query planner override.
        searxng_adapter: Optional SearXNG adapter instance.
    """
    country_code = country_code.strip().upper()
    active_service = service_key or "ai_automation"
    query_planner = planner or RegionalQueryPlanner()

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
) -> Dict[str, Any]:
    """Assesses a company entity and produces an append-only LeadAssessment snapshot.

    Args:
        company_id: The ID of the company to evaluate.
        context: Optional evaluation context or override weights.
        db: Optional Database instance.
    """
    database = _get_db(db)
    conn = database.connect()
    company_repo = CompanyRepository(conn)
    evidence_repo = EvidenceRepository(conn)
    lead_repo = LeadRepository(conn)

    company = company_repo.get_company(company_id)
    if not company:
        return {
            "status": "error",
            "error": f"Company '{company_id}' not found in registry",
        }

    evidence_list = evidence_repo.list_for_company(company_id)
    evidence_ids = [e.evidence_id for e in evidence_list]

    ctx = context or {}
    model_eval = ctx.get("model_evaluation") or ctx.get("reasoning_result")

    # 1. Fit score: domain validity, industry presence, and evidence presence
    if "fit_score" in ctx:
        fit_score = float(ctx["fit_score"])
    elif isinstance(model_eval, dict) and "fit_score" in model_eval:
        fit_score = float(model_eval["fit_score"])
    else:
        score = 0.3
        if company.primary_domain:
            score += 0.3
        if company.public_contacts_json:
            score += 0.2
        if evidence_list:
            score += 0.2
        fit_score = min(1.0, score)

    # 2. Pain score: baseline reflects unverified raw signals; explicit model assessment sets qualification truth
    # Invariant docs/09-final-design-review.md:108: keyword lists aid query planning but never constitute lead qualification truth.
    if "pain_score" in ctx:
        pain_score = float(ctx["pain_score"])
    elif isinstance(model_eval, dict) and "pain_score" in model_eval:
        pain_score = float(model_eval["pain_score"])
    else:
        pain_score = 0.50

    # 3. Urgency score
    if "urgency_score" in ctx:
        urgency_score = float(ctx["urgency_score"])
    elif isinstance(model_eval, dict) and "urgency_score" in model_eval:
        urgency_score = float(model_eval["urgency_score"])
    else:
        urgency_score = 0.75 if evidence_list else 0.50

    # 4. Reachability score: public contacts availability
    if "reachability_score" in ctx:
        reachability_score = float(ctx["reachability_score"])
    elif isinstance(model_eval, dict) and "reachability_score" in model_eval:
        reachability_score = float(model_eval["reachability_score"])
    else:
        reachability_score = 0.90 if company.public_contacts_json else 0.35

    # 5. Composite Final Score
    final_score = round(
        0.30 * fit_score + 0.30 * pain_score + 0.20 * urgency_score + 0.20 * reachability_score,
        2,
    )

    # 6. Determine Lead Status and Priority Bucket
    # Invariant docs/09-final-design-review.md:108: keyword lists aid query planning but never constitute lead qualification truth.
    # Unassisted baseline keeps lead in DISCOVERED pending model-assisted qualification or operator confirmation.
    has_model_eval = model_eval is not None or "qualified" in ctx
    is_qualified_eval = False
    is_rejected_eval = False

    if has_model_eval:
        if isinstance(model_eval, dict):
            if (
                model_eval.get("qualified") is True
                or model_eval.get("decision") in ("qualified", "qualify")
                or model_eval.get("status") == "qualified"
            ):
                is_qualified_eval = True
            elif (
                model_eval.get("qualified") is False
                or model_eval.get("decision") in ("rejected", "disqualified")
                or model_eval.get("status") == "rejected"
            ):
                is_rejected_eval = True
            else:
                is_qualified_eval = final_score >= 0.70
        elif isinstance(model_eval, bool):
            if model_eval:
                is_qualified_eval = True
            else:
                is_rejected_eval = True
        elif isinstance(model_eval, str):
            if model_eval.lower() in ("qualified", "qualify", "true"):
                is_qualified_eval = True
            elif model_eval.lower() in ("rejected", "disqualified", "false"):
                is_rejected_eval = True
        elif "qualified" in ctx:
            if ctx["qualified"]:
                is_qualified_eval = True
            else:
                is_rejected_eval = True

    lead_id = f"lead_{company_id}"
    existing_lead = lead_repo.get_lead(lead_id)

    if has_model_eval:
        if is_qualified_eval:
            lead_status = LeadStatus.QUALIFIED
            priority_bucket = 1 if final_score >= 0.85 else 2
        elif is_rejected_eval or final_score < 0.40:
            lead_status = LeadStatus.REJECTED
            priority_bucket = 3
        else:
            lead_status = LeadStatus.DISCOVERED
            priority_bucket = 2
    else:
        # Unassisted baseline: never qualifies automatically via keywords or baseline score alone.
        # Preserve existing progression if already qualified/advanced by operator or model,
        # otherwise retain DISCOVERED.
        if existing_lead and existing_lead.status not in (LeadStatus.DISCOVERED, LeadStatus.REJECTED):
            lead_status = existing_lead.status
        else:
            lead_status = LeadStatus.DISCOVERED
        priority_bucket = 1 if final_score >= 0.85 else (2 if final_score >= 0.50 else 3)

    # Save or update lead
    if existing_lead:
        existing_lead.status = lead_status
        existing_lead.priority_bucket = priority_bucket
        existing_lead.updated_at = utc_now()
        lead_repo.save_lead(existing_lead)
    else:
        new_lead = Lead(
            lead_id=lead_id,
            company_id=company_id,
            funnel=company.funnel,
            status=lead_status,
            priority_bucket=priority_bucket,
            recommended_service_key=ctx.get("service_key"),
            created_at=utc_now(),
            updated_at=utc_now(),
        )
        lead_repo.save_lead(new_lead)

    # Append Assessment Snapshot
    assessment_id = f"asm_{company_id}_{uuid.uuid4().hex[:8]}"
    provider_identity = (
        ctx.get("provider_identity")
        or (model_eval.get("provider_identity") if isinstance(model_eval, dict) else None)
        or ("model_assisted" if has_model_eval else "deterministic_rules")
    )
    confidence = float(
        ctx.get("confidence")
        or (model_eval.get("confidence") if isinstance(model_eval, dict) else None)
        or (1.0 if has_model_eval else 0.60)
    )

    reasoning_summary = (
        f"{'Model-assisted qualification' if has_model_eval else 'Unassisted baseline'}: "
        f"fit={fit_score:.2f}, pain={pain_score:.2f}, "
        f"urgency={urgency_score:.2f}, reachability={reachability_score:.2f}. Status: {lead_status.value}"
    )

    assessment = LeadAssessment(
        assessment_id=assessment_id,
        lead_id=lead_id,
        fit_score=fit_score,
        pain_score=pain_score,
        urgency_score=urgency_score,
        reachability_score=reachability_score,
        final_score=final_score,
        confidence=confidence,
        recommended_service_key=ctx.get("service_key"),
        evidence_ids=evidence_ids,
        reasoning_summary=reasoning_summary,
        provider_identity=provider_identity,
        created_at=utc_now(),
    )
    lead_repo.save_assessment(assessment)

    return {
        "status": "success",
        "assessment_id": assessment_id,
        "company_id": company_id,
        "lead_id": lead_id,
        "fit_score": fit_score,
        "pain_score": pain_score,
        "urgency_score": urgency_score,
        "reachability_score": reachability_score,
        "final_score": final_score,
        "lead_status": lead_status.value,
        "priority_bucket": priority_bucket,
        "reasoning_summary": assessment.reasoning_summary,
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


DOMAIN_TOOLS: List[Callable[..., Any]] = [
    scan_market,
    assess_lead,
    list_leads,
    request_approval,
]
