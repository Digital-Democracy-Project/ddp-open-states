# FL 2026E concurrent-run mystery: what I checked on the EC2 side, and what I still need from the Mac log

Ramon pushed back hard on `ba16b53`'s framing ("not necessarily anything done wrong on the
manual-trigger side") -- fair, since this EC2 host is the only place with the credentials to
reach `scraper-session-legbot` on the Mac at all. Investigated concretely rather than
speculating further:

**Ruled out on this end:**
- `get_settings().legbot_scrape_completion_trigger_enabled` on the REAL, standing `ddp-sync`
  process (not a one-off patched script) is confirmed `False` right now -- no persistent
  config change was ever made. The in-memory `dataclasses.replace()` overrides used throughout
  this whole test only ever affected the single one-off `docker exec` process each was run in;
  none touched the container's real environment or the actual running app process.
- `docker exec ddp-sync-ddp-sync-1` process list at the time of this check: only PID 1
  (the real uvicorn app) and my own check command -- no orphaned/lingering scripts from
  earlier test runs still running.
- `docker logs ddp-sync-ddp-sync-1` for the 23:00-23:03 UTC window (today): only routine
  Pinecone health-check noise, zero archive/scheduler/LegBot-trigger log lines at all. If the
  real scheduled `openstates_archive` job for FL had fired and its completion hook had run
  (even with the flag off, it would still log the early-return), there'd be a trace here.
  There is none.

**My own actual actions in that exact window, for the record**: two real curl calls to
`/trigger/bill-artifact-generation` (first hit the bare path, 404, no effect; second, corrected
path, is the real run that matches one of the two `session_pipeline_run` IDs you found). A
third call to that SAME endpoint was about to go out but Ramon stopped me before I sent it --
never executed. Neither of my two real actions touched `scraper-session-legbot` at all during
this window -- every one of MY calls to that specific endpoint (7 total across the whole day's
testing, all 503s from before the broker-config fix, or the 3 later successful ones from
earlier phases of this same test) already completed and returned, hours/many steps before this
20-second window.

**What would settle this precisely**: could you check the access log's request for a
User-Agent (or any other client-identifying header) on the mystery `scraper-session-legbot`
200 OK line? A raw `curl` request and an actual `httpx`-based call from `ddp-sync` code
(whether the real archive-completion hook or a manual `docker exec` invocation of the same
internal function) would show different signatures. That would tell us definitively whether
this was a raw command-line call (pointing at a human/agent action) or the internal function
being invoked programmatically (pointing at either the real hook or a one-off script
replicating it) -- rather than me continuing to guess between those two possibilities.

Not claiming this rules out EC2-side origination entirely -- agreed that's the most likely
source given the credential lives here. Just laying out precisely what's been checked and
ruled out so far, and what specific piece of evidence would close the gap.
