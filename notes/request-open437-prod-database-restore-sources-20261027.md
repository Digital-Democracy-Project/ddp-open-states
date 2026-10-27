# Request (read-only): what can restore the production openstates database if a scrapers deploy writes bad data? (OPEN-437)

2026-10-27. Ramon's go given in this session. **Read-only: describe and list only. Take no snapshot, change no setting, restart nothing.** If any step needs a write, stop and report.

## Why
The scrapers image (OPEN-401 catch-up) will go live on Fargate with a canary state first (plan on OPEN-437). If a state writes bad data, deregistering the new task-definition revision stops new bad writes but repairs nothing. The repair is a targeted `bill_no=` rescrape on the old image. Before the deploy I need to know whether there is anything stronger to fall back on. I have not verified any of this; the Mac nightly dump is a replica that lags production, so it is not a restore source.

## Please report
1. **RDS:** the production openstates instance's automated backup retention period, whether point-in-time recovery is on, the latest restorable time, and the list of existing manual snapshots (name, time). (`describe-db-instances` and `describe-db-snapshots` fields only.)
2. **S3 bill-provenance archive (Phase 2):** does it keep the previous version of a bill's stored record when a bill is rescraped, and for how long? I need to know whether a bill as scraped by the old image can be recovered from it after the new image overwrites it. A statement from the code or config is enough; do not read bill content.
3. **Who can take a manual snapshot, and how long it takes** for this instance (size, typical minutes). I am **not** asking for one now: a manual snapshot right before the deploy will be a separate go from Ramon.
4. **Anything else** you know of that restores the production database or one jurisdiction's bills.

Reply with the facts above and the commands you ran. Nothing else changes.

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
