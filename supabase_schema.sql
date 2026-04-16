-- Solar System Facility -- Supabase Schema
-- Run this in Supabase SQL Editor (Dashboard > SQL Editor > New Query)

-- Entity profiles (linked to Supabase auth.users)
CREATE TABLE entity_profiles (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    display_name TEXT NOT NULL,
    bio TEXT,
    affiliation TEXT,
    capabilities TEXT[],
    contribution_count INT DEFAULT 0,
    missions_completed INT DEFAULT 0,
    joined_at TIMESTAMPTZ DEFAULT now()
);

-- Unified contributions table
CREATE TABLE contributions (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    object_designation TEXT NOT NULL,
    entity_id UUID REFERENCES auth.users(id),
    entity_name TEXT NOT NULL,
    kind TEXT NOT NULL CHECK (kind IN ('comment', 'observation', 'correction', 'mission_report')),
    parent_id UUID REFERENCES contributions(id),
    body TEXT,
    structured_data JSONB,
    source_references TEXT[],
    status TEXT DEFAULT 'published',
    upvotes INT DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_contributions_object ON contributions(object_designation);
CREATE INDEX idx_contributions_entity ON contributions(entity_id);
CREATE INDEX idx_contributions_kind ON contributions(kind);

-- Exploration missions
CREATE TABLE exploration_missions (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    object_designation TEXT NOT NULL,
    requested_by UUID REFERENCES auth.users(id),
    requested_by_name TEXT NOT NULL,
    status TEXT DEFAULT 'deploying'
        CHECK (status IN ('deploying', 'in_transit', 'investigating', 'returning_data', 'mission_complete', 'mission_failed')),
    sources_queried TEXT[],
    findings_summary TEXT,
    data_gaps TEXT[],
    completeness_score FLOAT,
    contribution_id UUID REFERENCES contributions(id),
    duration_seconds FLOAT,
    started_at TIMESTAMPTZ DEFAULT now(),
    completed_at TIMESTAMPTZ
);

CREATE INDEX idx_missions_object ON exploration_missions(object_designation);
CREATE INDEX idx_missions_status ON exploration_missions(status);

-- Row Level Security
ALTER TABLE entity_profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE contributions ENABLE ROW LEVEL SECURITY;
ALTER TABLE exploration_missions ENABLE ROW LEVEL SECURITY;

-- Everyone can read all data
CREATE POLICY "Public read entity_profiles" ON entity_profiles FOR SELECT USING (true);
CREATE POLICY "Public read contributions" ON contributions FOR SELECT USING (true);
CREATE POLICY "Public read exploration_missions" ON exploration_missions FOR SELECT USING (true);

-- Authenticated users can insert their own data
CREATE POLICY "Users insert own profile" ON entity_profiles FOR INSERT WITH CHECK (auth.uid() = id);
CREATE POLICY "Users update own profile" ON entity_profiles FOR UPDATE USING (auth.uid() = id);

CREATE POLICY "Auth users insert contributions" ON contributions FOR INSERT WITH CHECK (auth.uid() = entity_id);
CREATE POLICY "Users update own contributions" ON contributions FOR UPDATE USING (auth.uid() = entity_id);
CREATE POLICY "Users delete own contributions" ON contributions FOR DELETE USING (auth.uid() = entity_id);

CREATE POLICY "Auth users insert missions" ON exploration_missions FOR INSERT WITH CHECK (auth.uid() = requested_by);
CREATE POLICY "Auth users update own missions" ON exploration_missions FOR UPDATE USING (auth.uid() = requested_by);
