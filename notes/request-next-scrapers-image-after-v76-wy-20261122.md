# REQUEST (not a GO): the next scrapers image after v76, for OPEN-752 (Wyoming session types). Scrapers main is `e4f3a319`; core is unchanged at `7f531958`. 2026-11-22 (Mac side, State Specific Handling)

**Not a GO.** Ramon builds the image (one command, `deploy-scrapers-image.sh`). v76 (`ddp-scrapers:78` / `ddp-scrapers-db:5`) carries everything through #207 (`8cf0b939`), checked inside it by the PM session.

## What is new since v76 (scrapers main `e4f3a3191e9da906f7806c9c0d57e32673d26b40`)
| Merge | What |
|---|---|
| #208 (OPEN-752, `e4f3a319`; from Onboard New States) | Wyoming sessions mirror the legislature: 2012 becomes a regular session (the "2012 Budget Session"; marked special before, its ordinary bills would have been skipped); session names follow wyoleg.gov; eight end dates are corrected to the legislature's last legislative day; `wy` joins the session-type test |

* No migration and no new setting.
* **Wyoming's first scrape waits on this image**, and comes on Ramon's go, requested by Onboard New States.
* Later merges will be added to this request as UPDATE notes, as for v76.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
