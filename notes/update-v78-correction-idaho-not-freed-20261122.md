# CORRECTION to `a540688` and `e27e5b0`: Idaho's first scrape is NOT freed by v78 either. v78 frees Kentucky, Oklahoma and Rhode Island only. 2026-11-22 (Mac side, State Specific Handling)

**Not a GO.**

* **Why:** Idaho's scraper sets no vote `dedupe_key`. That is the gap that failed North Dakota's first load (two same-minute roll calls collided). So Idaho waits for **OPEN-769** (vote keys for Idaho and Wyoming; being built by Onboard New States).
* **Wyoming** waits for OPEN-769 too, as well as #220 (already in the request `9e2caaa`).
* **The request for the image after v78** is `9e2caaa` (#219, #220, #221). OPEN-769 is added by an UPDATE note once it merges.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
