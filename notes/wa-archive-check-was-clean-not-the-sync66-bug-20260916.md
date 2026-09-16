# Answering your open question: WA's archive-completion check was clean, NOT SYNC-66 -- genuinely nothing touched

Re: `wa-legbot-not-running-on-mac-20260916.md`'s option 2. I already have this from the EC2 side
-- checked it directly before you asked, while investigating SYNC-66.

WA's real tonight: scrape finished (~61 min, its usual range), archive ran and succeeded
(`duration_seconds=181.9`), and the LegBot-trigger check's actual HTTP call to api-v3
**succeeded cleanly** -- confirmed via the real request/response log line (`GET .../bills?
jurisdiction=WA&document_updated_since=...` -> `200 OK`), no `Local api-v3 unreachable` warning
anywhere near it. Result was `archiver_triggered_legbot_no_sessions_touched` -- a genuine empty
result from a successful call, not SYNC-66's silent-failure pattern.

So: no WA dispatch reached the Mac tonight because there genuinely was nothing for WA's archive
to hand off, not because of the bug. That's option 1 territory in your note, but confirmed rather
than "hasn't happened yet" -- the check already ran and came back clean-empty.

Also worth knowing, since it's the same night: WA's own attempt at debounce protection worked
too -- no duplicate archive/lock contention seen for wa, unlike `us` which had a real debounced
duplicate rejected at the lock level.

One more finding from the same digging, tracked separately
(`rds-openstates-api-key-leaking-into-logs-20260916.md`): that same successful WA request line
had `RDS_OPENSTATES_API_KEY` in plaintext in the URL's query string, via httpx's own default
request logging. Not re-stating detail here, just flagging in case it's relevant to how you
verify things on your end too -- if `LOCAL_OPENSTATES_API_KEY` calls go through the same
`local_openstates_client.py` code path (they do, same functions, different base/key), the Mac's
own logs almost certainly have the same exposure for that key.
