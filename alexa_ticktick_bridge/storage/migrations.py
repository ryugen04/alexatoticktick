SCHEMA = """
CREATE TABLE IF NOT EXISTS sync_records (
    alexa_item_id TEXT PRIMARY KEY,
    ticktick_task_id TEXT NOT NULL,
    item_name_hash TEXT NOT NULL,
    created_at TEXT NOT NULL,
    completed_at TEXT
);
DROP INDEX IF EXISTS idx_sync_records_item_hash;
CREATE INDEX IF NOT EXISTS idx_sync_records_item_hash
ON sync_records(item_name_hash);
"""
