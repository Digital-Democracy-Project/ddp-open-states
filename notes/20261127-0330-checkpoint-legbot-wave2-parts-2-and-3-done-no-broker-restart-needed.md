# Checkpoint 11-27 03:30 UTC: LegBot wave 2 (RI, MO, ND; OPEN-910) Parts 2 and 3 DONE; no broker restart was needed; no LegBot run

Run at 03:16 to 03:26 UTC on Ramon's go, **without the broker `.env` edit and without any broker recreate** (your `251e47b0` correction).

## Part 2
* Fresh notes check, quiet checks (no RI, MO or ND lock; no LegBot write in the last 10 minutes; no hold in any note) all passed. The incoming `main` (`e0964d7a`) differed from my recorded `af88d018` **only by the six flag lines for `ri`, `mo` and `nd`** (checked key by key) **and a docs file (PRIMITIVES.md)**; **the Maine revert PR is not merged yet**, so Maine is unchanged (still live).
* Manifest rollout 03:17 UTC (dry run exit 0, then real): checkout file, api-v3 copy and the file inside the container all `19ede2dae2f467658d181608bb68ba6f`; api-v3 healthy; `/schedule` 35 jobs; core-pin drift exit 0; jurisdiction drift exit 0. **No ddp-sync restart** (ddp-sync still up since 11-26 16:26 UTC).
* api-v3 recreated by service name only, 03:17:29 to 03:17:39: healthy at 200 in 10 s, restarts 0.
* **Your enrolment print, from the broker's web container, which I did not restart (up since 11-26 23:37 UTC):** `manifest_codes("replica_routing")` and `replica_jurisdictions()` both print **AZ FL LA MI MO NC ND NE NM OR PA RI US UT VA WA WY (seventeen)**: **Missouri, North Dakota and Rhode Island are in it** without any restart, so **no broker restart was needed** for the manifest to take effect. The `.env` list is unchanged (the fourteen), so a drift warning for those three may log until it is tidied (cosmetic, optional).
* ddp-sync's own LegBot allowed codes (manifest-derived): **AZ FL LA MA MI MO NC ND NE NM OR PA RI US UT VA WA WY**: **RI, MO and ND are in it** (Massachusetts was already there).

## Part 3 (read-only)
* Bills through the broker: **Rhode Island 2026: 3,011; Missouri 2026: 3,161; North Dakota 69: 1,089** (all 200).
* LegBot gate on this host's ddp-sync, `dry_run: true`, `limit: 1`, one bare-UUID bill each (RI HB 7002, MO HB 10, ND HB 1001): **all three 200, no `jurisdiction_not_on_rds_replica_allowlist`**, 1 bill considered, `artifacts_generated` empty. (The ddp-sync log names these as `scraper_triggered_legbot_start/complete` with `dry_run=True`: that is only the wrapper's wording; nothing was dispatched.)

## Things you may notice, none caused by this
* **93 new artifacts for `US`, `ai_generated`, since about 03:10 UTC**: the United States' nightly run (03:00 UTC) triggers LegBot after its archive, as it does every night. Not wave 2.
* **Five web "Traceback" lines** in the last 12 minutes: all `Invalid HTTP_HOST header` for the host's public address, i.e. outside probes; nothing from this work.
* No nginx 5xx; broker containers healthy; no artifact for RI, MO or ND.

## Not done, and next
**No LegBot run and no 100-bill sample** (your separate go, one state at a time on the Mac). **The Mac host's manifest rollout is Ramon's step and is next**: LegBot's gate on the Mac reads that copy. After it and Ramon's go, I run the samples as for Oregon and Wyoming.
