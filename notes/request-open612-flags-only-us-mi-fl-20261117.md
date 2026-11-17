# REQUEST (waits on Ramon's go): give US Congress, Michigan and Florida's archived documents their missing bill-version flag (OPEN-612). 2026-11-17 (Mac side)

**Not a GO yet.** Nothing here runs until Ramon says go and a GO note follows. No image, no deploy, no new code: the command is in the live scrapers image (`recompute-diff-order --flags-only`: OPEN-492 `249ed268` and OPEN-498 `6aed98cc` are both in v62's core `44c3b8dc`, checked).

## Why
* The archiver stores, on each saved document, whether it is a real bill version (`ddp_bill_version_document.is_bill_version`, OPEN-492, 2026-11-04).
* Documents saved before 2026-11-04 get the flag only when their state's comparisons are rebuilt. Since then, US Congress, Michigan and Florida have had only the 11-16 `--baseline-only` pass, which leaves this flag alone by design. So their older documents have no flag.
* api-v3 treats "no flag" as "not full text" for a version core cannot place by name. So the website and the broker skip the newest text of bills such as US SRES 866 ("Agreed to Senate"), US HR 7730 ("Received in Senate") and Michigan HR 10 ("House Adopted Resolution").
* Ramon, 2026-11-17: "File a ticket to check them" (OPEN-612).

## Measured on the Mac replica of production (read only, 2026-11-17)
Archived documents with no flag (all of them saved between 07-26 and 11-04):

| State | No flag | All documents | Errors among the no-flag | Versions core cannot place |
|---|---|---|---|---|
| us | 92,768 | 93,137 | 0 | 2,420 ("Agreed to Senate" 2,018, "Received in Senate" 296, ...) |
| mi | 14,458 | 14,624 | 174 | 910 ("House Adopted Resolution" 568, "Senate Adopted Resolution" 270, ...) |
| fl | 20,072 | 20,072 | 2 | 0 |

None of the three states has a "not a bill version" rule in core, so every one of these documents should come out **True**. Only the "cannot place" ones change what api-v3 serves; Florida changes nothing visible, but is done too so no document is left undecided.

## Steps (prod agent, after Ramon's GO)
Same host and tool as the 11-16 baseline passes. One state at a time, in this order: fl, mi, us. Nothing is scraped for these states at the same time (US scrapes nightly at 03:00 UTC, MI and FL Sundays 02:00).

1. For each state, the dry run:
   `os-text-extract recompute-diff-order <st> --flags-only`
   **Gate:** the flag summary shows `set` = the state's "No flag" number above (or its count at run time, if a scrape archived more since; say which), `changed` = 0, `not a version` = 0; and "diffs untouched (--flags-only)".
   (`--expect` works only with `--baseline-only`; the dry run is the count guard, as on 11-17.)
2. If the gate holds: the same command with `--commit`, then a second dry run that must show `set` = 0.
3. Report per state: the dry-run summary line, the commit line, the second dry run.

## After (Mac side; prod agent: nothing more)
* Re-count on the Mac replica: documents with no flag = 0 for us, mi, fl (or each remainder named).
* Spot check, before and after, on the Mac api-v3 (before read 2026-11-17: each version below is `is_bill_version=None`, `is_full_text=False`):
  * US SRES 866 "Agreed to Senate" (2026-09-30), US SRES 662 "Agreed to Senate" (2026-09-29), US HR 7730 "Received in Senate" (2026-09-17);
  * MI HR 10 "House Adopted Resolution", MI SR 61 "Senate Adopted Resolution".
  Expected after: `is_bill_version=True`, `is_full_text=True`.
* The broker keeps each bill's latest version from api-v3 (BROKER-489). Bills whose latest text changes need its version-order refresh, as after OPEN-593; that is a separate broker step on Ramon's go, and its count is BROKER-515's kind of report.

## Not authorized
Anything but the three `--flags-only` runs: no comparison rebuild, no `--baseline-only`, no other state, no scrape, no broker or api-v3 change.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
