-- DROP TABLE IF EXISTS issues;
-- DROP TABLE IF EXISTS resolutions;

CREATE TABLE IF NOT EXISTS issues (
    key         TEXT,
    created     BIGINT,
    resolved    BIGINT,
    resolution  TEXT,
    category    TEXT
);

CREATE TABLE IF NOT EXISTS resolutions (
    id   TEXT,
    key  TEXT
);

-- Индексы (ускоряют join/фильтры)
CREATE INDEX IF NOT EXISTS idx_issues_resolution ON issues(resolution);
CREATE INDEX IF NOT EXISTS idx_issues_category   ON issues(category);
CREATE INDEX IF NOT EXISTS idx_issues_created    ON issues(created);
CREATE INDEX IF NOT EXISTS idx_issues_resolved   ON issues(resolved);
