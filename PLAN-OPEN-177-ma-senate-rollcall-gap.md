# OPEN-177 — MA: 6 bills cite a Senate roll call and hold no Senate vote

**2026-08-26.** All six identified and root-caused. Two causes, both fixed, neither of them the
one the ticket predicted.

**Live requests to malegislature.gov: 0.** The six bills, their action text, and the reason each
vote is missing all came from the `openstates` database and the archived `logs/scraper.log`.
The ticket estimated "six bills through the `bill_no=` path is minutes"; it turned out to need
no fetches at all.

---

## The six

```
SENATE   bills citing a roll call: 126   holding one: 133   MISSING: 6
HOUSE    bills citing a roll call: 117   holding one: 122   MISSING: 0
```

Reproduced exactly. The six, with the action that cites the roll call:

| bill | date | action text | cause |
|---|---|---|---|
| S 18 | 2025-02-13 | `Report accepted, as amended -see Roll Call #17 (Yeas 39 to Nay 0)` | parse gate |
| S 19 | 2025-02-13 | `Report accepted, as amended -- see Roll Call #24 (Yeas 39 to Nay 0)` | parse gate |
| S 2917 | 2026-01-15 | `Passed to be engrossed -see Roll Call #118 (Yeas 37 to Nay 1)` | parse gate |
| S 2565 | 2025-07-24 | `Passed to be engrossed -- see Roll Call #65 (Yeas 39 to Yeas 0)` | parse gate |
| H 4530 | 2025-09-18 | `Passed to be engrossed -see Roll Call #70 (Yeas 39 to Nays 0)` | fetch failure |
| S 2903 | 2026-01-15 | `Passed to be engrossed -- see Roll Call #128 (Yeas 38 to Nays 0)` | fetch failure |

The ticket's ranked guesses were: a PDF fetch failure, an action wording the regex cannot parse,
or a genuine source-side absence. The first two are both right, for different bills. **The third
is not the cause of any of them** — Massachusetts published every one of these roll calls. There
is nothing here to record as "not a defect on our side."

---

## Cause 1 — the parse gate rejects three of the four spellings (4 bills)

The Senate branch only created a vote when the action text contained the literal substring
`"nays"`:

```python
if "yeas" in action_name.lower() and "nays" in action_name.lower():
```

Massachusetts does not consistently write it that way. Across all **236** roll-call actions in
MA 194th:

| shape | count |
|---|---|
| `Yeas 39 to Nays 0` — matches the old gate | 230 |
| `Yeas 39 to Nay 0` — singular | 3 |
| `Yeas 39 to Yeas 0` — source-side typo | 1 |
| `Quorum Roll Call - 149 YEAS to 0 NAYS` — not a bill vote | 2 |

The 3 singular and the 1 typo are exactly 4 of these 6 bills. The failure is total rather than
partial: no vote event was created at all, so there was nothing to notice — no tally-only row,
no warning, nothing.

The typo case (S 2565, `Yeas 39 to Yeas 0`) is worth being explicit about, because accepting it
is a judgment rather than a parse. It is a transcription error on the legislature's side. The
alternative is discarding a real 39-0 roll call whose PDF is available and readable, so the fix
records the second number as the nay count and takes the voters from the PDF, which is
authoritative regardless of what the action text says.

## Cause 2 — a failed fetch discarded the whole vote (2 bills)

H 4530 and S 2903 parse fine. Their votes were created, and then thrown away:

```python
if self.scrape_senate_vote(cached_vote, rollcall_pdf) is False:
    self.warning("Skipping vote {} -- roll call fetch failed")
else:
    ...
    yield cached_vote
```

Confirmed in the archived log for the 2026-08-12 run — 18 Massachusetts roll calls were skipped
that night, and two of them are these:

```
Skipping vote http://malegislature.gov/RollCall/194/SenateRollCall70.pdf  -- roll call fetch failed
Skipping vote http://malegislature.gov/RollCall/194/SenateRollCall128.pdf -- roll call fetch failed
```

H 4530's action cites Roll Call **#70**. S 2903's cites **#128**. The match is exact.

This is the part worth carrying forward past this ticket. **A transient network failure was
allowed to delete a real vote** — the tally was already parsed and correct, sitting in memory,
and it was discarded because a separate document could not be downloaded. Nothing retried and
nothing recorded that a vote had been dropped; the only trace is one `warning` line in a log that
rotates.

Note also that 18 roll calls failed that night while only 2 bills show as missing. The other 16
were recovered by a later run or belong to bills that hold another Senate vote. **The audit is
per-bill, so it under-reports**: it cannot see a bill that lost one of its several roll calls.
The true number of dropped votes is higher than 6, and this measure will not tell you what it is.

---

## The fix

Branch **`fix/OPEN-176-177-ma-rollcall-recovery`** on
`Digital-Democracy-Project/openstates-scrapers` (commit `13b7ba5ca`, pushed, **no PR opened**).
Shared with OPEN-176 — same file, same defect from the other side.

**1. Accept every spelling of the nay count.**

```python
_SENATE_TALLY_RES = (
    re.compile(r"(\d+)\s+yeas\b.*?(\d+)\s+nays\b", re.I),          # older "39 yeas ... 0 nays"
    re.compile(r"\byeas?\s+(\d+)\s+to\s+(?:nays?|yeas?)\s+(\d+)", re.I),
)
```

**2. Never discard a vote because its roll call could not be fetched.** The vote is recorded with
its real tally and marked `extras["voters_unavailable"]`, with a warning naming the bill. This is
the same change OPEN-176 needs, for the opposite symptom: 176 is a vote that looks complete and
is not, 177 is a vote that vanished entirely. One rule fixes both — **the tally comes from the
action text and is real whatever the PDF does.**

A labelled gap can be found again with one query. A silent absence can only be found by someone
thinking to run a per-bill audit, which is how this ticket came to exist a full session late.

**Tests:** 18 in `tests/test_ma_rollcall_recovery.py`, including one per spelling above and one
asserting the typo form still parses. All pass. Six pre-existing failures in
`test_classify_motion.py` are unrelated — confirmed by re-running on the base commit.

---

## What you need to do

1. **Review and open the scrapers PR.** It is pushed and tested, and covers both tickets.

2. **Re-scrape the six bills** once it lands — minutes, as the ticket estimated:

   ```bash
   ./run-scrape.sh ma "session=194th bill_no=S18"
   ./run-scrape.sh ma "session=194th bill_no=S19"
   ./run-scrape.sh ma "session=194th bill_no=S2565"
   ./run-scrape.sh ma "session=194th bill_no=S2903"
   ./run-scrape.sh ma "session=194th bill_no=S2917"
   ./run-scrape.sh ma "session=194th bill_no=H4530"
   ```

3. **Re-run the audit and expect zero.** All six roll calls exist at the source, so unlike
   OPEN-176 there is no expected residue. If any bill still shows missing, that is a third cause
   and not a partial fix.

---

## One thing I did not do

The ticket asks to "distinguish 'we failed to collect it' from 'MA never published it'". I
established that all six are the first kind, from the action text and the fetch log, without
fetching anything. I did **not** confirm that the six PDFs are downloadable right now — that is a
network question, it is answered by step 2 above, and it changes nothing about the diagnosis: two
of them were fetched successfully in earlier runs, and the four parse-gate bills were never
requested at all, so their availability was never in question.

---

## Verification query

```sql
WITH b AS (
  SELECT b.id, b.identifier FROM opencivicdata_bill b
  JOIN opencivicdata_legislativesession s ON b.legislative_session_id = s.id
  JOIN opencivicdata_jurisdiction j ON s.jurisdiction_id = j.id
  WHERE j.id LIKE '%state:ma%' AND s.identifier = '194th'
), cites AS (
  SELECT DISTINCT b.id, b.identifier FROM b
  JOIN opencivicdata_billaction a ON a.bill_id = b.id
  WHERE a.description ILIKE '%Roll Call%'
), holds AS (
  SELECT DISTINCT b.id FROM b
  JOIN opencivicdata_voteevent ve ON ve.bill_id = b.id
  JOIN opencivicdata_organization o ON ve.organization_id = o.id
  WHERE o.classification = 'upper'
)
SELECT c.identifier FROM cites c WHERE c.id NOT IN (SELECT id FROM holds) ORDER BY 1;
```

Today: 6 rows. After the re-scrape: none.

---

## Reference

- **OPEN-169** — the House equivalent, closed; contributed upstream as `openstates/openstates-scrapers` #5776
- **OPEN-176** — 152 MA roll calls importing with a tally and no voters; shares this fix
- `openstates-scrapers` `scrapers/ma/bills.py` — the `"Roll Call"` Senate branch and `scrape_senate_vote()`
- `logs/scraper.log.20260812T023000Z.gz` — the run that dropped roll calls #70 and #128
