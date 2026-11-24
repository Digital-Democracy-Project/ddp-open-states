# UPDATE (not a GO): ONE release order for v85, replacing the order in `de80ea4`, `a92378e` and `f5ffdd4` and adding Maryland. Core `eb197d74` everywhere, then v85 (Ramon is building it now: scrapers `928138b2`, core `eb197d74`), the Utah canary, then the re-imports one at a time, each with its Stage 3 check. 2026-11-24 ~03:10 UTC (Mac side, Onboard New States)

**Not a GO.** Each numbered step waits on Ramon's go in your session. Recompute **commits** each wait on a second go after he has seen the dry-run numbers. The pass/fail lines, gates and "Not authorized" lists in the earlier notes still apply where this note points to them.

Ramon, 02:46 UTC (relayed by the PM session): "let's get all the states unblocked". He started the v85 build himself.

## What v85 carries (scrapers `928138b2`, core `eb197d74`)
| State | Fix | Ticket |
|---|---|---|
| HI | version names by stage; sponsors (initials, Office of the Governor) | OPEN-804, OPEN-805 |
| HI (core) | sponsors of carried-over bills matched by introduction date (Aquino, Ward) | OPEN-809 |
| MS | stage names kept; amendment papers not-a-version (core); sponsors by name and chamber | OPEN-807, OPEN-808 |
| MO (core) | amendment papers not-a-version; Perfected / Truly Agreed stages | OPEN-806 |
| ME | the bill's own LD paper named "Introduced" | OPEN-811 |
| MD | versions named by reader; Impact Note becomes a document; Speaker / President from the manifest | OPEN-813, OPEN-814, OPEN-815 |
| MA | the Speaker comes from the manifest only (output unchanged) | OPEN-810 |
| all | every request goes through core's certificate-checked session | OPEN-800, OPEN-803 |

* **People data** (people main **`05d7e4cc`**): ME (#48, OPEN-812) and MD (#49, OPEN-816).
* **Manifest:** ddp-open-states main **`1109edf`** has MD's officers (#479). The image clones ddp-open-states main at build time, so v85 carries it.
* **Not in this release:** OPEN-817 (core #148, votes dated after a session's end; in review). It needs a later core rollout and a new image. Without it, only MD's 2 "Harlan" votes stay blank.

## Step 1: core `eb197d74` (`f5ffdd4`, unchanged)
* EC2 api-v3, EC2 ddp-sync and the Mac api-v3, all at `eb197d7407253550912fc8ba9f9b0aa0c9da127f`.
* ddp-sync stays at `85c8888` with the new `DDP_CORE_SHA`, as you said in `208ee45`.
* Your own windows apply:
    * after 04:45 UTC;
    * not while any run is loading;
    * api-v3 not 05:00–07:00 UTC.
* Then `check-core-pin-drift.py --image-core eb197d74…` exits 0.

## Step 2: v85 (Ramon)
* When his build reports its revision, check:
    * `DDP_CORE_COMMIT` is `eb197d74`;
    * the image's scrapers contain `928138b2`.
* I'll confirm both from the Mac.
* **Then ddp-sync's SYNC-188 rebuild** (ddp-sync `132d8cf`): `8653f08` with `DDP_SCRAPERS_SHA=928138b2e94310b2d92a6040028669755a5a271d`, core `eb197d74`. On its own go; it may share step 1's restart if v85 exists by then.

## Step 3: the Utah canary (`3e6c766` step 3)
* `ut` once, on v85, before anything else on v85.
* A certificate error stops everything below.

## Step 4: people (one pull covers both; any time after step 1)
1. Pull `/opt/ddp-open-states/people` to **`05d7e4cc`** or later. Since `d1acd229`, only #48 (17 ME files) and #49 (MD: Alexander Harlan merged into Alex Harlan) changed.
2. `os-people` with `--safe` first, then real, **one state at a time**:
    * **ME:** created 0, updated 17;
    * **MD:** only Harlan's files change; report the exact lines.
3. Anything else: stop and report.

## Step 5: re-imports on v85, one heavy load at a time, in this order
Each one is a full re-import: `POST /ddp-sync/v1/trigger/openstates-scrape/<st>?full=true&sessions=…`. The answer must be 202 with `"full": true`. Report:
* the run id and revision;
* the counts per session;
* the archive result.

After each, **I run Stage 3 on the Mac replica and post "verified" or a stop.** Don't start the next state until my note, unless Ramon says to keep going.

| # | State | Sessions | Why this order | Pass/fail after (Stage 3 at core `eb197d74`, plus the request's own SQL) |
|---|---|---|---|---|
| 5a | **MS** | `2026,20261E` | smallest (4,124 bills) | versions without a stage about 0% (was 61.4%); sponsors about 1.4% (was 16.9%); no "Current version" (`de80ea4`) |
| 5b | **MD** | `2026,2026s1` | after step 4's MD people | versions about 0% (was 74.8%); unmatched votes 2,733 → **2** (the 2 Harlan votes, until OPEN-817); no "Racial Equity Impact Note" versions; "Speaker" and "Mr. President" linked |
| 5c | **HI** | `2026` | 6,728 bills | versions about 0.01% (was 100%); sponsors: Aquino / WARD / Ward unmatched **0** (SQL in `f5ffdd4`); total unmatched about 0 (was 6.5%) |
| 5d | **ME** | `132R1,132R2,132S1` | biggest (148k votes); after step 4's ME people | `a92378e` M3: unmatched votes 0 (was 13,001); every "TERRY of Gorham" vote on Parnell Terry; 0 paper-number names (was 2,368) |
| 5e | **OK** | as in `8108de3` (2026 at least) | **only after its orphan import lock clears, about 23:03 UTC 11-24** | `8108de3`'s lines: Hader 0, "Mr. Speaker" → Hilbert, about 44 unmatched |
| 5f | **IA** | `2025`, then `2026` as needed | **only after its lock clears, about 23:50 UTC 11-24** | `aa0bf45` / `12be6e8` |

* **MD, after its re-import and archive:** `os-text-extract remove-stale-documents md`.
    * Dry run first if the command has one; report the count.
    * **No deletion of the old Impact Note archive rows** (Ramon: leave them).
* Other states the onboarding runs now under way find a need for get **one** short addendum to this note, not a new order.

## Step 6: recomputes, dry runs only (after step 1; each after its state's re-import is verified)
| State | When | Expect |
|---|---|---|
| **MO** | any time after step 1 | `not_a_version` 700–800, `corrected` 420–510 (`c639029`; still true at `eb197d74`) |
| **MS** | after 5a verified | I post ranges after measuring the re-imported data |
| **MD** | after 5b and the stale-document step | I post ranges after measuring |
| **HI** | after 5c verified | report only |
| **OK** | after 5e verified | I post ranges first (`fe2bb48`) |
| **KY** | dry run already done (`73344ed`: corrected 811, set 652, all in range) | **the commit waits only on Ramon's second go** |

No commit for any state without Ramon's second go after he has seen that state's numbers.

## Step 7: go-live (not in this note)
For each state that passes after its re-import, I'll:
* open the go-live manifest PR (`status: live`, routing) and the matching requests;
* list them for Ramon.

Nothing goes live from this note.

## Not authorized
* Any step before its go.
* Any recompute commit.
* A second re-import of any state.
* Two heavy loads at once.
* Deleting any lock or Redis key.
* Any manifest, schedule, routing or LegBot change.
* Any certificate exception or setting.
* Any state not listed.

Tickets: OPEN-146; OPEN-668 (HI), OPEN-669 (MS), OPEN-671 (MO), OPEN-672 (ME), OPEN-674 (MD), OK and IA go-live tickets; OPEN-800, OPEN-803, SYNC-188.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
