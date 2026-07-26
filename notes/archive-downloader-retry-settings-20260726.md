# Archive downloader retry settings: matched FL, decided not to bump WA/VA/MI/AZ (2026-07-26)

## What changed

The bill-document archive step's downloader (`openstates-core/openstates/cli/text_extract.py`,
module-level `scraper = scrapelib.Scraper(verify=False)`) was using scrapelib's bare defaults —
`retry_attempts=0`, no backoff — for every jurisdiction, regardless of how flaky that
jurisdiction's site is known to be. FL's own scraper class (`openstates-scrapers/scrapers/fl/bills.py`)
deliberately overrides this to `retry_attempts=5`, `retry_wait_seconds=5`, but the archive
downloader is a separate tool from the actual per-jurisdiction scrapers and didn't inherit any
of that.

Fixed: the downloader now sets `retry_attempts=5`/`retry_wait_seconds=5` to match FL, applied
globally since it's a single shared `scraper` instance used for every jurisdiction's archive run,
not something configured per state. Shipped via `openstates-core` PR #1
(`fix/archive-scraper-match-fl-retry` → `cherry-pick-line`), merged 2026-07-26 — picked up
automatically by `apply-local-patches.sh`'s range-pick, no separate deploy step.

Verified live in the isolated dev checkout via the real `os-text-extract` CLI's own interpreter
(not a bare `python3` invocation, which resolves to a different, unrelated global install and
gave a false negative on the first check) — confirmed `scraper.retry_attempts`/`retry_wait_seconds`
actually read back as `5`/`5` after the change.

## Should WA/VA/MI/AZ's own scrapers get the same treatment? Decided: not yet.

This question is about a *different* piece of code — each jurisdiction's own scraper class in
`openstates-scrapers`, not the archive downloader above. Traced the real (non-shallow — this
checkout's clone was shallow and initially gave a misleading single "boundary" commit for all
three overrides; unshallowed from `upstream` to get accurate history) commit history behind every
existing retry override upstream currently has:

| State | Commit | Author | Message |
|---|---|---|---|
| FL | `46f2d5790` (2025-03-05) | Sogo Ogundowole | "chore: handle blockages from fl website" |
| DE | `d6c906798` (2024-02-27) | NewAgeAirbender | "DE: increase timeout for ~1 loading bill" |
| SC | `c03097a98` (2020-07-14) | James Turk | "SC: add retries, #77" |

Every one of these traces to a specific, documented problem with that state's site — not a
blanket policy applied across the board. **WA, VA, MI, and AZ have zero retry-related commits in
the project's entire (unshallowed) history** — not "nobody's gotten to it yet," but genuinely
never touched. Given this project clearly does patch specific states reactively when their sites
misbehave (FL alone has had multiple such fixes — this one, the floor-vote source-URL bug, the
WAF-cookie issue), the absence of any retry fix for these four states is real evidence their
sites haven't caused this class of trouble, not just an oversight.

**Decision: don't bump WA/VA/MI/AZ preemptively.** The archive-downloader fix made sense because
it was DDP's own code being weaker than the state's dedicated scraper for no reason — an internal
inconsistency, not a response to an observed problem. Adding retry logic to these four states'
actual scrapers would mean growing DDP's own diff surface against upstream (see
`PLAN-fork-management.md` — every local change here is something that has to survive a future
upstream merge) for a problem nobody has ever observed. The upstream project's own pattern is
reactive, not preemptive, and that seems like the right model to follow: if one of these four
ever does start failing, that's the signal to add it then, not before.
