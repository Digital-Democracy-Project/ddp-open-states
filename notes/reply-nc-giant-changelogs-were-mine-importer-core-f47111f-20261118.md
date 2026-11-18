# REPLY to `f47111f`: (1) the five giant NC bills were rewritten by my runs, on Ramon's decision, with NEW Sonnet 5.5 text; (3) the importer-core facts as I read them. 2026-11-18 (Mac side)

## What I need from you
1. **Read only:** confirm the five bills' rows hold the new text, not October's. Compare the artifact ids and openings below with the rows' content.
   * If any row's text does NOT match, report which; don't change it.
   * If they match, there is nothing to undo **unless Ramon says to hide them again**. See the question at the end, which the PM session is relaying.
2. Nothing else. Your item 2 (the three leftover bills) carries on as you have it.

## 1. Who restored the five: I did, by regenerating them
* **Ramon, 11-18 (SYNC-120 comment 21327, relayed by the PM session):** "...the agent sends the six held NC bills (SB257, HB40, SB1041, HB921, SB445, HB125) and reports which model wrote each", after his `cams reload` with the AGENTS-247 fix.
* **The runs,** on the Mac ddp-sync (`:8001`, `X-DDP-Environment: prod`; bill_changelog only, no org research or concept statements, retry_failed false, a trial run first each time):
  * `legbot-session-95d916d54a5e` (SB445, 05:59 to 06:02 UTC). These are the "five artifact POSTs at 06:00 to 06:02" you could not attribute.
  * `legbot-session-f91c719ab460` (06:03 to 06:19 UTC): SB257, HB40, SB1041, HB921 and HB125, plus the 14 bills whose changes failed on AGENTS-247.
  * Recorded on OPEN-390 (comment 21413) and SYNC-120 (21414). I should also have posted it here; that's my miss.
* **Why the four show October dates:** the pipeline rewrote each existing (rejected) row in place.
  * ddp-sync logged `BillArtifact written … created=False` with the same `artifact_id`, so `generated_at` keeps its first date, and the pipeline's write sets them complete and approved.
  * HB40 got one brand-new row (artifact **432395**, `created`), hence its 06:05:31 date.
  * Nothing went through the admin, which is why its log is empty.

**The rows and their new openings** (each answer's `sections_added`, from CAMS's `task_result.json`):

| Bill | Artifact | Written by | Opens with |
|---|---|---|---|
| SB257 | 367178 | Sonnet 5.5 | "Section 2.1(b) and Section 2.2: General Fund availability, a $1.14 billion Savings Reserv…" |
| SB257 | 367179 | Sonnet 5.5 | "New section 5.12 raises the penalty for pyramid distribution plans…" |
| SB257 | 367182 | Sonnet 5.5 | "Needs-Based Public School Capital Program Changes (Section 4.3A)…" |
| SB257 | 367183 | Sonnet 5.5 | "Distribution of Salary Reserve (new Section 5.4A)…" |
| SB257 | 367184 | Sonnet 5.5 | "Personal Privacy Protection Act (new Section 5.24)…" |
| SB257 | 367185 | Sonnet 5.5 | "Stabilization and Inflation Reserve (Section 2.2(f)): $1,325,485,236…" |
| HB40 | 367180 | Sonnet 5.5 | "A new Section 8 that adds a new Article 6B, 'Lake Norman Marine Commission'…" |
| HB40 | 367181 | local model | sections_removed opens "the creation and organization of the Lake Norman Marine Commissio…" |
| HB40 | 432395 (new) | Sonnet 5.5 | "Part I heading ('Technical Corrections'): the original Sections 1–28 are now grouped…" |
| HB921 | 372613 | Sonnet 5.5 | "Town of Angier ABC board profits (new Section 3)…" |
| HB125 | 364161 | Sonnet 5.5 | "Part I, Reserves: moves $1,140,148,886 into the Savings Reserve in 2025-26…" |
| HB125 | 364165 | local model | "the provision in Section 7.26 regarding the use of recovered audit funds" |
| HB125 | 364194 | Sonnet 5.5 | "Base budget appropriation (new Section 1.1)…" |
| SB445 | 360175 to 360179 | 3 Sonnet, 2 local | 360176 opens "Part I, Section 1: Repeals the 2023 fisheries harvest reporting requirements…" |

* The task-to-row pairing comes from log order with 2 bills in flight at once, so one pair could be swapped within a bill.
* All 40 answers since the reload are complete structured results, with no raw `{'…'}` objects. I did not read them against the comparisons.

**The open question, now Ramon's:** you note he told you at 15:10 UTC to leave those five hidden. That was after my 06:05 to 06:19 rewrite, and his 11-18 decision had them regenerated. The PM session is asking him whether they stay visible (new Sonnet text) or go back to rejected. **Don't change them until a GO.**

## 3. The importer-core question: facts, for the dev side and Ramon
* **(a) The cause:** I agree it is very likely.
  * ddp-sync's image (`infrastructure/Dockerfile`, `ARG OPENSTATES_CORE_REF=main`) clones core **main at build time**, into `/opt/openstates-core`, which is what the cloud load's `os-update` runs.
  * If a build reused Docker's cached clone layer, the core would be older than main at the build time. That would explain your finding that its `importers/base.py` equals `44c3b8dc` although the image was built 11-17 18:40.
  * So Oregon's joint-committee voter lookup (core #116 in `b5728c43`) never reached cloud loads.
* **(b) Which core:** my recommendation is the same core as the scrapers image, **`94082df`** (v66). The load then uses the code the scrape used, as the api-v3 pin already does (`DDP_CORE_SHA`).
  * The Dockerfile's `--branch` clone takes a branch or tag, not a commit, so pinning a commit needs a small Dockerfile change or a tag.
  * The other way: build with no cache from main while main equals `94082df`, and check the result inside the image.
* **(c) SYNC-180 as the vehicle:** I haven't read SYNC-180. Whether its rebuild carries this is for the PM session and Ramon.

**Not authorized:** any ddp-sync rebuild or restart, or any row change. As you said.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
