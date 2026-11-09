# Request (production change, GO given): api-v3 on EC2 to `7b66e66`, then a read-only report on tonight's Pennsylvania archive (OPEN-516). 2026-11-09, about 20:45 UTC (Mac side)

**Ramon's go** (2026-11-09, his words): "let's deploy", then "pull in and restart api-v3 on the new main, then tell the prod agent to do the same".
* It covers **api-v3 on EC2 only** (Part 1).
* Part 2 is read-only.

## Why
Pennsylvania prints words that a later printing removes struck through. The PDF text extraction keeps them, so LegBot read removed words as current law. OPEN-516 reads Pennsylvania's text from its "DOC" printing instead: an OpenDocument file where struck text is marked, and left out.
* **openstates-core #88** (`28226658`) is the reader. It ships in the scrapers image **v52**, which Ramon is building now. **You do nothing for the image.** Registering it is Ramon's step, and tonight's 04:00 UTC Pennsylvania scrape and archive will run on it.
* **api-v3 #53** (`7b66e66`) is one line in `BillPagination._archived_row_for`: when a version has several stored documents, the order is XML, then **OpenDocument** (`application/vnd.oasis.opendocument.text`), then PDF. Pennsylvania's 6,198 PDF documents stay stored (nothing is deleted), so without this line the PDF would keep winning.
* **Until tonight's archive stores the OpenDocument rows, the line changes nothing.** No such rows exist yet.

**Mac side, done:** Ramon's Mac api-v3 runs `7b66e66` (`refresh-api-v3.sh`, 20:40 UTC). It is healthy, and Postgres was untouched. HB 2625 still serves its PDF text, as expected.

## Part 1: api-v3 on EC2 to `7b66e66`
1. **Record the EC2 api-v3 checkout's current revision** (expected `fe6532a9`, from 11-08) and list the commits this brings. Expected: only #53.
2. **Follow api-v3's runbook section 8,** as on 11-08:
   * tag a `pre-open516` rollback image;
   * `git pull --ff-only`;
   * **ensure before recreate**;
   * build and recreate **the `api` service only, by name** (`docker compose -p ddp-openstates-rds -f docker-compose.rds.yml ... api`).
   * **Never an unscoped recreate.**
3. **Check:**
   * health is 200;
   * the container's `api/bills.py` contains `vnd.oasis.opendocument.text`;
   * `GET /bills/ocd-bill/eac0da98-b48c-46f8-9f12-85d6fc0d1585?include=versions` (Pennsylvania HB 2625) answers 200 and its versions still carry the PDF text today;
   * `/ddp/enrollment` is unchanged.

## Part 2 (read-only, after tonight's Pennsylvania archive)
The archive that follows tonight's 04:00 UTC Pennsylvania scrape should, once, fetch every Pennsylvania DOC printing: **about 6,200 downloads** from palegis.us, at the plain scraper's pace. **That is expected.** Do not stop it unless the site blocks it.

Please report:
1. **The task-definition revision and image the scrape and the archive ran on.** It should be v52, if Ramon has registered it by then; say if it is still v51.
2. **The archive's summary line:**
   * `fetched`, `archived`, `blocked`, `extract_errors`, `fetch_errors`, `persist_errors`, `s3_unverified`;
   * any `blocked response ... expected application/msword magic bytes` lines. **There should be none on v52.**
3. **Read-only SQL on RDS**, Pennsylvania documents by `media_type` and `is_error`:
   ```sql
   SELECT d.media_type, d.is_error, count(*)
   FROM ddp_bill_version_document d
   JOIN opencivicdata_bill b ON b.id = d.bill_id
   JOIN opencivicdata_legislativesession s ON s.id = b.legislative_session_id
   WHERE s.jurisdiction_id = 'ocd-jurisdiction/country:us/state:pa/government'
   GROUP BY 1, 2 ORDER BY 1, 2;
   ```
   **Expect:** `application/pdf` false 6,198 (unchanged) and about 6,200 `application/vnd.oasis.opendocument.text`, nearly all `is_error` false.
4. **Whether the after-scrape LegBot trigger fired** for Pennsylvania, and its result. LegBot runs on the Mac; just report what EC2 logged.

## Rollback
* **api-v3:** go back to the `pre-open516` image, or return the checkout to the recorded revision, and recreate the `api` service the same way.
* **The image:** a rollback is Ramon's (deregister v52's revision). The OpenDocument rows can stay: api-v3 on `fe6532a9` ignores them.

## Not authorized
* Any recompute (`recompute-diff-order`), reextract, search refresh, or a scrape or archive launched by hand.
* Registering or deregistering a task definition.
* Any LegBot run.
* Any change to the session rows, the flags, or the Nebraska/Louisiana switch-on (that is the separate request `6d3234b9`).
* An unscoped recreate.
* Anything on the Mac.

## What I check on the Mac side
After the archive, on the Mac replica:
* Pennsylvania's OpenDocument rows and counts;
* HB 2625 PN3751's text has no §9301 and loses "for definitions and";
* its comparison with PN3586 shows the removal;
* the Mac and EC2 api-v3 both serve the OpenDocument text for HB 2625.

Then LegBot regenerates Pennsylvania from the corrected text. Ramon stopped the old Pennsylvania LegBot run on 11-09.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
