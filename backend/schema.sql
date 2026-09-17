-- ============================================================================
-- Novu Opportunity Radar — Production PostgreSQL Schema
-- Version: 1.0 (17 September 2026)
-- Target: PostgreSQL 15 / 16
-- 
-- Compliant with:
--   • Novu Opportunity Radar BRD & Developer Handover v1.0
--   • Software Requirements Specification (SRS) v1.0 (§5 Data Requirements)
-- ============================================================================

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ----------------------------------------------------------------------------
-- ENUM TYPES & DOMAINS
-- ----------------------------------------------------------------------------

DO $$ BEGIN
    CREATE TYPE connector_type_enum AS ENUM (
        'web_search', 'rss_feed', 'rfp_portal', 'x_twitter', 'reddit', 'manual_capture'
    );
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE TYPE access_state_enum AS ENUM (
        'ready', 'credential_required', 'needs_repair', 'disabled', 'rate_limited'
    );
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE TYPE run_state_enum AS ENUM (
        'queued', 'running', 'completed', 'partial', 'failed'
    );
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE TYPE buyer_intent_enum AS ENUM (
        'buyer', 'nonbuyer', 'uncertain'
    );
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE TYPE opportunity_kind_enum AS ENUM (
        'direct_purchase', 'rfp', 'agency_staffing', 'hiring_signal', 'indirect_pain', 'seller_promotion', 'other'
    );
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE TYPE service_category_enum AS ENUM (
        'CUSTOM_DEV', 'MOBILE_APP', 'WEBSITE', 'ERP', 'CRM', 'LMS',
        'AI_AUTOMATION', 'STAFF_AUGMENTATION', 'MANAGED_IT', 'CLOUD_DEVOPS', 'CYBERSECURITY'
    );
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE TYPE score_band_enum AS ENUM (
        'Hot', 'High potential', 'Review', 'Archive'
    );
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE TYPE opportunity_status_enum AS ENUM (
        'new', 'review', 'reviewed', 'contacted', 'meeting', 'proposal', 'won', 'rejected', 'closed'
    );
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE TYPE duplicate_decision_enum AS ENUM (
        'pending', 'accepted', 'rejected'
    );
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE TYPE contact_verification_enum AS ENUM (
        'published', 'verified', 'invalid', 'catch_all', 'unknown'
    );
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE TYPE outbox_state_enum AS ENUM (
        'pending', 'processing', 'completed', 'failed'
    );
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

-- ----------------------------------------------------------------------------
-- 1. SOURCES (Connectors & Access Configurations)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS sources (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    connector_type connector_type_enum NOT NULL,
    name VARCHAR(128) NOT NULL,
    enabled BOOLEAN NOT NULL DEFAULT FALSE,
    access_state access_state_enum NOT NULL DEFAULT 'credential_required',
    settings JSONB NOT NULL DEFAULT '{}'::jsonb,
    rate_limit_per_minute INT NOT NULL DEFAULT 60,
    daily_spend_cap NUMERIC(10, 2) NOT NULL DEFAULT 50.00,
    current_day_spend NUMERIC(10, 2) NOT NULL DEFAULT 0.00,
    last_success_at TIMESTAMPTZ,
    last_failure_at TIMESTAMPTZ,
    last_error_class VARCHAR(128),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ----------------------------------------------------------------------------
-- 2. SEARCH TERMS (Source queries, markets & schedules)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS search_terms (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_id UUID NOT NULL REFERENCES sources(id) ON DELETE CASCADE,
    query TEXT NOT NULL,
    market VARCHAR(64) NOT NULL DEFAULT 'Pakistan',
    language VARCHAR(16) NOT NULL DEFAULT 'en',
    schedule_cron VARCHAR(64) NOT NULL DEFAULT '*/15 * * * *',
    enabled BOOLEAN NOT NULL DEFAULT TRUE,
    last_cursor TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ----------------------------------------------------------------------------
-- 3. RUNS (Connector execution instances & audit metrics)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_id UUID NOT NULL REFERENCES sources(id) ON DELETE CASCADE,
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    finished_at TIMESTAMPTZ,
    state run_state_enum NOT NULL DEFAULT 'queued',
    trigger VARCHAR(32) NOT NULL DEFAULT 'scheduled',
    fetched_count INT NOT NULL DEFAULT 0,
    new_count INT NOT NULL DEFAULT 0,
    duplicate_count INT NOT NULL DEFAULT 0,
    error_count INT NOT NULL DEFAULT 0,
    qualified_count INT NOT NULL DEFAULT 0,
    error_detail TEXT,
    spend_amount NUMERIC(8, 4) NOT NULL DEFAULT 0.0000,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ----------------------------------------------------------------------------
-- 4. OBSERVATIONS (Raw collected items with provenance & hash)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS observations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_id UUID NOT NULL REFERENCES sources(id) ON DELETE RESTRICT,
    run_id UUID REFERENCES runs(id) ON DELETE SET NULL,
    external_id VARCHAR(256),
    original_url TEXT NOT NULL,
    canonical_url TEXT NOT NULL,
    author VARCHAR(256),
    source_text TEXT NOT NULL,
    source_published_at TIMESTAMPTZ,
    fetched_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    content_hash CHAR(64) NOT NULL, -- SHA-256
    is_manual BOOLEAN NOT NULL DEFAULT FALSE,
    raw_payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ----------------------------------------------------------------------------
-- 5. COMPANIES (Verified or evidence-supported business entities)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS companies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    official_domain VARCHAR(255) UNIQUE,
    name VARCHAR(255) NOT NULL,
    country VARCHAR(128),
    industry VARCHAR(128),
    evidence_quote TEXT,
    evidence_url TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ----------------------------------------------------------------------------
-- 6. OPPORTUNITIES (Qualified buyer requirements & sales records)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS opportunities (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID REFERENCES companies(id) ON DELETE SET NULL,
    company_name VARCHAR(255),
    company_website TEXT,
    country VARCHAR(128),
    industry VARCHAR(128),
    requirement TEXT NOT NULL,
    text TEXT NOT NULL,
    primary_category service_category_enum NOT NULL,
    secondary_categories TEXT[] NOT NULL DEFAULT '{}',
    technologies TEXT[] NOT NULL DEFAULT '{}',
    intent buyer_intent_enum NOT NULL DEFAULT 'uncertain',
    kind opportunity_kind_enum NOT NULL DEFAULT 'other',
    confidence NUMERIC(4, 3) NOT NULL DEFAULT 0.000,
    score INT NOT NULL DEFAULT 0 CHECK (score >= 0 AND score <= 100),
    score_version VARCHAR(32) NOT NULL DEFAULT '1.0',
    band score_band_enum NOT NULL DEFAULT 'Review',
    status opportunity_status_enum NOT NULL DEFAULT 'new',
    owner_id INT, -- Maps to application auth user
    owner_name VARCHAR(128),
    detected_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    source_published_at TIMESTAMPTZ,
    deadline DATE,
    budget_text TEXT,
    budget_normalized NUMERIC(12, 2),
    budget_currency VARCHAR(8),
    revision INT NOT NULL DEFAULT 1,
    review_reasons TEXT[] NOT NULL DEFAULT '{}',
    intent_evidence TEXT,
    field_evidence JSONB NOT NULL DEFAULT '{}'::jsonb,
    notes TEXT NOT NULL DEFAULT '',
    last_follow_up TIMESTAMPTZ,
    next_follow_up TIMESTAMPTZ,
    extraction_version VARCHAR(32) NOT NULL DEFAULT '1.0',
    merged_into_id UUID REFERENCES opportunities(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ----------------------------------------------------------------------------
-- 7. OPPORTUNITY_OBSERVATIONS (M:N link with canonical pointer)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS opportunity_observations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    opportunity_id UUID NOT NULL REFERENCES opportunities(id) ON DELETE CASCADE,
    observation_id UUID NOT NULL REFERENCES observations(id) ON DELETE CASCADE,
    is_canonical BOOLEAN NOT NULL DEFAULT TRUE,
    linked_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_opportunity_observation UNIQUE (opportunity_id, observation_id)
);

-- ----------------------------------------------------------------------------
-- 8. CONTACTS (Published & verified business contacts with provenance)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS contacts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    opportunity_id UUID NOT NULL REFERENCES opportunities(id) ON DELETE CASCADE,
    company_id UUID REFERENCES companies(id) ON DELETE SET NULL,
    name VARCHAR(255),
    designation VARCHAR(128),
    email VARCHAR(255),
    phone VARCHAR(64),
    evidence_url TEXT,
    evidence_quote TEXT,
    provenance VARCHAR(64) NOT NULL DEFAULT 'source_evidence',
    verification_state contact_verification_enum NOT NULL DEFAULT 'published',
    is_suppressed BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ----------------------------------------------------------------------------
-- 9. DUPLICATE CANDIDATES (Cross-source reviewable pairs)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS duplicate_candidates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_opportunity_id UUID NOT NULL REFERENCES opportunities(id) ON DELETE CASCADE,
    target_opportunity_id UUID NOT NULL REFERENCES opportunities(id) ON DELETE CASCADE,
    similarity_score NUMERIC(4, 3) NOT NULL,
    decision duplicate_decision_enum NOT NULL DEFAULT 'pending',
    reviewer_id INT,
    reason TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    resolved_at TIMESTAMPTZ,
    CONSTRAINT uq_candidate_pair UNIQUE (source_opportunity_id, target_opportunity_id)
);

-- ----------------------------------------------------------------------------
-- 10. ACTIVITIES (Audit history, notes & pipeline transitions)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS activities (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    opportunity_id UUID NOT NULL REFERENCES opportunities(id) ON DELETE CASCADE,
    actor_id INT,
    actor_name VARCHAR(128) NOT NULL,
    kind VARCHAR(64) NOT NULL,
    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ----------------------------------------------------------------------------
-- 11. DRAFTS (Prepared human-reviewed sales outreach messages)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS drafts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    opportunity_id UUID NOT NULL REFERENCES opportunities(id) ON DELETE CASCADE,
    author_id INT,
    content TEXT NOT NULL,
    model_version VARCHAR(64) NOT NULL DEFAULT 'gemini-1.5-pro',
    approved_by_id INT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ----------------------------------------------------------------------------
-- 12. OUTBOX (Idempotent export & notification delivery ledger)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS outbox (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_key VARCHAR(128) NOT NULL UNIQUE,
    destination VARCHAR(64) NOT NULL,
    opportunity_id UUID REFERENCES opportunities(id) ON DELETE CASCADE,
    revision INT NOT NULL DEFAULT 1,
    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    state outbox_state_enum NOT NULL DEFAULT 'pending',
    error TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    processed_at TIMESTAMPTZ
);

-- ----------------------------------------------------------------------------
-- 13. SYNC TARGETS (Cloud Excel & external integration destinations)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS sync_targets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    destination VARCHAR(64) NOT NULL,
    name VARCHAR(128) NOT NULL,
    enabled BOOLEAN NOT NULL DEFAULT TRUE,
    config JSONB NOT NULL DEFAULT '{}'::jsonb,
    credentials_ref VARCHAR(128),
    last_synced_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ----------------------------------------------------------------------------
-- 14. AUDIT EVENTS (System-wide immutable security & administrative log)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS audit_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    actor_id INT,
    actor_name VARCHAR(128) NOT NULL,
    action VARCHAR(64) NOT NULL,
    object_type VARCHAR(64) NOT NULL,
    object_id VARCHAR(64) NOT NULL,
    change_payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ----------------------------------------------------------------------------
-- 15. OPERATING SETTINGS (System-wide runtime configuration parameters)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS operating_settings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    key VARCHAR(64) NOT NULL UNIQUE,
    value JSONB NOT NULL,
    description TEXT,
    updated_by_id INT,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ============================================================================
-- INDEXES & PERFORMANCE OPTIMIZATIONS
-- ============================================================================

CREATE UNIQUE INDEX IF NOT EXISTS uq_source_external_id 
    ON observations (source_id, external_id) 
    WHERE external_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_observations_content_hash 
    ON observations (content_hash);

CREATE INDEX IF NOT EXISTS idx_observations_canonical_url 
    ON observations (canonical_url);

CREATE INDEX IF NOT EXISTS idx_observations_fetched_at 
    ON observations (fetched_at DESC);

CREATE INDEX IF NOT EXISTS idx_opportunities_score_detected 
    ON opportunities (score DESC, detected_at DESC);

CREATE INDEX IF NOT EXISTS idx_opportunities_status 
    ON opportunities (status);

CREATE INDEX IF NOT EXISTS idx_opportunities_intent 
    ON opportunities (intent);

CREATE INDEX IF NOT EXISTS idx_opportunities_band 
    ON opportunities (band);

CREATE INDEX IF NOT EXISTS idx_opportunities_primary_cat 
    ON opportunities (primary_category);

CREATE INDEX IF NOT EXISTS idx_opportunities_owner 
    ON opportunities (owner_id);

CREATE INDEX IF NOT EXISTS idx_opportunities_deadline 
    ON opportunities (deadline) 
    WHERE deadline IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_outbox_state_created 
    ON outbox (state, created_at) 
    WHERE state = 'pending';

CREATE INDEX IF NOT EXISTS idx_activities_opp_created 
    ON activities (opportunity_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_contacts_opp 
    ON contacts (opportunity_id);

CREATE INDEX IF NOT EXISTS idx_contacts_email 
    ON contacts (email) 
    WHERE email IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_runs_source_started 
    ON runs (source_id, started_at DESC);
