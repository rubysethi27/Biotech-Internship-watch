"""
Orchestrates the whole tracker run:
  1. load config/companies.yaml + config/keywords.yaml
  2. hit each company's ATS API
  3. filter jobs against business/technical keyword lists
  4. upsert into SQLite (tracks first_seen_date, flips stale postings to 'closed')
  5. write docs/data.json for the dashboard
  6. write a plain-text run summary to stdout (shows up in GitHub Actions logs)

Run with: python scripts/pipeline.py
"""
import hashlib
import json
import sys
import sqlite3
import yaml
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from fetch_greenhouse import fetch_greenhouse_jobs
from fetch_lever import fetch_lever_jobs
from fetch_workday import fetch_workday_jobs
from init_db import init_db, DB_PATH

ROOT = Path(__file__).parent.parent
CONFIG_DIR = ROOT / "config"
DOCS_DIR = ROOT / "docs"
TODAY = datetime.now(timezone.utc).strftime("%Y-%m-%d")
NOW_ISO = datetime.now(timezone.utc).isoformat()


def load_yaml(name):
    with open(CONFIG_DIR / name) as f:
        return yaml.safe_load(f)


def job_hash(company, job_id):
    return hashlib.sha256(f"{company}:{job_id}".encode()).hexdigest()[:16]


def classify(title, keywords_cfg):
    title_l = title.lower()

    for bad in keywords_cfg.get("exclude_if_contains", []):
        if bad.lower() in title_l:
            return None, []

    matched = []
    tracks = set()
    for kw in keywords_cfg.get("business_track", []):
        if kw.lower() in title_l:
            matched.append(kw)
            tracks.add("business")
    for kw in keywords_cfg.get("technical_track", []):
        if kw.lower() in title_l:
            matched.append(kw)
            tracks.add("technical")

    if not tracks:
        return None, []

    track = "both" if len(tracks) == 2 else list(tracks)[0]
    return track, matched


def fetch_company(company):
    ats = company["ats"]
    if ats == "greenhouse":
        return fetch_greenhouse_jobs(company["token"])
    elif ats == "lever":
        return fetch_lever_jobs(company["token"])
    elif ats == "workday":
        return fetch_workday_jobs(company["tenant"], company["site"], company.get("wd_host"))
    else:
        return {"status": "error", "error": f"unknown ats type '{ats}'", "jobs": []}


def run():
    init_db()
    companies_cfg = load_yaml("companies.yaml")
    keywords_cfg = load_yaml("keywords.yaml")

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    seen_ids_this_run = set()
    summary_lines = []

    for company in companies_cfg.get("ats_tracked", []):
        name = company["name"]
        category = company.get("category", "unknown")
        result = fetch_company(company)

        cur.execute(
            """INSERT INTO source_status (company, ats, status, error, last_checked)
               VALUES (?, ?, ?, ?, ?)
               ON CONFLICT(company) DO UPDATE SET
                 ats=excluded.ats, status=excluded.status,
                 error=excluded.error, last_checked=excluded.last_checked""",
            (name, company["ats"], result["status"], result.get("error"), NOW_ISO),
        )

        if result["status"] != "ok":
            summary_lines.append(f"  [BROKEN] {name} ({company['ats']}): {result['error']}")
            continue

        matched_count = 0
        for job in result["jobs"]:
            track, matched_kw = classify(job["title"], keywords_cfg)
            if track is None:
                continue

            matched_count += 1
            jid = job_hash(name, job["job_id"])
            seen_ids_this_run.add(jid)

            cur.execute("SELECT first_seen_date FROM jobs WHERE id = ?", (jid,))
            existing = cur.fetchone()
            first_seen = existing[0] if existing else TODAY

            cur.execute(
                """INSERT INTO jobs (id, company, title, location, url, category, track,
                                     matched_keywords, source, first_seen_date, last_seen_date, status)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'open')
                   ON CONFLICT(id) DO UPDATE SET
                     last_seen_date=excluded.last_seen_date, status='open',
                     title=excluded.title, url=excluded.url""",
                (jid, name, job["title"], job["location"], job["url"], category,
                 track, ",".join(matched_kw), company["ats"], first_seen, TODAY),
            )

        summary_lines.append(f"  [OK] {name}: {len(result['jobs'])} total postings, {matched_count} matched keywords")

    # anything not seen this run that was previously open -> mark closed
    cur.execute("SELECT id FROM jobs WHERE status = 'open'")
    all_open = {row[0] for row in cur.fetchall()}
    newly_closed = all_open - seen_ids_this_run
    for jid in newly_closed:
        cur.execute("UPDATE jobs SET status = 'closed' WHERE id = ?", (jid,))

    conn.commit()

    # ---- export dashboard JSON ----
    cur.execute("""SELECT company, title, location, url, category, track,
                          matched_keywords, source, first_seen_date, last_seen_date, status
                   FROM jobs ORDER BY first_seen_date DESC""")
    cols = ["company", "title", "location", "url", "category", "track",
            "matched_keywords", "source", "first_seen_date", "last_seen_date", "status"]
    jobs_out = [dict(zip(cols, row)) for row in cur.fetchall()]

    cur.execute("SELECT company, ats, status, error, last_checked FROM source_status")
    src_cols = ["company", "ats", "status", "error", "last_checked"]
    sources_out = [dict(zip(src_cols, row)) for row in cur.fetchall()]

    conn.close()

    DOCS_DIR.mkdir(exist_ok=True)
    output = {
        "generated_at": NOW_ISO,
        "jobs": jobs_out,
        "source_status": sources_out,
        "watchlist": companies_cfg.get("watchlist", []),
    }
    with open(DOCS_DIR / "data.json", "w") as f:
        json.dump(output, f, indent=2)

    print(f"=== Internship Tracker Run — {NOW_ISO} ===")
    print("\n".join(summary_lines))
    print(f"\nTotal open matched postings: {len([j for j in jobs_out if j['status']=='open'])}")
    print(f"Newly closed this run: {len(newly_closed)}")
    print(f"Dashboard data written to {DOCS_DIR / 'data.json'}")


if __name__ == "__main__":
    run()
