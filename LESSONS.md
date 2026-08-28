---
name: Lessons the scrape pipeline paid for
description: What each production incident taught, and the rule that came out of it. Written for whoever rebuilds this pipeline somewhere else — the code can be replaced, these cannot be re-derived cheaply.
type: reference
---

# LESSONS — what this pipeline learned the hard way

**Read this before rebuilding any part of the scrape path.** `PRIMITIVES.md` is the sibling
document and answers a different question: it catalogs the scripts that exist and the conventions
they share. This one records **what went wrong, what it cost, and the rule that came out of it.**

## Why this document exists

`run-scrape.sh` is 1,244 lines, and **677 of them are comments.** It is not really a program; it is
a written record of 27 incidents with the code that prevents each one wrapped around it. That is
why replacing it is easy and *losing* it is not.

The migration to AWS (OPEN-180) will rebuild the runner from scratch rather than teach the existing
script to run in a container — a smaller job, and it avoids carrying the Mac's assumptions forward.
**The risk that decision creates is this document's reason for existing.** A fresh runner that does
not carry these lessons will reproduce the incidents that taught them, and most of them are silent.

**Two rules for anyone doing that rebuild:**

1. **Reuse rather than reimplement, wherever a decision already sits in a shared file.** The
   unreachable-site matcher and the import-report parser already live in `import-summary.sh`
   precisely so they can be sourced rather than copied. A second implementation of a judgement call
   is a second thing to keep correct.
2. **Every lesson below should end up with a test.** They are all *silent* failures — that is what
   makes them expensive — so none of them will announce itself if the rebuild gets it wrong.

## What comes free, and must not be touched

**48 tickets' worth of lessons live in `openstates-scrapers` and `openstates-core`**, not here: the
WAF and cookie resilience work (OPEN-19/21/22/23/52/53/54/106/132), Michigan's last-action baseline
(OPEN-134), the text-extraction and version-ordering fixes (OPEN-7/9/10/11/33/34/90/92), the
person-resolution chamber bug (OPEN-110–116). **All of it is already portable and runs anywhere.**
Nobody rewrites it, and a rebuild inherits it by using the same `os-update` entrypoint.

The lessons below are the ones encoded in *the part being replaced*.

---

## 1. Silent success is the failure mode that costs the most

Every expensive incident in this pipeline's history has the same shape: **something reported
success and had not done the work.** Not a crash. Not an alert. A green run.

### A zero is not a zero (OPEN-152)

`openstates-core` raises the same "no objects returned" error for *"nothing changed since the
cutoff"* and *"I could not read the site."* Treating the second as the first recorded a
WAF-blocked Michigan run as a measured zero on 2026-08-24 — **and advanced the watermark past a
window whose bills were never examined**, so no later incremental run would ever revisit it.

> **Rule.** A run that measured nothing must never advance its memory. Ask the run's own output
> which case it is before deciding. Absence of data and absence of access are different answers.

Encoded as `scrape_output_shows_unreachable_site()` in `import-summary.sh` — a marker list plus a
negation guard, so a future diagnostic line reading `no WAF block detected` cannot invert it.

### Count what changed, not what you wrote (OPEN-139)

Arizona scraped **895 bill files a night for 14 nights** while importing nothing new. Every health
check passed. The file count was flat and healthy; only the *import* knew that all 895 were
unchanged. A stuck incremental cutoff looks exactly like a working one if you measure the wrong
number.

> **Rule.** Health is `new + updated` from the load, not files written by the collection. Record
> both, and alert on the shape "collected many, changed none".

### Refusing is better than guessing (OPEN-134)

Michigan cannot run incrementally without its last-action baseline. The tempting fallback — seed it
from the site's current state — would mark every already-stale bill as current. **On the real
corpus that would have buried 187 genuine differences**, including bills that had become Public
Acts. The other fallback, treating everything as changed, is a ~3,900-request full walk against a
10-requests-per-minute cap.

> **Rule.** When memory is missing or corrupt and both automatic options are wrong, **stop and say
> so.** For an expensive or block-sensitive source, refusal is the expected behaviour, not a
> degradation.

### An unreadable answer is not an empty one (OPEN-181)

The same shape again, one layer out. When the memory store cannot be reached, "no memory" and "no
answer" must not collapse into one result — the first means collect everything, and for Michigan
that is the outage above.

> **Rule.** Reads of external state return three answers, not two: found, genuinely absent, and
> could-not-tell. Fail on the third.

---

## 2. Two runs of the same thing are worse than none

### Collection destroys its own directory (OPEN-154)

`openstates-core`'s `do_scrape()` **wipes the jurisdiction's data directory at scrape start.** Two
overlapping runs of one state therefore do not merely duplicate work — the second deletes
everything the first has collected, the first keeps writing into an emptied directory, and both
race to write the watermark.

> **Rule.** One collection per source at a time. In a design where each run writes its own
> isolated output this specific destruction disappears — **but the second reason to exclude does
> not: two runs double the request rate at a source that may be rate-limited or actively blocking.**

### A lock that cannot be cleared is an outage (OPEN-128)

A run killed between taking a lock and recording its owner leaves a lock nothing will ever release.
The fix is an age-out, and the threshold has to exceed any real run — **Massachusetts' full walk
measured 8.2 hours**, so the cutoff sits at 24.

> **Rule.** Every lock needs a defined way to be released by something other than its holder.

### Do the work incrementally or it collapses at the end (OPEN-86, OPEN-163)

The import-as-you-go sweep originally re-staged the *entire accumulated* output every cycle, so a
run's import cost grew all run long. Measured at ~62ms per staged bill, the final cycle for a large
jurisdiction runs for minutes — and the final import waits only 180 seconds for its lock before
failing the whole run. **A scrape that had worked perfectly for hours would be reported as a
failure.** Separately, successful sweep cycles logged *nothing at all*, so there was no evidence
the mechanism ever ran; `grep sweep` returning empty was misread as "it never executed".

> **Rule.** Bound per-cycle work to one interval's worth. And **log success, not only failure** —
> a mechanism that is silent when it works cannot be measured, tuned or closed out.

---

## 3. "Which copy is this?" must have no answer

### Inputs may fall back; outputs never may (OPEN-159, OPEN-172, OPEN-162)

Two checkouts share one machine. A dev run read **production's** watermark, announced
`incremental cutoff=2026-08-24T03:51:48`, and would have written production's markers from a run
that imported into a different database entirely — so production would silently skip the window
that other run had scraped. Found live on 2026-08-26, and **it only failed loudly because
Michigan's baseline guard happened to refuse.** A jurisdiction without such a guard would have
reported success.

> **Rule.** Configuration and paths may fall back to a shared default. **State that other runs read
> back may not.** If a runner can be asked "which copy are you?", the answer is a bug waiting.

---

## 4. Talking to a source that does not want to talk

### Retrying a block makes it worse (OPEN-53, OPEN-87)

A blind retry against a WAF is more traffic from an already-suspect client. So a block is
**terminal** — it must stop the run rather than feed a retry loop.

Two mechanical details that were learned the hard way:

* **The exit code is not enough.** The retry wrapper decides on a **flag file**, not the code, so a
  run meaning "do not retry" must do both. An exit code alone silently gets retried.
* **Classify where the evidence is.** The block marker is only visible in the scrape's own output.
  The scheduler sees a truncated stderr tail, which is why its own classifier never once fired on a
  real Michigan block.

> **Rule.** Decide terminal-versus-retryable at the one point that can actually see the evidence,
> and signal it in a way the retrying layer actually reads.

### The parts nobody thinks of also need resilience (OPEN-106)

A 12-day Utah stall came from `get_session_list()` — the *session list*, not the bills — having no
retry. Everything downstream was resilient; the first call was not.

> **Rule.** Resilience belongs on every request to a source, including the small ones.

---

## 5. Per-jurisdiction facts are load-bearing and easy to miss

* **Ten jurisdictions register a separate `votes` scraper** and must be asked for it by name —
  `ct ia ks ma md mn nm or pr tx`. Asking for it where it does not exist **fails the entire run**,
  so "always request votes" is not a safe simplification. Probe what the jurisdiction registers;
  do not keep a hand-maintained list (OPEN-50).
* **`--allow_duplicates` is needed by `mi`, `fl`, `va`, `ma`.** `ma` was missing from that list
  until OPEN-55, which cost a **completed 9,496-bill Massachusetts scrape its entire import**. The
  list had been extended four times by hand; it is now a flat comma list precisely so a missing
  entry is visible at a glance.
* **A jurisdiction can have two sessions active at once** — VA and UT both did (OPEN-24). Anything
  keyed on "the current session" is wrong.
* **Where a per-jurisdiction setting lives is itself a decision** (OPEN-124). Scheduling and
  eligibility belong to the scheduler's config; a data-behaviour flag that must hold on every run
  belongs with the runner. Six independently-invented mechanisms existed before this was settled.

---

## 6. Alerting has its own failure modes

* **Alert once and you will be ignored; alert always and you will be muted.** The staleness
  watchdog alerts in escalating tiers with a de-duplicating sentinel, because the original version
  alerted exactly once at the moment of going stale — easy to miss, and never repeated (OPEN-130).
* **Alert when a scheduled thing did not happen, not when a clock ran out.** The watchdog's
  deadlines are *derived from the scheduler's own config* rather than typed out separately, so the
  two cannot drift (OPEN-135).
* **The same alert function is copied in five scripts** (OPEN-43). Extraction is tracked; the
  watchdog may deliberately stay a copy, because monitoring should not share code with the thing it
  monitors.
* **A retry wrapper must suppress intermediate alerts**, or a blip that recovered on attempt two
  still pages someone twice (OPEN-87).

---

## 7. The machine you are on

Mostly irrelevant after the migration, but it explains a lot of the current code's shape, and the
first two matter anywhere:

* **Test the script, not just its helpers.** Three separate silent-failure bugs (OPEN-152, 154,
  155) accumulated in a script that could not be driven by a test. The fix was making it
  overridable enough to run against a stub.
* **A test that reaches production is not a test.** An early attempt at the above ran a real
  Virginia scrape against the live site because an environment variable was clobbered.
* This Mac's `/bin/bash` is **3.2.57** and permanently will be: no associative arrays, no
  `$BASHPID`. Its `stat`/`find`/`date` are BSD. Bash 4 syntax fails here with no warning.

---

## How to use this when rebuilding

For each lesson above, the rebuild should be able to answer: **what in the new design prevents
this, and what test proves it?** Where the answer is "the same code, sourced" — good, that is the
cheapest correct answer. Where it is "the new architecture makes it impossible" — say why, in
writing, because that claim is exactly the kind that turns out to be half true (the per-source lock
in OPEN-180's §3 dissolved for one of its two reasons and not the other).

Where the answer is "we will be careful", it is not answered.
