# REQUEST (2026-11-04): read-only count of the page sizes callers ask api-v3 for, and of the refusals (OPEN-493, BROKER-431). Nothing is changed.

**STATUS: needs Ramon's go in your session** (he asked for this check on 2026-11-04). **Read-only: no edit, no restart, no deploy, no write, no setting.** It can be run at any quiet moment; it does not depend on `ba65a42` (the `is_bill_version` request) and does not change what that request asks.

From: Claude (broker side). Background: the website's bill list needs three side-by-side calls to api-v3 per 50-row page because api-v3's `/bills` refuses more than 20 bills a page (`max_per_page = 20`, answer `400 invalid per_page, must be in [1, 20]`). Production measurements (BROKER-431) show the three calls queue on the database count. Ramon decided to **raise that cap to 50 when the request has no `include=`** (OPEN-493; the broker half is BROKER-431). Raising a maximum only changes requests that ask for more than 20, which fail today. I read the callers' code (ddp-sync hard-codes 20, VoteBot's roster reads use `/people` with its own cap, ddp-open-states `quality_check.py` sends 20, the broker sends 20), but code in merged branches cannot show callers I did not read. **This count shows whether anyone asks for more than 20 and relies on the refusal.**

## What I need (counts only; no query strings, no keys, no addresses in the note)
From api-v3's access log on the broker host (container `ddp-openstates-api-1`), over **everything you still have**: the current container's log since its 19:27 UTC start, the saved `log-archive/ddp-openstates-api-pre-recreate-20261104T1924Z.log.gz`, and any older api-v3 archives in `log-archive/`. Say which files you read and the time span each covers.
1. **A table: endpoint path, `per_page` value, HTTP status, number of requests**, for `/bills` first and, if cheap, for every other endpoint. If a request carries no `per_page`, count it as "none". **Never print a query string as it is: the API key travels in it.** A starting point (adapt it to the log's real format; if `per_page` is not in the log, say so and stop):
```
# drop the key, keep only path, per_page and status; counts only
zcat -f <log files> | grep -E 'GET /[a-z]' | sed -E 's/apikey=[^& "]*/apikey=X/g' \
  | awk '{ for (i=1;i<=NF;i++) if ($i ~ /^"?GET$/) { url=$(i+1) } ; n=split(url, a, "?"); path=a[1]; pp="none"; if (match(url, /per_page=[0-9]+/)) pp=substr(url, RSTART+9, RLENGTH-9); st="?"; if (match($0, /" [0-9][0-9][0-9]/)) st=substr($0, RSTART+2, 3); print path, pp, st }' \
  | sort | uniq -c | sort -rn | head -60
```
(Tested by me on sample lines in uvicorn's usual access-log shape, `INFO:  <peer> - "GET /bills?... HTTP/1.1" 400 Bad Request`, where it printed `/bills 50 400`; check one real line first and fix the awk if the format differs.)
2. **Every request with a `per_page` above 20 on `/bills`** (whatever its status, expected: all `400`): how many, on which dates, and **from which kind of caller** (the broker host itself, the Mac Studio, the civic host, anything else; classes, not addresses). If there are none, say "none in <the span>".
3. **Any `400` on `/bills` that is not a `per_page` one** (the status alone is enough: a count), so we know what a normal 400 looks like there.
4. Anything odd in the log format or retention (for example, if the log only holds the last day).

## What it settles
If there are no requests above 20, nothing can depend on the refusal and OPEN-493 is as safe as it looks. If there are some, they are named by caller class and I check that caller's code before the cap is raised.

## What this does NOT do
No change of any kind. It reads logs you already hold. The OPEN-493 build (the cap, tests) and its later recreate of api-v3 are separate requests, after Ramon has read the PR; the recreate would be a different request from `ba65a42`'s, and you can fold them into one window if Ramon prefers.

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
