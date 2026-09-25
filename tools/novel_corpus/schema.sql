PRAGMA foreign_keys = ON;
PRAGMA user_version = 1;

CREATE TABLE IF NOT EXISTS works (
  work_id TEXT PRIMARY KEY,
  author TEXT NOT NULL,
  title TEXT NOT NULL,
  drive_file_id TEXT NOT NULL,
  manifest_relative_path TEXT NOT NULL,
  current_segmentation_id INTEGER,
  FOREIGN KEY (current_segmentation_id) REFERENCES segmentations(id) ON DELETE RESTRICT
);

CREATE TABLE IF NOT EXISTS source_revisions (
  id INTEGER PRIMARY KEY,
  work_id TEXT NOT NULL REFERENCES works(work_id) ON DELETE RESTRICT,
  sha256_raw TEXT NOT NULL,
  byte_size INTEGER NOT NULL CHECK (byte_size >= 0),
  codepoint_length INTEGER NOT NULL CHECK (codepoint_length >= 0),
  relative_path TEXT NOT NULL,
  drive_file_id TEXT NOT NULL,
  utf8_bom INTEGER NOT NULL CHECK (utf8_bom IN (0,1)),
  crlf_count INTEGER NOT NULL,
  bare_lf_count INTEGER NOT NULL,
  bare_cr_count INTEGER NOT NULL,
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  UNIQUE (work_id, sha256_raw)
);

CREATE TABLE IF NOT EXISTS segmentations (
  id INTEGER PRIMARY KEY,
  source_revision_id INTEGER NOT NULL REFERENCES source_revisions(id) ON DELETE RESTRICT,
  rules_sha256 TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  UNIQUE (source_revision_id, rules_sha256)
);

CREATE TABLE IF NOT EXISTS segments (
  id INTEGER PRIMARY KEY,
  segmentation_id INTEGER NOT NULL REFERENCES segmentations(id) ON DELETE RESTRICT,
  ordinal INTEGER NOT NULL CHECK (ordinal >= 1),
  kind TEXT NOT NULL CHECK (kind IN ('numbered','title_section','prologue','epilogue','note','frontmatter','tail','unresolved')),
  boundary_status TEXT NOT NULL CHECK (boundary_status IN ('confirmed','candidate','hold')),
  label TEXT,
  number_claimed INTEGER CHECK (number_claimed IS NULL OR number_claimed > 0),
  number_occurrence INTEGER,
  start_cp INTEGER NOT NULL CHECK (start_cp >= 0),
  end_cp INTEGER NOT NULL CHECK (end_cp >= start_cp),
  text_sha256 TEXT NOT NULL,
  body TEXT NOT NULL,
  note TEXT,
  UNIQUE (segmentation_id, ordinal),
  UNIQUE (segmentation_id, start_cp),
  CHECK (number_occurrence IS NULL OR number_occurrence >= 1),
  CHECK (number_claimed IS NOT NULL OR number_occurrence IS NULL)
);

CREATE INDEX IF NOT EXISTS segments_number ON segments(segmentation_id, number_claimed, number_occurrence);
CREATE INDEX IF NOT EXISTS segments_kind ON segments(segmentation_id, kind, boundary_status);

CREATE VIEW IF NOT EXISTS current_segments AS
SELECT w.work_id, w.author, w.title AS work_title, sr.sha256_raw,
       sr.relative_path, s.*
FROM works w
JOIN segmentations sg ON sg.id = w.current_segmentation_id
JOIN source_revisions sr ON sr.id = sg.source_revision_id
JOIN segments s ON s.segmentation_id = sg.id;

CREATE VIEW IF NOT EXISTS first_50_status AS
WITH RECURSIVE n(value) AS (SELECT 1 UNION ALL SELECT value + 1 FROM n WHERE value < 50),
matches AS (
 SELECT w.work_id, n.value AS target_number,
   COUNT(s.id) AS candidate_count,
   SUM(CASE WHEN s.kind = 'numbered' AND s.boundary_status = 'confirmed' THEN 1 ELSE 0 END) AS confirmed_count,
   MIN(CASE WHEN s.kind = 'numbered' AND s.boundary_status = 'confirmed' THEN s.id END) AS confirmed_segment_id
 FROM works w CROSS JOIN n
 LEFT JOIN segments s ON s.segmentation_id = w.current_segmentation_id AND s.number_claimed = n.value
 GROUP BY w.work_id, n.value
)
SELECT work_id, target_number,
 CASE WHEN candidate_count = 0 THEN 'unmapped'
      WHEN candidate_count > 1 THEN 'conflict'
      WHEN confirmed_count = 1 THEN 'mapped'
      ELSE 'hold' END AS mapping_status,
 CASE WHEN candidate_count = 1 AND confirmed_count = 1 THEN confirmed_segment_id END AS segment_id,
 candidate_count
FROM matches;

CREATE TRIGGER IF NOT EXISTS no_source_update BEFORE UPDATE ON source_revisions BEGIN SELECT RAISE(ABORT, 'source revision is immutable'); END;
CREATE TRIGGER IF NOT EXISTS no_source_delete BEFORE DELETE ON source_revisions BEGIN SELECT RAISE(ABORT, 'source revision is immutable'); END;
CREATE TRIGGER IF NOT EXISTS no_segmentation_update BEFORE UPDATE ON segmentations BEGIN SELECT RAISE(ABORT, 'segmentation is immutable'); END;
CREATE TRIGGER IF NOT EXISTS no_segmentation_delete BEFORE DELETE ON segmentations BEGIN SELECT RAISE(ABORT, 'segmentation is immutable'); END;
CREATE TRIGGER IF NOT EXISTS no_segment_update BEFORE UPDATE ON segments BEGIN SELECT RAISE(ABORT, 'segment is immutable'); END;
CREATE TRIGGER IF NOT EXISTS no_segment_delete BEFORE DELETE ON segments BEGIN SELECT RAISE(ABORT, 'segment is immutable'); END;
CREATE TRIGGER IF NOT EXISTS current_segmentation_work_update BEFORE UPDATE OF current_segmentation_id ON works
WHEN NEW.current_segmentation_id IS NOT NULL AND NOT EXISTS (
  SELECT 1 FROM segmentations sg JOIN source_revisions sr ON sr.id=sg.source_revision_id
  WHERE sg.id=NEW.current_segmentation_id AND sr.work_id=NEW.work_id
)
BEGIN SELECT RAISE(ABORT, 'current segmentation belongs to another work'); END;
