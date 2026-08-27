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
She is the single largest unmatched name in Michigan by a wide margin — 680 rows against 379
for the next largest, `O’Neal`. Michigan holds 1,427 unresolved rows across 154 names, so she is
not larger than the other 153 combined (680 against 747); §9's acceptance query states the same
two numbers.

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

Exactly one match is what `resolve_person()` needs — it errors on zero and on more than one.
`os-people lint mi` passes. No production database was touched.

**The bare-`Phillips` row deserves a word, because zero could mean either "safe" or "regression".**
Her `family_name` changes from `Phillips` to `Myers Phillips`, so a journal writing a bare
`Phillips` would stop resolving to her. It would be a regression if Michigan ever wrote her that
way. It does not — there is not a single Michigan vote row whose voter name is `Phillips`:

```sql
SELECT DISTINCT pv.voter_name FROM opencivicdata_personvote pv ... 
 WHERE j.id LIKE '%state:mi%' AND lower(pv.voter_name) = 'phillips';
-- (none)
```

Every Michigan vote naming her spells it `Myers-Phillips`, all 680 of them. The zero is the safe
kind.

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

Three real options:

| option | effect | cost |
|---|---|---|
| **A. Wait for upstream** | correct everywhere, no local divergence | unbounded — the precedent is a month and counting |
| **B. Re-point production's `people` at the DDP fork**, carry this fix there, merge upstream regularly | DDP roster corrections take effect within one weekly refresh | a standing fork to own, sync and eventually exit |
| **C. Targeted backfill of `voter_id`** on the 680 rows | repairs the data now, with the roster fix landing separately | none that survives, once the roster is right — see below |

**I originally recommended B. On the evidence below I now recommend C for the repair, and treat B
as a separate decision that is not this ticket's to make.**

Two things changed my mind.

**C's stated weakness does not actually hold.** The objection to a backfill is that it "does not
survive the next import". That is true only while the roster is still wrong. Once
openstates/people#4036 (or an equivalent) is in the pipeline, a re-import resolves her correctly
by itself — so a backfilled row is either left alone or rewritten to the same value. The backfill
stops being a recurring chore and becomes a one-off catch-up.

**B is not a stopgap, it is a platform decision.** Re-pointing production's roster source changes
where the pipeline's people data comes from, permanently, and needs answers this ticket has no
business settling: who owns the fork, how often it merges upstream, what is allowed onto it, what
reviews it, and what event moves production back to upstream. Those are OPEN-38-level questions —
they apply to every future roster correction, not to one surname — and they should be decided as
policy rather than inherited from a bug fix. Worth deciding soon, since §6 shows a lot of
roster-shaped work queued behind the same upstream wait.

### How the repair actually behaves, since the plan rests on it

`PersonVote` is registered in the vote-event importer's `related_models`
(`vote_events.py:15-17`) with no merge key, which puts it on `_update_related()`'s default path:

```python
# default logic is to just wipe and recreate subobjects
if do_delete:
    getattr(obj, field).all().delete()
if do_update:
    self._create_related(obj, {field: items}, subfield_dict)
```

`items_differ()` compares the incoming rows — which carry a freshly resolved `voter_id` — against
the stored ones, which carry NULL. They differ, so the rows are deleted and recreated. **A
re-import repairs the NULLs and cannot duplicate them.** That is a code-level guarantee rather
than an assumption, and it is worth stating because "re-import to fix it" would be a bad plan if
the importer merged rather than replaced.

### But a re-import cannot reach most of the 680, and that is the real constraint

`run-scrape.sh`'s `do_scrape()` wipes `$SCRAPED_DATA_DIR/$STATE` at the start of every run, so
`openstates-scrapers/_data/mi` holds only the **last** run's output — today, 398 bill files from
the 2026-08-24 incremental. An import-only pass (`os-update mi --import`) would therefore repair
only the vote events in that partial set, not the eighteen months of rows.

Reaching all 680 by re-import means a **full Michigan re-scrape** — roughly 3,800 requests over
7–8 hours against the fleet's most WAF-sensitive jurisdiction. That is a large price for a
column update whose correct value is already known and unambiguous.

Hence the recommendation: **backfill the column, and let the roster fix prevent recurrence.**

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

1. **Backfill `voter_id` for the 680 rows** (§4). This is the repair, and it is a production
   write, so it is yours. Before/after checks below.
2. **Decide separately** whether production's roster source moves to the DDP fork (§4, option B).
   Not required for the repair; it decides how fast the *next* roster correction lands.
3. **Re-run** `python manage.py report_unmatched_voters --jurisdiction MI` and expect the 30
   motions to clear. Per the ticket: motions that do not clear are a second cause, and §5 already
   names it.
4. **File two tickets** if you agree with them — drafts in §8, so it is a paste rather than a
   writing job.

### Acceptance, measured at the replica

The ticket's own criterion is the broker's 30 motions, but this plan argues the replica's 680 rows
are the impact that matters — so that is where it should be checked. Before and after:

```sql
-- expect 680 before, 0 after
SELECT count(*) AS unresolved
FROM opencivicdata_personvote pv
JOIN opencivicdata_voteevent ve ON pv.vote_event_id = ve.id
JOIN opencivicdata_legislativesession s ON ve.legislative_session_id = s.id
JOIN opencivicdata_jurisdiction j ON s.jurisdiction_id = j.id
WHERE j.id LIKE '%state:mi%' AND pv.voter_name = 'Myers-Phillips'
  AND pv.voter_id IS NULL;

-- expect 0 before, 680 after, ALL pointing at the one existing identity
SELECT pv.voter_id, count(*)
FROM opencivicdata_personvote pv
JOIN opencivicdata_voteevent ve ON pv.vote_event_id = ve.id
JOIN opencivicdata_legislativesession s ON ve.legislative_session_id = s.id
JOIN opencivicdata_jurisdiction j ON s.jurisdiction_id = j.id
WHERE j.id LIKE '%state:mi%' AND pv.voter_name = 'Myers-Phillips'
GROUP BY 1;
-- expected: one row, ocd-person/787d9bda-d4dd-47fe-aaf0-348c505211e4, 680

-- expect 1,427 before and 747 after -- nothing but her rows should move
SELECT count(*) FROM opencivicdata_personvote pv
JOIN opencivicdata_voteevent ve ON pv.vote_event_id = ve.id
JOIN opencivicdata_legislativesession s ON ve.legislative_session_id = s.id
JOIN opencivicdata_jurisdiction j ON s.jurisdiction_id = j.id
WHERE j.id LIKE '%state:mi%' AND pv.voter_id IS NULL;
-- 1,427 before; 747 after (1,427 - 680), all of them the §6 causes
```

And the total number of Michigan person-vote rows (**91,524**) must be identical before and after
— a backfill sets a column and must not change how many vote rows exist. If that number moves,
something other than the backfill ran.

## 8. Draft tickets, so these are not lost

I have not filed these. Filing was not part of what I was asked to do, and this repo's convention
wants a parent epic and labels copied from sibling tickets rather than invented — that is your
call to place. Both are written to be pasted.

**Ticket 1 — MI: the journal parser merges adjacent legislators' surnames into one voter name**

> Labels: `local-openstates-migration`, `data-quality`. Parent: OPEN-38 (or wherever the MI
> scraper defects sit).
>
> Michigan roll calls produce voter names that are two legislators joined into one string —
> `Theis Victory`, `Bellino Bumstead`, `Hauck Hoitenga`, `Lindsey Outman`, and 140 others.
> They match no roster entry, resolve to nobody, and are silently dropped, leaving the motion's
> attached votes short of its stated tally. 144 distinct merged names across 300 vote rows in
> Michigan. Root-caused in OPEN-174 §5 while explaining broker motions 4165/4166 (the ticket's
> original 4161/4162), where the effect is a Senate motion 26 votes short of its own text.
> The defect is in the vote-column parsing in `openstates-scrapers/scrapers/mi/`; it is not a
> roster problem and no roster fix will touch it.

**Ticket 2 — Fleet-wide: 69,445 vote records name a person and resolve to nobody**

> Labels: `data-quality`, `local-openstates-migration`. Parent: likely its own epic.
>
> Across all seven tracked jurisdictions, 69,445 of 1,790,625 person-vote rows (3.88%) have a
> voter name and a NULL `voter_id` — 623 distinct names. Virginia 35,240; US 22,279;
> Massachusetts 6,180. Utah is zero, so this is not inherent to the pipeline. At least six
> distinct causes are already visible (roster name mismatch, curly apostrophes, mojibake, merged
> surnames, non-person entries like `Mr. Speaker`, chamber-suffixed forms like `Banks (R-IN)`).
> Bears directly on OPEN-38: the case for serving the replica rather than the public API is that
> its per-voter records are better, and these are records where we have a name and no person.
> Measured in OPEN-174 §6; not investigated further there deliberately.
>
> Recommended first step: classify Virginia's 14 names carrying 35,240 rows. That is half the
> total and the smallest number of distinct causes.

**Does this block the MA/MI production flips?** My read is that it **informs** rather than blocks:
these rows carry a voter name, so nothing is silently wrong on the page in the way OPEN-1 was —
a tally is short, which reads as an absence. But it is a launch-risk decision rather than a
technical one, and it should be recorded on OPEN-38 either way rather than left implicit.

No production data was written, and no live requests were made to any legislature site.

---

## Reference

- **OPEN-94** — the investigation this was split from, closed
- [openstates/people#4036](https://github.com/openstates/people/pull/4036) — the name fix, opened upstream
- `openstates-core/openstates/importers/base.py:573-700` — `resolve_person()`
- `ddp-broker-py` PR #350 — `report_unmatched_voters`
- **BROKER-111** — the same class of silent drop in a different guise
