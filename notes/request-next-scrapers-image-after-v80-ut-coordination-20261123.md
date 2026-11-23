# REQUEST (not a GO): the next scrapers image after v80 (v81), for OPEN-775 (Utah's coordination-clause links). Scrapers main is `414311c6`; core is unchanged at `42b48982`. 2026-11-23 (Mac side, State Specific Handling)

**Not a GO.** Ramon builds the image (`deploy-scrapers-image.sh`).
* v80 (ddp-scrapers:82, db:9, core `42b48982`) holds scrapers `5a52ad72`, per the PM session's check.
* This request does not change v80's release steps (`fd0419f`, `2a19865`) or the Arizona re-import (`753a793`).

## What is new since v80 (scrapers main `414311c60c1f87facec698393fe2f9f77b34c2e7`)
| Merge | What |
|---|---|
| #229 (OPEN-775, `414311c6`; this session) | Utah stores each bill named in a bill summary's "coordination clause" as a `related` link (never `companion`), labelled "coordination clause". Ramon decided this on 2026-11-23 ("Store as related", OPEN-650). |

* **No migration and no new setting.** Core is unchanged, so there is no api-v3 or ddp-sync step.
* **No scorecard change:** the broker follows only `companion` links.
* **The links appear only on Utah bills scraped after this image.** Utah 2026 needs the separate re-import request (`request-open775-utah-reimport-2026-20261123.md`).

## After the build
* **Mac side** checks the image's scrapers commit is `414311c6` or later, and that `DDP_CORE_COMMIT` is `42b48982`.
* **Prod side:** please report the image tag and task-definition revisions.

Tickets: OPEN-775, OPEN-650. Plan: PLAN-companion-lineage §5.3.1.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
