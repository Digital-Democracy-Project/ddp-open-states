# Mac-side LEGBOT_SCRAPE_COMPLETION_TRIGGER_ENABLED flip: not needed, per Ramon

Re: the ask in `legbot-trigger-paused-and-mi-nightly-schedule-request-20260914.md` to also flip
the Mac's copy of `LEGBOT_SCRAPE_COMPLETION_TRIGGER_ENABLED` off. Ramon's direct call: skip it --
EC2 is the side that initiates the archive-completion-triggers-LegBot call in the first place, so
with EC2's own copy already off, it never attempts to reach the Mac at all. The Mac's flag value
is moot either way while EC2 stays paused, so there's no need to touch it (and no need to
coordinate a Mac-side restart for this). Leaving it as-is.
