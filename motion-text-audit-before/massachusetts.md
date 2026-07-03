# Motion texts — Massachusetts

**20 unique motion texts** across 45 vote events. 45 (100%) have an OpenStates classification set.

| Motion text | Classification | Votes | Pass | Fail |
|---|---|---|---|---|
| Passed to be engrossed | `passage` | 14 | 14 | 0 |
| Enacted | `passage` | 12 | 12 | 0 |
| Committee of conference report accepted, in concurrence | `passage` | 2 | 2 | 0 |
| Adopted | `passage` | 1 | 1 | 0 |
| Amendment #1 (Tarr) rejected | `passage` | 1 | 0 | 1 |
| Item 0330-0300 passed over veto | `passage` | 1 | 1 | 0 |
| Item 1231-1000 passed over veto | `passage` | 1 | 1 | 0 |
| Item 2810-0100 passed over veto | `passage` | 1 | 1 | 0 |
| Item 4000-0051 passed over veto | `passage` | 1 | 1 | 0 |
| Item 4000-0641 passed over veto | `passage` | 1 | 1 | 0 |
| Item 4110-1000 passed over veto | `passage` | 1 | 1 | 0 |
| Item 4512-0200 passed over veto | `passage` | 1 | 1 | 0 |
| Item 4513-1020 passed over veto | `passage` | 1 | 1 | 0 |
| Item 7002-1091 passed over veto | `passage` | 1 | 1 | 0 |
| Item 7003-0606 passed over veto | `passage` | 1 | 1 | 0 |
| Item 7004-0109 passed over veto | `passage` | 1 | 1 | 0 |
| Item 7004-3036 passed over veto | `passage` | 1 | 1 | 0 |
| Item 7007-0150 passed over veto | `passage` | 1 | 1 | 0 |
| Item 7061-9010 passed over veto | `passage` | 1 | 1 | 0 |
| Item 7077-0023 passed over veto | `passage` | 1 | 1 | 0 |

---

## Analysis

OpenStates sets `motion_classification = "passage"` on **all 20 motion types** (100%). The scraper
is mostly correct for MA — the legislature primarily records only final-stage votes — but two
categories are false positives.

**Note:** This analysis is based on a partial scrape (45 votes from 7,124 bills). The scrape timed
out downloading a Senate vote PDF. More motion text types may exist; re-run after a complete scrape.

### PASSAGE (4 patterns, 29 votes / 64%)

| Motion text | Votes | Notes |
|---|---|---|
| `Passed to be engrossed` | 14 | House passing bill to Senate for engrossment — chamber passage vote |
| `Enacted` | 12 | Final enactment — both chambers have agreed |
| `Adopted` | 1 | Generic adoption — floor passage |
| `Committee of conference report accepted, in concurrence` | 2 | Conference report adoption — final bicameral agreement |

### NOT PASSAGE — false positives in OpenStates

| Motion text | Votes | Why it's wrong |
|---|---|---|
| `Amendment #1 (Tarr) rejected` | 1 | Amendment vote, not passage — tagged `passage` by scraper in error |
| `Item [XXXX-XXXX] passed over veto` | 14 | Veto override on individual budget line items — a distinct vote type (`veto-override` in OpenStates schema), not initial passage |

**Amendment false positive (1 vote):** "Amendment #1 (Tarr) rejected" is an amendment rejection
vote — it failed (0 pass, 1 fail). The MA scraper blindly classifies all scraped roll calls as
`passage` regardless of the motion text, so any floor vote including amendment votes gets the
wrong label. This is the same structural problem as AZ, UT, MI.

**Veto override votes (14 votes):** The 14 "Item [number] passed over veto" records are the
legislature overriding the governor's line-item vetoes on the budget bill. These are categorically
different from initial passage (require 2/3 majority; the bill already passed, the question is
whether to override the executive). Should be `["veto-override"]` not `["passage"]`. Whether
these should be *scored* on a legislator's scorecard is a policy question — they reflect a
legislator's support for a specific budget item over gubernatorial objection, which could be
meaningful. Currently excluded by our NOT PASSAGE classification.

### Recommended regex

```python
MA_NOT_PASSAGE_PATTERNS = (
    r"^amendment.*rejected",      # amendment votes mis-tagged passage
    r"^amendment.*adopted",       # same — amendment adoption is not bill passage
    r"^item .+ passed over veto", # veto override on budget line items
)
MA_PASSAGE_PATTERNS = (
    r"^passed to be engrossed",
    r"^enacted",
    r"^adopted",
    r"^committee of conference report accepted",
)
```

Alternatively: trust OpenStates `classification == "passage"` for MA but exclude via NOT_PASSAGE
patterns first. Given that the scraper hardcodes `passage` on everything, the NOT_PASSAGE exclusion
list is the safer primary gate.

### Coverage summary

| Category | Votes | % of total |
|---|---|---|
| PASSAGE (classified) | 29 | 64.4% |
| NOT PASSAGE (classified) | 15 | 33.3% |
| Unknown | 1 | 2.2% |

### Key findings

1. **MA scraper hardcodes all votes as `passage`** — same structural problem as AZ, UT, MI. Only
   works for MA because the scraper happens to mostly capture final-stage votes.
2. **False positive rate is low (~3% clear, ~33% if veto overrides excluded)** — the MA legislature
   records few intermediate votes in the format this scraper reads, so the hardcode mostly works.
3. **Veto override votes need a policy decision** — currently classified NOT PASSAGE; reconsider
   if scoring veto behavior is a scorecard goal.
4. **Partial scrape warning** — 45 votes from 7,124 bills. Full 194th session likely has many more
   vote types. Re-run analysis after a complete scrape completes successfully.
