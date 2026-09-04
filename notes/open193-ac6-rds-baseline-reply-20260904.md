# OPEN-193 AC6 reply: RDS-side numbers, same shape -- one real gap (NC), one non-gap explained

*Replies to `notes/open193-ac6-local-baseline-20260903.md`.*

Ran the equivalent queries against RDS for the same 9 jurisdictions, same shape (confirmed exact
table/column names directly against RDS's own schema first, not assumed from the plan docs):
`opencivicdata_bill` joined through `opencivicdata_legislativesession.jurisdiction_id`,
`opencivicdata_voteevent`, and `ddp_bill_version_document.diff_from_previous_version IS
[NOT] NULL` for the diff split. `spot_check_bill` uses the same selection rule as
`infra/rds/README.md`'s OPEN-191 checklist (`ORDER BY version_count DESC, updated_at DESC LIMIT
1`, version_count = count of `ddp_bill_version_document` rows per bill).

## Two things worth flagging before the raw numbers -- not leaving this as just data

**1. NC is not "stale," it's completely absent from RDS.** `bill_count: 0`,
`vote_event_count: 0`, `version_doc_count: 0`, `spot_check_bill: null` -- every field zero, not
small-and-old. Matches the known structural fact from OPEN-193's canary work: NC has never had
an individual Fargate trigger target (`_OPENSTATES_SINGLE_JURISDICTION` has no `nc` entry), so
there's never been a path for NC data to reach RDS at all, distinct from every other
jurisdiction here. Worth confirming that's actually the reason (rather than a load that silently
failed) before calling AC6 closed for NC specifically.

**2. WA and VA show byte-for-byte identical `max_bill_updated_at` between local and RDS** -- zero
drift, not "RDS newer" like the other six. This isn't a missed load. It traces directly to
yesterday's `is_in_session()` investigation (`notes/open253-is-in-session-two-real-bugs-20260903.md`):
WA is confirmed (real-world, web-verified) adjourned since 3/12; VA's own live OpenStates data
shows its real 2026 sessions ended 3/14 and 5/1 (the only reason `is_in_session('VA', ...)`
claimed otherwise was the empty-end-date bug from a 2018 special session, not real 2026
activity). Both being out of session means today's incremental Fargate scrape correctly found
nothing new for either -- identical timestamps is the *expected* result here, not a gap.

## RDS-side baseline, same shape as the local-Postgres one

```json
{
  "fl":  {"bill_count": 7685,  "max_bill_updated_at": "2026-09-03T00:13:20.195963+00:00", "vote_event_count": 10228, "version_doc_count": 20038, "diff_null": 11518, "diff_not_null": 8520,  "spot_check_bill": {"id": "ocd-bill/520e5f27-23f2-406e-b2ff-2a64a46d5d53", "identifier": "SB 1452", "updated_at": "2026-08-29T17:39:26.079349+00:00", "version_count": 14}},
  "wa":  {"bill_count": 3411,  "max_bill_updated_at": "2026-06-15T23:09:25.032880+00:00", "vote_event_count": 2302,  "version_doc_count": 11636, "diff_null": 7096,  "diff_not_null": 4540,  "spot_check_bill": {"id": "ocd-bill/0147f79c-da68-44ad-a310-934fd23491bc", "identifier": "HB 1960", "updated_at": "2026-06-15T23:09:05.098932+00:00", "version_count": 12}},
  "usa": {"bill_count": 37852, "max_bill_updated_at": "2026-09-04T03:04:45.154836+00:00", "vote_event_count": 1556,  "version_doc_count": 88955, "diff_null": 76072, "diff_not_null": 12883, "spot_check_bill": {"id": "ocd-bill/fab1200c-53c6-48fa-8e8b-cde9e19d1338", "identifier": "HR 6644", "updated_at": "2026-08-13T23:00:57.935370+00:00", "version_count": 18}},
  "va":  {"bill_count": 4380,  "max_bill_updated_at": "2026-08-25T00:31:20.943513+00:00", "vote_event_count": 11553, "version_doc_count": 25541, "diff_null": 8787,  "diff_not_null": 16754, "spot_check_bill": {"id": "ocd-bill/2ddfc5a1-6b08-495a-8f0e-81e415e2675a", "identifier": "HB 308",  "updated_at": "2026-06-29T17:29:06.098355+00:00", "version_count": 32}},
  "mi":  {"bill_count": 3930,  "max_bill_updated_at": "2026-09-03T01:05:32.230492+00:00", "vote_event_count": 1208,  "version_doc_count": 13585, "diff_null": 8868,  "diff_not_null": 4717,  "spot_check_bill": {"id": "ocd-bill/006abf23-5a5a-4aa3-9e14-a53aa8bb2f19", "identifier": "HB 4420", "updated_at": "2026-06-14T01:52:56.034029+00:00", "version_count": 27}},
  "ma":  {"bill_count": 11471, "max_bill_updated_at": "2026-09-03T19:07:47.685099+00:00", "vote_event_count": 524,   "version_doc_count": 11623, "diff_null": 11332, "diff_not_null": 291,   "spot_check_bill": {"id": "ocd-bill/7d4d7f0f-6637-478a-a698-23185e6bc7e4", "identifier": "H 3911",  "updated_at": "2026-08-24T23:37:57.450862+00:00", "version_count": 2}},
  "ut":  {"bill_count": 1021,  "max_bill_updated_at": "2026-09-03T02:15:54.196416+00:00", "vote_event_count": 1917,  "version_doc_count": 9371,  "diff_null": 2043,  "diff_not_null": 7328,  "spot_check_bill": {"id": "ocd-bill/d369d37d-d652-421c-a7a2-e1c3f5cb6b5d", "identifier": "HB 44",   "updated_at": "2026-09-03T02:15:31.438259+00:00", "version_count": 58}},
  "az":  {"bill_count": 2190,  "max_bill_updated_at": "2026-09-03T02:30:19.414243+00:00", "vote_event_count": 3443,  "version_doc_count": 8901,  "diff_null": 4458,  "diff_not_null": 4443,  "spot_check_bill": {"id": "ocd-bill/684dd592-426c-44b6-b635-b851b8aa91f4", "identifier": "HB 2999", "updated_at": "2026-06-16T22:04:19.528671+00:00", "version_count": 16}},
  "nc":  {"bill_count": 0, "max_bill_updated_at": null, "vote_event_count": 0, "version_doc_count": 0, "diff_null": 0, "diff_not_null": 0, "spot_check_bill": null}
}
```

## One more raw observation, not analyzed further -- leaving the actual diff/write-up to you as offered

`version_doc_count` is *lower* in RDS than local for three jurisdictions despite those same three
(az, mi, usa) showing fresher `max_bill_updated_at` in RDS: az 8901 vs 8933, mi 13585 vs 13825,
usa 88955 vs 89091. Bill counts also went the opposite direction for mi (RDS 3930 < local 4013).
Flagging as raw fact rather than asserting it's wrong -- the plan doc's own §5 already says exact
equality isn't the bar and RDS/local document sets can legitimately differ by independent
scrape/load timing, so this may be exactly that, not a new problem. Numbers are here either way
for your diff.
