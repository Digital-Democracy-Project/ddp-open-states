# UPDATE to `ad86ad0` (US 118th/119th re-import, OPEN-643): gate 1 is met, v75 contains #194. 2026-11-21 (Mac side, State Specific Handling)

**Not a GO.**

* **Gate 1, met:** the PM session checked inside the v75 image. Its `scrapers/usa/bills.py` has OPEN-643's `relation_label`, so v75's scrapers contain #194 (`b3d4c154`). The US re-import does not wait for another image.
* **Still waiting:** gate 2, step 4 of `1f1e692`. That is EC2 api-v3 and EC2 ddp-sync at core `7f5319583f9d30684ef3f042ea308554f1cc0676`, with the drift check exiting 0; it is with Ramon and you. The Mac api-v3 is being rebuilt at that core now.
* Gate 3 (nothing US running) and everything else in `request-open643-us-118-119-reimport-labels-v75-20261121.md` stand.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
