# Reply: api-v3 bill list phase timing and quiet re-time of the broker's lists (OPEN-484, OPEN-489, BROKER-424, BROKER-425). Read-only, run 2026-11-04 16:06 to 16:12 UTC, at the user's go

**The ~400 ms outside the two queries is the page's count.** Run inside the api container (`ddp-openstates-api-1`, image `5659b12c601a`, started 2026-11-03 20:56 UTC; no ECS task running, host load 0.3 to 0.5). Nothing changed: no index, no `ensure`, no restart, no deploy; PR #47 not run, PR #48 not pulled. No secrets printed. This is **before** any index build (the index request `6c59836` has not been run).

## Step 1: `bills_phases.py` (7 runs each; cold run, then again after 60 s)
| step | cold run 16:06:49 median / max | warm run 16:07:58 median / max |
|---|---|---|
| build query | 0.3 / 0.4 ms | 0.3 / 0.4 ms |
| **count (round trip)** | **480.7 / 514.1 ms** | **474.5 / 482.4 ms** |
| options | 0.5 / 0.5 ms | 0.4 / 0.8 ms |
| page query + load rows | 143.1 / 164.9 ms | 142.2 / 148.7 ms |
| rows to response objects | 2.3 / 2.6 ms | 2.4 / 3.0 ms |
| encode as JSON | 2.8 / 3.2 ms | 2.8 / 3.2 ms |
| **TOTAL of these steps** | **627.5 / 685.1 ms** | **625.7 / 634.2 ms** |

Everything except the count and the page query is under 10 ms in total. The steps add up to **626 to 628 ms**, and the endpoint answered in **642 ms** over HTTP in my baseline (`1f82173`): so the gap between "the two queries" and the endpoint is not extra work around them; it is that the **count as the endpoint runs it takes about 475 to 480 ms**, not the 80 ms my baseline reported.
Why the baseline's 80 ms differed (my reading, not tested): the baseline script built its count from the query with `order_by(None)` (as the request's own script did: "count without its sort"), while this script counts the query **with** the newest-action sort still on it (`q.count()`), which is what the endpoint code does. That matches the idea behind PR #48 ("a count without its sort"). I did not run a count both ways in the same script, so this is the likely cause, not a measured one.

## Step 2: connection cost
- First connection plus `select 1`, three times (a fresh Python process each time, measured from before the `api.db` import): **2,088, 2,179 and 2,131 ms.** This number includes starting Python and importing the api modules, so it is **not** the cost of connecting to the database alone; I did not separate them.
- `select 1` on one already-open session, loop of 20: **median 0.58 ms, max 0.73 ms, min 0.52 ms.** So a query on an open connection costs well under a millisecond of round trip; the 475 ms is query work, not the network.

## Step 3: quiet re-time of the broker's lists (`timing_prod_nosearchdiscovery.py`, 16:08:22 to 16:11:57 UTC, same way as before, through the public name; load 0.3)
| call | 02:20 UTC run, median ms | **16:10 UTC run, median ms** (1st, max) |
|---|---|---|
| bills list p1 | 1,620 | **1,642** (2,124, 2,124) |
| bills list US | 730 | **762** (630, 874) |
| legislators list p1 | 717 | **596** (2,175, 2,175) |
| legislators list US | 585 | **587** (608, 620) |
Other rows in the same run: jurisdictions 46, topics 144, bills resolve 32, bills tally 37, bill scorecard 36, legislator profile 45, votes p1 39, votes p20 39 (all 200). Back to back, openstates-bills: **[83, 807, 797, 803] ms** (the 0.8 s pause still there); burst of 3 at once: openstates-bills [117, 121, 155], legislators list [682, 688, 688] ms.
**The 02:20 numbers were not an abnormal window**: the quiet-host numbers are the same (1.6 s for the bills list, 0.6 s for the legislator list). The first call of each list is slower (2.1 s) than the median.
How the pieces fit for `bills list p1` (1.64 s through the broker): api-v3's endpoint 0.64 s (its count 0.48 s + page query 0.14 s + 0.01 s of other steps); the broker's part is the remaining about 1 s (not split further here).

## Not run / caveats
- Not run: nothing from the request. Step 2's first-connection number is of limited use (see above).
- The raw printed outputs are in `notes/api-v3-speed-20261104/prod-bills-phases-output.txt` and `prod-broker-retime-output.txt`.

## What happens next
Per the user's decision, I will build the index (`6c59836`) at a **quiet hour tonight** (around 04:00 UTC, after the busy US day) under the user's go, if the gates are clean then. I will say here when I start.
