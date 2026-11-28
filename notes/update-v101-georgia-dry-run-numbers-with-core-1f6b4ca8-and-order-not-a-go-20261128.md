# UPDATE (adds to my request `3ab2aa9` and my order note `06c9f77`; still NOT a GO): **the image core is now `1f6b4ca8` or newer (core #194, #195 and #196), and Georgia's dry run numbers change.** 2026-11-28 (Mac side, Onboard New States)

## What I need from you (changes)
1. **Read first (no write):** the core recorded in the image you launch must be `1f6b4ca8` (the merge of core #196, OPEN-959) **or a descendant**. Report the digest and the sha; stop if older. (Core `main` now holds #191 to #196.) Everything else in Part 1 of `3ab2aa9` stands.
2. **Georgia dry run (Part 3 of `3ab2aa9`), new expected lines:** `recompute-diff-order ga --dry-run` should read **`is_bill_version` changed = 60** (the 53 papers of OPEN-944 plus the **7** Senate floor-amendment fragments of OPEN-959: HB 295, HB 308, HB 1283, HB 54 "HB 54/SFA", SB 170, SB 220, SB 293), **comparisons nulled = 6, corrected = 6, `diff_baseline_id` changed = 12**. **If any number differs, stop and report; do not commit.** Please quote the latest paper of three bills in the dry-run's change list or from a read: **HB 54 should end on "SCSFA to HB 54"; SB 17 on "SFA to SB 17"; SB 131 on "SB 131/SFA"** (the last two are the enacted text and **stay versions**: the SFA papers of SB 17 and SB 131 replace the whole bill and must NOT be marked). No SCSFA paper (31 of them) may change.
3. **The order (unchanged, explicit):** (a) the image with core `1f6b4ca8` or newer is live (Parts 1 and 2 of `3ab2aa9`: rebuilds, pin check); (b) the PM and the reviewer tell you that ddp-open-states **#520** (Mississippi's `clean_ms_text`) is merged, once your note shows the image live; (c) the manifest rollout (pull first, then the script, dry run first); (d) the Mississippi recompute dry run, then a commit on Ramon's go. Georgia's and Kentucky's dry runs do not depend on the manifest rollout.
4. **Also merged since `3ab2aa9`, nothing for you to do yet:** ddp-open-states #518 (a connection probe line `PROBE <state>:` at the start of every cloud collection; it rides the image only after the manifest and scrapers copy it; the one Oklahoma and one Massachusetts run to read it is a separate request on Ramon's go), broker #874 (Maryland, migration 0142) and #875 (`validate_bill_stages --api-url`): they go with the broker release, not this note.

## Hold
The draft manifest pull requests **#521 (Nevada), #522 (Hawaii), #523 (Alabama), #524 (Idaho) stay UNMERGED**: any manifest rollout copies the whole of `main`'s manifest, so a merged draft would ride along. I will tell you in a note when any of them is cleared.

## Not authorized
As in `3ab2aa9` and `06c9f77`: any commit; any manifest rollout before the image is live; any scrape or re-import; any other state; `legbot_replica`; VoteBot's state list.

Tickets: OPEN-959, OPEN-944, OPEN-947, OPEN-946, OPEN-949, OPEN-950, OPEN-587; OPEN-146.

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
