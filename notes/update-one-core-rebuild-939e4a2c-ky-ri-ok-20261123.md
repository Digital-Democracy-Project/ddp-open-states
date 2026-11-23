# UPDATE (not a GO) to `22d7100` (KY), `98e5dcb` (RI) and `3cef331` (your rebuild plan): ONE core rebuild at **`939e4a2c`** covers Kentucky, Rhode Island and Oklahoma. Then the next scrapers image is built after it. 2026-11-23 (Mac side, Onboard New States)

**Not a GO.** Ramon's go and your plan in `3cef331` (rebuild after Oklahoma's archive) stand. Only the core commit changes.

## The core
* **Rebuild at `DDP_CORE_SHA=939e4a2c85cff8eef2446b2b8743ec14b73ce9ce`** (core main now), not `42b48982` or `40c36019`.
* Since `42b48982`, core main gained exactly two merges, and **no migration** (`git diff 42b48982 939e4a2c -- '*migrations*'` is empty):

| Merge | Ticket | What |
|---|---|---|
| #140 `40c36019` | OPEN-784 | Rhode Island: exact-name ranks for "As Amended" / "Substitute A" / "Substitute A As Amended" … so several substitutes order as printed. Changes 0 of the replica's other (state, name) pairs |
| #141 `939e4a2c` | OPEN-788 | Oklahoma: version stages and not-a-version papers (`openstates/ddp_states/ok.py`, `version_ordering.py`). A whole-replica comparison of all 29,086 (state, name) pairs changes 895 rows, **all Oklahoma** |

* Everything in `22d7100` (Kentucky, `42b48982`) is included.
* **The order is unchanged:** both api-v3 copies, then EC2 ddp-sync, all at `939e4a2c`. Then `check-core-pin-drift.py --image-core 939e4a2c…` exits 0 for each.
    * SYNC-186's `b569cf2` still rides the ddp-sync rebuild (`9825134`, `b8bb9d7`).
* **Loading in-flight runs on the old core is still safe.** #140 and #141 act on version ranks and the not-a-version flag (archive and recompute), not on how a load matches people. My `5ae8ab3` covers the rest.

## The image
* The next scrapers image must be **built after this core is on main**, which it already is, so that `DDP_CORE_COMMIT` is `939e4a2c`.
* Build at scrapers main **`2688a473` or later**. That holds Idaho #234 (OPEN-781), North Carolina #233 (OPEN-783), and Rhode Island #235 and #236 (OPEN-784/785).
* One image serves Idaho's step 2 (`7788700` / `9b4d8b9`) and Rhode Island's step 3 (`98e5dcb`). Build it after the manifest `ce2d4cc7`, which is already on ddp-open-states main.
* Mac side checks the scrapers tree contains `2688a473` and `DDP_CORE_COMMIT` is `939e4a2c`.

## After the rebuild (each its own GO, requests separate)
* **Kentucky:** `recompute-diff-order ky` dry run, then commit (`22d7100` step 4). Same expected numbers; #140 and #141 don't touch Kentucky's names.
* **Oklahoma:** `recompute-diff-order ok`, dry run first.
    * Measured on the Mac replica with `939e4a2c` (read-only session): `6005 bills checked | unchanged=7682 corrected=7261 nulled=2631`; `is_bill_version: set=0 changed=3272 not_a_version=3272`; `diff_baseline_id: set=3882 changed=3379 cleared=2631`.
    * I'll post its own request, with the commit gated on Ramon's go. Ramon still has an optional call on "Amended And Engrossed".
* **Rhode Island:** `98e5dcb` steps 2–5 unchanged; its step 1 is this rebuild.

## Not authorized
Anything beyond `3cef331`'s rebuild plan with this commit. In particular no recompute commit, no re-import, and no manifest change.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
