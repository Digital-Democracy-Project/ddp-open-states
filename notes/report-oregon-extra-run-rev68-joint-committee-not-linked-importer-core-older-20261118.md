# Report: the extra Oregon run completed clean on revision 68, but the 931 joint-committee votes are NOT linked: the importer that loads into RDS runs an older core

Written 05:06 UTC 11-18 (date -u at write time). From the production EC2 host. User's words in session: "i approve the extra oregon scrape that you requested". One POST, no retry.

## The run (or-8290a384c248)
- Launched 04:41:59 UTC; ECS task on **ddp-scrapers:68**; ddp-sync read 93 Oregon people (no skip flag). The scraper's "no session provided, using active sessions" line named **{'2026R1'}** for both the bills scraper (04:42:38) and the votes scraper (04:42:47).
- **Pipeline done 04:46:42: status=completed failed=0 archived=True, 282.5 s** (scrape 190 s, archive 91 s).
- **Bills 304, vote events 724** (the same as the 03:34 run on 11-17). By organization: lower 357, upper 327, legislature 40.
- Archive summary: 304 bills checked, **fetched=0, skipped=1085, archived=0, fetch_errors=0, blocked=1** (the same one blocked document; nothing new to fetch).

## The expected result did not happen
You expected core #116 (OPEN-608) to link Oregon's joint-committee member votes (931 of 931). On production RDS after this run:
- Member votes by chamber class: **legislature (the joint committees) 931 total, 0 linked to a person**; lower 12,472 of 12,472 linked; upper 6,210 of 6,210 linked.
- Overall: 19,613 member votes, 18,682 linked, **unlinked share 4.75%**, i.e. unchanged (you expected below 4.7%).

## What I found (observed facts, then the likely cause)
- Facts: the cloud path loads the scraped bills into RDS inside **ddp-sync's container**, using its own openstates-core copy at /opt/openstates-core (version 6.26.5, built into the image on 11-17 18:40 UTC, the cb5eade build; pyproject dated 11-13). I compared that copy's openstates/importers/base.py with core commits: it is **identical to core 44c3b8dc** (v62's core, 0 diff lines), differs from **b5728c43** (v63's, which has #116) by 9 lines, and from **46cc5759** (v65's) by 35 lines.
- Likely cause (not proven; I did not trace the importer code path itself): the importer that links voters and applies the state action rules (`openstates/ddp_states/<st>.py`) is this container's older copy, not the scrapers image's core. So **#116's joint-committee lookup and v65's action rules for ne, ma, ut, mi, va (and v62-to-v65's other importer changes) do not apply to cloud imports until ddp-sync's image is rebuilt with the newer core.** The scrapers image's core only matters for the collection step. If that is right, every state's "first run on v63/v64/v65" has been loaded with the 44c3b8dc importer.
- I have not changed anything. A fix is a ddp-sync image rebuild at the target core (plus a restart), which needs the user's go and your decision on which core; I will not do it unasked.

Question for you: how does ddp-sync's image get its core (the root Dockerfile's openstates-builder stage reads requirements-openstates.txt plus the local checkout)? Please confirm the cause and say which core the rebuild should carry.
