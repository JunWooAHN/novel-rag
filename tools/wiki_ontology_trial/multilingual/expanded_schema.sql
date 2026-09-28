-- Extra inventory for the five-target full-body trial. Base reality tables
-- remain the source/candidate/vector store in this separate trial database.
CREATE TABLE IF NOT EXISTS reality_target_links (
    target text NOT NULL,
    qid text,
    wiki_id text NOT NULL,
    requested_title text NOT NULL,
    fetch_status text NOT NULL,
    fetch_reason text,
    ingest_status text NOT NULL CHECK (ingest_status IN ('not_applicable','ingested','failed')),
    ingest_error_type text,
    source_file_sha256 char(64),
    page_key text REFERENCES reality_source_pages(page_key),
    PRIMARY KEY (target, wiki_id, requested_title)
);

CREATE TABLE IF NOT EXISTS reality_full_pages (
    page_key text PRIMARY KEY REFERENCES reality_source_pages(page_key),
    segmentation_version text NOT NULL,
    body_sha256 char(64) NOT NULL,
    unit_count integer NOT NULL CHECK (unit_count >= 0)
);

CREATE TABLE IF NOT EXISTS reality_span_embeddings (
    unit_id text NOT NULL REFERENCES reality_source_units(unit_id),
    start_byte integer NOT NULL,
    end_byte integer NOT NULL,
    model text NOT NULL,
    model_revision text NOT NULL,
    dimension integer NOT NULL CHECK (dimension=384),
    input_sha256 char(64) NOT NULL,
    vector vector(384) NOT NULL,
    PRIMARY KEY (unit_id,start_byte,end_byte,model,model_revision,input_sha256),
    CHECK (start_byte >= 0 AND end_byte > start_byte)
);

CREATE TABLE IF NOT EXISTS reality_embed_failures (
    unit_id text NOT NULL REFERENCES reality_source_units(unit_id),
    model text NOT NULL,
    model_revision text NOT NULL,
    error_type text NOT NULL,
    PRIMARY KEY (unit_id,model,model_revision)
);
