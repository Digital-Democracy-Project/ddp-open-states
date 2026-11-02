/Users/agentsmith/Developer/repos/ddp-open-states-dev/.venv/lib/python3.9/site-packages/google/auth/__init__.py:54: FutureWarning: You are using a Python version 3.9 past its end of life. Google will update google-auth with critical bug fixes on a best-effort basis, but not with any other fixes or features. Please upgrade your Python version, and then update google-auth.
  warnings.warn(eol_message.format("3.9"), FutureWarning)
/Users/agentsmith/Developer/repos/ddp-open-states-dev/.venv/lib/python3.9/site-packages/google/oauth2/__init__.py:40: FutureWarning: You are using a Python version 3.9 past its end of life. Google will update google-auth with critical bug fixes on a best-effort basis, but not with any other fixes or features. Please upgrade your Python version, and then update google-auth.
  warnings.warn(eol_message.format("3.9"), FutureWarning)
/Users/agentsmith/Developer/repos/ddp-open-states-dev/.venv/lib/python3.9/site-packages/google/api_core/_python_version_support.py:242: FutureWarning: You are using a non-supported Python version (3.9.6). Google will not post any further updates to google.api_core supporting this Python version. Please upgrade to the latest Python version, or at least Python 3.11, and then update google.api_core.
  warnings.warn(message, FutureWarning)
13:20:51 DEBUG openstates.stats: Stat emission is not enabled.
13:20:51 INFO openstates: save jurisdiction Nebraska as jurisdiction_ocd-jurisdiction-country:us-state:ne-government.json
13:20:51 DEBUG openstates: {
    "_id": "ocd-jurisdiction/country:us/state:ne/government",
    "classification": "state",
    "division_id": "ocd-division/country:us/state:ne",
    "extras": {},
    "id": "ocd-jurisdiction/country:us/state:ne/government",
    "legislative_sessions": [
        {
            "_scraped_name": "102nd Legislature 1st and 2nd Sessions",
            "end_date": "2012-04-18",
            "identifier": "102",
            "name": "102nd Legislature (2011-2012)",
            "start_date": "2011-01-05",
            "classification": "primary"
        },
        {
            "_scraped_name": "102nd Legislature 1st Special Session",
            "end_date": "2011-11-22",
            "identifier": "102S1",
            "name": "102nd Legislature, 1st Special Session (2011)",
            "start_date": "2011-11-01",
            "classification": "primary"
        },
        {
            "_scraped_name": "103rd Legislature 1st and 2nd Sessions",
            "end_date": "2014-05-30",
            "identifier": "103",
            "name": "103rd Legislature (2013-2014)",
            "start_date": "2013-01-08",
            "classification": "primary"
        },
        {
            "_scraped_name": "104th Legislature 1st and 2nd Sessions",
            "end_date": "2016-12-31",
            "identifier": "104",
            "name": "104th Legislature (2015-2016)",
            "start_date": "2015-01-07",
            "classification": "primary"
        },
        {
            "_scraped_name": "105th Legislature 1st and 2nd Sessions",
            "end_date": "2018-12-31",
            "identifier": "105",
            "name": "105th Legislature (2017-2018)",
            "start_date": "2017-01-04",
            "classification": "primary"
        },
        {
            "_scraped_name": "106th Legislature 1st and 2nd Sessions",
            "end_date": "2020-12-31",
            "identifier": "106",
            "name": "106th Legislature (2019-2020)",
            "start_date": "2019-01-09",
            "classification": "primary"
        },
        {
            "_scraped_name": "107th Legislature 1st and 2nd Sessions",
            "identifier": "107",
            "name": "107th Legislature (2021-2022)",
            "start_date": "2022-01-05",
            "end_date": "2022-04-20",
            "classification": "primary",
            "active": false
        },
        {
            "_scraped_name": "107th Legislature 1st Special Session",
            "identifier": "107S1",
            "name": "107th Legislature 1st Special Session",
            "start_date": "2021-09-13",
            "end_date": "2022-09-14",
            "classification": "special",
            "active": false
        },
        {
            "_scraped_name": "108th Legislature 1st and 2nd Sessions",
            "identifier": "108",
            "name": "108th Legislature (2023-2024)",
            "start_date": "2023-01-04",
            "end_date": "2024-04-19",
            "classification": "primary",
            "active": false
        },
        {
            "_scraped_name": "108th Legislature 1st Special Session",
            "identifier": "108S1",
            "name": "108th Legislature First Special Session",
            "start_date": "2024-07-25",
            "end_date": "2024-07-31",
            "classification": "special",
            "active": false
        },
        {
            "_scraped_name": "109th Legislature 1st and 2nd Sessions",
            "identifier": "109",
            "name": "109th Legislature (2025-2026)",
            "start_date": "2025-01-08",
            "end_date": "2026-04-19",
            "classification": "primary",
            "active": true
        }
    ],
    "name": "Nebraska",
    "url": "http://nebraskalegislature.gov/"
}
13:20:51 INFO openstates: save organization Nebraska Legislature as organization_22c60fc6-d6ea-11f1-aa69-ee75dcf20307.json
13:20:51 DEBUG openstates: {
    "_id": "22c60fc6-d6ea-11f1-aa69-ee75dcf20307",
    "classification": "legislature",
    "extras": {},
    "links": [],
    "name": "Nebraska Legislature",
    "parent_id": null,
    "sources": []
}

Written to notes/ne-onboarding-probe-20261102.md
# Onboarding Probe — ne (Nebraska)

**Classification:** YELLOW
**Run at:** 2026-11-02T18:20:51.557630+00:00  |  **Wall clock:** 1.8s

PLAN-push-button-onboarding.md §4.4 / §5 Stage 0 -- OPEN-222. Read-only: no production database writes, no scraper code changes, no tickets filed. See the script's own docstring for exactly what each gate checks and the judgment calls made where the plan's prose left a gap.

Gates A, B and D come from the Fargate run probe-ne-20261031 (2026-10-31T18:40:52.879659+00:00); C, E, F, G, H and I ran here against its downloaded sample.

## Gate summary

| Gate | Blocking? | Status | Summary |
|---|---|---|---|
| A | yes | PASS | 31 scraped session(s), 1 active |
| B | yes | PASS | module shape recorded |
| C | yes | PASS | all 1 media_type(s) seen have an extractor entry: application/pdf |
| D | yes | PASS | dry scrape OK: 10 bill(s) in 24.2s |
| E | no | WARN | no motion_classification.yaml block for 'ne' yet |
| F | no | SKIP | walk direction (informational only, NOT written to the manifest per OPEN-34's 2026-08-07 correction): unknown (0 classifiable multi-version bill(s) in this dry scrape's sample) |
| G | no | PASS | people data / broker session-shape check OK |
| H | yes | PASS | 27 BillVersionLink row(s) present |
| I | yes | PASS | only one active session, so there is no other session to collide with |
| J | no | WARN | 17/637 personvote rows unresolved (2.7%) across 1 session(s) |

## Details

### Gate A

**PASS** (blocking) — 31 scraped session(s), 1 active
- active: 109

### Gate B

**PASS** (blocking) — module shape recorded
- votes scraper registered: False
- bills scraper accepts start=: False
- WAF resilience profile: none
- no module-level RPM override found (NE_SCRAPELIB_RPM not set) -- platform default applies
- no credential env-var references found in scraper source

### Gate C

**PASS** (blocking) — all 1 media_type(s) seen have an extractor entry: application/pdf

### Gate D

**PASS** (blocking) — dry scrape OK: 10 bill(s) in 24.2s
- wall clock: 24.2s
- objects written: 10
- sample: 10 bill(s) and 13 vote event(s) (23 objects); stopped by: bill limit (limits: 10 bills, 200 objects)
- avg per-bill latency: 2.42s

### Gate E

**WARN** (advisory) — no motion_classification.yaml block for 'ne' yet
- sample motion texts already in local DB: ['Advanced to Enrollment and Review Initial', 'Agriculture AM77 adopted', 'DeKay AM310 adopted', 'General Affairs AM549 adopted', 'Lippincott MO158 failed', 'Passed on Final Reading 34-10*-5', 'Passed on Final Reading 47-0-2', 'Passed on Final Reading 48-0-1', 'Passed on Final Reading with Emergency Clause 48-0-1', 'Raybould AM646 lost']

### Gate F

**SKIP** (advisory) — walk direction (informational only, NOT written to the manifest per OPEN-34's 2026-08-07 correction): unknown (0 classifiable multi-version bill(s) in this dry scrape's sample)

### Gate G

**PASS** (advisory) — people data / broker session-shape check OK
- people/data/ne/legislature/ non-empty: True
- broker fixture not found locally (/Users/agentsmith/Developer/repos/ddp-broker-py/common/fixtures/jurisdictions.csv) -- this is a different repo's checkout, not expected to be present here; skipped rather than guessed

### Gate H

**PASS** (blocking) — 27 BillVersionLink row(s) present
- import command: /Users/agentsmith/Developer/repos/ddp-open-states-dev/.venv/bin/os-update ne --import --datadir /private/tmp/claude-502/-Users-agentsmith-Developer-repos-ddp-open-states/8b7ad370-5f81-4ec0-92d5-c8ff222bf33b/scratchpad/probe-ne/_probe/_import
- import exit code: 0
- LegislativeSession rows for ne after import: 11 (102, 102S1, 103, 104, 105, 106, 107, 107S1, 108, 108S1, 109)
- BillVersionLink rows for ne (session 109): 27
- most recent opencivicdata_bill.updated_at for ne (session 109): 2026-10-31 15:51:17.509868+00:00

### Gate I

**PASS** (blocking) — only one active session, so there is no other session to collide with
- probed session 109: 13 vote event file(s)

### Gate J

**WARN** (advisory) — 17/637 personvote rows unresolved (2.7%) across 1 session(s)
- sampled sessions: 109
- personvote rows: 637
- unresolved (voter_name set, voter_id NULL): 17
- 'Meyer': 13 unresolved vote(s)
- 'Strommen*': 1 unresolved vote(s)
- 'Lonowski*': 1 unresolved vote(s)
- 'Rountree*': 1 unresolved vote(s)
- 'Guereca*': 1 unresolved vote(s)

## Recommendation

Needs scoped code work before progressing: blocking gate(s) none, advisory gate(s) needing attention: ['E', 'J']. File templated tickets per RUNBOOK.md §5 Stage 1, copying the AC structure from the matching solved OPEN ticket named in each gate's detail above.

