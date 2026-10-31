# Reply: OPEN-458 Part 2 — Saturday 10-31 launches (read-only), 15:55 UTC

Sunday 11-01 02:00 batch not yet run; two session checks scheduled (02:17 UTC start, 13:07 UTC finish) and will be reported in a follow-up.

**Revision: NOT confirmed.** My role cannot read ECS and the ddp-sync log does not name the task revision, so I can say the runs were healthy but not that they ran on revision 42. Please confirm in the console, or name a v39-only log marker and I will look for it.

| Launch (UTC) | Stream | Result |
|---|---|---|
| WA scrape 02:30 | 2f4faa22... | run wa-3e9d7ea5ed05 status ok, found 0, 244 s; ends "no new objects since cutoff (no-op)" (ScrapeError no objects returned, handled) |
| WA archive 02:36 | 54031cba... | ok: 3,411 checked, fetched 0, no errors |
| US scrape 03:01 | 1f7ae9f9... | usa-abf2c898c754 ok, found 400, 349 s; 11 "Unable to parse vote date" lines (individual senate.gov roll-call files) |
| US archive 03:09 | 5bc4d0ab... | ok: 39,136 checked, fetched 40, archived 40, blocked 570, errors 0 |
| US scrape 04:23 | 22b812c7... | usa-7267e3a5780f ok, found 140, 109 s |
| US archive 04:27 | a04f980e... | ok: fetched 4, archived 4, blocked 570, errors 0 |
| AL archive 05:00 | aee617cf... | ok, fetched 0 |

The 570 blocked govinfo PDF responses ("expected application/pdf, got HTML") — I did not compare against an older run.

**Counts vs 10-30 18:15 baseline** (`counts-20261031.txt`, taken 15:49 UTC): eight states identical. US bills 39,097 -> 39,136 (+39); vote events 1,604 -> 1,600 (-4, -0.25%); person votes 561,033 -> 560,633 (-400). Inside the 2%/5% thresholds. Cause of the 4 missing vote events not investigated. Duplicates, VA 'H VOTE:' and FL committee lines unchanged.

No rollback performed.
