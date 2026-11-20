# REQUEST (not a GO): Nebraska's stored action relabel (`os-text-extract relabel ne`, OPEN-550) for its go-live; the dry run now, the commit on Ramon's go. 2026-11-20 (Mac side, Onboard New States)

**Why:**
* Ramon waived Nebraska's soak (2026-11-20: "let's waive the soak period and not wait for sunday ...").
* One of its remaining go-live steps is the relabel of stored history that OPEN-550 set for go-live, under the scorecard gate.
* Nebraska's rule (core `openstates/ddp_states/ne.py`) stops "President/Speaker signed" and "Passed over" lines counting as passage.
* New imports already apply it, but stored rows don't change until this runs.

**Measured on the Mac replica today, core `10f32ce0`** (the live core; scrapers v72):
* `os-text-extract relabel ne --dry-run`
* → **actions changed=650 unchanged=17558, all `passage -> (none)`; bills changed=0;** latest_passage_date would change on **300** bills.
* That matches OPEN-550's measurement exactly.

## What I need from you
1. **Now (read-only, no go needed):**
   * Run the same dry run on production with core `10f32ce0`: the scrapers image's core, as for the NM recompute.
   * Prove the rule is present first (`openstates/ddp_states/ne.py` exists in that core).
   * `os-text-extract relabel ne --dry-run --list <file>`.
   * Report the counts and the list's md5. **Expected: 650 / 0 / 300.** Anything else: stop and report.
2. **Commit: holds until a GO note** (Ramon's go for Nebraska's go-live). Then:
   * **Gate:** nothing is running for `ne`.
   * `os-text-extract relabel ne --commit --expect 650 --list <committed file>`.
   * Report the counts.
   * Afterwards, the broker reads the corrected history on its next sync. The committed list is the undo record.

## Not authorized
`--commit` before the GO; any other state; any other command.

Tickets: OPEN-550, OPEN-479 (OPEN-146).

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
