# NC found with real, substantial underlying data but zero rows in the table the new LegBot trigger depends on

While estimating when the newly-enabled archive-completion trigger will actually fire for
real, checked recent archive activity across every scheduled jurisdiction. Found something
specific and worth a look for North Carolina.

**Real data exists**: confirmed directly against RDS -- NC has 2,338 real bills and 6,191
real bill versions (`opencivicdata_bill`/`opencivicdata_billversion`). This lines up almost
exactly with `sync_schedule.yaml`'s own comment on the `openstates_archive.jurisdictions`
block: "NC's one-time catch-up run (6192/6192 archived, Stage 4's gate) already cleared its
backlog." So the underlying scrape/archive data is real and substantial, not missing.

**But `ddp_bill_version_document` (the table `resolve_touched_sessions`'s
`document_updated_since` filter reads -- the one thing the archive-completion hook actually
checks to decide whether to trigger LegBot) has zero rows for NC.** Not stale -- genuinely
none, confirmed via direct count. For comparison, Michigan (same Thursday schedule slot as
NC) shows real, distinct weekly entries in this exact table across multiple separate cycles
(Aug 20, Aug 27, Sep 10, all Thursdays) -- so this table clearly does get populated correctly
for jurisdictions where the current Fargate archiver has actually run and succeeded fully.

**My read, not confirmed**: the "6192/6192" one-time catch-up predates NC's real weekly
Fargate schedule (NC was only added to `openstates_archive.jurisdictions` alongside its
Thursday slot recently) and, per the earlier Stage 6 soak note
(`nc-stage6-findings-zero-confirmed-cycles-20260909.md`), was a manual validation run, not
the recurring pipeline -- plausibly using a path that writes to S3/RDS's bill-version data but
never touches this specific metadata table. Whether NC's real weekly Thursday run has
actually executed even once since being added, and if so whether it's silently failing to
write this specific table while everything else succeeds, isn't something I can tell from
here -- I don't have ECS/CloudWatch access to check NC's own task history (same gap already
flagged on other threads).

**Practical consequence**: even once both sides' trigger flags are live (they are, as of
today), NC's Thursday runs will never fire LegBot -- not because NC is out of session (it may
or may not be, separate question), but because the specific signal the trigger looks for will
never appear for NC regardless of what the archiver actually does, until this gap is closed.

Flagging for whoever has the access to check NC's actual recent Fargate task history and
confirm which of the two explanations above is real.
