# UPDATE (NOT A GO; replaces my v101 notes `a4ed7d5` and `73ae55f` and my options note `fcf1987`): **v102 is built. ONE rebuild of api-v3 (both hosts) and ddp-sync (EC2) on it. What is live, what to rebuild, the checks, the rollback.** 2026-11-28 (Mac side, Onboard New States)

Ramon chose **option A** of `fcf1987` (build v102 first, then one rebuild). He gives each go in the prod agent's session, naming the full SHAs. **This note is not a go for anything.** Where this note and the three it replaces differ, this one wins; the manifest-rollout order of `6d6928d` and the Mississippi order of `06c9f77` still stand (see Part 5).

## What is live and what is built
* **Live in production (your notes, not mine):** scrapers image v100 (core `0ade8816`), since 23:34 UTC 11-27. v101 was built but is superseded; do not roll it out.
* **Built, from Ramon's `deploy-scrapers-image.sh` output (relayed by the PM; I cannot read the image or the task definitions myself): tag `v102`, digest `sha256:ae31b0267cc8f52b078268d1887768339f731025acc1e78c32df013657e291f7`, task definitions `ddp-scrapers:104` and `ddp-scrapers-db:31`, core `1ffc3f5402dfed161e27bdd013ba37939a93b658`.** The build's own checks passed (imports, one-bill Utah smoke test exit 0). Not verified by a prod note yet.
* **Scrapers commit: `d695c16a4fcea7c0e8ff4696bf0273c82244922b`** (scrapers `main`, the #329 Maine merge; it contains #328 Maryland `8d233f1b`). I read that from git on the fork, not from the image: the image prints no scrapers commit. **Please confirm it from the launched image** by md5 of two files that differ from v101: `scrapers/me/bills.py` must be `944495a3d3ccee8356a912d0db963f8f` and `scrapers/md/bills.py` must be `663c82025c734667888d832fc8969afd` (the md5 of those files at `d695c16a`, computed on the Mac from git). If either differs, stop and tell me the sha you find; do not pick one.

## What I need from you
1. **Read first (no write):** the image the pipeline launches reports core `1ffc3f5402dfed161e27bdd013ba37939a93b658` exactly (`DDP_CORE_COMMIT`) and digest `ae31b026...`; and the two md5s above. Stop if any differs.
2. **ONE rebuild, api-v3 on both hosts and ddp-sync on EC2**, with `DDP_CORE_SHA=1ffc3f5402dfed161e27bdd013ba37939a93b658` and `DDP_SCRAPERS_SHA=d695c16a4fcea7c0e8ff4696bf0273c82244922b` (once confirmed in 1), in the form and under the gates of my note `db0ef2b` Parts 1 to 5 (no cloud load or pipeline lock, no ddp-sync job in the last 10 to 12 minutes, avoid Sunday from 02:00 UTC and each nightly start, "now" recorded as the restore point; `api` and `ddp-sync` recreated only; the build imports the app before it finishes). **Pennsylvania's nightly run holds its lock until it finishes** (your note of 04:15 UTC): start only after it is clear. The api-v3 build is from api-v3 `main`, which includes pull request #81 (`c89d3ef1`, vote events expose `dedupe_key`). The Mac host's api-v3 refresh is Ramon's step.
3. **The core-pin drift check**, all three named: `python3 check-core-pin-drift.py --image-core 1ffc3f5402dfed161e27bdd013ba37939a93b658 --container <api-v3 container> --sync-container ddp-sync-ddp-sync-1`. **It fails until api-v3 is rebuilt; that is expected before step 2.** After step 2 expect exit 0 and ddp-sync's scrapers commit printed. Paste every line; also report both containers healthy, `/schedule` unchanged, 0 errors in the first minutes of ddp-sync's log.
4. **One read-only confirmation after the rebuild:** replay Kentucky bills `SB 197`, `HB 56` and `SJR 134` (session 2026RS) through api-v3 with `include=votes` and quote each vote event's `dedupe_key`. Expected: all non-empty. If any has none, say so and change nothing. (This replaces Part 2 of `73ae55f`.)

## Part 5. The order after the rebuild (replaces `a4ed7d5` Part 3; each step is a dry run and commits hold for their own go notes)
(a) The dry runs of `3ab2aa9` Part 3 with the corrected Georgia numbers of `dd2da9c` (`is_bill_version` changed 60, nulled 6, corrected 6, `diff_baseline_id` changed 12) and the Kentucky and Mississippi dry runs, now on v102 (same core as v101 plus #197). (b) Iowa `recompute-diff-order ia --dry-run`: expect what `fcf1987` says (`is_bill_version` changed 1,003, 1,608 comparison changes, about 1,004 non-empty comparisons, no non-Iowa change). (c) Then ddp-open-states #520 is merged (I tell you; it is held until your note shows v102 live), then the manifest rollout (pull first, then the script, dry run first; it also turns Maine live, see `6d6928d`), then the Mississippi recompute dry run with the cleaner. The held draft manifest pull requests #521 to #524 stay unmerged. Maryland (#328) and Maine (#329) scraper fixes reach the data only with a rescrape or re-import on v102, each on its own go.

## Rollback
* api-v3: tag the running image `pre-v102` before building, then retag it as the running tag and recreate `api` only. ddp-sync: same with `ddp-sync:pre-<its sha>`, recreate `ddp-sync` only (as `db0ef2b` Part 5).
* Rolling back the rebuild does not undo a stored recompute; none is part of this note.
* Scrapers image: deregister revisions 104 and 31 and keep v100's (102 and 29) (Ramon's step, per the build output).

## Not authorized
Any commit; a scrape or re-import; a manifest rollout before steps 1 to 3; any other state; `legbot_replica`; VoteBot's state list; merging #520 or #521 to #524.

Tickets: OPEN-146, OPEN-672, OPEN-673, OPEN-674, OPEN-667, OPEN-587, OPEN-669, OPEN-962, OPEN-954, OPEN-850, OPEN-957, OPEN-958, OPEN-913; SYNC-180, SYNC-188.

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
