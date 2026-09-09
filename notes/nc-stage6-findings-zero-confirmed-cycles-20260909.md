# NC Stage 6: can't confirm even one clean cycle -- real gaps found, not just "check again later"

*Replies to `notes/nc-stage6-soak-verification-request-20260909.md`.* Short answer up front:
**not ready for promotion.** I can't confirm even one clean weekly scrape cycle, let alone two,
and found a real discrepancy in what "Stage 4 archive enabled" actually means today.

## 1. NC is not on the cloud/Fargate path at all -- explains a zero-evidence result, doesn't excuse it

`config/sync_schedule.yaml`: `nc` is in `secondary.jurisdictions` (scheduled Sunday 02:00 UTC),
but **absent from `openstates_scrape.cloud_path.jurisdictions`**
(`["fl","wa","usa","va","mi","ma","ut","az"]` -- confirmed on both this host's local copy and
`origin/main`) and **absent from `openstates_archive.jurisdictions`**
(`["fl","ut","az","wa","va","mi","ma","al","us"]`, same on both). So NC's real production
scrape, if it's running at all, runs through the pre-cloud/legacy path (Mac Studio, local
Postgres) -- not something visible from this EC2 host's S3/RDS-facing tooling.

**Direct evidence of this gap:** `ddp-openstates-scraper-memory`'s `prod/` prefix has
watermark/memory objects for every cloud-path jurisdiction (`az, fl, fl_2026*, ma, mi, usa*, ut,
ut_2025S2, va, wa`) and **zero for `nc`, anywhere in the bucket**. If NC's weekly secondary
scrape had run even once through this architecture, there would be something here. There isn't.

## 2. jurisdictions.yaml's `archive.enabled: true` is a manual-run gate, not the recurring schedule

Its own comment says so directly: *"Not yet on ddp-sync's recurring weekly schedule
(`config/sync_schedule.yaml` `openstates_archive.jurisdictions`, confirmed absent) -- that
addition waits for a real timed validation run's evidence."* So "Stage 4 archive enabled
~2026-09-01" in the original ask is the *gate*, not a live recurring job -- worth not conflating
the two going forward.

## 3. Real S3 evidence: one archive event, today, not a recurring cycle

`ddp-bill-archive` does have `nc` documents -- **6,192 objects**, but every one I sampled has
`LastModified` within the same ~90-second window, **2026-09-09T00:08:58-00:08:59Z, i.e. hours
before this Stage 6 request was even posted.** That's the signature of one manual/supervised
validation run (exactly what jurisdictions.yaml's comment says is still pending), not evidence
of a recurring weekly cadence.

## 4. Couldn't check RDS directly -- hit a live credential failure, same as the parallel OPEN-192 thread

Tried `psql` against `RDS_DATABASE_URL` from this host's `/opt/ddp-sync/.env` to check real NC
bill counts/timestamps as a cross-check independent of S3. Got the identical failure being
tracked on the OPEN-192 Fargate/RDS thread right now: `FATAL: password authentication failed
for user "openstates_admin"`. Not investigating that credential myself -- it's already being
chased on the other thread -- but flagging that it blocked half of this verification too, so
whoever fixes it, this NC check should be re-run against RDS once it's working again to settle
whether NC has ANY rows there at all (an earlier session's note claimed NC has zero rows in RDS
entirely -- consistent with everything found here, but not independently re-confirmed today).

## Conclusion

Per the soak table's own two-clean-cycles-for-yellow rule (couldn't locate
`PLAN-push-button-onboarding.md` in this checkout to re-verify the exact wording myself --
taking the original ask's citation at face value): **zero clean cycles confirmed, not two, not
even one.** This isn't "wait a bit longer" -- it's "the recurring cloud-side pipeline shows no
NC activity ever, and the one real archive evidence that exists is a single manual run from
earlier today, not a cadence." Recommend against flipping `nc.status` to `live` on this
evidence. If NC scraping is genuinely happening successfully on the Mac's legacy path every
week, that needs confirming from a session with access there -- this EC2 host's evidence alone
says no.
