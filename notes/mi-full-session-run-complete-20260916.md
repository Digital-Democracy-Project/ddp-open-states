# Michigan full-session LegBot run: complete, clean

The full-session MI sweep (`run_id=cce7bb54-8ded-449d-9e9d-f6990fef0d2d`, started 2026-09-14
21:16:11) finished around 2026-09-16 04:33 UTC -- confirmed by count plateau across two
consecutive checks, and independently by Ramon observing MLX activity stop on the Mac.

**Final numbers**: 3,947 of ~3,973 bills touched (~99.3%), 32,798 total `BillArtifact` rows --
29,088 complete (88.7%), 3,710 failed (11.3%). All failures fall into the same three categories
seen throughout the run, nothing new appeared: 3,700 legitimate `insufficient_information`
declines, 8 `no_archived_bill_text` (flat since early in the run), 2 `no_prior_version_archived`
(flat since early in the run). No systemic issue at any point across the full ~31.5-hour run.

**PR #158 (OPEN-292, lock-lease renewal) can now go live on the Mac** -- the restart was
deliberately held specifically until this run finished (a Mac-side `ddp-sync` restart would have
killed it mid-flight). That condition no longer applies. Not restarting it myself -- flagging as
unblocked for whenever you want to coordinate it.

Separately tracked and still open from tonight, not related to this run's own health: SYNC-66
(archive->LegBot trigger false negative on transient network blips) and the
RDS/LOCAL_OPENSTATES_API_KEY logging leak -- both already have their own notes above with full
detail.
