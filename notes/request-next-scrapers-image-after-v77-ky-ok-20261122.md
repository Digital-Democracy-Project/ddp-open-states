# REQUEST (not a GO): the next scrapers image after v77, for OPEN-760 (Kentucky, Montana and Iowa vote keys) and OPEN-758 (Oklahoma bills by filing year). Scrapers main is `6176a590`; core is unchanged at `7f531958`. 2026-11-22 (Mac side, State Specific Handling)

**Not a GO.** Ramon builds the image (`deploy-scrapers-image.sh`). v77 holds scrapers `d657f665` exactly (checked in `8fe3207`).

## What is new since v77 (scrapers main `6176a59093456778bfbbc09b67bef6696108daab`; both from Onboard New States)
| Merge | What |
|---|---|
| #216 (OPEN-760, `6176a590`) | Kentucky, Montana and Iowa votes get a `dedupe_key` from the source's own roll-call identity, the same fix as ND's OPEN-757. **Kentucky's first scrape waits on this image**; after it, only Ramon's go (request on ddp-sync, `30ae9df`) |
| #214 (OPEN-758, `32315f43`) | Oklahoma: each bill is filed under the yearly session of its first action, and each roll call under its own date; 2025 and 2026 are both active. **Ramon accepted the run being about 1.75 h longer** |

* No migration and no new setting.
* Later merges are added as UPDATE notes. Expected: #215 (OPEN-756), OPEN-759, and OPEN-765 (North Carolina's 2025 end date, being built here).

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
