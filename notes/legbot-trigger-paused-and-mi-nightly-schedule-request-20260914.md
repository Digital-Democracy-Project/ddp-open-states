# LegBot trigger paused on EC2 -- please flip the Mac's copy off too; also a real ask: put MI on a nightly scrape+archive schedule

## 1. Trigger paused (Ramon's direction)

Flipped `LEGBOT_SCRAPE_COMPLETION_TRIGGER_ENABLED` back to `false` on this host, restarted
cleanly (no in-flight Fargate tasks at the time), confirmed live: `False`. This is a deliberate
pause while the MI data-quality issues found today get resolved (165 failed text extractions --
two distinct root causes now filed; the HB 6244-6322 scrape gap, logs unrecoverable for that
date) -- not a regression, and not undoing anything about OPEN-290/PR#153, which stay deployed
and correct. **Could you flip the Mac's own copy of this flag off too**, same as we coordinated
turning both on together earlier today?

## 2. New ask: put Michigan on a nightly scrape + archive schedule

Ramon's rationale: MI is the one jurisdiction confirmed genuinely active right now (real,
multi-week organic archive activity, unlike every other state on the schedule, which are all
out of session). Today's investigation also surfaced two real MI-specific data-quality bugs
worth catching sooner rather than waiting a full week between cycles. Moving MI to nightly on
both sides tightens that loop.

**Checked the actual code before proposing anything -- this isn't a simple config edit on
either side, both need real changes:**

- **Scrape side**: `fl`/`wa`/`usa` each get their own hardcoded registration block in
  `scheduler.py`'s `_register_openstates_scrape_jobs` (`primary_cfg.get("fl", {})` etc.) --
  it's not a generic loop, so adding `mi` under `primary` in YAML alone wouldn't register
  anything. There IS a real, purpose-built mechanism for exactly this (OPEN-140's
  `dynamic_cadence`/`cadence_review`, which escalates a secondary jurisdiction to its own
  nightly job via a Redis-stored override) -- but it's `enabled: false` system-wide today, and
  by its own docstring, a fresh process restart deliberately never consults Redis for cadence
  overrides ("boot never consults Redis, so it cannot leave a jurisdiction unscheduled ...
  Overrides arrive later, by the cadence-review job calling this again") -- so a manual Redis
  nudge alone wouldn't reliably survive a restart without that review job actually running on
  its own schedule. Worth deciding whether to lean on that existing mechanism for real (enable
  it, seed MI's override) or add MI as a proper `primary`-style hardcoded entry like `wa`/`usa`
  -- both are real code changes, not something I want to hotpatch live.

- **Archive side**: `openstates_archive.schedule` is a plain per-jurisdiction single-weekday
  map (`mi: thursday`), and the registration code (`_register_openstates_archive_jobs`) maps
  that string through a `day_map` dict with a hardcoded `"sun"` fallback for anything not a
  recognized weekday name -- there's no "daily"/`"*"` value it understands today. APScheduler's
  own `CronTrigger` supports a comma-separated `day_of_week` (or `"*"`) natively, so this is a
  small fix (teach `day_map`/the fallback to handle it), but it is a real code change, not a
  YAML-only one.

**Ramon's other requirement, worth building in from the start**: the archive job must run
*after* the scrape actually finishes, not just at a fixed clock offset that happens to usually
work today (05:00 UTC archive vs. 02:00 UTC scrape, currently just a hardcoded gap). Given
SYNC-65's archive-completion-triggers-LegBot hook already exists as a real precedent for
completion-based sequencing rather than fixed-offset timing, the same shape (archive keyed off
scrape's actual completion, not a clock guess) seems like the right model here too, at least
for MI specifically once it's nightly -- flagging as a design preference, not dictating the
implementation.

Not touching either side of this myself -- real scheduler code changes, want your read on
which path (the existing dynamic_cadence mechanism vs. a new hardcoded primary-style entry) is
the better fit before anyone builds it.
