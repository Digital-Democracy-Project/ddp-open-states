/Users/agentsmith/Developer/repos/ddp-open-states-dev/.venv/lib/python3.9/site-packages/google/auth/__init__.py:54: FutureWarning: You are using a Python version 3.9 past its end of life. Google will update google-auth with critical bug fixes on a best-effort basis, but not with any other fixes or features. Please upgrade your Python version, and then update google-auth.
  warnings.warn(eol_message.format("3.9"), FutureWarning)
/Users/agentsmith/Developer/repos/ddp-open-states-dev/.venv/lib/python3.9/site-packages/google/oauth2/__init__.py:40: FutureWarning: You are using a Python version 3.9 past its end of life. Google will update google-auth with critical bug fixes on a best-effort basis, but not with any other fixes or features. Please upgrade your Python version, and then update google-auth.
  warnings.warn(eol_message.format("3.9"), FutureWarning)
/Users/agentsmith/Developer/repos/ddp-open-states-dev/.venv/lib/python3.9/site-packages/google/api_core/_python_version_support.py:242: FutureWarning: You are using a non-supported Python version (3.9.6). Google will not post any further updates to google.api_core supporting this Python version. Please upgrade to the latest Python version, or at least Python 3.11, and then update google.api_core.
  warnings.warn(message, FutureWarning)
13:20:49 DEBUG openstates.stats: Stat emission is not enabled.
13:20:49 INFO openstates: save jurisdiction Pennsylvania as jurisdiction_ocd-jurisdiction-country:us-state:pa-government.json
13:20:49 DEBUG openstates: {
    "_id": "ocd-jurisdiction/country:us/state:pa/government",
    "classification": "state",
    "division_id": "ocd-division/country:us/state:pa",
    "extras": {},
    "id": "ocd-jurisdiction/country:us/state:pa/government",
    "legislative_sessions": [
        {
            "_scraped_name": "2009-2010 Regular Session",
            "classification": "primary",
            "identifier": "2009-2010",
            "name": "2009-2010 Regular Session",
            "start_date": "2009-01-06",
            "end_date": "2010-11-30"
        },
        {
            "_scraped_name": "2009-2010 Special Session #1 (Transportation)",
            "classification": "special",
            "identifier": "2009-2010 Special Session #1 (Transportation)",
            "name": "2009-2010, 1st Special Session",
            "start_date": "2010-09-16",
            "end_date": "2010-09-16"
        },
        {
            "_scraped_name": "2011-2012 Regular Session",
            "classification": "primary",
            "identifier": "2011-2012",
            "name": "2011-2012 Regular Session",
            "start_date": "2011-01-04",
            "end_date": "2012-11-30"
        },
        {
            "_scraped_name": "2013-2014 Regular Session",
            "classification": "primary",
            "identifier": "2013-2014",
            "name": "2013-2014 Regular Session",
            "start_date": "2013-01-02",
            "end_date": "2014-11-12"
        },
        {
            "_scraped_name": "2015-2016 Regular Session",
            "classification": "primary",
            "identifier": "2015-2016",
            "name": "2015-2016 Regular Session",
            "start_date": "2015-01-06",
            "end_date": "2016-11-30"
        },
        {
            "_scraped_name": "2017-2018 Regular Session",
            "classification": "primary",
            "identifier": "2017-2018",
            "name": "2017-2018 Regular Session",
            "start_date": "2017-01-03",
            "end_date": "2018-11-30"
        },
        {
            "_scraped_name": "2019-2020 Regular Session",
            "classification": "primary",
            "identifier": "2019-2020",
            "name": "2019-2020 Regular Session",
            "start_date": "2019-01-01",
            "end_date": "2020-11-30"
        },
        {
            "_scraped_name": "2021-2022 Regular Session",
            "classification": "primary",
            "identifier": "2021-2022",
            "name": "2021-2022 Regular Session",
            "start_date": "2021-01-05",
            "end_date": "2022-11-30",
            "active": false
        },
        {
            "_scraped_name": "2023-2024 Regular Session",
            "classification": "primary",
            "identifier": "2023-2024",
            "name": "2023-2024 Regular Session",
            "start_date": "2023-01-03",
            "end_date": "2024-11-30",
            "active": false,
            "extras": {
                "session_year": "2023"
            }
        },
        {
            "_scraped_name": "2023-2024 Special Session #1 (Victims of Sexual Abuse)",
            "classification": "primary",
            "identifier": "2023-2024S1",
            "name": "2023-2024 Special Session #1",
            "start_date": "2023-01-09",
            "end_date": "2024-11-30",
            "active": false
        },
        {
            "_scraped_name": "2025-2026 Regular Session",
            "classification": "primary",
            "identifier": "2025-2026",
            "name": "2025-2026 Regular Session",
            "start_date": "2025-01-07",
            "end_date": "2026-11-30",
            "active": true,
            "extras": {
                "session_year": "2025"
            }
        }
    ],
    "name": "Pennsylvania",
    "url": "http://www.legis.state.pa.us/"
}
13:20:49 INFO openstates: save organization Pennsylvania General Assembly as organization_2136f22e-d6ea-11f1-b7c5-ee75dcf20307.json
13:20:49 DEBUG openstates: {
    "_id": "2136f22e-d6ea-11f1-b7c5-ee75dcf20307",
    "classification": "legislature",
    "extras": {},
    "links": [],
    "name": "Pennsylvania General Assembly",
    "parent_id": null,
    "sources": []
}
13:20:49 INFO openstates: save organization Senate as organization_2136fe0e-d6ea-11f1-b7c5-ee75dcf20307.json
13:20:49 DEBUG openstates: {
    "_id": "2136fe0e-d6ea-11f1-b7c5-ee75dcf20307",
    "classification": "upper",
    "extras": {},
    "links": [],
    "name": "Senate",
    "parent_id": "2136f22e-d6ea-11f1-b7c5-ee75dcf20307",
    "sources": []
}
13:20:49 INFO openstates: save organization House as organization_2137078c-d6ea-11f1-b7c5-ee75dcf20307.json
13:20:49 DEBUG openstates: {
    "_id": "2137078c-d6ea-11f1-b7c5-ee75dcf20307",
    "classification": "lower",
    "extras": {},
    "links": [],
    "name": "House",
    "parent_id": "2136f22e-d6ea-11f1-b7c5-ee75dcf20307",
    "sources": []
}

Written to notes/pa-onboarding-probe-20261102.md
# Onboarding Probe — pa (Pennsylvania)

**Classification:** YELLOW
**Run at:** 2026-11-02T18:20:48.967188+00:00  |  **Wall clock:** 2.2s

PLAN-push-button-onboarding.md §4.4 / §5 Stage 0 -- OPEN-222. Read-only: no production database writes, no scraper code changes, no tickets filed. See the script's own docstring for exactly what each gate checks and the judgment calls made where the plan's prose left a gap.

Gates A, B and D come from the Fargate run probe-pa-20261031 (2026-10-31T18:40:57.806727+00:00); C, E, F, G, H and I ran here against its downloaded sample.

## Gate summary

| Gate | Blocking? | Status | Summary |
|---|---|---|---|
| A | yes | PASS | 57 scraped session(s), 1 active |
| B | yes | PASS | module shape recorded |
| C | yes | PASS | all 3 media_type(s) seen have an extractor entry: application/msword, application/pdf, text/html |
| D | yes | PASS | dry scrape OK: 10 bill(s) in 27.2s |
| E | no | WARN | no motion_classification.yaml block for 'pa' yet |
| F | no | SKIP | walk direction (informational only, NOT written to the manifest per OPEN-34's 2026-08-07 correction): unknown (0 classifiable multi-version bill(s) in this dry scrape's sample) |
| G | no | WARN | people data / broker session-shape check -- see details |
| H | yes | PASS | 33 BillVersionLink row(s) present |
| I | yes | PASS | only one active session, so there is no other session to collide with |
| J | no | PASS | 0/397 personvote rows unresolved across 1 session(s) |

## Details

### Gate A

**PASS** (blocking) — 57 scraped session(s), 1 active
- active: 2025-2026

### Gate B

**PASS** (blocking) — module shape recorded
- votes scraper registered: False
- bills scraper accepts start=: False
- WAF resilience profile: none
- no module-level RPM override found (PA_SCRAPELIB_RPM not set) -- platform default applies
- no credential env-var references found in scraper source

### Gate C

**PASS** (blocking) — all 3 media_type(s) seen have an extractor entry: application/msword, application/pdf, text/html

### Gate D

**PASS** (blocking) — dry scrape OK: 10 bill(s) in 27.2s
- wall clock: 27.2s
- objects written: 10
- sample: 10 bill(s) and 16 vote event(s) (26 objects); stopped by: bill limit (limits: 10 bills, 200 objects)
- avg per-bill latency: 2.72s

### Gate E

**WARN** (advisory) — no motion_classification.yaml block for 'pa' yet
- sample motion texts already in local DB: ['Committee vote (Appropriations): Re-Reported as Committed', 'Committee vote (Children & Youth): Appeal the Ruling of the Chair', 'Committee vote (Children & Youth): Re-refer Bill To Another Committee', 'Committee vote (Education): Re-refer Bill To Another Committee', 'Committee vote (Education): Reported as Committed', 'Committee vote (Health): Re-refer Bill To Another Committee', 'Committee vote (Intergovernmental Operations): Reported as Committed', 'Committee vote (Judiciary): Motion to appeal the ruling of the Chair', 'Committee vote (Judiciary): Re-refer Bill To Another Committee', 'Committee vote (Rules & Executive Nominations): Adopt Amendment A01953']

### Gate F

**SKIP** (advisory) — walk direction (informational only, NOT written to the manifest per OPEN-34's 2026-08-07 correction): unknown (0 classifiable multi-version bill(s) in this dry scrape's sample)

### Gate G

**WARN** (advisory) — people data / broker session-shape check -- see details
- people/data/pa/legislature/ non-empty: True
- broker fixture not found locally (/Users/agentsmith/Developer/repos/ddp-broker-py/common/fixtures/jurisdictions.csv) -- this is a different repo's checkout, not expected to be present here; skipped rather than guessed
- session code(s) not matching the broker's regex: 2025-2026 (a broker-side code change would be needed for these)

### Gate H

**PASS** (blocking) — 33 BillVersionLink row(s) present
- import command: /Users/agentsmith/Developer/repos/ddp-open-states-dev/.venv/bin/os-update pa --import --datadir /private/tmp/claude-502/-Users-agentsmith-Developer-repos-ddp-open-states/8b7ad370-5f81-4ec0-92d5-c8ff222bf33b/scratchpad/probe-pa/_probe/_import
- import exit code: 0
- LegislativeSession rows for pa after import: 11 (2009-2010, 2009-2010 Special Session #1 (Transportation), 2011-2012, 2013-2014, 2015-2016, 2017-2018, 2019-2020, 2021-2022, 2023-2024, 2023-2024S1, 2025-2026)
- BillVersionLink rows for pa (session 2025-2026): 33
- most recent opencivicdata_bill.updated_at for pa (session 2025-2026): 2026-10-31 15:54:41.531030+00:00

### Gate I

**PASS** (blocking) — only one active session, so there is no other session to collide with
- probed session 2025-2026: 16 vote event file(s)

### Gate J

**PASS** (advisory) — 0/397 personvote rows unresolved across 1 session(s)
- sampled sessions: 2025-2026
- personvote rows: 397
- unresolved (voter_name set, voter_id NULL): 0

## Recommendation

Needs scoped code work before progressing: blocking gate(s) none, advisory gate(s) needing attention: ['E', 'G']. File templated tickets per RUNBOOK.md §5 Stage 1, copying the AC structure from the matching solved OPEN ticket named in each gate's detail above.

