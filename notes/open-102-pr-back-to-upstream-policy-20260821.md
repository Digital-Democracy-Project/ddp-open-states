# OPEN-102: DDP's PR-back-to-upstream policy

`PLAN-fork-management.md` §7 identified a real gap: DDP has at least one fix
(`openstates-core`'s `d6653a5`/`767a2782`, "read `CACHE_DIR`/`SCRAPED_DATA_DIR` from env vars")
that's genuinely general -- it would fix the same bug for any consumer of the public
`openstates-core` project, not just DDP -- but was never actually opened as a PR against
`openstates/openstates-core`. There was no decided policy for when DDP contributes its own
fixes back upstream at all, so every future DDP-only fix faced the same undecided question.

## The decision

**Yes, DDP does open PRs upstream, but only for fixes that are genuinely general** -- a bug or
gap that would affect any consumer of the public project, not behavior that's specific to DDP's
own operational choices (proxy/resilience-profile setups, WAF-evasion tactics, DDP's own
archival/versioning features). Concretely:

- **Contribute upstream:** a fix to a real bug in shared code (an importer, a model, core
  utilities) that has no DDP-specific assumption baked in, and is small/self-contained enough
  to review on its own. `d6653a5`/`767a2782` is exactly this shape -- a portable env-var
  fallback fix, unrelated to anything DDP-specific.
- **Keep DDP-only:** anything that encodes a DDP-specific operational choice or tradeoff that a
  different consumer of the public project might reasonably want to make differently. The
  clearest example found this session (OPEN-98's upstream-merge cycle, 2026-08-21): DDP's Utah
  scraper fix blends in as a browser User-Agent to dodge WAF blocking, while upstream's own fix
  for the same underlying symptom self-identifies honestly per Utah's legislature's explicit
  request. Both are legitimate; they're just different policy choices, and DDP's isn't
  something to push onto the public project as "the" fix.
- **Cadence/trigger:** opportunistic, not scheduled. Whoever lands a DDP fix that turns out to
  be genuinely general opens (or flags for opening) the upstream PR as part of closing that
  same piece of work, rather than batching it into a separate review cycle. This matches how it
  already happened once in practice, discovered during OPEN-98's 2026-08-21 merge: the FL
  `flhouse.gov` WAF-session-refresh fix (`f76852483`, opened as openstates/openstates-scrapers#5751)
  was DDP's own earlier contribution, opened and merged upstream the same way this policy now
  describes explicitly.
- **Who reviews:** no separate DDP-side review gate beyond the normal PR review DDP already
  does for its own fork -- the public project's own maintainers are the real reviewers for an
  upstream PR, the same as any other outside contributor.

## Resolving the one concretely known pending case

`d6653a5`/`767a2782` fits the "contribute upstream" bucket cleanly: portable, small, no
DDP-specific assumption. **Not yet opened as a real PR against `openstates/openstates-core`** --
opening a PR against a third-party public repository is a visible, externally-facing action
(unlike everything else in this epic, which stays inside DDP's own forks/infra), so it's
deliberately left for an explicit human go-ahead rather than done automatically as part of this
epic's otherwise-autonomous PR/pm-review/In-Review flow. See the OPEN-102 Jira ticket for that
decision once made.
