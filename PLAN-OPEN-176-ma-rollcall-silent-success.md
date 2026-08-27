# OPEN-176 — MA: 152 roll calls import with a tally and no voters

**2026-08-26.** Root cause, fix, and the recovery plan for the 152 Massachusetts 194th vote
events that carry a real tally and zero individual voters.

**Live requests to malegislature.gov: 0.** Everything below was established from the production
scrapelib cache, the `openstates` database, and `logs/scraper.log`. The one question that does
need the network — whether the missing data is fetchable *today* — is the first step of the
re-scrape below, not a prerequisite for deciding anything.

---

## Summary

The count is right and the diagnosis in the ticket is wrong. The 152 are not one problem and
they are not malformed PDFs; they are four distinct causes behind one shared mechanism, and
**115 of them are recoverable by a targeted re-scrape** once the fix in this branch lands.

| | events | cause | recoverable |
|---|---|---|---|
| Senate | **115** | pointed at an amendment content page, not a roll call | **yes — by re-scrape** |
| Senate | **2** | a House *quorum* roll call minted as a Senate bill vote | no — should not exist |
| Senate | **1** | action cites no roll-call number at all | no — nothing to fetch |
| House | **34** | roll call not yet in the year-aggregate journal PDF | later — source-side lag |
| | **152** | | |

---

## The correction: it was never a malformed PDF

OPEN-176 records S 2947's roll call as a genuinely corrupt PDF, citing `Couldn't find trailer
dictionary` and `Couldn't read xref table`. Those errors are real. The conclusion drawn from
them is not.

S 2947's vote event points at:

```
http://malegislature.gov/Bills/GetAmendmentContent/194/S2947/1/Senate/Preview
```

That object is in the production cache. It is **818 bytes of HTML**:

```
status: 200
Content-Type: text/html; charset=utf-8
...
<div class="modal-header">
    <button type="button" class="close" data-dismiss="modal" aria-label="Close dialog">
```

`convert_pdf` reports a broken trailer dictionary because it was handed an HTML modal dialog,
not because Massachusetts published a corrupt file. **The file is not a malformed PDF; it was
never a PDF.** This distinction decides the whole shape of the work: a corrupt source document
is unfixable and unrecoverable, whereas fetching the wrong URL is both.

It also means the ticket's largest open question — "whether the 152 share one cause, and nobody
has looked at a second one" — is now answered without sampling ten of them by hand. The source
URL of every event is stored in `dedupe_key`, so all 152 could be classified at once:

```
upper | no voters | malegislature.gov/Bills/GetAmendmentContent/<n>/S<n>/<n>/Senate/Preview | 114
upper | no voters | malegislature.gov/Bills/GetAmendmentContent/<n>/H<n>/<n>/Senate/Preview |   1
upper | no voters | malegislature.gov/RollCall/<n>/HouseRollCall<n>.pdf                     |   2
upper | no voters | (empty)                                                                 |   1
lower | no voters | malegislature.gov/Journal/House/<n>/<n>/RollCalls#<n>                    |  34
upper | HAS voters| malegislature.gov/RollCall/<n>/SenateRollCall<n>.pdf                     | 110
```

The last line is the tell. **Every Senate vote that worked came from `SenateRollCall<n>.pdf`,
and not one that failed did.**

---

## The mechanism

`scrape_action_page()` built the Senate roll-call URL as the *first link in the action cell*:

```python
rollcall_pdf = "http://malegislature.gov" + row.xpath("string(td[3]/a/@href)")
```

That cell carries several unrelated kinds of link — Chapter-of-the-Acts text, cross-references
to another bill number, an amendment's own content page — and this repo's own code already knows
that: the loop directly above it iterates `td[3]//a/@href` precisely to sort Chapter links from
bill cross-references. The roll-call branch then took whichever happened to be first.

What made this survive is the second half. `scrape_house_vote()` and `scrape_senate_vote()` had
**three answers to one question**:

| situation | returned | caller's `is False` test | result |
|---|---|---|---|
| fetch raised | `False` | caught | vote dropped |
| supplement not in PDF | `None` (bare `return`) | **missed** | vote yielded, no voters |
| parsed cleanly, named nobody | `None` (implicit) | **missed** | vote yielded, no voters |

Two of the three failures were indistinguishable from success. That is the whole of OPEN-176's
"an unreadable roll call imports as a success", and it is the same silence as OPEN-169.

---

## The fix

Branch **`fix/OPEN-176-177-ma-rollcall-recovery`** on `Digital-Democracy-Project/openstates-scrapers`
(commit `13b7ba5ca`, pushed, no PR opened — see "What you need to do"). It also carries OPEN-177,
which is the same file and the same defect seen from the other side.

**1. Build the Senate roll-call URL from the number the action cites, instead of picking a link.**

```python
_SENATE_ROLLCALL_URL = "http://malegislature.gov/RollCall/{}/SenateRollCall{}.pdf"
_ROLLCALL_NUMBER_RE = re.compile(r"Roll\s+Call\s+#\s*(\d+)", re.I)
```

This is not a guess. It is the rule the working data already follows, and it was checked both
ways before being relied on:

- Of the **110** Senate events that did import voters, **109** have a `Roll Call #<n>` in their
  bill's action text whose number equals the number in the URL that worked (99.1%).
- Of the **115** broken events, **115** have such a number available on a same-date action.

So the rule predicts the successes and covers every failure.

**2. An unreadable roll call is now loud, and the vote is still recorded.**

Both scrape functions return `True` only when they actually attached a voter; every failure path
returns `False`. The caller warns, naming the bill, and sets:

```python
cached_vote.extras["voters_unavailable"] = "senate-rollcall-unreadable"
```

The vote is yielded either way. **The tally comes from the action text and is real whatever the
PDF does** — so discarding the vote destroys good data to hide a gap in adjacent data. This is
deliberately not the "skip" behaviour the old code had on a fetch failure; that behaviour is
exactly what produced OPEN-177's two missing bills.

`extras` is an existing, already-populated mechanism here (1,792 vote events carry non-empty
extras today, e.g. MI/WA roll-call numbers), not a new invention, and it makes the remainder
countable in one query rather than inferable.

**3. Quorum roll calls no longer mint Senate bill votes.** `Quorum Roll Call - 149 YEAS to 0
NAYS (See YEA and NAY No. 249 )` is a count of who is present, not a vote on the bill — and the
two in this session are *House* counts. They are the 2 Senate events whose source URL points at
a House roll-call PDF.

**Tests:** 18 new in `tests/test_ma_rollcall_recovery.py`, covering every parse shape and every
failure path's return value. They pin the rules rather than a scraped snapshot, because a
snapshot would not have caught any of this — all of it produced well-formed output.

```
18 passed
```

Six pre-existing failures in `tests/test_classify_motion.py` (UT/MI/VA motion classification) are
unrelated. Verified by stashing this change and re-running on the base commit: the same 6 fail.

---

## What this recovers, and what it does not

**115 Senate events** should gain their voters on the next MA scrape that revisits those bills.
Their PDFs are ordinary `SenateRollCall<n>.pdf` files and 110 sibling events prove that path
works.

**34 House events** will not be fixed by any code change, and this is worth being precise about
because it is the one genuinely source-side item here. Every 2026 supplement up to **#235**
resolved; every failure is **#233 and #237–#270**, contiguously:

```
resolved : 118 119 141 145 150 ... 231 232 234 235
failed   : 233 237 238 239 ... 269 270
```

The year-aggregate journal PDF had not been republished with the July sittings when we fetched
it. That is a lag, not a defect, and the same bills will fill in on a later run. Until they do,
the fix makes the gap visible instead of letting it look like a complete vote — which is the
actual requirement in the ticket.

**3 events** (2 quorum, 1 with no roll-call number) will stop being created. The 2 quorum rows
already in the database are stale and want deleting or retiring; see "Open decisions".

---

## What you need to do

Nothing here has been run against production, and no PR was opened on the scrapers fork.

1. **Review and open the scrapers PR** from `fix/OPEN-176-177-ma-rollcall-recovery`. It is
   pushed and tested; it needs your review before it becomes fork `main`, per this repo's
   dev→prod discipline.

2. **Re-scrape the affected Massachusetts bills** once it lands. MA supports single-bill
   targeting, so this does not need a full session walk:

   ```bash
   ./run-scrape.sh ma "session=194th bill_no=S2947"
   ```

   The full list of 115 bills is reproducible with the query below. A single full MA scrape
   would also do it, but it is a many-hour job and the targeted path is the convention here.

3. **Re-measure, and expect a specific number.** After the re-scrape the tally-only count should
   fall from 152 to about 37 — the 34 House lag plus the 1 no-number Senate event, plus the 2
   stale quorum rows if they are not removed. Anything else is a new finding, not a smaller old
   one.

---

## Open decisions for you

**1. What a genuinely unreadable roll call should look like in the data** (the ticket's fifth
acceptance criterion). This branch answers it one way — record the vote, mark it
`voters_unavailable`, warn — on the reasoning that a labelled gap can be found again and a
silent one cannot. The alternative, dropping the vote, is what created OPEN-177. If you disagree,
this is the line to change, and it is one `if`.

**2. Whether 37 tally-only votes are acceptable to serve after the flip.** The ticket asks this
explicitly and it is yours, not mine. My read: yes, provided they are marked, because they are
honest about what they do and do not know — which is more than the public API offers for the
same bills.

**3. The 2 stale quorum vote events.** They will stop being created but the existing rows
persist. They are the same class as OPEN-95 and OPEN-175 (a small, provable set of rows that
should not exist), and are probably best handled with those rather than separately.

**4. A finding I did not act on.** Quorum roll calls are *also* being recorded as House votes —
supplement #154 is a quorum call that imported with real voters attached. Removing those would
change existing data with real voters in it, which is beyond this ticket. Worth its own ticket;
I have not filed one.

---

## Verification queries

Reproduce the headline count:

```sql
WITH ma AS (
  SELECT ve.id, ve.organization_id
  FROM opencivicdata_voteevent ve
  JOIN opencivicdata_legislativesession s ON ve.legislative_session_id = s.id
  JOIN opencivicdata_jurisdiction j ON s.jurisdiction_id = j.id
  WHERE j.id LIKE '%state:ma%' AND s.identifier = '194th'
)
SELECT o.classification AS chamber, count(*)
FROM ma JOIN opencivicdata_organization o ON ma.organization_id = o.id
WHERE EXISTS (SELECT 1 FROM opencivicdata_votecount vc
              WHERE vc.vote_event_id = ma.id AND vc.value > 0)
  AND NOT EXISTS (SELECT 1 FROM opencivicdata_personvote p
                  WHERE p.vote_event_id = ma.id)
GROUP BY 1;
```

Expected today: `lower 34`, `upper 118`.

List the 115 bills to re-scrape:

```sql
SELECT DISTINCT b.identifier
FROM opencivicdata_voteevent ve
JOIN opencivicdata_bill b ON ve.bill_id = b.id
JOIN opencivicdata_legislativesession s ON ve.legislative_session_id = s.id
JOIN opencivicdata_jurisdiction j ON s.jurisdiction_id = j.id
WHERE j.id LIKE '%state:ma%' AND s.identifier = '194th'
  AND ve.dedupe_key LIKE '%GetAmendmentContent%'
  AND NOT EXISTS (SELECT 1 FROM opencivicdata_personvote p
                  WHERE p.vote_event_id = ve.id)
ORDER BY 1;
```

Count what remains marked after the re-scrape:

```sql
SELECT ve.extras->>'voters_unavailable' AS reason, count(*)
FROM opencivicdata_voteevent ve
JOIN opencivicdata_legislativesession s ON ve.legislative_session_id = s.id
JOIN opencivicdata_jurisdiction j ON s.jurisdiction_id = j.id
WHERE j.id LIKE '%state:ma%' AND s.identifier = '194th'
  AND ve.extras ? 'voters_unavailable'
GROUP BY 1;
```

---

## Reference

- **OPEN-169** — the MA House vote gap: same silent-success mechanism, different cause, closed
- **OPEN-177** — the mirror of this on the other side; shares the branch and the fix
- `openstates-scrapers` `scrapers/ma/bills.py` — `scrape_action_page()`, `scrape_house_vote()`,
  `scrape_senate_vote()`
- `notes/ma-open-169-vote-coverage-20260826.md` — the coverage run this came out of
