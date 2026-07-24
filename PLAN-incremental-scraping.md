# Plan: Incremental Bill Scraping — All Active Jurisdictions

**Status: IMPLEMENTED 2026-06-22.** All 8 jurisdictions patched. Shell timestamp layer live. See `logs/last-run/` for per-jurisdiction cutoff files and RUNBOOK.md for operational details.

## Context

Every nightly scrape was a full rescrape. FL 2026 regular paginates ~2,000 bills
through flsenate.gov and hits flhouse.gov once per bill — 30–40 hours per run due
to bot-detection backoffs. USA federal takes 3–4 hours for 10k+ bills. Both run daily.
WA and the secondary states (MI, UT, MA, AZ, VA) also rescrape fully on their cadences.

Goal: for every jurisdiction, nightly runs only fetch bills updated since the last run.
Implementation is local patches only (no upstream PRs).

---

## Standard pattern (applies to every state)

1. **Shell layer** (`run-scrape.sh`): record a UTC timestamp after each successful import
   in `logs/last-run/<key>.ts`. On the next run, read it back and pass `start=<timestamp>`
   to `os-update`.

2. **Scraper** (`scrapers/<state>/bills.py`): accept a `start=` kwarg in `scrape()`, parse
   it, and skip bills whose last-action/last-modified date is ≤ start. The correct skip
   mechanism in spatula is `raise SkipItem(...)` from `process_item()`.

3. **Format**: `%Y-%m-%dT%H:%M:%S` (ISO 8601 with T separator, no space) throughout —
   avoids bash word-splitting when `start=2026-06-19T01:00:00` is passed as a single
   CLI token.

---

## Implementation status (as of 2026-06-22)

| State | Incremental support | Signal used | SHA | Notes |
|---|---|---|---|---|
| USA | ✅ | GovInfo sitemap `lastmod` | `371e7e6` | Format string fix only — filter already existed |
| FL | ✅ | Last-action date in HTML `td[3]` | `5ccf523` | `SkipItem` in `BillList.process_item()`; td[3] verified against live HTML |
| WA | ✅ | `CurrentStatus/ActionDate` from GetLegislation | `8bc4525` | Still O(n) GetLegislation calls; skips 5-6 downstream calls per unchanged bill |
| MI | ✅ | `dateFrom=` URL param | `b9e2d6f` | Semantics unverified — may be intro date not last-action date |
| UT | ✅ | `actionHistoryList[0].actionDate` | `4cb3f8d` | Saves processing only, not HTTP calls |
| MA | ✅ | `PrimarySponsor.ResponseDate` | `e9e4c28` | Weak proxy — sponsor date not action date; acceptable since votes are now scraped |
| AZ | ✅ | `max(BillStatusAction.ReportDate)` | `939b4b7` | Still O(n) API calls; skips sub-calls for unchanged bills |
| VA | ✅ | `max(EventDate)` from events call | `bdd256b` | Events call unavoidable; saves 3/4 per-bill calls |

All patches on `ddp-incremental` branch in `openstates-scrapers` fork. Cherry-picked via `apply-local-patches.sh`.

---

## Prerequisite fix (ship first, independently)

**File:** `run-scrape.sh` lines 55–61

Add `fl` to the `--allow_duplicates` guard (same pagination-overlap bug as MI #5697;
FL import currently fails with `DuplicateItemError` for HB 6009):

```bash
if [ "$STATE" = "mi" ] || [ "$STATE" = "fl" ]; then
    $OS_UPDATE "$STATE" --import --allow_duplicates $DIR_FLAGS \
        >> "$LOG_DIR/scraper.log" 2>&1
```

---

## Implementation

### Part 1 — Shell timestamp layer (`run-scrape.sh`)

**Key naming:** `$STATE` + `$SESSION_ARG` with spaces/`=` replaced by `_`:
- `fl session=2026` → `logs/last-run/fl_session_2026.ts`
- `usa session=119 chamber=lower` → `logs/last-run/usa_session_119_chamber_lower.ts`
- `wa` (no session arg) → `logs/last-run/wa.ts`

**Add after line 6 (`SESSION_ARG=...`):**

```bash
LAST_RUN_DIR="$LOG_DIR/last-run"
SCRAPE_KEY=$(echo "${STATE}${SESSION_ARG:+ $SESSION_ARG}" | tr ' =' '__')
TS_FILE="$LAST_RUN_DIR/${SCRAPE_KEY}.ts"

INCREMENTAL_FLAG=""
if [ -f "$TS_FILE" ]; then
    LAST_RUN=$(cat "$TS_FILE")
    START_ARG=$(python3 -c "
import datetime, sys
try:
    dt = datetime.datetime.strptime('$LAST_RUN', '%Y-%m-%dT%H:%M:%S')
    print((dt - datetime.timedelta(hours=1)).strftime('%Y-%m-%dT%H:%M:%S'))
except Exception:
    sys.exit(0)
" 2>/dev/null)
    if [ -n "$START_ARG" ]; then
        INCREMENTAL_FLAG="start=$START_ARG"
        echo "[$(date)] Incremental run: start=$START_ARG" | tee -a "$LOG_DIR/scraper.log"
    fi
fi
```

Append `$INCREMENTAL_FLAG` (unquoted — no spaces in value) to both `os-update` calls
on lines 42 and 47. Remove the `case "$STATE"` guard — once all scrapers support
`start=`, it's passed universally. (Scrapers that don't implement `start=` will just
receive an unexpected kwarg and fail loudly, making it easy to detect missing
implementation during rollout. Alternatively, keep the guard and expand it state by
state as each scraper is patched.)

**Add after the import log line (line 63):**

```bash
mkdir -p "$LAST_RUN_DIR"
date -u +%Y-%m-%dT%H:%M:%S > "$TS_FILE"
```

Timestamp is written only on successful import (`set -e` trap prevents writing on
failure), so a failed run preserves the previous checkpoint.

---

### Part 2 — USA scraper (1-line fix)

**File:** `openstates-scrapers/scrapers/usa/bills.py:102`

```python
# before
start = datetime.datetime.strptime(start, "%Y-%m-%d %H:%I:%S")
# after
start = datetime.datetime.strptime(start, "%Y-%m-%dT%H:%M:%S")
```

Update comment on line 99:
```python
# to scrape everything UPDATED after a given date/time, start="2020-01-01T22:01:01"
```

Mechanism (already implemented, lines 137–150): iterates GovInfo sitemap, only fetches
bills where `lastmod > start`. Skips ~95% of the 10k bills on a daily incremental run.

---

### Part 3 — FL scraper

**File:** `openstates-scrapers/scrapers/fl/bills.py`

**3a — `FlBillScraper.scrape()` (line 896):** add `start=None`, parse it, pass to BillList:

```python
def scrape(self, session=None, start=None):
    ...
    start_dt = None
    if start:
        try:
            start_dt = datetime.datetime.strptime(start, "%Y-%m-%dT%H:%M:%S")
        except ValueError:
            self.warning(f"Invalid start= '{start}', doing full scrape")

    def do_scrape_with_retry():
        bill_list = BillList({
            "session": session,
            "house_session_number": house_session_number,
            "start": start_dt,  # None = full scrape
        })
        yield from self._process_bill_list(bill_list)
```

**3b — `BillList.process_item()` (after line 168):** add SkipItem filter.

Add `SkipItem` to the existing spatula import on line 16:
```python
from spatula import HtmlPage, HtmlListPage, XPath, SelectorError, PdfPage, URL, SkipItem
```

After extracting `title`:
```python
start = self.input.get("start")
if start is not None:
    last_action_cell = item.xpath("string(../following-sibling::td[3])").strip()
    date_matches = re.findall(r"\d{1,2}/\d{1,2}/\d{4}", last_action_cell)
    if date_matches:
        try:
            last_action = datetime.datetime.strptime(date_matches[0], "%m/%d/%Y")
            if last_action < start:
                raise SkipItem(f"{bill_id} last action {date_matches[0]} ≤ cutoff")
        except ValueError:
            pass  # unparseable date — scrape this bill
    # No date found → fall through (scrape this bill — safe)
```

**Column index (`td[3]`):** Assumed to hold last-action text like
`"3/13/2026 S Died in Appropriations"` based on typical flsenate.gov table layout.
**Verify before committing:**

```python
from lxml import html; import urllib.request
tree = html.fromstring(urllib.request.urlopen(
    "https://flsenate.gov/Session/Bills/2026?chamber=both").read())
items = tree.xpath('//th/a[contains(@href, "/Session/Bill/")]')
print([td.text_content().strip()[:50] for td in items[0].xpath('../following-sibling::td')])
```

If the column index differs for special sessions, the empty-list fallback path handles
it safely — bills without a parseable date are always scraped.

**Performance impact:** Every bill that passes `BillList.process_item` triggers a
flhouse.gov `HouseSearchPage` request (60-second bot-detection backoff when blocked).
Skipping ~1,950 of ~2,000 bills eliminates ~1,950 flhouse.gov calls. FL scrape time
drops from 30+ hours to minutes on a nightly run.

Note: BillList still paginates all 38 pages to check dates — unavoidable without
server-side date filtering. But 38 lightweight HTML GETs are negligible.

---

### Part 4 — WA scraper

**File:** `openstates-scrapers/scrapers/wa/bills.py`

**How the scraper works today:**
- `scrape()` (line 241) → `scrape_chamber()` (line 259) → `GetLegislationByYear?year={y}`
  returns ~3,000 bill summaries (`LegislationInfo`) with NO date fields
- Then `scrape_bill()` (line 306) is called per bill → `GetLegislation?biennium=X&billNumber=Y`
  → response includes `CurrentStatus/ActionDate` (line 319)
- Each `scrape_bill()` also calls: `scrape_actions`, `scrape_sponsors`, `scrape_hearings`,
  `scrape_votes`, `scrape_chapter`, `scrape_cites` — 5-6 additional API calls per bill

**Approach — filter in `scrape_bill()` using `CurrentStatus/ActionDate`:**

`GetLegislationByYear` has no date filtering, so we still make one `GetLegislation` call
per bill. But after parsing that response we can check `CurrentStatus/ActionDate` and
skip the 5-6 downstream sub-scraper calls for unchanged bills:

```python
def scrape(self, chamber=None, session=None, start=None):
    # parse start= if provided (same format as other scrapers)
    self._start_dt = None
    if start:
        try:
            self._start_dt = datetime.datetime.strptime(start, "%Y-%m-%dT%H:%M:%S")
        except ValueError:
            self.warning(f"Invalid start= '{start}', doing full scrape")
    # ... rest of existing scrape() unchanged ...
```

In `scrape_bill()` (line 306), after fetching and parsing the `GetLegislation` response
(line 319), add an early-return check:

```python
# After: page = xpath(page, "//wa:Legislation")[0]
if self._start_dt:
    action_date_str = xpath(page, "string(wa:CurrentStatus/wa:ActionDate)")
    if action_date_str:
        try:
            action_dt = datetime.datetime.fromisoformat(action_date_str.rstrip("Z"))
            if action_dt <= self._start_dt:
                return  # skip sponsors, actions, hearings, votes, etc.
        except ValueError:
            pass  # unparseable — fall through to full scrape
```

**Impact:** One `GetLegislation` call per bill is unavoidable (no list-level date data).
But skipping the 5-6 downstream calls per unchanged bill reduces per-run API load by 5-6×
when most bills haven't changed. For WA's ~3,411 bills, if 50 changed: ~3,411 calls
instead of ~3,411 + 3,411×5 = ~20,466.

**Future upgrade path:** If `GetLegislativeStatusChangesByDateRange` exists in the WA
WSDL (verify at `http://wslwebservices.leg.wa.gov/legislationservice.asmx`), it would
return only bill IDs with status changes in a date range — eliminating the O(n)
`GetLegislation` calls entirely. Check the WSDL and upgrade the approach if available.

WA session ends each spring and is currently inactive; implement after FL/USA are validated.

---

### Part 5 — MI

**File:** `openstates-scrapers/scrapers/mi/bills.py`

**How the scraper works:**
- `scrape()` (line 47) → `POST https://legislature.mi.gov/Search/ExecuteSearch` with
  a search form body that includes `dateFrom=&dateTo=` parameters (currently empty, line 51)
- Returns HTML table; extracts bill links from `td[1]/a`
- `scrape_bill()` (line 78) → fetches per-bill detail page → `scrape_actions()` (line 111)
  reads History table where `td[1]` contains the action date

**Approach — populate `dateFrom=` in the search URL (fastest path):**

The search URL at line 51 already has `dateFrom=` in its query string. If this parameter
filters by last-action date (not just introduction date), adding `start=` support is a
near-zero-cost change:

```python
def scrape(self, session, start=None):
    date_from = ""
    if start:
        try:
            dt = datetime.datetime.strptime(start, "%Y-%m-%dT%H:%M:%S")
            date_from = dt.strftime("%Y-%m-%d")
        except ValueError:
            pass
    # Pass date_from into the search URL/form body where dateFrom= currently appears
```

**⚠ Must verify:** The `dateFrom=` parameter's actual semantics — does it filter by
introduction date or last-action date? Test by setting `dateFrom=2026-06-01` and checking
whether bills with earlier last actions are excluded. If it only filters by introduction
date, this won't help for incremental runs (most bills were introduced months ago).

**Fallback if `dateFrom=` is introduction-only:** filter per-bill using the History table.
In `scrape_bill()`, the first row of `//div[@id='History']/table/tbody/tr` at line 115
has the most recent action in `td[1]`. Check this date and `return` early if ≤ start.
Still O(n) HTTP calls but avoids full bill processing.

**Note:** MI uses `--allow_duplicates` (pagination-overlap bug). This is unchanged.
MI does not use spatula — use `return` / `continue`, not `raise SkipItem`.

---

### Part 6 — UT

**File:** `openstates-scrapers/scrapers/ut/bills.py`

**How the scraper works:**
- `scrape()` (line 39) → `https://le.utah.gov/billlist.jsp?session={slug}` → HTML list
  with bill IDs and links only, **no date info in list**
- `scrape_bill()` (line 95) → for 2025+ sessions, calls `scrape_bill_details_from_api()`
  (line 214) → `GET https://le.utah.gov/data/{session}/{bill}.json` — **one request returns
  ALL bill data** including `actionHistoryList[0].actionDate` (most recent action)

**Approach — check `actionHistoryList[0].actionDate` after fetching JSON:**

Since the bill list has no date info, we must fetch each bill's JSON regardless. But once
we have the JSON, we can return early before processing sponsors, versions, actions, and
votes (all of which are in the same JSON blob — no additional HTTP requests, just parsing).

In `scrape_bill_details_from_api()` (line 214), after `data = json.loads(response.content)`
at line 218:

```python
if start and data.get("actionHistoryList"):
    most_recent = data["actionHistoryList"][0]  # list is newest-first
    date_str = most_recent.get("actionDate", "")
    try:
        # UT dates: "1/15/2026 1:41 PM" or "01/15/2026"
        action_dt = dateutil.parser.parse(date_str)
        start_dt = datetime.datetime.strptime(start, "%Y-%m-%dT%H:%M:%S")
        if action_dt.replace(tzinfo=None) <= start_dt:
            return  # skip sponsors, versions, actions, votes
    except (ValueError, TypeError):
        pass  # unparseable — fall through to full processing
```

**Impact:** UT makes exactly 1 HTTP request per bill (its JSON API is all-in-one). The
savings are processing time and DB import, not HTTP calls. UT sessions run Jan–Mar and
are currently inactive, so this is lower urgency.

**Note:** UT does not use spatula for this path — use `return` not `raise SkipItem`.
Pass `start` through the call chain: `scrape() → scrape_bill() → scrape_bill_details_from_api()`.

---

### Part 7 — MA

**File:** `openstates-scrapers/scrapers/ma/bills.py`

**How the scraper works:**
- `scrape_bill_list()` (line 87) → `GET https://malegislature.gov/api/GeneralCourts/{session}/Documents`
  → JSON array of all bills in the session (~10,891 records)
- Each record includes `PrimarySponsor.ResponseDate` and `Cosponsors[].ResponseDate`
  (ISO 8601 with ms, e.g. `"2023-01-04T10:02:36.727"`) — these are the dates sponsors
  **acknowledged** the bill, not the dates of legislative action
- `scrape_chamber()` (line 111) → iterates `self.bill_list` → `scrape_bill()` per bill

**Approach — filter in `scrape_bill_list()` using `PrimarySponsor.ResponseDate`:**

`ResponseDate` is a weak proxy — it reflects when a legislator last responded (e.g.,
added a cosponsor), not when the bill had floor action or a vote. For MA's 2-year sessions
with no vote events tracked, this may be the best available list-level signal.

In `scrape_bill_list()` at lines 95–109, before appending to `self.bill_list`:

```python
if start:
    start_dt = datetime.datetime.fromisoformat(start)
    # Collect all ResponseDates from primary sponsor and cosponsors
    response_dates = []
    if row.get("PrimarySponsor", {}).get("ResponseDate"):
        try:
            response_dates.append(
                datetime.datetime.fromisoformat(
                    row["PrimarySponsor"]["ResponseDate"].split(".")[0]))
        except ValueError:
            pass
    for cs in row.get("Cosponsors", []):
        if cs.get("ResponseDate"):
            try:
                response_dates.append(
                    datetime.datetime.fromisoformat(cs["ResponseDate"].split(".")[0]))
            except ValueError:
                pass
    if response_dates and max(response_dates) <= start_dt:
        continue  # skip this bill
```

**⚠ Caveat:** `ResponseDate` is sponsorship metadata. A bill with a new floor action
but no sponsor changes since `start` will be incorrectly skipped. For MA (which has
0 vote events — it doesn't scrape votes/actions), this may be acceptable. If MA ever
starts collecting votes, this filter would need to be revisited.

MA does not use spatula for bill list — use `continue`, not `raise SkipItem`.

---

### Part 8 — AZ

**File:** `openstates-scrapers/scrapers/az/bills.py`

**How the scraper works:**
- `scrape()` (lines 396–434) → POST to set session cookie → `GET https://www.azleg.gov/bills/`
  → HTML table of bill IDs with **no date fields**
- Per bill: `GET https://apps.azleg.gov/api/Bill/?billNumber=X&sessionId=Y&legislativeBody=Z`
  → JSON with full bill data including `BillStatusAction[].ReportDate` (ISO 8601 with ms),
  `IntroducedDate`, `PreFileDate`, `GovernorActionDate`

**Approach — check most recent `BillStatusAction.ReportDate` in the detail API response:**

Since the HTML list has no dates, we need the per-bill API call to get any date. This
means AZ incremental does NOT reduce HTTP calls — it reduces DB write and parsing work
per unchanged bill. The per-bill API call is unavoidable.

In `scrape_bill()` (or in the `scrape()` loop at line 432 after calling the detail API),
after loading the JSON:

```python
if start_dt and page:
    all_dates = []
    for action in page.get("BillStatusAction", []):
        d = action.get("ReportDate", "")
        if d:
            all_dates.append(d.split(".")[0])  # strip ms
    for key in ("IntroducedDate", "PreFileDate", "GovernorActionDate"):
        if page.get(key):
            all_dates.append(page[key].split(".")[0])
    if all_dates:
        latest = max(datetime.datetime.strptime(d, "%Y-%m-%dT%H:%M:%S")
                     for d in all_dates)
        if latest <= start_dt:
            continue  # skip sponsors, versions, votes sub-scraper calls
```

**Impact:** AZ makes 1 primary API call per bill already. Saving the follow-on sub-scraper
calls (sponsors, versions, votes — separate API calls) for unchanged bills is the main win.
AZ session runs Jan–April; currently inactive. Lower urgency.

AZ does not use spatula for bill list — use `continue` / `return`.

---

### Part 9 — VA

**File:** `openstates-scrapers/scrapers/va/bills.py`

**How the scraper works:**
- `scrape()` → `POST https://lis.virginia.gov/Legislation/api/getlegislationlistasync`
  with `{"SessionCode": <int>, "IncludeFailed": true}` → JSON with `Legislations[]` array
- Per bill: 4 additional API calls — events (`getlegislationeventbylegislationidasync`),
  texts (`getlegislationtextbyidasync`), patrons (`GetLegislationPatronsByIdAsync`),
  votes (`getvotebyidasync`)

**API research findings (2026-06-22):**

The bill list response has 5 date fields — `CandidateDate`, `VersionDate`,
`HousePassageDate`, `SenatePassageDate`, `IntroductionDate` — but **all are null for
every bill** across both the 2026 regular session (3,955 bills) and 2026S1 special
session (273 bills). These fields are never populated by the API.

Server-side date filtering does not exist:
- `startDate`/`ModifiedAfter`/`EventDateFrom` params in the POST body have no effect
  (still returns all 3,955 bills)
- Guessed date-range endpoints (`getlegislationbyeventdateasync`,
  `getlegislationeventbydateasync`, etc.) all return 404
- The `startDate` GET param on the per-bill events endpoint is silently ignored (returns
  the same full event list regardless)

The **only reliable date signal** is `EventDate` on individual event records returned by
`getlegislationeventbylegislationidasync`. Each event has a precise ISO 8601 timestamp.

**Approach — check max EventDate from the events call, skip remaining 3 calls if unchanged:**

The events call is already required for `add_actions()`. By checking `max(EventDate)`
before calling `add_versions()`, `add_sponsors()`, and `add_votes()`, we save 3 of 4
per-bill API calls for unchanged bills:

```python
def scrape(self, session=None, scrape_chunk_number=None, start=None):
    ...
    start_dt = None
    if start:
        try:
            start_dt = dateutil.parser.parse(start)
        except Exception:
            self.warning(f"Invalid start= '{start}', doing full scrape")
```

In the bill loop (line 92), refactor so events are fetched first and the result is
passed to `add_actions()` instead of re-fetched:

```python
for row in bill_list:
    ...
    bill = Bill(...)

    events_data = self._fetch_events(row["LegislationID"])
    self.add_actions(bill, events_data)   # pass pre-fetched data

    if start_dt:
        dates = [e["EventDate"] for e in events_data if e.get("EventDate")]
        if dates:
            latest = max(dateutil.parser.parse(d) for d in dates)
            if latest.replace(tzinfo=None) <= start_dt.replace(tzinfo=None):
                # Bill unchanged — skip texts, patrons, votes
                bill.add_source(...)
                yield bill
                continue

    self.add_versions(bill, row["LegislationID"])
    self.add_sponsors(bill, row["LegislationID"])
    yield from self.add_votes(bill, row["LegislationID"])
    ...
```

**Impact:** The bill list fetch (1 call) and one events call per bill are unavoidable.
But for unchanged bills, the 3 remaining per-bill calls (texts, patrons, votes) are
skipped. For the 2026 regular session with ~3,955 bills and ~50–100 changing per active
day: currently ~15,820 calls; incremental ~4,105 calls (~74% reduction). For a completed
session (most bills inactive), savings approach ~75%.

**Note:** VA sessions are short (Jan–Mar regular, occasional specials). The 2026 regular
session is complete; 2026S1 special session is the active one (273 bills). With only 273
bills and 4 calls each = ~1,092 calls per run, VA is the lowest-urgency jurisdiction for
incremental work — but the pattern is clean to implement.

`VA_API_KEY` must be set in the environment (from `.env` via `activate.sh`).

---

## Deployment convention

Every scraper change goes through the local-patches mechanism:

```
# In openstates-scrapers (after apply-local-patches.sh puts us on local-patches):
git add scrapers/<state>/bills.py
git commit -m "feat(<state>): add start= incremental filtering"
# Note the SHA
```

Add to `apply-local-patches.sh`:
```bash
cherry_pick <sha>  # feat(<state>): start= incremental filtering
```

The `case "$STATE"` guard in `run-scrape.sh` can serve as a rollout gate — add each
state to the `case` as its scraper patch is validated.

---

## Files changed

| File | Change | Skip mechanism |
|---|---|---|
| `run-scrape.sh` | `--allow_duplicates` for FL; timestamp read/write; `$INCREMENTAL_FLAG` | — |
| `apply-local-patches.sh` | Cherry-pick SHAs for each state's `start=` patch | — |
| `scrapers/usa/bills.py` | Fix `%I`→`%M` + space→`T` at line 102 | existing (sitemap filter) |
| `scrapers/fl/bills.py` | `start=` in `scrape()` + filter in `BillList.process_item()` | `raise SkipItem` (spatula) |
| `scrapers/wa/bills.py` | `start=` in `scrape()`; early `return` in `scrape_bill()` after checking `CurrentStatus/ActionDate` | `return` (not spatula) |
| `scrapers/mi/bills.py` | `start=` in `scrape()`; populate `dateFrom=` in search URL OR early `return` in `scrape_bill()` | `continue` / `return` |
| `scrapers/ut/bills.py` | `start=` threaded to `scrape_bill_details_from_api()`; early `return` after JSON parse | `return` (not spatula) |
| `scrapers/ma/bills.py` | `start=` in `scrape()`; `continue` in `scrape_bill_list()` loop using `PrimarySponsor.ResponseDate` | `continue` (not spatula) |
| `scrapers/az/bills.py` | `start=` in `scrape()`; early `continue` in bill-rows loop using `BillStatusAction.ReportDate` | `continue` (not spatula) |
| `scrapers/va/bills.py` | `start=` in `scrape()`; refactor events fetch out of `add_actions()` to be called first; skip versions/patrons/votes if max `EventDate` ≤ start | `continue` (not spatula) |
| `RUNBOOK.md` | Document `logs/last-run/`, timestamp format, per-state rollout, VA API inspection step | — |

---

## Implementation order

Priority is by session activity and impact:

1. **Prerequisite** — `--allow_duplicates` for FL in `run-scrape.sh` (ship independently, now)
2. **Shell timestamp layer** — rest of `run-scrape.sh` changes
3. **USA** — 1-line fix, cherry-pick, validate (daily active, 10k bills, ~95% savings)
4. **FL** — verify `td[3]` column, cherry-pick, validate (daily active, 30-hr→minutes)
5. **WA** — `CurrentStatus/ActionDate` filter, cherry-pick, validate; also check WSDL for date-range endpoint upgrade
6. **MI** — verify `dateFrom=` semantics, cherry-pick, validate (weekly, 3,629 bills)
7. **UT** — `actionHistoryList[0].actionDate` filter, cherry-pick (weekly, session inactive)
8. **AZ** — `BillStatusAction.ReportDate` filter (weekly, session inactive, lower ROI)
9. **MA** — `ResponseDate` filter with caveat, or defer until better date signal found
10. **VA** — refactor events fetch; use max `EventDate` to skip 3/4 per-bill calls; low urgency (active session is only 273 bills)

---

## Verification

**Test 1 — timestamp mechanics:**
```bash
echo "2026-06-19T02:00:00" > logs/last-run/fl_session_2026.ts
bash -x ./run-scrape.sh fl "session=2026" 2>&1 | grep "start=\|Incremental"
# Expected: "Incremental run: start=2026-06-19T01:00:00"
```

**Test 2 — USA incremental (after cherry-pick):**
```bash
source activate.sh
$OS_UPDATE usa --scrape bills session=119 chamber=lower \
    start=2026-06-18T00:00:00 --cachedir $CACHE_DIR --datadir $SCRAPED_DATA_DIR
ls $SCRAPED_DATA_DIR/usa/bill*.json | wc -l
# Full ~4,000 files; 2-day window should yield <200
```

**Test 3 — FL incremental (after cherry-pick):**
```bash
source activate.sh
$OS_UPDATE fl --scrape bills session=2026 \
    start=$(python3 -c "import datetime; print((datetime.datetime.utcnow()-datetime.timedelta(days=1)).strftime('%Y-%m-%dT%H:%M:%S'))") \
    --cachedir $CACHE_DIR --datadir $SCRAPED_DATA_DIR 2>&1 | grep -c "SkipItem"
# Should see many SkipItem log lines and far fewer BillDetail fetches
```

**Test 4 — end-to-end cycle:**
```bash
rm -f logs/last-run/fl_session_2026.ts   # force full first run
./run-scrape.sh fl "session=2026"
cat logs/last-run/fl_session_2026.ts     # should show today's UTC timestamp
./run-scrape.sh fl "session=2026"        # second run uses timestamp
grep "Incremental run" logs/scraper.log | tail -5
```
