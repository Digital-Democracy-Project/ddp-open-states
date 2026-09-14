# Independent diagnosis of the NC/RDS_CREDENTIALS_SECRET_ARN finding -- confirms the mechanism, disputes the scope, raises a bigger question

Ramon asked me to independently verify `nc-root-cause-rds-credentials-secret-arn-missing-
20260914.md` rather than just accept it. Dug in against real RDS/S3/schedule evidence, not
just the Mac's log. Conclusion: **the specific bug is real and well-corroborated, but "breaks
every jurisdiction's Fargate archive launch" overstates it, and there's a real architectural
question underneath worth deciding before just patching the missing value.**

## What's confirmed real

Checked `ddp_bill_version_document` for exact timestamps around the claimed cutoff
(2026-09-10 21:13 EDT = 2026-09-11 01:13 UTC) across every scheduled jurisdiction. Utah,
Arizona, Virginia, Michigan, and Massachusetts show **zero** rows after that cutoff. The two
apparent counter-examples (Washington 8,086 rows on 9/11 12:57-13:19 UTC; US 46,473 rows
spanning 9/11-9/13) are both clearly manual/one-off activity, not real scheduled runs --
neither timing lines up with either jurisdiction's actual 05:00 UTC slot, and the US batch
overlaps exactly with manual OPEN-192/268 testing I ran myself this week. So the "no real
scheduled success since the cutover" pattern holds once manual noise is excluded.

**Direct, same-day, same-jurisdiction proof the missing value is the real differentiator**:
on 2026-09-13 (Sunday), the Mac's own `us` attempt failed with exactly this error (per your
log evidence). On the exact same day, **this EC2 host's own `us` attempt succeeded completely
and automatically** -- confirmed in [[open192_fargate_cutover_deploy]]: "the `us` archive job
completed cleanly, fully automatically... First time archiving has ever completed on its own
real schedule on this host." Same jurisdiction, same day, opposite outcomes, exactly tracking
which host has a working ARN. This is about as clean a confirmation as this kind of claim
gets.

## What I think overstates it

**This EC2 host's own `OPENSTATES_ARCHIVE_ENABLED` was only flipped on yesterday (2026-09-13,
Sunday)** -- before that, this host's scheduler never fired a real archive job at all, every
prior success was a manual trigger. So for every jurisdiction except `us` (whose slot happened
to fall on the exact day the flag flipped), **this host hasn't had a real chance to attempt
its own schedule yet** -- FL/UT's Monday slot (today) was this host's very first-ever
independent attempt at either of them, and MI/NC's Thursday slot hasn't happened even once
under this host's own live schedule yet. "Every jurisdiction has failed since the cutover" is
true for the Mac's attempts specifically; it isn't evidence this host's attempts would also
fail, since this host's credential is fine and its one clean same-day test (`us`) proves it.

**Today's real Utah result (zero new rows) isn't itself evidence of a launch failure.** Utah's
been out of session since March (confirmed via direct web search earlier today) -- an empty
result is the expected, correct outcome regardless of which host attempted it or whether the
attempt technically succeeded-but-found-nothing vs. failed at launch. I can't distinguish those
two from the RDS data alone, and for an out-of-session state they look identical either way.

## The bigger question

`cloud_archiver.py`'s own docstring already states the design intent explicitly: "there is no
on-prem production archiver... production archiving is cloud-only, full stop" (Ramon's own
correction, dated 2026-08-31, well before today). If that's still the real intent, **the Mac's
own archive scheduler firing at all is itself the actual bug** -- not a missing config value
to patch, but a leftover schedule that shouldn't be running in production anymore now that
this host is proven to handle it independently. Setting `RDS_CREDENTIALS_SECRET_ARN` on the
Mac would make its attempts *succeed* again, which -- given both hosts currently have
`openstates_archive` fully enabled for all 10 jurisdictions simultaneously, with no
coordination between them beyond the in-Fargate-task `SourceLock` -- would recreate exactly
the kind of duplicate-uncoordinated-dispatch problem OPEN-290 was just built to close for the
LegBot trigger step, except one step earlier, at the archive-launch step itself.

**My recommendation, not a decision**: rather than fixing the Mac's missing value, consider
disabling `openstates_archive` on the Mac entirely (its `OPENSTATES_ARCHIVE_ENABLED` flag),
now that this EC2 host is confirmed to be the real, working, sole intended production
archiver. That closes the gap for good rather than patching one symptom of two schedulers
still both being live. Ramon's call either way -- flagging the question, not making it.

NC's own specific gap is separate and still genuinely open either way: its Thursday slot
hasn't been attempted by this host's own (now-live) schedule even once yet -- first real
chance is this coming Thursday (9/17), same day as Michigan. Worth watching that specific run
directly rather than assuming either explanation until then.
