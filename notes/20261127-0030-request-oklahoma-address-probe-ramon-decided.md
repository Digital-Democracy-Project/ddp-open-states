# REQUEST (Ramon decided, 11-27): build the Oklahoma address-and-connection probe; no more full retries

Ramon's decision in this session (a plain-language question about Oklahoma's three same-way failures; his choice, the first and recommended option): **"Ask the dev for a probe."** Not another full attempt, not leaving it alone.

## What he approved
* A small step that **records the public address our scraper leaves from, and tests the connection to `webapps.oklegislature.gov` (a plain connect with its timing), at the start of an Oklahoma collection task** (or as a one-off probe task), so we can tell whether our address is being dropped. Where it sits is yours to choose; the evidence is below.
* **No more full Oklahoma retries meanwhile.** The 2026 session stays unloaded; 2025's data is unchanged.

## Why (from my 19:15 note)
All the failures so far are the same: the very first request (`GET https://webapps.oklegislature.gov/WebApplication3/WebForm1.aspx`) never connects; urllib3 retries three times about 2 min 13 s apart; then `ConnectTimeout`, exit 1, about 541 to 545 s; no HTTP status ever; no 403, 429 or 5xx; varied hours; the 2025 retry once succeeded. **The OPEN-892 logging (outbound address and connect timing) printed nothing in the v98 run**: my reading is that it sits on a different request path than this first GET, which I did not check in the code. So "which address did we leave from" is still unanswered.

## Needs, when the probe exists
A new image (Ramon builds; v99 or later) or a probe task definition he approves; then I will run it once on his go and report: the address, the connect result and timing, and which address the other scrapers use in the same minute (for comparison).

Tickets: OPEN-887 (Oklahoma), OPEN-892 (the logging). Nothing was changed on production for this.
