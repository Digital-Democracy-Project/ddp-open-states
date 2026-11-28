# REQUEST (not a GO): **next scrapers image (core `6bc462ff` or newer): then api-v3 and ddp-sync rebuilds, and the dry runs for Georgia, Kentucky and Mississippi (OPEN-944, OPEN-947, OPEN-946, OPEN-949, OPEN-950).** 2026-11-28 (Mac side, Onboard New States)

Ramon gives each go in your session; nothing here runs without it. Ramon builds the image himself (the script prints the core and the task-definition revisions; the PM relays them). Part 2 and the later parts need that image to exist; Part 1 is a read.

## What I need from you
1. **Read first (no write):** the core recorded in the image you launch (`DDP_CORE_COMMIT`): it must be `6bc462ff5f5d80d85fbc76d8e7a5cfecd531bfba` or a descendant (core `main` after #195); report the digest and the sha; stop if older. Also report the scrapers files' md5 for `scrapers/nv/bills.py` and `scrapers/ia/bills.py` against scrapers `main` `7576e4685354b45323185e9bbb1c2b9d163c0342` (the #320 merge), which I take as `DDP_SCRAPERS_SHA` unless Ramon's build output names another commit.
2. **api-v3 on both hosts and ddp-sync on EC2** rebuilt at that core and scrapers commit, exactly as in my note `db0ef2b` (rollback tags, pin check naming all three, no cloud load running, narrow restart rule). The api-v3 pull request #81 (`dedupe_key` on vote events, OPEN-957) is NOT merged; this rebuild does not carry it.
3. **Dry runs only, in this order, paste exact lines, do not commit:**
   * **Georgia:** `recompute-diff-order ga --dry-run` (name the core commit). Expect `is_bill_version changed=53` (the 53 auditor's certifications, fiscal notes, actuarial investigations, "Local Ads" and "withdrawn" stubs of OPEN-944), `corrected 0`, `nulled 0`, `diff_baseline_id changed 0`. If the count differs, stop and report.
   * **Kentucky:** `os-text-extract relabel ky` dry run (OPEN-947: "enrolled, signed by" lines stop carrying `passage`; my replay predicts **480 lines** relabelled and only HB 642 losing "Passed both chambers", 214 to 213), then `os-text-extract refresh-extraction ky` dry run (OPEN-946 / core #193 changes Kentucky's comparison cleaner: my replay over the 854 stored comparisons predicts non-empty comparisons 483 to 460 and 23 becoming empty; report the exact lines and say which command changes the stored comparisons).
   * **Mississippi:** `os-text-extract refresh-extraction ms` dry run (OPEN-950, core #195: about **3,202** HTML documents change, none gains a character), then `recompute-diff-order ms --dry-run` (OPEN-949, core #194: the diff cleaner `clean_ms_text` changes the stored comparisons; the manifest's `quality.diff_cleaner` for Mississippi must read `clean_ms_text`, which is NOT yet in the manifest, so report what the recompute says and whether it needs that manifest change first).
4. After each, tell me; I check on the Mac replica and post `reply-verified` notes. Commits are separate parts that hold for go notes from Ramon, per state.

## What the changes are (plain)
| Ticket | Repo and merge | What it does |
|---|---|---|
| OPEN-944 | openstates-core #191 (`88d4b12b`) | Georgia: papers that are not bill versions (certifications, fiscal notes, actuarial investigations, ads, withdrawn stubs) are marked so, and a bill no longer shows one as its latest version |
| OPEN-947 | core #192 (`397cc94`) | Kentucky: signature lines no longer carry `passage` |
| OPEN-946 | core #193 (`f032bb9`) + manifest change ddp-open-states #515 (merged) | Kentucky: re-spaced duplicate words no longer show up as changes in comparisons |
| OPEN-949 | core #194 (`590a45c`) | Mississippi: drops stage lines, bare bill-number lines and "* * *" before comparing |
| OPEN-950 | core #195 (`6bc462f`) | Mississippi: removes struck-out words in the HTML copies |

Also in scrapers `main` (not in v100): Nevada's six upstream fixes (#312 to #317; **Nevada's events scrape becomes slower: a 60-per-minute limit, upstream saw about 11 to 50 minutes**, and fiscal notes appear for new loads), Iowa roll calls (#326, #327), Maine (#322, #323), Mississippi roll-call order (#319), Florida vote labels (#318), Oklahoma test fix (#320). Montana's #321 and #325 are not merged yet. Re-imports or rescrapes for any of those are separate requests.

## Not authorized
Any commit; any `--commit` recompute or refresh; a scrape or re-import; a manifest change; any other state; a restart beyond the rebuilds; `legbot_replica`; VoteBot's state list.

## What I check on the Mac side afterwards
Georgia: the 53 papers read `is_bill_version=false`, none has a comparison, no bill's latest version is one of them. Kentucky: 480 signature lines no longer `passage`, comparisons as predicted, no real word change lost. Mississippi: struck words gone from the HTML copies, HTML no more than 5% longer than the PDF twin (628 to 27 predicted), the cleaner's effect on stored comparisons. Then the dev LegBot re-samples.

Tickets: OPEN-944, OPEN-947, OPEN-946, OPEN-949, OPEN-950, OPEN-587, OPEN-667, OPEN-669; OPEN-146.

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
