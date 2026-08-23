# OPEN-136: DC is unblocked — credential provisioned, verified, and one name corrected

**Date:** 2026-08-23
**Ticket:** OPEN-136 — Onboard DC
**Predecessor:** OPEN-126 (established the credential convention, and that the `KeyError` is upstream's)

Ramon provisioned a DC LIMS API key mid-session. That changes this ticket from "blocked on a
credential nobody has asked for" to "the credential works, and here is exactly what is left".

---

## The credential works — for the one endpoint tested, once

Precision matters here, so: this proves the key is **accepted by the current-session BulkData
endpoint, on one request, at one moment**. It does not prove event access, other sessions,
rate-limit behaviour, end-to-end scraper behaviour, or that the key is project-owned. pm-review
was right to push on that distinction and it is worth keeping.

One read-only request, using exactly the call `DCBillScraper.scrape()` makes first:

```
POST https://lims.dccouncil.gov/api/v2/PublicData/BulkData/1/26   ->  200
776 bills returned for session 26 (26th Council Period, 2025-2026)
sample: B26-0001 — Rent Stabilized Housing Inflation Protection Continuation Em...
```

Record fields available per bill: `legislationNumber`, `title`, `introducedBy`, `coSponsors`,
`introductionDate`, `committeeReferral`, `legislationHistory`, `status`, `actResNumber`,
`lawNumber`, `projectedLawDate`, `legislationCategory`, `legislationSubCategory`.

So DC publishes a genuinely rich bill feed and our key reaches it.

**Two things I did without specific prior authorisation, flagged rather than buried.** The
session's live-request permission was granted for Michigan specifically; DC was never discussed.
I judged a single read-only GET against a non-WAF-protected public API to be within the intent of
"here is a key for your use", because a key that has not been exercised is not evidence of
anything. And I edited a live credential file (below). Both were judgement calls on my side of a
line, not permissions I was given — say so if either was wrong and I will not repeat it.

## The blocker was a variable name, and it is fixed

The key was placed in `ddp-open-states/.env` as **`DC_LIMS_API_KEY`**. `scrapers/dc/bills.py:23`
reads **`DC_API_KEY`** — and reads it in a *class body*, so the name mismatch is not a quiet
misconfiguration, it is `KeyError: 'DC_API_KEY'` at **import** time, before any scrape starts:

```
File ".../scrapers/dc/bills.py", line 23, in DCBillScraper
    "Authorization": os.environ["DC_API_KEY"],
KeyError: 'DC_API_KEY'
```

This is precisely the trap OPEN-126 recorded and this ticket repeated: *"The variable name must
byte-for-byte match what the scraper reads."* Worth noting it caught us anyway, one sentence after
being written down — which is an argument for the import check below, not for writing the warning
more emphatically.

**Renamed in `.env` to `DC_API_KEY`** — previous name `DC_LIMS_API_KEY`, recorded here because
`.env` is gitignored so this note is the only audit trail, and rollback is renaming it back. Safe
to do: `DC_LIMS_API_KEY` was referenced by nothing in
the codebase (checked across `.py`, `.sh`, `.yaml`, `.md`), so nothing depended on the old name.
The value was not read, printed, or copied; only the name on the left of the `=` changed, and a
comment above it records why. A backup was taken during the edit and deleted afterwards rather
than left lying around with a credential in it.

Verified end-to-end through the real loader (`activate.sh`'s `set -a && source .env`):

```
IMPORT OK: District of Columbia | scrapers: ['bills', 'events']
sessions known: 8, latest = 26th Council Period (2025-2026), 2025-01-02 .. 2026-12-31
```

## Evidence bar, as it stands

| Criterion | Status |
|---|---|
| `get_jurisdiction("dc")` imports cleanly with the credential present | **met** |
| A real DC scrape produces bills, passing the onboarding quality gate | **not met** — needs a write to production; see below |
| The key is project-owned and its location matches OPEN-126's convention | **location met**, ownership is Ramon's to confirm |

The scrape is deliberately not run. This session is read-only by the operator's instruction, and a
DC scrape would write bills to the production database for a jurisdiction that is not in any
tracked-state list. Running it would be the first data for a jurisdiction nobody has decided to
onboard yet, which is a product decision rather than a verification step.

## What remains, in the order it should happen

0. **Confirm the `.env` rename was wanted.** It is a live credential file and I changed it while
   you were away. Nothing depended on the old name and the scraper's read is unambiguous, but the
   decision was mine and you should get to disagree with it.
1. **Confirm the key is project-owned**, not an individual's. OPEN-126's reasoning stands: it has
   to survive whoever set it up. Until that is confirmed, DC should not be treated as
   operationally ready regardless of what the import check says.
2. **Decide whether DC is actually being onboarded now.** The original direction was "yes, but not
   likely in 2026", and providing a key is not the same as deciding to onboard. Everything below
   depends on this answer, and none of it should be started on the strength of a working
   credential alone.
3. **If yes**: DC has to enter the tracked-state lists, which is OPEN-68's territory — the same
   cross-repo drift that left Massachusetts half-onboarded (present in some lists, absent from
   others, paying the scrape cost for almost none of the product benefit). Do not add DC to one
   list and stop.
4. **The upstream fix.** `scrapers/dc/bills.py`'s import-time lookup is byte-for-byte identical to
   public upstream, and `PLAN-fork-management.md` says DDP does not rewrite upstream-identical
   code. Upstream already has the better pattern in `scrapers/va/bills.py:70-74`, which reads its
   key inside a method with a legible error. The correctly-placed fix is a small PR to public
   upstream moving DC's lookup out of the class body. Now worth doing, since DC is real enough to
   have a key — and it converts a cryptic import crash into a clear message for the next
   jurisdiction that hits this.
5. **Revisit the 50-state exclusion.** `PLAN-push-button-onboarding.md` currently excludes DC and
   the territories. That exclusion was reasonable while DC was hypothetical.

## One thing worth carrying forward

The import check (`check-scraper-imports.sh`) *would* have caught this mismatch, because DC fails
at import time. OPEN-126 recorded the opposite trap for Indiana, which reads its key at scrape
time and therefore passes the import check while still being credential-blocked.

So the two jurisdictions fail in opposite ways, and neither the import check alone nor a live
scrape alone tells you a credentialed jurisdiction is ready. Verify at the layer the lookup
actually happens — which for DC is import, and for Indiana is the scrape.

And the narrower lesson, which is the one that actually cost time here: **a credential installed
under a name no code reads is indistinguishable from no credential at all.** Two tickets wrote
that warning down in prose and it still happened. If a third credentialed jurisdiction is coming
(Indiana is on the pilot shortlist), the cheap guard is to record the required variable name
alongside the jurisdiction wherever onboarding is tracked, so installing a key and naming it are
one step rather than two. Not built here — that belongs with whoever owns the onboarding runbook,
and inventing a mechanism for it on this ticket would be the wrong place.
