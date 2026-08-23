# OPEN-88: WA SOAP API date-range endpoint investigation

## Context

`PLAN-incremental-scraping.md`'s "Reopened 2026-07-27" section named a follow-up that was never
closed: WA (along with UT/AZ) pays a hard per-bill-fetch floor on every scrape regardless of how
many bills actually changed, because its incremental filter only skips *downstream* sub-calls, not
the initial per-bill `GetLegislation` call itself. For WA specifically -- a **daily**-scraped
jurisdiction with ~3,400 biennium bills -- this costs a ~55-60 minute floor every night, including
out-of-session weeks with zero real activity.

The confirmed shape of the problem in `openstates-scrapers/scrapers/wa/bills.py`:

- `scrape_bill()` builds the `GetLegislation?biennium=…&billNumber=…` URL at **:353-357** and
  fetches it unconditionally at **:359** (`page = self.get(url)`).
- Only *then*, at **:363-371**, does the date filter run
  (`if self._start_dt: … if action_dt <= self._start_dt: return`), keying off
  `wa:CurrentStatus/wa:ActionDate`.
- So the early return only saves the downstream sub-calls -- sponsors (**:440**), actions
  (**:467**), rollcalls (**:652**) -- never the `GetLegislation` call that already happened.

This ticket asked whether WA's SOAP API exposes a `GetLegislativeStatusChangesByDateRange`-style
operation that would let the scraper learn *which* bills changed first, and skip `GetLegislation`
entirely for the rest.

**Answer: yes.** That operation exists, under exactly that name, and returns the right thing --
with one correctness trap (§4) and one open assumption a prototype has to validate (§5).

## Method

All queries were read-only `GET`s against the public endpoint (no `POST`, no SOAP mutation), which
is the same thing the scraper does routinely. Four requests total.

1. Fetched the WSDL: `https://wslwebservices.leg.wa.gov/legislationservice.asmx?WSDL`
   (196,890 bytes) and enumerated every operation in the `LegislationServiceSoap` portType.
2. Extracted the input/output message schema for the candidate operations from the WSDL itself
   rather than trusting operation names.
3. Exercised the promising operation over its documented HttpGet binding for three windows: a
   recent 3-day out-of-session window, a 30-day out-of-session window, and one busy in-session day.
4. Cross-checked the response's `BillId` format against the scraper's own existing normalizers
   (`_wa_bill_id_to_no` at :29-37, `norm_bill_id_re` at :76) to see what would actually match.

**Note on transport:** the scraper's comment block still lists the API docs as
`http://wslwebservices.leg.wa.gov/...` (:46), but `_base_url` (:48) is already `https`. Plain
port 80 did not accept connections at all from here (three attempts, all connect timeouts); `https`
worked first try. Nothing to fix -- `_base_url` is already correct -- but the `http://` reference in
the comment at :46 is stale, and the ticket's own restatement of the endpoint inherits it.

## Findings

### 1. `LegislationServiceSoap` exposes 38 operations

Full list as advertised by the WSDL portType (36 distinct names; `GetLegislativeStatusChanges` is
overloaded 3 ways, see below):

```
GetAmendmentsForBiennium                     GetLegislationPassedHouse
GetAmendmentsForYear                         GetLegislationPassedHouseWithinTimeFrame
GetCurrentStatus                             GetLegislationPassedLegislature
GetHearings                                  GetLegislationPassedLegislatureWithinTimeFrame
GetHouseLegislationPassedHouse               GetLegislationPassedOriginalBodyAndNot…OppositeBody
GetHouseLegislationPassedSenate              GetLegislationPassedSenate
GetLegislation                               GetLegislationPassedSenateWithinTimeFrame
GetLegislationByRequestNumber                GetLegislationTypes
GetLegislationByYear                         GetLegislativeBillListFeatureData
GetLegislationGovernorPartialVeto            GetLegislativeStatusChanges   (x3, overloaded)
GetLegislationGovernorSigned                 GetPreFiledLegislationInfo
GetLegislationGovernorVeto                   GetPrefiledLegislation
GetLegislationHistoricalRecapCategories…     GetPublishedEnrolledLegislation
GetLegislationInfoIntroducedSince            GetRcwCitesAffected
GetLegislationIntroducedSince                GetRollCalls
GetLegislationNotYetIntroducedInHouseOf…     GetSenateLegislationPassedHouse
GetSessionLawChapter                         GetSenateLegislationPassedSenate
GetSponsors                                  GetTotalLegislationIntroducedByDateRange
```

### 2. The operation the ticket hypothesised exists, by that exact name

`GetLegislativeStatusChanges` is a .NET-style overload with three distinct
input/output message pairs. The third is the one that matters:

| Input message name | Parameters | WSDL documentation |
| --- | --- | --- |
| `…ByBillNumber` | biennium, billNumber, beginDate, endDate | "Returns the current status of the bill in the legislative process." |
| `…ByBillId` | biennium, billId, beginDate, endDate | "Returns all changes to the status of the bill that occurred in the date range." |
| **`…ByDateRange`** | **biennium, beginDate, endDate** | **"Returns all changes to the legislation status that occurred in the date range."** |

`GetLegislativeStatusChangesByDateRange(biennium, beginDate, endDate)` returns
`ArrayOfLegislativeStatus`, and each `LegislativeStatus` carries:

```
BillId (string)   HistoryLine (string)   ActionDate (dateTime)   Status (string)
AmendedByOppositeBody / PartialVeto / Veto / AmendmentsExist (boolean)
```

So it returns **more than just bill IDs** -- it's the actual status-change records, keyed by
`BillId` and stamped with `ActionDate`. Critically, `ActionDate` is the *same field* the existing
filter at :363-371 already keys off (`wa:CurrentStatus/wa:ActionDate`). This is not a different or
weaker change signal; it is the same signal, computed server-side, in one call.

### 3. Verified live response shapes

| Window | Records | Distinct raw `BillId` | Real bills after `norm_bill_id_re` |
| --- | --- | --- | --- |
| 2026-08-19 → 2026-08-22 (out of session) | 0 | 0 | **0** |
| 2026-07-23 → 2026-08-22 (30d, out of session) | 7 | 7 | **0** (all `SGA`) |
| 2026-02-10 → 2026-02-11 (one busy session day) | 681 | 429 | **243** |

The out-of-session results are the headline. Over a **full 30-day out-of-session window**, the
only 7 records returned were `SGA` gubernatorial-appointment items (`"Resigned."`), which the
scraper already discards two separate ways -- `bill_num >= 9000` at :330-332 and `norm_bill_id_re`
not matching `SGA` at all. The number of real bills the scraper would need to fetch across that
entire month is **zero**, against the ~3,400 `GetLegislation` calls it currently makes *every
night*.

On the busiest kind of in-session day, 429 raw IDs collapse to 243 distinct base bills -- still a
~93% reduction against 3,400.

### 4. The `BillId` format trap, and the primitive that already solves it

The response's `BillId` is the *versioned* identifier, not the base one. The Feb 10 sample contains
forms like `SHB 1078`, `2SHB 1443`, `E2SHB 1170`, `ESSB 5374`, `3SHB 1834`, `E3SHB 1710`,
`SSJM 8016`, `SGA 9265`.

`_wa_bill_id_to_no()` (:29-37, added for OPEN-78) **does not** collapse these -- its prefix set is
only `HCR/SCR/HJM/SJM/HJR/SJR/HB/SB/HR/SR`, so `"SHB 1078"` normalizes to `"SHB1078"`, which would
never match `"HB1078"`. Verified directly:

```
'HB 1078'    -> 'HB1078'      'SHB 1078'  -> 'SHB1078'      'E2SHB 1170' -> 'E2SHB1170'
```

Reusing `_wa_bill_id_to_no` for the intersection would therefore **silently drop every substitute
and engrossed bill** -- exactly the bills most likely to be moving. That is the one real
correctness trap here.

The class already has the right primitive: `norm_bill_id_re` (:76,
`r"(?:S|H)(?:B|CR|JM|JR|R) \d+"`), used with `.findall()` at :341, matches mid-string and so
collapses every prefixed form to its base ID. Verified against the live values:

```
'SHB 1078'   -> ['HB 1078']    '2ESHB 1210' -> ['HB 1210']   'E2SHB 1170' -> ['HB 1170']
'ESSB 5374'  -> ['SB 5374']    '3SHB 1834'  -> ['HB 1834']   'SSJM 8016'  -> ['SJM 8016']
'SGA 9265'   -> []             'HJM 4012'   -> ['HJM 4012']
```

It also drops `SGA` for free, matching how :341-346 already filters the bill list.

### 5. Caveats, and the limits of what this sampling proves

**a. `ActionDate` is date-only.** Every returned `ActionDate` had a `00:00:00` time component, so
the window is effectively day-granular while `_start_dt` is a full datetime. The existing filter at
:363-371 already has this same coarseness (it compares a midnight `action_dt` against a precise
`_start_dt`), so this is not a new problem -- but the date-range window should be floored to the
date and treated as inclusive on both ends, rather than passed a bare `_start_dt`.

**b. The window filter returns a superset, not a subset.** In the 30-day query, 4 of the 7 records
had `ActionDate` values *outside* the requested range (2026-03-13, 2026-05-19, 2026-03-09 for a
2026-07-23→2026-08-22 window). All were `SGA` `"Resigned."` records, so practical impact here is
nil, but it shows the operation's own date filtering is loose for at least some record types.

This errs in the safe direction and is worth stating explicitly, because it defines the whole risk
profile of the change: the date-range call would be used **only to narrow the candidate set**, and
the existing `CurrentStatus/ActionDate` check at :363-371 stays in place as the authoritative
filter. A superset costs a few wasted fetches and changes nothing about correctness. Only a
*subset* -- a bill that changed but wasn't reported -- would drop data.

**What the sampling does and does not establish here.** In the windows sampled, the operation erred
toward returning extra records rather than missing them. That is *not* proof that it is always a
complete superset -- 3 windows over 4 requests cannot establish the absence of false negatives, and
no paired comparison against a full unfiltered scrape was run. Treat "no false negatives" as the
open assumption this investigation did not close, and the thing a prototype has to validate (see
the required validation below) rather than something already settled.

**Also untested, and worth checking before a build:** whether the operation paginates, truncates,
caps results, or faults on larger or busier windows than the single session day sampled. The
sampling was deliberately kept to four requests against a public government API, so this is
unresolved rather than ruled out.

**One more precision point:** the alignment between this operation's `ActionDate` and the filter's
`CurrentStatus/ActionDate` is established from the WSDL schema plus sample response shape -- they
*appear* to be the same status-change date, and the field naming and values are consistent with
that. It was not confirmed by comparing specific bills' `GetLegislation` `CurrentStatus/ActionDate`
against the date-range records for the same bills. That comparison is cheap and belongs in the
prototype's validation step.

## Conclusion

**Qualified yes -- suitable to prototype, with the paired validation below.**
`GetLegislativeStatusChangesByDateRange` exists, takes exactly `(biennium, beginDate, endDate)`,
returns per-bill status-change records keyed on what is evidently the same `ActionDate` the
scraper's own incremental filter already uses, and returned *zero* real bills across a 30-day
out-of-session window. That is the right shape to remove the per-bill-fetch floor rather than work
around it, which is what the ticket was asking for.

The question this ticket asked -- does such an operation exist and could it work -- is now answered
and can stop being open. What is *not* established is that the operation never omits a changed bill
(§5). That is the one assumption a prototype must validate before the optimisation is trusted; it
does not need more investigation to decide whether to try.

This is not a trivially-yes one-liner, because of the `BillId` prefix trap in §4, so per the task
framing no code was changed. The scoped sketch below is deliberately minimal.

## Scoped implementation sketch (NOT implemented)

The change is one extra API call plus one set-intersection, reusing machinery that already exists.
It should stay that small. All line numbers are current `scrapers/wa/bills.py`.

1. **New method, `_changed_bill_ids(self, start_dt)`** -- one `self.get()` against
   `f"{self._base_url}/GetLegislativeStatusChangesByDateRange?biennium={self.biennium}"
   f"&beginDate={…}&endDate={…}"`, parsed with the same
   `lxml.etree.fromstring` + `xpath(page, "//wa:LegislativeStatus")` idiom used everywhere else in
   the file. `beginDate` = `start_dt.date()`, `endDate` = today + 1 day. For each record, run
   `self.norm_bill_id_re.findall(xpath(rec, "string(wa:BillId)"))` and add `[0]` when it matches.
   Return the set, or `None` on any failure.

2. **`scrape()` (:273-299)** -- after `bill_ids` is de-duped at :295 and the existing `bill_nos`
   filter at :296-297, add the analogous narrowing: when `self._start_dt` is set, call
   `_changed_bill_ids()` and keep only `bill_ids` in that set. This slots into the exact spot, and
   exact idiom, that OPEN-78's `bill_no` filter already established.

3. **Fail open, always -- and distinguish "empty" from "broken".** These are two different
   outcomes and must not collapse into one:
   - A *successfully parsed but empty* `ArrayOfLegislativeStatus` means "no candidates" and should
     legitimately narrow to zero bills. This is the normal out-of-session case (§3) and is the
     entire point of the change.
   - A transport error, HTTP failure, unparseable/malformed XML, or rejected biennium should return
     `None` and fall back to the current behaviour (scrape all `bill_ids`).

   A failed optimisation must degrade to a slow-but-correct scrape, never to a silently-empty one.
   This is the only new failure mode worth guarding, and conflating the two cases is the way it
   would go wrong.

4. **Leave :363-371 exactly as it is.** It stays the authoritative per-bill filter, which is what
   makes a superset response harmless (§5b) and keeps the blind spot unchanged rather than widened
   (see below).

Explicitly **not** part of this: no caching layer, no new abstraction over the SOAP API, no shared
cross-jurisdiction "changed bills" framework, no WA scraper restructuring. UT and AZ still have no
equivalent operation (the ticket already established this), so there is no second caller to
generalise for and nothing to build a shared interface against.

**Pre-existing blind spot, unchanged and not to be fixed here:** a bill can change in ways that
produce no status/history line (a new version document, a sponsor change, a title correction), and
those bills would be skipped. The current filter at :363-371 *already* skips them for the same
reason, since it also only reads `CurrentStatus/ActionDate`. This change neither fixes nor worsens
that. Widening the change signal is a separate question and should not be bundled in.

**Required validation before the optimisation is trusted (not optional).** False negatives -- a
bill that changed but wasn't reported by the date-range call -- are the primary correctness risk
(§5), and the only way to close it is a paired run:

1. **The false-negative test.** For at least one busy in-session window, run the current
   full-fetch path and the optimised candidate path over the same window, then confirm **every**
   bill emitted by the current path is also emitted by the optimised one. Substitute and engrossed
   bills (`SHB`/`2SHB`/`E2SHB`/`ESSB`…) must be explicitly represented in the compared set, since
   §4 is exactly where a silent drop would come from. Any bill present in the unoptimised run and
   missing from the optimised run is a blocker, not a tuning issue.
2. **The quiet-window test.** Run with `start=` set to a known-quiet out-of-session date and
   confirm zero `GetLegislation` calls and zero bills emitted -- i.e. the saving is real.
3. **Lock §4 with unit tests.** The `norm_bill_id_re.findall()` normalisation of the live ID forms
   in §4 should be pinned by tests, since that is the failure mode most likely to silently skip
   bills later.
4. **Also confirm the date-boundary semantics** the implementation picks: which timezone the
   `beginDate`/`endDate` conversion uses, that the end of the window is inclusive, and that
   `endDate = today + 1 day` is actually safe given the day-granular `ActionDate` (§5a).

**Minimal logging, no new infrastructure:** log the raw candidate-record count, the normalised
real-bill count, and whether the run fell back to a full scrape. That is enough to notice a
suspiciously empty result during an active session without building anything.

## References

- Ticket: OPEN-88
- `ddp-infra/PLAN-incremental-scraping.md` -- "Reopened 2026-07-27: the per-bill network floor",
  "Two follow-ups this plan named and never closed", item 1
- `openstates-scrapers/scrapers/wa/bills.py` -- `scrape()` :273-299, `scrape_bill()` :348-371,
  `_wa_bill_id_to_no()` :29-37, `norm_bill_id_re` :76
- WSDL: `https://wslwebservices.leg.wa.gov/legislationservice.asmx?WSDL`
- Prior WA notes: `open-62-washington-eligibility-verification-20260812.md`
