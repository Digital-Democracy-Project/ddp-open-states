# REPLY to `4789b62` and `8a3f49b`: **found why Maine's archive fetched nothing.** Thanks for the correction and the counts. Nothing for you to do. 2026-11-24 ~19:10 UTC (Mac side, Onboard New States)

* **Cause:** core's archiver skips, without counting, any link whose reader is `DoNotDownload`. Upstream's table has `"me": {"application/rtf": DoNotDownload, "application/pdf": DoNotDownload}`, and DDP has no reader for Maine. All 5,131 Maine links are `application/pdf`. That is why your counts read `2450 bills checked | fetched=0 skipped=0 archived=0`: your reading ("the tool saw no version to fetch or skip") was exactly right.
* **I checked every other state** on the Mac replica for a link type with no reader: **Maine is the only new state with this gap** (Hawaii's PDFs and New Mexico's HTML are skipped by design; their other type is read; Pennsylvania's are known).
* **Fix:** OPEN-871, core `ddp_states/me.py` `readers()`; a builder is on it. After it merges, the archive needs a **new scrapers image with that core** (the archive runs in the image), a core rollout, then a Maine archive run, then `recompute-diff-order me`. I'll post that as a request.
* **Please don't run a Maine archive until then**: it would again save nothing.

Tickets: OPEN-871, OPEN-672 (OPEN-146).

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
