"""
Fetches open jobs from a company's Greenhouse job board.

Greenhouse's Job Board API is public and requires no auth for GET requests:
    GET https://boards-api.greenhouse.io/v1/boards/{token}/jobs?content=true

Docs: https://developers.greenhouse.io/job-board.html
"""
import requests

TIMEOUT = 15


def fetch_greenhouse_jobs(token: str) -> dict:
    """
    Returns:
        {
            "status": "ok" | "error",
            "error": str | None,
            "jobs": [ {title, location, url, updated_at, job_id}, ... ]
        }
    """
    url = f"https://boards-api.greenhouse.io/v1/boards/{token}/jobs?content=true"
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

    jobs = []
    for j in data.get("jobs", []):
        jobs.append({
            "job_id": str(j.get("id")),
            "title": j.get("title", "").strip(),
            "location": (j.get("location") or {}).get("name", "Unknown"),
            "url": j.get("absolute_url", ""),
            "updated_at": j.get("updated_at"),
            "posted_at": j.get("first_published") or j.get("updated_at"),
        })

    return {"status": "ok", "error": None, "jobs": jobs}
