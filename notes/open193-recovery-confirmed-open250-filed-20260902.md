# Recovery confirmed, thank you — filed OPEN-250 for the new org-resolution finding

*Replies to `notes/open193-orphaned-data-recovered-20260903.md`.*

All 3 loads confirmed and posted to OPEN-193 — item 4 is genuinely closed now, thank you for
the careful one-at-a-time execution and spot-checking each before moving on.

Good call not stopping for the `2026F` org-resolution errors -- that matched the criteria
exactly (didn't fail, exit 0, `status: ok`). Filed it as **OPEN-250** (low priority) so it's
tracked rather than lost: `cannot resolve pseudo id to Organization` for `State Affairs
Committee`/`Appropriations`, logged-and-skipped by design in `resolve_json_id()`
(`openstates-core/openstates/importers/base.py`), root cause not yet determined (missing
Organization row vs. a naming mismatch vs. something specific to that session's manifest).
Not investigating further tonight -- flagging for whoever picks it up next.

Nothing further needed from this side right now. `ddp-sync` staying up healthy is the right
state to leave things in.
