"""Creates the SQLite schema if it doesn't already exist."""
import os
import sqlite3
 
DB_PATH = "data/tracker.db"
 
SCHEMA = """
CREATE TABLE IF NOT EXISTS jobs (
    id TEXT PRIMARY KEY,          -- hash of company+job_id
    company TEXT NOT NULL,
    title TEXT NOT NULL,
    location TEXT,
    url TEXT,
    category TEXT,                -- pharma_biotech | consulting | vc
    track TEXT,                   -- business | technical | both
    matched_keywords TEXT,        -- comma-separated
    source TEXT,                  -- greenhouse | lever | workday
    first_seen_date TEXT NOT NULL,
    last_seen_date TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'open'   -- open | closed
);
 
CREATE TABLE IF NOT EXISTS source_status (
    company TEXT PRIMARY KEY,
    ats TEXT,
    status TEXT,                  -- ok | error
    error TEXT,
    last_checked TEXT
);
"""
 
 
def init_db(db_path: str = DB_PATH):
    parent_dir = os.path.dirname(db_path)
    if parent_dir:
        os.makedirs(parent_dir, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.executescript(SCHEMA)
    conn.commit()
    conn.close()
 
 
if __name__ == "__main__":
    init_db()
    print(f"Initialized {DB_PATH}")
