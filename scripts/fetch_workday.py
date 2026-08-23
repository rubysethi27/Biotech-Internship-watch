"""
Fetches open jobs from a company's Workday job board.
 
Workday does NOT publish a single stable public API the way Greenhouse/Lever
do -- this uses the common (but unofficial, undocumented, and occasionally
company-specific) CXS pattern:
 
    POST https://{tenant}.wd5.myworkdayjobs.com/wday/cxs/{tenant}/{site}/jobs
 
Because it's unofficial:
  - the numeric subdomain (wd5, wd1, wd3, etc.) varies by company and isn't
    guessable from the tenant name alone
  - the exact JSON shape occasionally differs
  - some companies require Referer/Origin headers or reject large page sizes
 
Treat every Workday result as "best effort." When a company shows as broken
in the dashboard, the error message now includes Workday's actual response
body (not just the HTTP status) -- that's usually enough to tell you exactly
what it's rejecting.
"""
import requests
 
TIMEOUT = 15
# Common subdomains to try, in likely-order. First one that returns 200 wins.
CANDIDATE_HOSTS = ["wd5", "wd1", "wd3", "wd12"]
 
 
def fetch_workday_jobs(tenant: str, site: str, wd_host: str = None) -> dict:
    hosts_to_try = [wd_host] if wd_host else CANDIDATE_HOSTS
    last_error = None
 
    for host in hosts_to_try:
        url = f"https://{tenant}.{host}.myworkdayjobs.com/wday/cxs/{tenant}/{site}/jobs"
        try:
            resp = requests.post(
                url,
                json={"appliedFacets": {}, "limit": 20, "offset": 0, "searchText": ""},
                timeout=TIMEOUT,
                headers={
                    "User-Agent": "Mozilla/5.0 (compatible; internship-tracker/1.0)",
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                    "Referer": f"https://{tenant}.{host}.myworkdayjobs.com/{site}",
                    "Origin": f"https://{tenant}.{host}.myworkdayjobs.com",
                },
            )
        except requests.RequestException as e:
            last_error = f"network error on {host}: {e}"
            continue
 
        if resp.status_code != 200:
            # capture Workday's actual error body -- this is what tells us
            # WHY it's rejecting the request, not just that it did
            body_snippet = resp.text[:300].replace("\n", " ") if resp.text else "(empty body)"
            last_error = f"HTTP {resp.status_code} on {host} -- response: {body_snippet}"
            continue
 
        try:
            data = resp.json()
        except ValueError:
            last_error = f"non-JSON response on {host}"
            continue
 
        postings = data.get("jobPostings")
        if postings is None:
            last_error = f"unexpected response shape on {host}: {str(data)[:200]}"
            continue
 
        jobs = []
        for j in postings:
            path = j.get("externalPath", "")
            jobs.append({
                "job_id": path or j.get("bulletFields", [""])[0],
                "title": (j.get("title") or "").strip(),
                "location": j.get("locationsText", "Unknown"),
                "url": f"https://{tenant}.{host}.myworkdayjobs.com/{site}{path}" if path else "",
                "updated_at": j.get("postedOn"),
                "posted_at": j.get("postedOn"),
            })
        return {"status": "ok", "error": None, "jobs": jobs, "working_host": host}
 
    return {"status": "error", "error": last_error or "no host worked", "jobs": []}
