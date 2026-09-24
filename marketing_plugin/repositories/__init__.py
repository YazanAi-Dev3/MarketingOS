"""Marketing OS Repositories.

Database repositories owning marketing domain state in SQLite:
sources, companies, evidence, signals, leads, assessments, content, approvals, interactions, agent_runs.
"""
from marketing_plugin.repositories.agent_run_repo import AgentRunRepository
from marketing_plugin.repositories.approval_repo import ApprovalRepository
from marketing_plugin.repositories.company_repo import CompanyRepository
from marketing_plugin.repositories.content_repo import ContentRepository
from marketing_plugin.repositories.database import Database
from marketing_plugin.repositories.evidence_repo import EvidenceRepository
from marketing_plugin.repositories.lead_repo import LeadRepository
from marketing_plugin.repositories.source_repo import SourceRepository

__all__ = [
    "Database",
    "AgentRunRepository",
    "ApprovalRepository",
    "CompanyRepository",
    "ContentRepository",
    "EvidenceRepository",
    "LeadRepository",
    "SourceRepository",
]


