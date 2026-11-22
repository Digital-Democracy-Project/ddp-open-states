# CORRECTION to `e27e5b0` (image v78 check): Wyoming's first scrape is NOT freed by v78. 2026-11-22 (Mac side, State Specific Handling)

**Not a GO.**

* **What `e27e5b0` got wrong:** it listed Wyoming among the first scrapes v78 frees. Wyoming's last date fix, **OPEN-766 (scrapers #220: six end dates moved to the last working day, per Ramon)**, is not merged and is not in v78. So **Wyoming's first scrape waits for the image after v78** (from Onboard New States).
* **Still freed by v78** (each on Ramon's go): Kentucky, Oklahoma, Rhode Island, Idaho.
* **Expected in the image after v78** (each added by an UPDATE note once merged):
  * OPEN-766 (#220, Wyoming);
  * OPEN-764 (#221, Louisiana presiding officers; needs ddp-open-states #460's new manifest field);
  * OPEN-767 (openstates-core, date-aware voter matching; still being built);
  * OPEN-765 (#219, North Carolina 2025 end date);
  * BROKER-579 (#222, PA/NE/LA veto overrides).

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
