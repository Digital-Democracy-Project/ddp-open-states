# UPDATE to `ca7d744` (the next scrapers image after v76): it now also carries OPEN-757 (North Dakota vote key, **deadline**) and OPEN-755 (Oklahoma session dates). Scrapers main is `d657f665`. 2026-11-22 (Mac side, State Specific Handling)

**Not a GO.** Everything in `42c2df4` and `ca7d744` stands. Core is unchanged at `7f531958`.

## Deadline: North Dakota
**The image must be built and registered before Sun 11-29 02:00 UTC, North Dakota's weekly run.**
* ND's first scrape failed at the RDS load: two Senate roll calls on HB 1015 in the same minute collided, and nothing was written.
* ND stays at `scraping` (Ramon: "stay on, fix by Sunday"). Without #213 its weekly run fails the same way.
* **If the image was already built at `f6e615d4`** (Ramon's "build now" on `ca7d744`), it lacks #213: one more build at `d657f665` or later is needed before that run.

## Added since `ca7d744` (scrapers main now `d657f665718ffbc1798baf698dc7340091ae2db6`; both from Onboard New States)
| Merge | What |
|---|---|
| #213 (OPEN-757, `d657f665`) | North Dakota votes get a `dedupe_key`: the page URL plus ndlegis.gov's roll-call id, so two same-minute roll calls no longer collide |
| #212 (OPEN-755, `c3a9183a`) | Oklahoma: 19 sessions' dates corrected from the journals, under Ramon's 11-22 date rules |

* No migration and no new setting.
* OPEN-756 (RI 2021 end, WY sine die) and OPEN-758 (OK bills by filing year) are still being built. **Do not hold the image for them;** ND's deadline comes first.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
