# Can MA's daily House and Senate journals tell a scraper which bills changed?

**Date:** 2026-11-16 (requests 2026-11-17 02:47–02:57 UTC)
**Predecessors:**
- OPEN-133 (`notes/open133-ma-api-enumeration-20260823.md`): no date filter; committee set-diffing; `/Journal` gave 405.
- OPEN-134 and OPEN-150: Michigan's journals had 57% recall.

**Live requests:** 67 read-only GETs, 1.8 s apart, all 200 (`reqlog.tsv`).
**Ground truth:** the Mac replica `openstates_rds_repl_20260911`, read-only. Newest MA bill `updated_at` 2026-11-15 16:48 UTC.

## Short answer
The journals catch floor activity almost perfectly, but alone they catch only **68.2%** of each week's changed bills. That's because 44% of MA's weekly activity is new filings and dockets, 7% is governor signings and 3% is hearing notices.

| Sources | Weekly recall |
|---|---|
| Journals only | 68.2% |
| + new bills (bill-list diff) | 88.5% |
| + Session Laws | 95.0% |
| + hearings | 98.3% |

A run would re-scrape about **83 bills a week (0.7% of 11,932)**, for about 20 requests.

## 1. Daily recall (window 2026-09-21 to 11-15; the House sat 18 days, the Senate 17)

| | Bills with an action | Named in journal | Recall |
|---|---|---|---|
| House | 385 | 240 | 62.3% |
| Senate | 326 | 322 | 98.8% |
| Both | 711 | 562 | 79.0% |

| Kind | Recall |
|---|---|
| Floor | 99.5% (396 bill-days; House 100%) |
| Committee reports read into the chamber | 98.5% (64/65) |
| Governor | 0% (0/3) |
| Filings and dockets | 42.1% |

The House's gap is a labelling gap: the Senate prints SD numbers in the margin, the House prints no HD numbers. Of the House misses, 111 are agency reports "Placed on file" and 31 are late-filed petitions named by petitioner.

**Bucketing rule, applied in order:**
1. **Filing/docket:** an HD or SD identifier, or a description matching `^(Referred to the committee on (House Rules|Rules of the two branches)|Reported, referred to the committee on Joint Rules)`.
2. **Governor/executive:** organization `executive`, or the description matches `Signed by the Governor|Chapter \d+ of the Acts|veto|Governor returned|returned .*by the Governor|Approved by the Governor|Governor's (amendment|recommendation)|Emergency (preamble|letter).*Governor`.
3. **Joint, non-committee:** organization `legislature`.
4. **Committee:** `Hearing (scheduled|rescheduled|updated|location)|Reporting date extended|study order|Committee (reported|recommended)|reported favorably|Reported from the committee|Reported by the committee|Accompanied (a|by)|New draft|Discharged|Reported, in part|Reported on a part`, or the classification contains `committee-passage`.
5. **Floor:** everything else. A bill counts once per day, as floor if any of its actions is floor.

## 2. Weekly recall

| Week | Active | New | Journals | +new | +Session Laws | +hearings | Run size |
|---|---|---|---|---|---|---|---|
| 09-21 | 77 | 29 | 50 | 70 | 72 | 74 | 75 |
| 09-28 | 113 | 54 | 77 | 101 | 112 | 112 | 117 |
| 10-05 | 55 | 15 | 43 | 47 | 55 | 55 | 57 |
| 10-12 | 118 | 69 | 65 | 108 | 117 | 118 | 122 |
| 10-19 | 84 | 32 | 56 | 67 | 73 | 81 | 85 |
| 10-26 | 76 | 31 | 62 | 69 | 73 | 73 | 81 |
| 11-02 | 62 | 33 | 44 | 58 | 60 | 62 | 65 |
| 11-09 | 59 | 21 | 42 | 50 | 50 | 58 | 63 |
| **Total** | **644** | **284** | **439 (68.2%)** | **570 (88.5%)** | **612 (95.0%)** | **633 (98.3%)** | **665** |

- **New bills:** all 284 bills first filed in the window are in the bill list the scraper already downloads.
- **Overlap:** a 3-day overlap changes nothing, because sessions fall on Mondays and Thursdays.
- **With publication delay** (a run at Sunday 23:59, pessimistic Senate timing):
  - no overlap: 80.9%;
  - 4-day overlap: 84.8%;
  - 7-day overlap: 86.5%.

  Hence the recommendation below to re-read 14–21 days of journals each run.
- **Still missed by journals plus new bills (74):** 42 governor signings, 22 joint-committee hearing notices, 10 other.
- **Still missed at 98.3% (11 of 644):**
  - 5 late-filed petitions (caught one run later, once numbered);
  - 4 Senate Ways and Means reports;
  - 3 records of one joint session;
  - 2 Senate procedural actions.

## 3. Run size and cost
- The journals name about 58 bills a week: 13.9 per House journal, 19.9 per Senate journal.
- 633 of the 665 bills re-scraped (95%) really had an action.
- Requests per weekly run:
  - 2–4 month index pages;
  - 4–6 journal PDFs (House about 200 KB each, Senate about 2.5 MB);
  - 1 bill list (12,084 records, 9 s);
  - 1 Session Laws page;
  - 1 hearings list, plus about 10 hearing detail pages.

## 4. Timeliness
The site gives no `Last-Modified` or `ETag` headers; the figures below come from the dates inside each PDF.
- **House:** 1 journal appeared the same day, 17 the next day, 3 after 2 days, 1 after 4 days and 2 after 6 days.
- **Senate:** each file is drafted 0–5 days before the session and edited 0–15 days after it, median 1 day; outliers were 12 and 15 days. Its first-posting time can't be seen.
- **Missing days:** none. Every session day has a journal.
- **"UNCORRECTED PROOF":** on 21 of 24 House journals. Whether a proof is later replaced wasn't observed.

## 5. Filling the gaps
- **Session Laws page** (1 request): all 45 governor signings in the window match by bill and date.
- **Hearings API** (event list plus detail pages): 9 of 9 checked hearing-notice bills found. That is a small sample, so the 98.3% is an upper bound.
- **OPEN-133 committee diffs:** would add only 4 Senate Ways and Means reports (0.6%), for 57 requests. Not needed in this window.

## Recommendation
Journals, plus the new-bill diff, plus Session Laws, plus the hearings diff:
- re-read the last 14–21 days of journals each run;
- keep a periodic full walk (for example monthly) as the backstop for the last 2–5% and for format changes.

Unlike Michigan, MA's journals are near-perfect on floor activity. They fall short alone because most of MA's weekly activity is filings and signings, and each of those has its own one-request feed.

## What was NOT examined
- **One season only:** the fall informal sessions, about 80 active bills a week. Re-check on a spring formal-session window, where journals are longer and have amendments and conference reports.
- **The ground truth is our own scraped database**, so activity the scraper doesn't record is invisible.
- **Senate first-posting time is unknown;** the last-edit date is only an upper bound.
- **Proof replacement:** whether a posted journal is later replaced was not observed.
- **Hearings:** only 9 bills in 3 hearings were verified; reschedules and weekly volume were not measured.
- **OPEN-133's committee-diff detection rate** is still unmeasured.
- **Parsing:** checked by reading the misses. The bare "H. 1234" form (seen once) isn't matched.
- **Scope:** only the 194th General Court and the 2026 Session Laws page.

**Files** (scratch folder of the 2026-11-17 measuring session, not committed): `reqlog.tsv`, `dl/`, `pdf/`, `dl2/`, `txt/`, `bin/parse.py` → `journal_bills.json`, `bin/analyze.py` → `analyze_out.txt`, `bin/combo.py` → `combo.json`, `actions.csv`, `billspan.csv`, `sessionlaws.json`.

## Addendum: re-measured with the built code (OPEN-609, 2026-11-17)

The selection as built (`scrapers/ma/catchup.py` in the scrapers fork) was replayed week by week against the
Mac replica (`openstates_rds_repl_20260911`, read-only; MA bills updated up to 2026-11-15 16:48 UTC). Each weekly
run is taken at Sunday 23:59 with `start=` one week earlier less one hour, so it reads the journals dated from 21
days before `start=`. "Active" = bills with any action that week.

| Window | Active bill-weeks | Journals | + new bills | + Session Laws | + hearings (upper bound) | Bills read per run |
|---|---|---|---|---|---|---|
| Fall 2026-09-21 to 11-15 (8 weeks) | 644 | 75.9% | 96.3% | 96.3% | **98.3%** | 180-259 (mean 218) |
| Spring 2026-03-02 to 04-26 (8 weeks) | 3,684 | 87.6% | 91.4% | 91.7% | **94.0%** | 1,348-2,291 (mean 1,767) |

- **Spring is under 95%, and why:** 199 of its 221 misses are House committee "Reporting date extended" actions
  (141 of them one batch on 2026-03-18/19). The House journal prints the extension order as covering "current House
  documents" and names only the order itself (House, No. 5263), never the bills, so no journal reader can find them.
  Without those, spring is 99.4% (3,463 of 3,485). The 28-day full walk picks them up. The other 22 misses are
  Joint Rules reports, Senate "Accompanied S..." and "Rules suspended" lines, and the three joint-session records.
- **The 21-day re-read** raises the journals' own share in the fall from 68.2% to 75.9% and makes the Session Laws
  source add nothing in either window (the enactment is already in a re-read journal); Session Laws stays as the
  check for a signing with no recent journal entry.
- **Posting delay:** in the fall, 94.3% is caught by the run of the same week (journal PDF creation or last edit
  date before the run) and the rest by the next run, which re-reads the same journals. In spring this cannot be
  measured: the files served now were edited months later.
- **Hearings** remain an upper bound (every "Hearing scheduled/rescheduled" bill counted as found), as above.
- **Journals that name nothing:** the House month lists also carry `hj..._RollCalls.pdf` roll-call sheets
  (6 in spring); they are read and name no bill in the "House, No." form, which is harmless.

**Requests and time per weekly run.** Measured live once on 2026-11-17 (the built code, 30 requests a minute,
`start=2026-11-09T23:00:00`, a record holding today's bill list and all hearings but the newest 10): the Documents
list 7.5 s; the sources 37 requests in about 75 s (4 month pages, 12 House journal PDFs of which one is a
roll-call sheet, 9 Senate journal PDFs, the Session Laws page, the hearing list and 10 hearing pages); 178 bills selected. Then, not measured live (it would be a
real run): the OPEN-509 amendment pre-pass, unchanged by this work, reads every Documents row without a docket number
(1,390 bill pages) and the histories of the ~145 amendment papers; and each selected bill costs a page, a cosponsor page and
one or more history pages. At the ~2 s per page of a full walk, that is about 50 minutes for the pre-pass, plus about
10-15 minutes for a fall week's ~220 bills and 1.5-2 hours for a spring week's ~1,770. So about 1-1.25 h a run in
the fall and 2.5-3 h in spring, against 10-14 h for a full walk. The first runs' logged durations are the real check.
