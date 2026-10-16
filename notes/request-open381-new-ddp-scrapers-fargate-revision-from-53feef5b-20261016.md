# REQUEST: OPEN-381, a new `ddp-scrapers` image and task-definition revision built from openstates-core `53feef5b` (Mac side, 2026-10-16 EDT)

**For:** whoever has ECS and ECR access (the Mac session with Ramon built v34 / revision 37 last time, see `reply-open352-fargate-v34-revision-37-registered-20261016.md`; the prod agent cannot do this).

**STATUS: GO to build, test and register one new revision.** Ramon asked for this request (Mac session, 2026-10-16). It is independent of the stored-data update, which runs from a temporary copy of the code on the prod agent's host. If a HOLD note from Ramon appears on this branch, follow it instead. A failed check is not permission to improvise: stop and report.

## 1. What and why

The latest ACTIVE `ddp-scrapers` revision is **37**, image **v34**, built from core `cbf13925`. Since then three more changes merged into openstates-core `main` (now **`53feef5b`**), none of them in v34:
* **OPEN-368:** Arizona's committee and floor-action versions are ordered by the document number in their link (`GetDocumentPdf/<id>`) (#68);
* **OPEN-379:** Arizona's failed floor amendments (`SENATE - <name> flr amend (...) failed`) are no longer bill versions (#69);
* **OPEN-382:** Arizona's House/Senate Engrossed Versions are placed among its action documents by the bill's origin chamber (#70). `version_sort_key` takes `urls` and `origin`; `recomputed_diffs_for_documents` requires `bill_identifier`.

**Effect of deploying:** only data archived from now on (new Arizona scrapes use the new order and exclusion). **Not deploying** means the next weekly run (Sunday 2026-10-18 02:00 UTC) archives new Arizona data under the old rules; a later recompute fixes it. Nothing already stored changes either way.

## 2. What to do (same as last time)

1. **Build a new image from openstates-core exactly at `53feef5b`** (`53feef5bdde1f277195719a9144f88f6c38fe4dc`), the same way as v34. Tag it the next version after v34 (v35); keep the old images.
2. **Prove the code before registering anything.** In the new image, with its own Python, this must print `OK` with the `openstates` path inside the image (the same snippet against v34 must fail, on `origin_chamber`):
```python
import inspect, openstates
from openstates.utils.version_ordering import (
    is_procedural_document as p, version_sort_key as k, note_stage, STAGE_INTRODUCED,
    origin_chamber, document_number)
from openstates.cli.text_extract import (
    _has_text, _clean_nc_text, _clean_al_text, recomputed_diffs_for_documents)
assert "bill_identifier" in inspect.signature(recomputed_diffs_for_documents).parameters
# the OPEN-352 fixes (still present)
assert p("North Carolina", "A1: Amendment") and not p("North Carolina", "A1: ABR-9-V-1")
assert k("Filed", "") < k("Edition 1", "") < k("Edition 2", "") < k("Ratified", "") < k("SL 2025-14", "")
assert p("Alabama", "Judiciary 1st Amendment") and not p("Alabama", "Judiciary 1st Substitute")
assert note_stage("Joint Memorial")[0] == STAGE_INTRODUCED
assert not _has_text("\n \n") and _has_text("A")
assert p("Utah", "Comparison to Sub #1") and not p("Utah", "Amended 2/12/2026 10:02:409")
# OPEN-379
assert p("Arizona", "SENATE - Ortiz flr amend (ref Bill) failed")
assert not p("Arizona", "SENATE - Finchem flr amend (ref FED) adopted")
# OPEN-368
az = lambda i: [f"https://apps.azleg.gov/BillStatus/GetDocumentPdf/{i}"]
assert k("HOUSE - Education", "", az(100)) < k("HOUSE - Appropriations", "", az(200))
assert document_number(az(536047)) == 536047 and document_number([]) == 0
# OPEN-382
assert origin_chamber("HB 2014") == "house" and origin_chamber("SCR 1049") == "senate"
h = lambda n, u=(): k(n, "", u, "house")
assert h("HOUSE - Judiciary", az(5)) < h("House Engrossed Version") < h("SENATE - Natural Resources", az(1)) < h("Senate Engrossed Version")
s_ = lambda n, u=(): k(n, "", u, "senate")
assert s_("SENATE - Judiciary", az(5)) < s_("Senate Engrossed Version") < s_("HOUSE - Education", az(1)) < s_("House Engrossed Version")
print("OK", openstates.__file__)
```
(I ran the `version_ordering` assertions against `53feef5b` before writing this note; the `text_extract` imports need the full environment.) If it does not print `OK`, stop and report.
3. **Register one new task-definition revision** of `ddp-scrapers` that differs from revision 37 **only** in the image (copy 37, change the image). Do not deregister 37.
4. **Confirm:** `aws ecs describe-task-definition --task-definition ddp-scrapers` shows the new revision (38), the new image tag and digest, and that the only change from 37 is the image.
5. **Rollback (record it):** `aws ecs deregister-task-definition --region us-east-1 --task-definition ddp-scrapers:38` makes 37 the latest ACTIVE again.

Do this before **Sunday 2026-10-18 01:00 UTC**.

## 3. Reply

A `reply-open381-fargate-...` note: image tag and digest, the printed `OK` line, the new revision and its difference from 37, the rollback command, times.

## 4. Not authorized

Running any task; deregistering revision 37 or any other revision; changing any schedule, flag, role or secret; touching RDS; any recompute; any scrape, archive, embedding or LegBot run.
