-- 001_initial_schema.sql
-- Marketing OS Initial SQLite Domain Schema
-- Enforces WAL mode, foreign keys, and indexes for performant lookups.

PRAGMA foreign_keys = ON;

-- 1. Schema Migrations Tracking
CREATE TABLE IF NOT EXISTS schema_migrations (
    version INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. Country Profiles
CREATE TABLE IF NOT EXISTS country_profiles (
    country_code TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    languages TEXT NOT NULL, -- JSON array
    enabled INTEGER NOT NULL DEFAULT 1,
    manual_weight REAL,
    query_lexicon_version TEXT NOT NULL DEFAULT '1.0',
    source_policy_version TEXT NOT NULL DEFAULT '1.0',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_by TEXT NOT NULL DEFAULT 'system'
);

-- 3. Service Profiles
CREATE TABLE IF NOT EXISTS service_profiles (
    service_key TEXT PRIMARY KEY,
    priority_class TEXT NOT NULL CHECK(priority_class IN ('primary', 'secondary', 'tertiary')),
    enabled INTEGER NOT NULL DEFAULT 1,
    allowed_funnels TEXT NOT NULL, -- JSON array
    offer_summary TEXT NOT NULL,
    qualification_policy_version TEXT NOT NULL DEFAULT '1.0'
);

-- 4. Sources Registry
CREATE TABLE IF NOT EXISTS sources (
    source_id TEXT PRIMARY KEY,
    domain_or_platform_key TEXT NOT NULL,
    country_scope TEXT NOT NULL, -- JSON array
    source_family TEXT NOT NULL,
    languages TEXT NOT NULL, -- JSON array
    status TEXT NOT NULL CHECK(status IN ('candidate', 'trusted', 'degraded', 'blocked', 'dead')),
    first_seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_success_at TIMESTAMP,
    access_mode TEXT NOT NULL CHECK(access_mode IN ('public', 'authorized_connector', 'manual')),
    metadata_json TEXT NOT NULL DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS idx_sources_domain ON sources(domain_or_platform_key);
CREATE INDEX IF NOT EXISTS idx_sources_status ON sources(status);

-- 5. Source Capability Scores
CREATE TABLE IF NOT EXISTS source_capability_scores (
    source_id TEXT NOT NULL REFERENCES sources(source_id) ON DELETE CASCADE,
    capability TEXT NOT NULL,
    score REAL NOT NULL DEFAULT 0.0,
    sample_count INTEGER NOT NULL DEFAULT 0,
    last_updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    score_version TEXT NOT NULL DEFAULT '1.0',
    PRIMARY KEY (source_id, capability)
);

-- 6. Search Runs
CREATE TABLE IF NOT EXISTS search_runs (
    search_run_id TEXT PRIMARY KEY,
    intent TEXT NOT NULL,
    country_code TEXT NOT NULL REFERENCES country_profiles(country_code),
    service_key TEXT REFERENCES service_profiles(service_key),
    query_plan_json TEXT NOT NULL DEFAULT '{}',
    engine_profile TEXT NOT NULL DEFAULT 'default',
    config_snapshot_hash TEXT NOT NULL DEFAULT '',
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    finished_at TIMESTAMP,
    status TEXT NOT NULL DEFAULT 'pending',
    result_count INTEGER NOT NULL DEFAULT 0,
    error_summary TEXT
);
CREATE INDEX IF NOT EXISTS idx_search_runs_country ON search_runs(country_code);

-- 7. Search Results
CREATE TABLE IF NOT EXISTS search_results (
    search_result_id TEXT PRIMARY KEY,
    search_run_id TEXT NOT NULL REFERENCES search_runs(search_run_id) ON DELETE CASCADE,
    url TEXT NOT NULL,
    normalized_url TEXT NOT NULL,
    title TEXT NOT NULL,
    snippet TEXT NOT NULL,
    rank INTEGER NOT NULL,
    engine_sources TEXT NOT NULL, -- JSON array
    discovered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_search_results_run ON search_results(search_run_id);
CREATE INDEX IF NOT EXISTS idx_search_results_norm_url ON search_results(normalized_url);

-- 8. Companies
CREATE TABLE IF NOT EXISTS companies (
    company_id TEXT PRIMARY KEY,
    canonical_name TEXT NOT NULL,
    primary_domain TEXT,
    country_code TEXT NOT NULL REFERENCES country_profiles(country_code),
    city TEXT,
    sector TEXT,
    public_contacts_json TEXT NOT NULL DEFAULT '{}',
    funnel TEXT NOT NULL CHECK(funnel IN ('b2b', 'academic')),
    entity_confidence REAL NOT NULL DEFAULT 1.0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_companies_domain ON companies(primary_domain);
CREATE INDEX IF NOT EXISTS idx_companies_country ON companies(country_code);

-- 9. Evidence Store
CREATE TABLE IF NOT EXISTS evidence (
    evidence_id TEXT PRIMARY KEY,
    company_id TEXT REFERENCES companies(company_id) ON DELETE SET NULL,
    source_id TEXT NOT NULL REFERENCES sources(source_id),
    url TEXT NOT NULL,
    artifact_path TEXT,
    observed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    published_at TIMESTAMP,
    fact_type TEXT NOT NULL,
    fact_text TEXT NOT NULL,
    extractor TEXT NOT NULL CHECK(extractor IN ('deterministic', 'model_assisted', 'manual')),
    content_hash TEXT NOT NULL,
    confidence REAL NOT NULL DEFAULT 1.0
);
CREATE INDEX IF NOT EXISTS idx_evidence_company ON evidence(company_id);
CREATE INDEX IF NOT EXISTS idx_evidence_hash ON evidence(content_hash);

-- 10. Signals
CREATE TABLE IF NOT EXISTS signals (
    signal_id TEXT PRIMARY KEY,
    company_id TEXT NOT NULL REFERENCES companies(company_id) ON DELETE CASCADE,
    type TEXT NOT NULL,
    summary TEXT NOT NULL,
    evidence_ids TEXT NOT NULL, -- JSON array
    confidence REAL NOT NULL DEFAULT 1.0,
    model_or_rule_identity TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    valid_until TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_signals_company ON signals(company_id);

-- 11. Leads
CREATE TABLE IF NOT EXISTS leads (
    lead_id TEXT PRIMARY KEY,
    company_id TEXT NOT NULL REFERENCES companies(company_id) ON DELETE CASCADE,
    funnel TEXT NOT NULL CHECK(funnel IN ('b2b', 'academic')),
    status TEXT NOT NULL CHECK(status IN (
        'discovered', 'qualified', 'rejected', 'outreach_ready', 'contacted',
        'replied', 'meeting', 'proposal', 'won', 'lost', 'dormant'
    )),
    priority_bucket INTEGER NOT NULL DEFAULT 3,
    recommended_service_key TEXT REFERENCES service_profiles(service_key),
    owner TEXT,
    next_action TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_leads_company ON leads(company_id);
CREATE INDEX IF NOT EXISTS idx_leads_status ON leads(status);
CREATE INDEX IF NOT EXISTS idx_leads_priority ON leads(priority_bucket);

-- 12. Lead Assessments (Append-Only)
CREATE TABLE IF NOT EXISTS lead_assessments (
    assessment_id TEXT PRIMARY KEY,
    lead_id TEXT NOT NULL REFERENCES leads(lead_id) ON DELETE CASCADE,
    assessment_version TEXT NOT NULL DEFAULT '1.0',
    fit_score REAL NOT NULL DEFAULT 0.0,
    pain_score REAL NOT NULL DEFAULT 0.0,
    urgency_score REAL NOT NULL DEFAULT 0.0,
    reachability_score REAL NOT NULL DEFAULT 0.0,
    final_score REAL NOT NULL DEFAULT 0.0,
    confidence REAL NOT NULL DEFAULT 1.0,
    recommended_service_key TEXT REFERENCES service_profiles(service_key),
    evidence_ids TEXT NOT NULL, -- JSON array
    reasoning_summary TEXT NOT NULL,
    provider_identity TEXT NOT NULL DEFAULT 'antigravity',
    prompt_contract_version TEXT NOT NULL DEFAULT '1.0',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_assessments_lead ON lead_assessments(lead_id);

-- 13. Content Ideas
CREATE TABLE IF NOT EXISTS content_ideas (
    content_idea_id TEXT PRIMARY KEY,
    funnel TEXT NOT NULL CHECK(funnel IN ('b2b', 'academic')),
    market_scope TEXT NOT NULL, -- JSON array
    service_key TEXT NOT NULL REFERENCES service_profiles(service_key),
    source_signal_ids TEXT NOT NULL, -- JSON array
    topic TEXT NOT NULL,
    objective TEXT NOT NULL CHECK(objective IN ('trust', 'education', 'demand_capture', 'direct_offer', 'case_style')),
    score REAL NOT NULL DEFAULT 0.0,
    status TEXT NOT NULL DEFAULT 'proposed'
);

-- 14. Content Assets
CREATE TABLE IF NOT EXISTS content_assets (
    content_asset_id TEXT PRIMARY KEY,
    idea_id TEXT NOT NULL REFERENCES content_ideas(content_idea_id) ON DELETE CASCADE,
    master_content TEXT NOT NULL,
    platform TEXT NOT NULL,
    format TEXT NOT NULL,
    body TEXT NOT NULL,
    media_brief TEXT,
    cta TEXT NOT NULL,
    status TEXT NOT NULL CHECK(status IN ('draft', 'awaiting_approval', 'approved', 'rejected', 'scheduled', 'published', 'failed')),
    version INTEGER NOT NULL DEFAULT 1
);
CREATE INDEX IF NOT EXISTS idx_content_assets_idea ON content_assets(idea_id);
CREATE INDEX IF NOT EXISTS idx_content_assets_status ON content_assets(status);

-- 15. Approvals
CREATE TABLE IF NOT EXISTS approvals (
    approval_id TEXT PRIMARY KEY,
    action_type TEXT NOT NULL,
    target_type TEXT NOT NULL,
    target_id TEXT NOT NULL,
    requested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    resolved_at TIMESTAMP,
    actor_id TEXT,
    decision TEXT NOT NULL CHECK(decision IN ('pending', 'approved', 'rejected', 'rewrite_requested')),
    notes TEXT
);
CREATE INDEX IF NOT EXISTS idx_approvals_decision ON approvals(decision);

-- 16. Interactions
CREATE TABLE IF NOT EXISTS interactions (
    interaction_id TEXT PRIMARY KEY,
    lead_id TEXT REFERENCES leads(lead_id) ON DELETE SET NULL,
    channel TEXT NOT NULL,
    external_party_ref TEXT,
    direction TEXT NOT NULL CHECK(direction IN ('inbound', 'outbound')),
    actor TEXT NOT NULL DEFAULT 'human' CHECK(actor IN ('human', 'agent_draft', 'external')),
    content_summary TEXT NOT NULL,
    outcome_tag TEXT,
    raw_content_path TEXT,
    occurred_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_interactions_lead ON interactions(lead_id);
CREATE INDEX IF NOT EXISTS idx_interactions_actor ON interactions(actor);

-- 17. Agent Runs
CREATE TABLE IF NOT EXISTS agent_runs (
    agent_run_id TEXT PRIMARY KEY,
    task_type TEXT NOT NULL,
    provider_path TEXT NOT NULL,
    model_identity TEXT,
    input_refs TEXT NOT NULL, -- JSON array
    input_size_estimate INTEGER NOT NULL DEFAULT 0,
    output_contract_version TEXT NOT NULL DEFAULT '1.0',
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    finished_at TIMESTAMP,
    status TEXT NOT NULL DEFAULT 'started',
    error_class TEXT,
    approval_required INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_agent_runs_task ON agent_runs(task_type);
CREATE INDEX IF NOT EXISTS idx_agent_runs_status ON agent_runs(status);


