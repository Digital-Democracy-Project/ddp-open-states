# UPDATE (corrects my `3ab2aa9`, `06c9f77` and `dd2da9c`; still NOT a GO): **v101 is built. The exact numbers, and the order.** 2026-11-28 (Mac side, Onboard New States)

Numbers from Ramon's build output (relayed by the PM) and my read-only look at the image on the test Docker VM (a throwaway container that only read files and was removed; nothing else touched):
* **Tag `v101`, digest `sha256:93c79600478863bcb44783d3e21f5c7fdf7f40ce8098a018faa0dd7f4ca3b7a7`, task definitions `ddp-scrapers:103` and `ddp-scrapers-db:30`** (new tasks launch v101 from now on; previous image v100).
* **Core in the image: `1f6b4ca86e0ad780e259bc6495f2a77549d59eae`** (read from the image's own `DDP_CORE_COMMIT`). It is the openstates-core #196 merge, checked with git on the fork: it contains #196's head `218e7726` and #195's `6bc462ff`, so it carries #191 to #196.
* **Scrapers commit: `cb8aef70d291fa24d622fca42b597cdeac001fd5`** (scrapers `main`, the #325 merge). The image prints no scrapers commit; I confirmed it by md5 of three files in the image against that commit: `scrapers/mt/bills.py` `02c05fda3692e63797ffebc2a56fd0f0`, `scrapers/ia/bills.py` `e82bfc77f76f1e4fd00dffdd9c2c1373`, `scrapers/nv/bills.py` `7ad26489389c2e0a6ba8f80d0c421ffd`: all three equal the files at that commit. It carries scrapers #312 to #323 and #325 to #327 (Nevada, Maine, Iowa, Mississippi, Montana, Florida labels, Oklahoma test fix). **Not in it: scrapers #328 (Maryland, OPEN-954, still in review).**

## What I need from you
1. **Read first:** the image you launch reports core `1f6b4ca86e0a...` exactly (`DDP_CORE_COMMIT`) and digest `93c79600...`; stop if not.
2. **api-v3 on both hosts and ddp-sync on EC2** rebuilt with `DDP_CORE_SHA=1f6b4ca86e0ad780e259bc6495f2a77549d59eae` and `DDP_SCRAPERS_SHA=cb8aef70d291fa24d622fca42b597cdeac001fd5`, exactly as in my note `db0ef2b` (rollback tags `pre-v101`, no cloud load running, the pin check naming all three, narrow restart rule). The Mac host's api-v3 refresh is Ramon's step. api-v3 pull request #81 (the vote key, OPEN-957) is not merged and is not in this rebuild.
3. **Dry runs (not commits), then the order:** (a) the dry runs of `3ab2aa9` Part 3 with the corrected Georgia numbers of `dd2da9c` (is_bill_version changed=60, nulled 6, corrected 6, diff_baseline_id 12) and the Kentucky and Mississippi dry runs; (b) **then** ddp-open-states #520 is merged (I tell you; it is held until your note shows v101 live); (c) the manifest rollout (pull first, then the script, dry run first); (d) the Mississippi recompute dry run with the cleaner, then commits only on Ramon's go. The held draft manifest pull requests #521 to #524 stay unmerged.
4. The connection probe (OPEN-887, ddp-open-states #518, merged): its `PROBE <state>:` line starts to print once the manifest and scrapers copy on the host carry it; the one Oklahoma and one Massachusetts run to read it is a separate request on Ramon's go.

## Not authorized
Any commit; a scrape or re-import; a manifest rollout before steps 1 and 2; any other state; `legbot_replica`; VoteBot's state list.

Tickets: OPEN-959, OPEN-944, OPEN-947, OPEN-946, OPEN-949, OPEN-950, OPEN-887; SYNC-180, SYNC-188; OPEN-146.

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
