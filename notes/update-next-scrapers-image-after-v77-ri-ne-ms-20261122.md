# UPDATE to `77bda86` (the next scrapers image after v77): it now also carries OPEN-756 (Rhode Island 2021 end), OPEN-761 (Nebraska "*" voter names) and OPEN-759 (Mississippi 20093E end). Scrapers main is `f0ac9ef8`. 2026-11-22 (Mac side, State Specific Handling)

**Not a GO.** Everything in `77bda86` stands. Core is unchanged at `7f531958`.

## Added since `77bda86` (scrapers main now `f0ac9ef85fc8e8fa62276bd4e526c9e746826188`; all from Onboard New States)
| Merge | What |
|---|---|
| #215 (OPEN-756, `a40f9b9a`) | Rhode Island's 2021 session ends 2022-01-04, its official close. Wyoming is unchanged |
| #217 (OPEN-761, `ea2d8ca7`) | Nebraska: the late-recorded-vote "*" is stripped from voter names, so about 312 session-109 votes link to their senators. **Its data effect needs a later NE 109 rescrape or re-import, on Ramon's go** |
| #218 (OPEN-759, `f0ac9ef8`) | Mississippi's 2009 Third Extraordinary Session (20093E) ends 2009-07-10 (Ramon: "Fix it to last action") |

* No migration and no new setting.
* Still expected: OPEN-765 (North Carolina's 2025 end date, scrapers #219, open) and BROKER-579's scraper part (veto overrides for PA, NE and LA, being built).

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
