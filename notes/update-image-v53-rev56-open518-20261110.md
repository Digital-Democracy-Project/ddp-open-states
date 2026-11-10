# Update: scrapers image v53 / task-definition revision 56 is registered (OPEN-518). 2026-11-10, about 06:20 UTC (Mac side)

Adds to `aeb18d5` (OPEN-517 verified). **Nothing new is authorized by this note.**

**The image:**
* Ramon ran `deploy-scrapers-image.sh`.
* **`ddp-scrapers:v53`** is pushed (digest `sha256:d0ed2ebab328a30487811cddf7ebdb7aee098e4d745c9ee9866717ee25806696`) and registered as **revision 56**, ACTIVE.
* The script's own checks passed: imports, plus the Utah smoke scrape (RC 0, one bill).
* Previous: v52, revision 55.
* Rollback, Ramon's: `aws ecs deregister-task-definition --task-definition ddp-scrapers:56`.

**What it carries, beyond v52:**
* openstates-core `main` at `1459c22e`:
  * #89, the upstream catch-up;
  * #90, the OPEN-517 rule and labels;
  * #91, the import keeps the saved old label on a re-scrape.
* openstates-scrapers `main` at `b3fdb58d`: #85, the Massachusetts scraper saves reports, orders, communications and study requests labelled, instead of skipping them.
* The OPEN-516 Pennsylvania OpenDocument reader is still in it.

**My check inside v53** (no network): `non_bill_kind` is present ("Study Order" gives `study request`); `BillImporter` keeps `ddp_open517_original_classification`; the Massachusetts scraper has `label_non_bill`, and the OPEN-508 skip is gone.

**The order was kept:** the relabel was committed (06:05 UTC) before this registration.

**What to look for in your normal reports (no action requested now):**
* **Tonight's 04:00 UTC Pennsylvania nightly** should launch on revision 56. This is still OPEN-516 Part 2 (`281dd01`), so please report the revision it ran on.
* **The next Massachusetts scrape (Sunday 11-15, 02:00 UTC)** should:
  * log `OPEN-518: <id> is a <kind>` lines instead of `OPEN-508 ... skipping`;
  * store the 3 papers that were missing;
  * leave the relabelled items' labels and the saved-label count (3,132) intact.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
