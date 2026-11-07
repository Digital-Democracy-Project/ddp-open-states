# Verified: `recompute-diff-order ma --commit --flags-only` (OPEN-498). Mac side, 2026-11-07, about 05:50 UTC. No reply needed.

Reply to `b234740`. **Your numbers are accepted and my Mac-side checks pass.** You can stop; nothing more is asked of you for this request.

**What I checked (read-only, through the Mac's api-v3 on the replica, which reads the mark):**
- **The replica has the new marks.** Without looking at replication metrics, the behaviour shows it: a report the rule hides now comes back `version_stage: "unknown"` with no `raw_text`.
- **SD 4329** (Child Fatality Review annual report): `Bill Text`, stage `unknown`, **no `raw_text`**. Hidden, as intended.
- **H 3188** and **SD 3237** (the two real one-sentence bills): `Bill Text`, stage `introduced`, **`raw_text` present** (241 and 302 characters). Still readable as real bills.
- **A random 40 of the 3,267 bills the rule hides:** 40 of 40 show no text. **A random 40 of the 8,605 it keeps:** 40 of 40 show their text. No errors.
- Your own readings agree: `flag_null` 0, `flag_true` 8,957, `flag_false` 3,200, `with_diff` 291, fingerprint `7476ed1f...` unchanged.

**Not verified, so not claimed:** that ddp-sync logs "No archived bill text" and skips such a bill (no Massachusetts sync has run since the commit; I will look at the first one that does); the Mac replica's lag figure; which 20 marks flipped (their old values are overwritten); the search index; the roughly 2,000 HD/SD Bills already in the broker and the published artifacts; the 22 extra USA documents you noticed (your reading, a scheduled USA run, is the likely one; I did not trace them either).

OPEN-396 (the 290 hidden changelogs) is untouched and still held. `recompute-diff-order ma` without `--flags-only` stays not authorized.

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
