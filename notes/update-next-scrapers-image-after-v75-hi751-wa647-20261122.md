# UPDATE to `5bcc4a4` (the next scrapers image after v75): it now also carries OPEN-751 (Hawaii special-session bills) and OPEN-647 (Washington companion links). Scrapers main is `8cf0b939`. 2026-11-22 (Mac side, State Specific Handling)

**Not a GO.** Everything in `d4fa3f5`, `abe29b8`, `1cde28e`, `bf9994e` and `5bcc4a4` stands. Core is unchanged at `7f531958`.

## Added since `5bcc4a4` (scrapers main now `8cf0b939`)
| Merge | What |
|---|---|
| #206 (OPEN-751, `e6b61a04`; from Onboard New States) | Hawaii: the four special sessions where both chambers sat (2013 2SS, 2016 2SS, 2017 1SS, 2021 1SS) collect their own 56 bills and resolutions from data.capitol.hawaii.gov PDFs and journals, with 17 roll calls. The new code is `scrapers/hi/special_measures.py`. Hawaii stays at probing, and those sessions stay switched off until a backfill |
| #207 (OPEN-647, `8cf0b939`) | Washington stores the companion bill the legislature lists, as `companion`, label "Companion bill" (about 1,168 links in 2025-26). No new download. New links appear only after the Washington re-import in `f179ccc`, whose gate 1 this image meets |

No migration and no new setting.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
