# UPDATE (adds to `a4ed7d5` step (c); still NOT a GO): **the next manifest rollout also turns Maine live and carries other `main` changes.** 2026-11-28 (Mac side, Onboard New States)

## What I need from you
1. **Before the manifest rollout (step (c) of `a4ed7d5`), read the dry run's change list against this list** (I diffed `jurisdictions.yaml` between `4c78d958`, your last rollout, and `main` today): (a) **Maine: `status` scraping to live and `search_refresh`, `embedding`, `api_smoke_test`, `qa_sweep` false to true** (ddp-open-states #514, merge `6d639993`; Ramon's two conditions for Maine are met: OPEN-907 is in the image, the recompute is committed and verified), so **this rollout is Maine's go-live: it needs Ramon's go in your session naming Maine**, and it ends your 11-27 hold note on Maine; (b) a new optional field `scrape.probe_urls` on every state (#518; the pull first brings the validator that accepts it); (c) Kentucky `quality.diff_cleaner` `none` to `clean_ky_text` (#515; the v101 core carries it); (d) Iowa `accepted_unmatched_voters: [Open]` (#517); (e) Mississippi `quality.diff_cleaner` `none` to `clean_ms_text` **only if #520 is merged by then** (held until your note shows v101 live; I will say when). Stop and report any other difference; do not run the real rollout.
2. The drift check after the rollout should be clean for every state, including Mississippi (once #520 is in) and Kentucky.
3. The held draft pull requests #521 (Nevada go-live), #522, #523 and #524 are **not** merged and stay out of this rollout.

## Not authorized
As in `a4ed7d5`: the real rollout without Ramon's go naming Maine; any other state's change; `legbot_replica`; VoteBot's state list; any commit.

Tickets: OPEN-672, OPEN-887, OPEN-946, OPEN-912, OPEN-949; OPEN-146.

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
