-- Manifest of materialized feature-store snapshots (ADR-011). Each row
-- documents exactly what data + code + config produced one feature_store_v{N}
-- table, so a model's training data is always reproducible: model -> snapshot
-- -> git commit + config -> immutable raw data.

CREATE TABLE IF NOT EXISTS feature_snapshots (
    version      INTEGER PRIMARY KEY,
    table_name   VARCHAR NOT NULL UNIQUE,
    created_at   TIMESTAMP NOT NULL,
    git_commit   VARCHAR,
    config_hash  VARCHAR NOT NULL,
    row_count    BIGINT NOT NULL,
    min_date     DATE,
    max_date     DATE
);
