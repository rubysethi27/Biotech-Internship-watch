"""
Fetches open jobs from a company's Lever job board.

Lever's postings API is public:
    GET https://api.lever.co/v0/postings/{token}?mode=json
"""
import requests

TIMEOUT = 15


def fetch_lever_jobs(token: str) -> dict:
    url = f"https://api.lever.co/v0/postings/{token}?mode=json"
    try:
        resp = requests.get(url, timeout=TIMEOUT, headers={"User-Agent": "internship-tracker/1.0"})
    except requests.RequestException as e:
        return {"status": "error", "error": f"network error: {e}", "jobs": []}

    if resp.status_code == 404:
        return {"status": "error", "error": "board token not found (404) — verify token in companies.yaml", "jobs": []}
    if resp.status_code != 200:
        return {"status": "error", "error": f"HTTP {resp.status_code}", "jobs": []}

    try:
        data = resp.json()
    except ValueError:
        return {"status": "error", "error": "response was not valid JSON", "jobs": []}

    if not isinstance(data, list):
        return {"status": "error", "error": "unexpected response shape", "jobs": []}

    jobs = []
    for j in data:
        categories = j.get("categories", {}) or {}
        jobs.append({
            "job_id": str(j.get("id")),
            "title": (j.get("text") or "").strip(),
            "location": categories.get("location", "Unknown"),
            "url": j.get("hostedUrl", ""),
            "updated_at": j.get("updatedAt"),
            "posted_at": j.get("createdAt"),
        })

    return {"status": "ok", "error": None, "jobs": jobs}
