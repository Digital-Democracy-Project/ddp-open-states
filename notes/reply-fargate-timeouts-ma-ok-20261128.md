# REPLY (dev agent): Massachusetts and Oklahoma cloud timeouts: a probe for every state is built (PR open, not merged, no image yet); what the evidence says about a block; what Ramon must decide. 2026-11-28

**What I need from you:**
1. **Nothing to run yet.** The probe is in a pull request (OPEN-887, `ddp-open-states`) that Ramon has not merged, so it is in no image. Please do not retry Massachusetts or Oklahoma before then (Ramon's rule stands).
2. **After Ramon merges it and builds the next scrapers image** (I do not know the number; he will say), and on Ramon's go: run ONE Oklahoma `2026` scrape and ONE Massachusetts scrape, and paste back **only these lines** from each task's collection log: the single line that starts `PROBE ok:` / `PROBE ma:` (it comes before any scraper output), and the first `ConnectTimeout` or `ERROR` line if the run still fails. Keep the address in that line out of the public branch: tell Ramon in session, and write "address seen, recorded in session" here.
3. A run that reaches the site needs nothing else. A run that does not still tells us what the task could see, which is the point.

**What the probe does.** At the start of every state's collection task (all 30 states in the manifest, not only Oklahoma) it prints ONE line: `PROBE <state>: egress address <ip>; connect: <host>:443 ok 0.21s` (or `FAILED TimeoutError after 10.0s`). The address is what a public lookup service sees the task leave from. The connect test opens a plain TCP connection to the state's site (the host or hosts in the manifest's new `scrape.probe_urls`, read from each scraper's own source) and closes it: **no request is sent to the state.** It prints a line, never retries, never changes the address, and cannot fail the run by itself (a lookup that fails prints `unknown (<error name>)`; a log line that cannot be written is ignored). Added about 10 s of waiting at most per step on a bad network; a slow name lookup could take longer, as it would for the scraper.

**Already there before this (I read the code, did not run it):** OPEN-892/904 (merged, in v99/v100) is **Oklahoma-only** (`scrapers/ok`): it logs the address and connection errors through the scraper's logging, as INFO and WARNING lines. In the v98 run it printed nothing, and it never existed for Massachusetts. The new line is printed straight to the task's log, so it shows for every state. Oklahoma's own logging is left as it is.

**Are the state sites blocking the cloud address range? Not verified; the evidence points both ways, and nothing here proves a block.**
- *Known (your measurements, read in the notes):* Oklahoma failed 3 of 11 collection tasks on 11-23..11-27 with a connect that never completed (no HTTP status, no 403/429/5xx, no reset); the others ran for hours. Massachusetts: the 11-08 cloud run completed; on 11-28 two runs 20 minutes apart both failed at the first request after about 3 minutes; the same API from the prod host's own address answered 200 in about 6 s.
- *Known (repo plans):* Fargate tasks run in public subnets with a public address assigned per task and no NAT, so each task normally gets its own address from AWS's range, and we log none of them today.
- *Fits a block:* a site that silently drops connections from some addresses (or from a whole cloud range) looks exactly like this, and the prod host's address is not in a cloud range.
- *Fits something else:* it was intermittent for Oklahoma (a failure and a success 90 s apart); a path problem on either side looks the same; Massachusetts' two failures could share one bad address or one bad half-hour.
- *Not known:* which addresses the failing and working tasks used. That is the one thing the probe adds. Until a failing task's address is on record, "blocked" is a guess.

**Options for the route, with cost (none is built; each changes where or how a scrape runs, so each is Ramon's call):**
1. **Do nothing more, wait for the probe run.** Cost: one more run per state, and Massachusetts' long scrape stays unloaded until then. Risk: none beyond waiting.
2. **A retry policy at the whole-task level** (the task tries again after a few minutes, which usually gets a new address). Cost: a small code and rule change, and Ramon has said no repeated retries. It would hide a real block until it persists, and repeated attempts against a site that is dropping us is the pattern we have said we avoid. Only worth it if the probe shows the address changes between tasks and the failures follow a bad address.
3. **A fixed outbound address (NAT gateway with an Elastic IP) for the collection tasks.** Cost: a monthly charge and a network change in ddp-infra; one address means a block, if any, hits every state at once, and the plan notes say this recreates the centralised-address problem. Only if a state agrees to allow that one address.
4. **Run Massachusetts (and/or Oklahoma) collection from the prod host.** Cost: moves heavy long runs back onto the Mac-side path we are leaving (a Massachusetts run hit the 12-hour limit on 11-01); it is a change of where a scrape runs. Works today because that address is answered.
5. **Ask the legislatures' web teams** (Ramon's earlier idea): whether they filter cloud addresses or throttle automated clients, and whether a bulk-data route exists. A conversation, not a technical workaround.
Rules unchanged: no user-agent change, no address rotation to get round a block, no pacing change.

**Which image carries it.** The next scrapers image built from `main` after Ramon merges the OPEN-887 pull request. The change is in `cloud_collector.py`, `validate_jurisdictions.py` and `jurisdictions.yaml`, all already copied into the image; it needs the manifest on the image only (no migration, no setting, no task-definition change). Not in v100.

**What must be decided by Ramon:** (a) merge the probe PR and build the image; (b) the go for one Oklahoma and one Massachusetts run to read the line; (c) after the line is read, which option above, if any; (d) whether to contact the legislatures.

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
