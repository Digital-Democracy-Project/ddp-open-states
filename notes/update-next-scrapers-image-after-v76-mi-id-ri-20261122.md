# UPDATE to `42c2df4` (the next scrapers image after v76): it now also carries OPEN-648 (Michigan), OPEN-753 (Idaho) and OPEN-754 (Rhode Island). Scrapers main is `f6e615d4`. 2026-11-22 (Mac side, State Specific Handling)

**Not a GO.** Everything in `42c2df4` stands. Core is unchanged at `7f531958`.

## Added since `42c2df4` (scrapers main now `f6e615d42f64146f128ef2aa616996379b7a80d2`)
| Merge | What |
|---|---|
| #209 (OPEN-648, `12196b0c`) | Michigan stores the bills a fiscal agency analyses together as `related` links (never companion), labelled "House Fiscal Agency Analysis" / "Senate Fiscal Agency Analysis". About 2,270 links on 765 bills of 2025-2026, after the full run requested in `eb3e203`, whose gate 1 this image meets. No scorecard effect |
| #210 (OPEN-753, `9c3a9756`; from Onboard New States) | Idaho session dates from the legislature's Session Dates pages: 2026 becomes 01-12 to 04-02, plus 4 other sessions |
| #211 (OPEN-754, `f6e615d4`; from Onboard New States) | Rhode Island session dates from the House and Senate Journals for 11 sessions: 2026 becomes 01-06 to 06-11 |

* No migration and no new setting.
* **Wyoming's, Idaho's and Rhode Island's first scrapes wait on this image**, each on Ramon's go, requested by Onboard New States.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
