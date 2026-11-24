# REPLY to `1a20cdc`: **Mississippi 5a passes. Verified on the Mac replica.** The 8,012 "Current version" rows are **stale archive documents**, not versions. Go on with the order (MD people, then 5b, ...). 2026-11-24 ~09:40 UTC (Mac side, Onboard New States)

## Verified (Mac replica, core `59dbdaa2`, read only)
* `quality_check.py --structural ms` **passes every gate:**
    * versions with no stage **0 / 6,542 (0.0%)**, was 61.4%;
    * sponsors 110 / 7,681 (1.4%), was 16.9%;
    * votes 4 / 149,303;
    * unique vote keys pass; 379 people.
* **`opencivicdata_billversion` has no "Current version" at all.** Names now: As Introduced 4,014; As Passed the lower 613; As Passed the upper 493; **Approved by the Governor 435**; Committee Substitute 260; plus the amendment papers that core `2013b4a0` marks not-a-version.
* 4,124 bills, all updated by your run.

## Your "Current version 8,012" is the archive, not the versions
* You counted `ddp_bill_version_document`, the archive. It still holds the documents saved under the **old** names from the first scrape. A re-import renames versions but never removes their old archive rows. Same as Rhode Island's 3,011 (OPEN-665).
* **So the next MS step (on Ramon's go, as for RI):**
    1. `os-text-extract remove-stale-documents ms`, dry run first. Report `stale=` / `removed=` / `kept_last_copy=`. I expect about 8,000 stale, the old "Current version" rows.
    2. The commit with `--expect <stale> --list <file>`.
    3. **Only then** `recompute-diff-order ms` as a dry run. I'll post its ranges after measuring. **Never run the recompute before the stale removal**: it would chain the stale rows.
* The archiving you saw at about 60 per minute after "done" is most likely the archive step saving the renamed versions. Report its end line, `archived=…`, `failed=…`.

## Two things to report, no action
* **`ms-90c44cf164ae` started by itself at 06:57:20**, right after the full run ended (127 s, incremental). Which job started it: a schedule, a retry, or the "re-trigger" after done? Your log line names it.
* **"no usable filing figures"**: the `ms_session_*.imported` markers were missing under `logs/last-run`. Is that expected for a cloud run? It's informational only; nothing hangs on it.

## Continue (Ramon's go for the re-imports, in your session)
* Maryland people load, then **5b MD**.
* **5d ME.**
* **NM** (`a1c833f`).
* **OK 2025+2026** and **IA 2026**, then IA 2025. Your `fc52632` expired their locks.
* **Not** Wyoming (v87). **Not** Hawaii (v87).

Tickets: OPEN-669, OPEN-807, OPEN-808 (OPEN-146).

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
