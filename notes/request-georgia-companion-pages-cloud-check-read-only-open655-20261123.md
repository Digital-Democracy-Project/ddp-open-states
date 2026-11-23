# REQUEST (not a GO): a one-off, read-only look at five Georgia bill pages from the cloud, because the Mac cannot reach Georgia's site. OPEN-655. 2026-11-23 (Mac side, State Specific Handling)

**Not a GO.** Read-only: plain web requests to Georgia's public site, nothing written to any database, no scrape, no setting changed. Ramon asked for it (2026-11-23, through the PM session): "this Mac can't reach Georgia's site, so write a prod-agent request note for a one-off cloud check of the Georgia companion pages".

## Why
OPEN-655 asks whether Georgia's legislature publishes companion or related-bill links. The data the Georgia scraper reads (the web service at `webservices.legis.ga.gov`) has no link field: 25 random 2025-26 bills were read on 2026-11-23 (PLAN-companion-lineage §5.3.1, ddp-infra #568). The **public bill pages** at `www.legis.ga.gov/legislation/<id>` are still unread: from this Mac they refuse or time out (2026-11-20, and 2026-11-23 in a real Chrome and with plain requests, while another legislature's site answered; ddp-infra #572). This is the last open part of step 1.

## The check
From any cloud host you normally use for outbound web requests (the EC2 host, or a one-off command in the scrapers' Fargate network), **plain GET** these five pages, one after another, no faster than one a second:

| Bill (2025-26) | Page |
|---|---|
| HB 66 | `https://www.legis.ga.gov/legislation/69385` |
| HB 1097 | `https://www.legis.ga.gov/legislation/72613` |
| SB 232 | `https://www.legis.ga.gov/legislation/70640` |
| HB 513 | `https://www.legis.ga.gov/legislation/70486` |
| SB 586 | `https://www.legis.ga.gov/legislation/73644` |

All five are among the 25 already read from the web service. The page numbers are that service's own legislation ids.

**Report, per page:**
1. The HTTP status and the size of the answer.
2. Whether the answer holds the bill's text and history, or is only a script shell that loads them later. If it's a shell: the address(es) of the JSON it loads, if they're plain to see in the HTML (for example under `/api/`), and the same checks below on that JSON for these five bills.
3. Any heading or list named "Companion", "Identical", "Related", "Similar" or "See also" (with the exact wording).
4. Every other bill named on the page (HB/SB/HR/SR and a number other than the bill's own), with the words around it.

Saving the five answers somewhere the Mac side can read is welcome but not needed. Quoted excerpts are enough.

## What happens next (Mac side)
* **No companion or related list on any page:** OPEN-655's step 1 is complete; the plan records "no companion listed by the legislature" for Georgia, and the ticket closes.
* **A list is there:** it becomes a Georgia scraper ticket like the other states' (OPEN-649, OPEN-783). If it isn't a companion, the legislature's other links are stored as related too (Ramon's 2026-11-23 decision for Nebraska, Louisiana and New Mexico).
* **The site refuses the cloud host too:** say so (status, or the error). Ramon then decides whether a person looks with a browser.

## Not asked
No scrape or re-import, no scraper or image change, and nothing on the broker.
