# Request (read-only): read the Vermont and New Mexico probe output on revision 44 (OPEN-470, OPEN-471), 2026-10-31 about 22:45 UTC

Ramon asked me to probe the two states the new image (v41 = `ddp-scrapers` revision 44) fixes. **Nothing here changes anything: do not stop, restart, re-run, launch, pull or edit anything.** Please do not print or commit secrets (redact the task token in log tails as before).

## What I launched (22:40 UTC, with `probe-on-fargate vt nm --date 20261031v41`)
| state | task id | run id | ended |
|---|---|---|---|
| vt | `c1b75813a6c248618da305651ddfbd38` | `probe-vt-20261031v41` | exit 0, "finished, uploaded", 22:41 UTC |
| nm | `da58490c6cdf4bfca4f8b0a5073421e0` | `probe-nm-20261031v41` | exit 0, "finished, uploaded", 22:41 UTC |
Both ran on **revision 44** (read from the launch record). Prefix `dev-probe-all-20261031v41/`; output under `probe/<st>/<run id>/`. No database, no import. (The 18:40 UTC all-states runs for these two states used a different prefix and run ids.)

## What I need
1. For each of vt and nm, committed unchanged to this branch under `notes/probe-vtnm-20261031/<st>/`: `result.json`, `report.md` **and `sample.tar.gz`** (the Mac half needs the sample).
2. The first 40 and last 20 log lines of each stream (`scraper/scraper/<task id>`), redacted, plus any `Traceback`, `406`, `403`, `HTTPError`, `mdb-export`, `refus`, `WAF` or `ERROR` line verbatim.
3. Object count and total size under the prefix, and whether anything was written outside it.

## What I will look for
* **Vermont:** a report exists (it crashed with none on revision 43 because gate A counted a generator) and gate A passes.
* **New Mexico:** gate D gets past `FileNotFoundError: 'mdb-export'`.

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
