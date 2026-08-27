# OPEN-174 — MI: Myers-Phillips, the 30 votes, and what else the sweep found

**2026-08-26.** Fix, verification, and the production steps left for you.

**Live requests to legislature.mi.gov: 0.** Michigan is the fleet's most WAF-sensitive
jurisdiction and none of this needed the network — the `openstates` database, the broker
database and the `openstates/people` roster held all of it.

---

## Summary

The ticket's diagnosis is right: she is in the roster, correctly seated, under a name that never
matches what the journal calls her. Three things it says are wrong, and one of them changes the
size of the work by more than an order of magnitude.

1. **It is 680 vote rows, not 30.** The 30 is a broker-side count of affected *motions*; the
   replica itself holds 680 unresolvable vote rows in her name, spanning 2025-01-08 to
   2026-07-03.
2. **The fix belongs in the roster, not the broker.** The failure is in the OpenStates import,
   one layer below where the ticket looks — and the replica is what production is switching to.
3. **Motions 4161/4162 are a different, now-named defect**, and they are not both Senate.

---

## 1. The attribution the ticket calls unproven

> *"Note this attribution is not yet demonstrated ... nobody has reproduced the mapping from
> those 30 motions to her specifically."*

Demonstrated now, and by a stronger measure than the motion mapping. In the replica:

```
voter_name       vote_rows   resolved   first_seen   last_seen
Myers-Phillips        680          0    2025-01-08   2026-07-03
```

Every vote the Michigan House journal records for her fails to resolve, across eighteen months.
She is the single largest unmatched name in Michigan — larger than the other 153 combined.

The roster row is exactly as the ticket describes, and there is no duplicate:

```
Representative id=1704  full_name='Tonya Phillips'  MI/lower district 7  vote rows: 0
```

**The 146-vs-148 symptom is explained**: she holds a seat and casts no resolvable vote, so she is
counted in one number and not the other.

---

## 2. Why 680 and 30 are both right

They count different things at different layers, and conflating them is what made this look small.

| layer | what fails | measure |
|---|---|---|
| `openstates` replica | `resolve_person()` matches her journal name against no `Person`, so `personvote.voter_id` is NULL | **680 vote rows** |
| `ddp-broker-py` | the broker's own resolution then has no one to attach | **30 motions** short one vote |

The broker sees fewer because it ingests a subset. **The replica number is the one that matters
for this epic**: OPEN-38 is the switchover to serving replica data, and the replica currently
holds 680 vote records that name a legislator and point at nobody.

This is also why the ticket's proposed stopgap — correcting the name on broker row 1704 — is the
wrong layer. It would repair the broker's 30 and leave the replica's 680 exactly as they are.

---

## 3. The fix, and it is verified

`resolve_person()` (`openstates-core/openstates/importers/base.py:660-668`) matches a bare name
against three fields:

```python
name_spec = (
    Q(name__iexact=name)
    | Q(other_names__name__iexact=name)
    | Q(family_name__iexact=name)
)
```

Michigan resolves on bare surname — `Outman` → Pat Outman, and so on for 145 others. Her roster
record offered `Tonya Phillips` / `Phillips` / `Phillips, T.` / `T. Phillips` / `T.M. Phillips`,
and the journal says `Myers-Phillips`. No match, and the `T.M.` alias is the roster half-knowing
the middle name it dropped.

**Upstream PR opened: [openstates/people#4036](https://github.com/openstates/people/pull/4036).**
It corrects `name` to `Tonya Myers Phillips` and `family_name` to `Myers Phillips`, adds
`Myers-Phillips` (the journal form) and `Tonya Phillips` (the old form, so nothing that already
worked stops working) as `other_names`, and renames the file to match convention. Her
`ocd-person` id is unchanged, so this corrects the existing identity — **no second record**,
which is the ticket's first acceptance criterion.

The evidence is entirely from her own record: her legislative email is
`tonyamyersphillips@house.mi.gov`, her photo is `Tonya_Myers_Phillips_20241022_115414.png`, and
the Ballotpedia, Wikipedia and House Democrats URLs already listed under `sources` are all
`tonya-myers-phillips`.

**Verified, not assumed.** The corrected roster was loaded into the *dev* database
(`openstates_dev`) and queried with `resolve_person()`'s own predicate:

| lookup | people matched |
|---|---|
| `Myers-Phillips` (journal form) | **1** |
| `Tonya Phillips` (old form) | 1 |
| `Tonya Myers Phillips` | 1 |
| `Phillips` (bare) | **0** |

Exactly one match is what `resolve_person()` needs — it errors on zero and on more than one — and
the bare-surname row confirms nothing was made ambiguous. `os-people lint mi` passes. No
production database was touched.

---

## 4. The stopgap question is harder than the ticket assumes

The ticket says to plan for the stopgap rather than hedge, because DDP's eight role-date fixes
(openstates/people #3902–#3909) have been open upstream for a month. That is sound. But the
obvious stopgap does not work, and it is worth knowing why before you pick one:

**Production's `people` checkout tracks upstream directly.**

```
$ git -C ~/Developer/repos/ddp-open-states/people rev-parse --abbrev-ref main@{upstream}
origin/main          # = openstates/people
```

`run-people-refresh.sh` does a plain `git pull --ff-only` on that branch every Sunday. A commit
on `Digital-Democracy-Project/people` is therefore **not in the production path at all** — the
DDP fork exists but nothing reads it. So "carry the fix on our fork" is not currently a stopgap;
it is a change to how the pipeline gets its roster.

Three real options, for you to choose:

| option | effect | cost |
|---|---|---|
| **A. Wait for upstream** | correct everywhere, no local divergence | unbounded — the precedent is a month and counting |
| **B. Re-point production's `people` at the DDP fork**, carry this fix there, merge upstream regularly | DDP roster corrections take effect within one weekly refresh | a real fork to maintain; `--ff-only` will need care |
| **C. Targeted backfill of `voter_id`** on the 680 rows, leaving the roster alone | fixes today's data | does not survive the next import; needs redoing each time |

My recommendation is **B**, but it is a standing-cost decision rather than a technical one, and it
is genuinely yours. Note that B also pays for itself against the three defects in §6 below, which
are all roster-adjacent and all currently blocked behind the same upstream queue.

Whichever you pick, **recovery of the 680 needs a re-import, not just a roster load.**
`voter_id` is resolved at vote-import time, so `os-people to-database mi` alone changes nothing
about rows already stored — the votes have to be re-imported (or the column backfilled) for the
existing 680 to resolve. That is a production write and is left for you.

---

## 5. Motions 4161/4162 — root-caused, and it is not the roster

They have renumbered since the ticket was written; they are now **4165** and **4166**. The
ticket's warning that fixing the name would make Michigan look healthy enough that these are
never chased is exactly right, so here they are.

They are also not both Senate — 4165 is Senate, **4166 is House**.

| broker id | chamber | text tally | attached |
|---|---|---|---|
| 4165 | upper | `ROLL CALL # 222 YEAS 24 NAYS 12 EXCUSED 2` | 4 yes / 10 no |
| 4166 | lower | `Roll Call #311 Yeas 101 Nays 7` | 98 yes / 3 no |

The replica's own copies show the cause immediately, in the unresolved names:

```
ROLL CALL # 222  →  Bellino Bumstead, Hauck Hoitenga, Lindsey Outman, Theis Victory
Roll Call #311   →  Carra DeSana, Farhat Fitzgerald, Fox Greene, J., Maddock Schriver,
                    Myers-Phillips, O’Neal
```

Every one of those is **two legislators' surnames joined into a single string**. Bellino and
Bumstead are two senators; so are Hauck and Hoitenga, Lindsey and Outman, Theis and Victory. The
Michigan journal parser is merging adjacent names out of the vote columns, producing a name that
belongs to nobody, which then resolves to nobody and is dropped.

That is a **named cause**, and it satisfies the acceptance criterion. It is a scraper defect in
`openstates-scrapers/scrapers/mi/`, unrelated to any roster entry, and it should be its own
ticket — I have not filed one, because the labelling convention here wants a parent epic and
sibling-matched labels and I would rather you place it.

---

## 6. The sweep the ticket asked for — and it is bigger than Michigan

> *"How many others have a journal name that differs from their roster name? ... there is no
> reason to think she is the only one."*

Correct, and by a wide margin. Across every tracked jurisdiction:

| jurisdiction | person-votes | unresolved | % | distinct names |
|---|---|---|---|---|
| Virginia | 452,159 | **35,240** | 7.79 | 14 |
| United States | 535,622 | **22,279** | 4.16 | 205 |
| Massachusetts | 44,945 | **6,180** | 13.75 | 206 |
| Florida | 325,234 | 3,369 | 1.04 | 43 |
| Michigan | 91,524 | 1,427 | 1.56 | 154 |
| Washington | 171,556 | 673 | 0.39 | 1 |
| Arizona | 75,720 | 277 | 0.37 | 1 |
| Utah | 93,865 | **0** | 0.00 | 0 |
| **total** | **1,790,625** | **69,445** | **3.88** | **623** |

**69,445 vote records name a person and resolve to nobody.** Utah at zero shows this is not an
inherent property of the pipeline.

They are not one problem. Michigan alone splits into four distinct causes:

| class | distinct names | vote rows | example |
|---|---|---|---|
| roster name mismatch | 8 | 690 | `Myers-Phillips` (680 of them) |
| curly apostrophe | 1 | 379 | journal `O’Neal` (U+2019) vs roster `O'Neal` |
| merged surnames | 144 | 300 | `Theis Victory`, `Runestad Theis Victory` |
| mojibake | 1 | 58 | `OâNeal` — UTF-8 read as latin-1 |

The two apostrophe classes are the same legislator, Amos O'Neal, failing twice in two different
ways — 437 rows for a punctuation mismatch. Note the Massachusetts scraper already normalises
this (`pdflines.decode("utf-8").replace("’", "'")`); Michigan's does not.

Other jurisdictions have their own shapes, visible in the top unresolved names:
`Mr. Speaker` (MA, 250 rows — not a person at all), `Valdés` / `Gómez` / `García` (FL/MA
diacritics), `Banks (R-IN)` / `Sheehy (R-MT)` (US, chamber-suffixed forms), and Virginia's
14 names carrying 35,240 rows between them — an enormous concentration that nobody has looked at.

**This wants its own epic, not a bullet on this ticket.** I have deliberately not chased it: the
work here is Michigan's, and 69,445 rows across seven jurisdictions and at least six causes is
not something to fold into a ticket about one legislator's surname. But it should not go back to
being invisible either — it is the single largest data-quality finding in this batch, and it
bears directly on OPEN-38, since the whole case for serving the replica is that per-voter records
are better than the public API's.

---

## 7. On making an unresolvable voter loud (acceptance criterion 6)

The ticket asks for a decision recorded, and notes BROKER-95 and BROKER-111 are the same
silence-as-failure-mode.

**It is not quite silent today, and the detail matters.** `resolve_person()` does call
`self.error()` on a miss — but the message is:

```
no people returned for spec
```

It names neither the person nor the jurisdiction nor the vote. So 69,445 failures produced 69,445
log lines that cannot be acted on, which in practice is the same as silence but is a much cheaper
thing to fix: **include the spec in the message.** That is a one-line change in
`openstates-core/openstates/importers/base.py`, it is general rather than DDP-specific, and by the
OPEN-102 policy it would be a candidate to contribute upstream.

**My recommendation, for your decision:**

- **Do** make the message name the spec and the jurisdiction. One line, no behaviour change.
- **Do not** make an unresolvable voter fail the import. A roll call with one unmatched name is
  still 100 correct votes, and refusing the lot would trade a small silent loss for a large loud
  one. This is the same call the MA fix in OPEN-176 makes for the same reason.
- **Do** treat the count as the signal — `personvote.voter_id IS NULL` is already a one-query
  measure, per jurisdiction, and unlike a log line it is cumulative and cannot be missed. If
  anything deserves a watchdog, it is that number moving, not each individual miss.

That last point is why I have not built anything here. `check-scrape-staleness.sh` is the
existing pattern for "a number that should not move", and wiring this into it is a small, obvious
change — but it is a new watchdog behaviour and belongs with the epic in §6, not smuggled in
under a ticket about one name.

---

## What you need to do

1. **Choose a stopgap route** — §4, options A/B/C. Nothing else here is blocked on it, but the
   680 rows stay broken until one is picked.
2. **Re-import Michigan votes** (or backfill `voter_id`) once the corrected roster is in the
   production path — the roster load alone will not repair rows already stored.
3. **Re-run** `python manage.py report_unmatched_voters --jurisdiction MI` and expect the 30
   motions to clear. Per the ticket: motions that do not clear are a second cause, and §5 already
   names it.
4. **File two tickets** if you agree with them: the MI merged-surname parser defect (§5), and the
   fleet-wide unresolved-voter epic (§6).

No production data was written, and no live requests were made to any legislature site.

---

## Reference

- **OPEN-94** — the investigation this was split from, closed
- [openstates/people#4036](https://github.com/openstates/people/pull/4036) — the name fix, opened upstream
- `openstates-core/openstates/importers/base.py:573-700` — `resolve_person()`
- `ddp-broker-py` PR #350 — `report_unmatched_voters`
- **BROKER-111** — the same class of silent drop in a different guise
