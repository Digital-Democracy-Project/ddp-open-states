# REQUEST 2 of 3 (not a GO): OPEN-685, roll-call numbers on stored Nebraska, Louisiana and New Mexico votes (`backfill-vote-rollcall-num.py`, ddp-open-states #435)

Written 2026-11-20 (Mac side, State Specific Handling). **Not a GO.** Each write waits for Ramon's go in your session.
- Comes after **request 1** (the image), so new votes already carry the number and this run only covers what is already stored.
- Comes before **request 3** (the broker release).

## What it writes
Into each stored vote's `extras`: the number the scrapers now write.

| State | Key | Value | Read from |
|---|---|---|---|
| Nebraska | `legislature-rollcall-num` | the KeyID | the vote's dedupe key |
| Louisiana | `house-` / `senate-rollcall-num` | `(#N)` | the end of the motion text |
| New Mexico | `house-` / `senate-rollcall-num` | the PDF's `RCS#` | the Mac-built list |

- **Guarded.** It writes only a vote with no roll-call key at all, never changes a stored number, never touches `updated_at`, and is all or nothing per run with `--expect`.
- **The tool:** `/opt/ddp-open-states` at `a6be426` or later (it contains #435), run the way `c7be369` part B2 ran the same tool (OPEN-628).

## Dry run on the Mac replica (2026-11-20)
**Nebraska 1,772. Louisiana 3,172** (House 1,624, Senate 1,548). **New Mexico 2.**
- New Mexico: only HB 253's two Senate votes share a bill, chamber and day, so only their PDFs were read. A vote alone on its day needs no order.
- Production will show a few more for NE and LA: votes stored since, by runs before the new image.

## Per state (stop at any step that does not match)
**Nebraska:**
1. `python3 backfill-vote-rollcall-num.py --dry-run --jurisdiction ne --list <lasting path>/open685-ne-dry.csv`. Expect **1,772 or a few more**, and **0 "number not readable"**.
2. `--apply-list <lasting path>/open685-ne-dry.csv --expect <that count> --list <lasting path>/open685-ne-committed.csv`
3. A second `--dry-run --jurisdiction ne` reports **0 to write**.

**Louisiana:** the same three steps with `--jurisdiction la`. Expect **3,172 or a few more** and 0 unreadable.

**New Mexico** (production has no PDF text, so apply the list built on the Mac, as given):
- **The list:** `notes/open685-nm-vote-rollcall-num-list-20261120.csv` on this branch, **md5 `0b0168c0381010c46ae15e5f4497888a`**, 2 rows: HB 253 Senate, RCS 158 and 173.
- **Steps:**
  1. `--dry-run --jurisdiction nm` with no `--nm-votes`. Expect **0 to write** and 259 or more unreadable: the read-only check that nothing is numbered yet.
  2. `--apply-list notes/open685-nm-vote-rollcall-num-list-20261120.csv --expect 2 --list <lasting path>/open685-nm-committed.csv`
- **Do not rebuild this list on the host.**

**Rollback (only if Ramon asks), per state:** `--undo <that state's committed list> --expect <its count> --list <lasting path>/open685-<st>-undone.csv`.

**Report:** each state's dry-run counts, its applied count, and the second dry run's 0.

## Not in this request
- OPEN-628's own backfill for WA, MI, VA and AZ (`c7be369` part B2, 12,851 votes). It is still not run: the replica shows no keys for WA, VA or AZ.
- **Before Washington's change list takes effect, B2 must run.** That is 21 earlier same-day WA votes stopping, with no scorecard change; details on OPEN-685, Jira comment 21803. The order between this request and B2 does not matter: different states, the same guarded tool.
- Any broker change (request 3).

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
