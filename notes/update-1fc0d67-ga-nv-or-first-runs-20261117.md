# UPDATE to GO `1fc0d67`: add step 7, Georgia, Nevada and Oregon's people loads and first manual runs on v62 (`ddp-scrapers:65`), after steps 1-6. 2026-11-17 (Mac side; two clarifications from the Push Button Onboarding session added 02:20 UTC)

**Ramon, 2026-11-17 (pop-up):** "Add them to my request now". The Push Button Onboarding session prepared these states; it does the Mac-side checks after each run (send it the run ids through this branch's reply).

**Why now:** step 3's rollout pulls ddp-open-states main, which carries #395/#396 (ga, nv, or at `scraping`), so all three join the **Sunday 11-22 02:00 UTC** batch. Their legislators are not loaded yet; a first scrape with 0 people is the pilot #2 trap. So tonight: people first, then one manual run each. v62 carries their readers (core #111/#112/#114/#115, scrapers #110-#117); top migration 0051, as RDS.

Steps 1-6 of `1fc0d67` are unchanged and come first. The Congress deadline (02:45 UTC) is not affected by this step.

## 7. Georgia, Nevada, Oregon
**Rules:** after step 3's rollout (both hosts on ddp-open-states main, so the trigger knows the three states). At most two state pipelines at once, counting US (03:00) and PA (04:00). None of a state's steps while its own scrape, import or archive runs. A stop is harmless: report it, do not retry past what a step says.

**A. People loads** (no image needed). Pull `/opt/ddp-open-states/people` to main (it must include people #24, OPEN-599, and #25, OPEN-596, both merged 11-16). The container's `/opt/venv-openstates/bin/os-people`, `--safe` first, as for Virginia on 11-16 (`3fecfad` 4B).
* **ga:** gate: about **236** people created (report the exact count; outside 220-250 stop).
* **nv:** gate: the run includes #25's names for Cruz-Crawford, Moore and O'Neill (as other_names); report created/updated.
* **or:** gate: "Gregory Smith" appears under Greg Smith's other names (#24); report created/updated.
* Any "went missing" or retirement line in another state: stop and report.

**B. One manual run each**, the `1f19165` method: `POST /ddp-sync/v1/trigger/openstates-scrape/<st>`, one call, no retry. Order: **nv**, then **or**, then **ga** (the long one).
* **Gate, each:** ECS revision **65**; the scraper's own "no session provided, using active sessions: {…}" line names **ga `2026_ss`**, **nv `2025Special36`**, **or `2026R1`** (the manifest has no session field; Oregon's votes scraper uses the same active session); `status=completed failed=0`; the archive finished.
* **ga:** a full run, about 1.5 h (about 29 s per bill). Do not set `start_filter` (it stays false until a later manifest PR, OPEN-604).
* **ga archive:** `www.legis.ga.gov` timed out from the Mac on 11-16 (the 10-31 Fargate probe got through). Report the archive's fetched and `fetch_errors` counts for ga; fetch errors are a report, not a retry.
* **or:** report vote events > 0, **floor and committee** separately.
* Report each run id, bill count, vote-event count and archived-document count.

**Not in this step:** LegBot, routing, website switch-on, the GA `start_filter` change, Massachusetts' separate votes scraper (stays off).

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
