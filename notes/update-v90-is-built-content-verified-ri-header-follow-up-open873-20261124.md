# UPDATE (not a GO) to `85ce7f0`: **Step 1 (image v90) is DONE.** Revisions as Ramon reported them: `ddp-scrapers:92` and `ddp-scrapers-db:19`. Everything else in `85ce7f0` still waits on his go. 2026-11-24 ~21:50 UTC (Mac side, Onboard New States)

**Not a GO.** Please confirm with Ramon in your session, as for every relayed answer. The task revisions come from him via the PM session; I did not read them from AWS (no credentials for an agent session).

## What I read on the Mac (the local copy of the image)
* **v90** = `ddp-scrapers@sha256:62d35b299138…` (local tag `v90`). `DDP_CORE_COMMIT` inside it = **`70146facdb8493d990415ee9deff19200c4e4777`**. Core is unchanged, so no core rollout, as in `85ce7f0`.
* **The image has no scrapers-commit record file**, so I checked the content instead: all five merged changes are in it: Wyoming's failed-introduction rule (#285), Nebraska's advancement lines (#284), Utah's 2nd-reading rule (#286), Oklahoma's `house-rollcall-num` / `senate-rollcall-num` (#287), Rhode Island's printed-bill readers (#288). Scrapers main is still `89e390d1`, so the image matches it.

## Rhode Island: one change, and one question for your re-import order
Ramon's answer (2026-11-24, via the PM): the three 2026 Senate roll calls with only a member line and a title (S 2067 twice, the Senate vote on H 7165) **count as passage**. **v90 does not contain it**; a small follow-up under OPEN-873 is being built (a separate PR, then the next image).
* **Recommendation: hold Rhode Island's re-import until that image**, so it runs once. All other states' re-imports in `85ce7f0` (WY, NE, UT, OK) run on v90 as written.
* **If Ramon wants Rhode Island sooner:** it runs on v90 and again on the next image. The cost is a second full 2026 run; nothing is lost either way.
* **Step 3's RI row in `85ce7f0` is therefore on hold**; the other rows stand.

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
