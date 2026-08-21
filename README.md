# Internship Tracker

Tracks business-track and technical-track internships across biotech, pharma,
consulting, and VC — auto-pulled from company career pages, refreshed on a
schedule, shown on a dashboard you can bookmark.

**What this does automatically:** checks ~20 companies' official job boards
(Greenhouse / Lever / Workday) every few days, filters postings against your
keyword list, and shows them on a dashboard with first-seen dates and direct
apply links.

**What it doesn't do (and why):** it can't pull from LinkedIn, Indeed, or
Handshake. All three block automated scraping in their terms of service, and
Handshake sits behind your school login besides. Instead the dashboard gives
you one-click pre-filled search links for LinkedIn and Indeed, and the
watchlist section links straight to career pages for firms too small to have
a public API. For any startup with no listed internship, just tell Claude
the company name in chat and ask for a contacts/events research pass — that
part stays manual by design.

---

## One-time setup (15–20 minutes)

### 1. Create the GitHub repo
1. Go to [github.com/new](https://github.com/new), name it something like
   `internship-tracker`, set it to **Public** (required for free GitHub
   Pages), and create it — don't initialize with a README, you already have
   one.
2. On your computer (or right in the GitHub web UI using "Add file → Upload
   files"), upload every file/folder from this project, keeping the folder
   structure exactly as-is:
   ```
   internship-tracker/
     .github/workflows/update.yml
     config/companies.yaml
     config/keywords.yaml
     scripts/*.py
     docs/index.html
     docs/data.json
     requirements.txt
     .gitignore
   ```

### 2. Turn on GitHub Pages
1. In your repo, go to **Settings → Pages**.
2. Under "Build and deployment," set **Source** to "Deploy from a branch."
3. Set **Branch** to `main` and folder to **`/docs`**, then Save.
4. GitHub gives you a URL like `https://yourusername.github.io/internship-tracker/` —
   bookmark that, it's your dashboard.

### 3. Turn on GitHub Actions
1. Go to the **Actions** tab in your repo. GitHub sometimes asks you to
   confirm you want workflows enabled for the repo — click through it.
2. You'll see "Update Internship Tracker" listed. Click into it, then click
   **Run workflow** (top right) to trigger the first run manually rather than
   waiting for the schedule.
3. After ~1 minute, refresh — you should see a green checkmark. That means it
   fetched all the companies, filtered them, and pushed `docs/data.json` back
   to the repo.
4. Refresh your dashboard URL from step 2 — postings should now appear.

From here it re-runs automatically every **Monday and Thursday at 9am ET**
(edit the `cron` line in `.github/workflows/update.yml` if you want a
different cadence — you can also always trigger it manually from the Actions
tab).

---

## Reading the dashboard

- **Colored dots at the top** show which companies' feeds are currently
  connecting successfully (green) vs. broken (red, hover for the error).
- **Cards** show one posting each, tagged `business` and/or `technical`, with
  the date it was first spotted and a direct apply link.
- **Quick searches** section gives you one-click LinkedIn/Indeed searches
  pre-filled with your keyword list — since those platforms can't be
  auto-tracked, this is the fastest manual check.
- **Watchlist** section is VC firms and boutique consultancies without a
  reliable public job feed — click through to their careers page directly.

---

## Fixing a broken company

Because I couldn't test live API calls while building this (no internet
access in my sandbox), several of the pre-filled tokens in
`config/companies.yaml` are best guesses, especially the Workday ones. When
the dashboard shows a company as broken (red dot), here's the fastest fix:

1. Open that company's real "Careers" page in your browser.
2. Look at the URL:
   - **Greenhouse**: if it redirects to `boards.greenhouse.io/SOMETHING`,
     `SOMETHING` is the correct `token`.
   - **Lever**: if it redirects to `jobs.lever.co/SOMETHING`, that's the
     `token`.
   - **Workday**: the URL looks like
     `https://SOMECOMPANY.wd5.myworkdayjobs.com/en-US/SITENAME` — `wd5` is
     the `wd_host`, `SOMECOMPANY` is the `tenant`, `SITENAME` is the `site`.
3. Update the matching entry in `config/companies.yaml`, commit the change,
   and either wait for the next scheduled run or trigger one manually from
   the Actions tab.

If a company doesn't use any of these three ATS platforms at all (some run
fully custom career sites), move it from `ats_tracked` into `watchlist` in
`companies.yaml` — it'll then just show as a careers-page link instead of
erroring.

---

## Adding a company

Add an entry under `ats_tracked` (if it's on Greenhouse/Lever/Workday) or
`watchlist` (if not) in `config/companies.yaml`, following the existing
format. No code changes needed — the pipeline reads this file fresh every
run.

## Adjusting keywords

Edit `config/keywords.yaml`. `business_track` and `technical_track` are
substring-matched (case-insensitive) against job titles. `exclude_if_contains`
filters out senior/non-intern roles even if another keyword matches.

## Running it locally (optional)

```bash
pip install -r requirements.txt
python scripts/pipeline.py
```
This regenerates `data/tracker.db` and `docs/data.json` — open
`docs/index.html` in a browser afterward (or just push to GitHub and let
Pages serve it).
