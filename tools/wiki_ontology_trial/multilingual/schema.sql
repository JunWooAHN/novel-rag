CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS reality_source_pages (
    page_key text PRIMARY KEY,
    wiki_id text NOT NULL,
    page_id bigint NOT NULL,
    revision_id bigint NOT NULL,
    slot text NOT NULL,
    language text NOT NULL,
    title text NOT NULL,
    source_kind text NOT NULL,
    snapshot_id text,
    revision_timestamp text,
    source_url text,
    retrieved_at text,
    body text NOT NULL,
    body_sha256 char(64) NOT NULL,
    UNIQUE (wiki_id, page_id, revision_id, slot)
);

CREATE TABLE IF NOT EXISTS reality_source_units (
    unit_id text PRIMARY KEY,
    page_key text NOT NULL REFERENCES reality_source_pages(page_key),
    start_byte integer NOT NULL,
    end_byte integer NOT NULL,
    text text NOT NULL,
    text_sha256 char(64) NOT NULL,
    CHECK (start_byte >= 0 AND end_byte > start_byte),
    UNIQUE (page_key, start_byte, end_byte)
);

CREATE TABLE IF NOT EXISTS reality_extract_attempts (
    attempt_id char(64) PRIMARY KEY,
    unit_id text NOT NULL REFERENCES reality_source_units(unit_id),
    model text NOT NULL,
    model_revision text NOT NULL,
    prompt_sha256 char(64) NOT NULL,
    status text NOT NULL CHECK (status IN ('running', 'completed', 'failed')),
    raw_response text,
    raw_sha256 char(64),
    error text,
    unmapped_notes jsonb NOT NULL DEFAULT '[]'::jsonb,
    started_at timestamptz NOT NULL DEFAULT now(),
    finished_at timestamptz
);

CREATE TABLE IF NOT EXISTS reality_candidates (
    candidate_id char(64) PRIMARY KEY,
    attempt_id char(64) NOT NULL REFERENCES reality_extract_attempts(attempt_id),
    unit_id text NOT NULL REFERENCES reality_source_units(unit_id),
    ordinal integer NOT NULL,
    layer text NOT NULL,
    mapping_refs jsonb NOT NULL,
    subject_text text,
    predicate_text text,
    object_text text,
    time_text text,
    uncertainty text,
    related_candidate_id char(64),
    evidence_quote text,
    evidence_start_byte integer,
    evidence_end_byte integer,
    status text NOT NULL CHECK (status IN ('candidate_unreviewed', 'held')),
    problems jsonb NOT NULL,
    payload jsonb NOT NULL,
    UNIQUE (attempt_id, ordinal)
);

CREATE TABLE IF NOT EXISTS reality_embeddings (
    target_kind text NOT NULL CHECK (target_kind = 'source_unit'),
    target_id text NOT NULL REFERENCES reality_source_units(unit_id),
    model text NOT NULL,
    model_revision text NOT NULL,
    dimension integer NOT NULL CHECK (dimension = 384),
    input_sha256 char(64) NOT NULL,
    vector vector(384) NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (target_kind, target_id, model, model_revision, input_sha256)
);
