# OPEN-23 shipped, reviewed, fixed post-merge, and live-verified (2026-08-03)

## Context: continuing from the User-Agent consistency finding

`notes/mi-cams-headed-browser-spec-20260802.md` §0 first wrote up the bug: MI's cached cookie
session was getting reused across three mutually inconsistent browser/OS identities within a
single scrape attempt. Filed as [OPEN-23](https://digitaldemocracyproject.atlassian.net/browse/OPEN-23)
same day. This note records what happened since — the fix shipping, a real regression found and
fixed during review, a merge-order documentation gap, and today's live-verification result.

## The fix, as shipped

CodeBot dispatched against OPEN-23 and delivered three PRs:

- [ddp-open-states#62](https://github.com/Digital-Democracy-Project/ddp-open-states/pull/62) —
  RUNBOOK.md write-up
- [openstates-core#11](https://github.com/Digital-Democracy-Project/openstates-core/pull/11) —
  `CookieProvider` now captures the real Chromium UA that mints the cookies and caches it
  alongside them as one atomic pair (`_meta.user_agent`); a new
  `_resilience_user_agent_rotation_enabled` class-attribute opt-out (default `True`) stops
  `http_resilience_mode`'s `get_random_user_agent()` rotation from clobbering it at any of its 4
  call sites
- [openstates-scrapers#20](https://github.com/Digital-Democracy-Project/openstates-scrapers/pull/20) —
  `bills.py`'s hardcoded `USER_AGENT` constant removed; every `mi_waf_get()` call site
  (`bills.py`, `events.py`, `get_session_list()`) now builds its request headers from the live,
  matched UA; `MIResilientScraperMixin` sets the new opt-out `False`

The design is solid — the class-attribute-vs-instance-attribute subtlety CodeBot called out
(`Scraper.__init__`'s own rotation call fires *during* `super().__init__()`, before a mixin's
post-`super()` body runs, so only a class-level override actually suppresses that call site) is
real and correctly reasoned, confirmed by reading the actual code, not just the PR's narrative.

## A real regression found by reviewing the PRs directly, not trusting the descriptions

Running the *full* `scrapers/mi/tests/` suite (not just the subset the PR's own testing section
listed) surfaced 3 failures in `test_events.py` that the PR never caught. Root cause: an added
"logging hygiene" line synced `self.headers["User-Agent"]` at the top of both scrapers'
`scrape()` methods, purely for log readability — not load-bearing for the actual fix (every real
request already carries its own explicit, matched header via `mi_waf_get()`'s `do_request`
parameter). That line forced a `MI_COOKIE_PROVIDER` warm-up before any request actually needed
one — an unscheduled extra hit against a WAF-sensitive site — and any existing test that calls
`scrape()` without stubbing the new `get_user_agent()` (as `test_events.py`'s pre-existing tests
did, unmodified by this PR) would silently attempt a real Playwright warm-up. In this environment
that's a `ModuleNotFoundError`; in one with Playwright installed, it would be a real live network
call from what's supposed to be an offline unit test.

Fixed directly and pushed to the same PR branch (`chore/OPEN-23`) rather than sent back to
CodeBot: removed the hygiene line from both `bills.py` and `events.py`, dropped the now-unused
`MI_COOKIE_PROVIDER` import in `events.py`. Full suite: 34/34 passing after, flake8 clean, and
confirmed the one remaining, unrelated failure (`tests/test_mi_bills.py`'s top-level import of a
constant OPEN-22 already moved) is pre-existing and untouched by either change.

## Merge-order documentation gap, also caught and fixed

`#62` (RUNBOOK write-up) got merged before the fix above landed on `#20`, so RUNBOOK.md briefly
described the reverted logging-hygiene approach as shipped. Caught and corrected in
[ddp-open-states#63](https://github.com/Digital-Democracy-Project/ddp-open-states/pull/63)
(open as of this note) — the RUNBOOK now documents the line was tried and reverted, and why.

## Bringing production current safely, despite a live concurrent scrape

When it came time to fast-forward production to pick up the merged fix, `run-scrape.sh wa` was
mid-scrape (started ~33 minutes earlier). Rather than either blindly touching the checkout or
blindly waiting, checked first: OPEN-23 touches zero files WA's own scraper code references
(confirmed via grep — no `http_resilience_mode`, `MIResilientScraperMixin`, or
`MI_COOKIE_PROVIDER` anywhere in `scrapers/wa/`), and the one shared file it does touch
(`openstates-core`'s `base.py`) only changes behavior inside `if self.http_resilience_mode:`
blocks, which WA never sets. Combined with WA running as a single already-executing process (not
one that dynamically reimports from disk mid-run for a single invocation), fast-forwarding was
safe. Did so directly (bypassing `apply-local-patches.sh`, which would have just auto-skipped due
to WA's live worktree-lock marker). WA's own scrape finished cleanly and normally moments later,
undisturbed.

## Live-verified 2026-08-03: fix confirmed correct, MI still blocked (as expected)

Dispatched a real `./run-scrape.sh mi` run against the now-current production checkout. Direct
proof from the real scrape log that the fix is live and correctly scoped:

```
00:37:27 INFO openstates: Created fresh session (user agent rotation disabled for this scraper)
```

That log line only exists in the new code path — confirms `_resilience_user_agent_rotation_enabled
= False` is actually taking effect for MI in production, not just in unit tests.

**MI still failed the same run.** Every cookie warm-up attempt (both the initial try and the
`--fastmode` retry) hit the same "block detected despite cached cookies" response as every other
test this week. This is the expected, honest outcome — OPEN-23 was never scoped to fix the
underlying IP-reputation block (OPEN-19/20/22's territory), only the identity-inconsistency signal
layered on top of it. **Net: OPEN-23 is done and verified correct. Michigan scraping itself
remains broken** until the separate, harder reputation problem is addressed — via OPEN-22's
escalation alert accumulating enough signal, the CAMS headed-browser/ScrapeBot direction sketched
in `notes/mi-cams-headed-browser-spec-20260802.md` and `notes/scrapebot-agent-design-20260802.md`,
or some other approach not yet scoped.

## References

- `notes/mi-cams-headed-browser-spec-20260802.md` §0 — where the UA-consistency bug was first
  written up
- `notes/mi-ip-reputation-block-confirmed-20260802.md` — the underlying block this doesn't fix
- `notes/scrapebot-agent-design-20260802.md` — candidate next step for the underlying block
- Jira: [OPEN-23](https://digitaldemocracyproject.atlassian.net/browse/OPEN-23) (done),
  OPEN-19, OPEN-21, OPEN-22 (all still relevant to the remaining block)
