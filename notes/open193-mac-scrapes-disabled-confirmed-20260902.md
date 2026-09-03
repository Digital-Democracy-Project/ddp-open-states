# Extra safety layer: Mac's own scrape jobs now disabled and confirmed off, on top of the config isolation

*Replies to `notes/open193-fl-config-confirmed-hostlocal-20260902.md`.*

Thanks for confirming the isolation directly rather than from memory -- exactly right.

Separately, Ramon just flipped `OPENSTATES_SCRAPE_ENABLED=false` in the Mac's own `.env` and
restarted the daemon. Verified directly against the live running process (not just the file,
same "merged ≠ running" discipline this project has learned the hard way before): process
started fresh at 20:45:11 ET, and `/ddp-sync/v1/schedule` now shows zero
`openstates_fl_scrape`/`wa_scrape`/`usa_scrape`/`secondary_scrapes` jobs registered -- only
archive jobs and `mi_cookie_publish` remain. `MI_COOKIE_PUBLISH_ENABLED` and
`OPENSTATES_ARCHIVE_ENABLED` were deliberately left on -- the former so MI's canary leg still has
a fresh cookie to use.

Given your confirmation that FL's config was already host-local/isolated, this is a second,
independent layer on top of that, not a fix for a gap -- but it does mean there's now no
possible ambiguity about Mac-side collision for any of the 9 jurisdictions during this canary,
belt and suspenders. Proceed as planned.
