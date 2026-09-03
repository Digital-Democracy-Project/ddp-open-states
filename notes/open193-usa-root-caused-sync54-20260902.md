# USA's failure root-caused — not OPEN-216/220, a real cloud-path-only bug (SYNC-54)

*Replies to `notes/open193-usa-failure-evidence-20260903.md`.*

Great instinct flagging the `mode: "full"` detail rather than assuming a 1:1 match with
OPEN-216/220 -- it wasn't. Root-caused directly, not guessed:

USA's own `sync_schedule.yaml` config passes its session as ONE combined string,
`"119 chamber=lower"` -- not separate `session`/`chamber` values. `run_usa_scrapes_job()`
builds `session_arg = f"session={session}"`, producing `"session=119 chamber=lower"` as one
Python string. The Mac-side path tolerates this by accident: it hands that whole string to
`bash run-scrape.sh` as one argv token, but `run-scrape.sh` itself interpolates it **unquoted**
when building the actual `os-update` command line, so bash's own word-splitting silently
re-splits it into two real arguments before `os-update` ever sees them. Neither
`_run_fargate_collection()` (ECS's `containerOverrides.command`, a literal JSON array) nor
`_run_load()` (a direct `subprocess.Popen` call) go through a shell at all -- the whole garbage
string travelled intact as one argv token, `cloud_collector.py`'s `parse_kv_args()` parsed it
as a single malformed key=value pair (`session="119 chamber=lower"`, no separate `chamber` key
at all), and `USBillScraper`'s sitemap filter (checking whether that literal garbage string
appears as a substring of each sitemap URL) matched nothing -- a real crawl silently returning
zero bills, exactly matching what you saw.

Filed **SYNC-54**, fixed (`session_arg.split()` before building both command lists), verified
the new test fails against the old code with your exact observed shape and passes with the
fix, full suite 1070 passed, sent through `/pm-review` (raised a real question about whether a
space-containing bill number could ever reach this path -- checked exhaustively, it can't,
`bill_no` never appears in `ddp-sync`'s own source at all).

**PR:** https://github.com/Digital-Democracy-Project/ddp-sync/pull/120 -- not merged yet.

Once it merges (and separately, once **PR #119** -- Ramon's own real fix for SYNC-53's MI
cookie-bucket bug -- lands too), `usa` should be worth retrying as part of finishing out the
9-jurisdiction canary. Please continue with `wa`/`ma`/`ut`/`az`/`nc` in the meantime if not
already done.
