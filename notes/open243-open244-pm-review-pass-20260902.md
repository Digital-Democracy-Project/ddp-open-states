# PR #114 and PR #220 also passed a product/implementation review before you get to them

*Adds to `notes/open243-open244-fixes-pr114-pr220-20260902.md`.*

Ran both through this project's `/pm-review` process before you pick them up (Ramon asked
specifically). Results:

- **PR #114 (OPEN-243, ddp-sync):** approved, ship. Only low-severity notes, all rollout
  items rather than code changes (confirm `OPENSTATES_ROOT` gets set on every non-Mac host,
  confirm no other call site needs the same treatment) plus one optional test. Added the
  optional empty-string-env-value test anyway since it was cheap and genuinely locks in
  correct existing behavior — pushed as a follow-up commit, still not merged.
- **PR #220 (OPEN-244, ddp-open-states):** needs-revision on first pass — the precedence and
  no-op tests confirmed status/exit code but not the underlying invariant they exist to
  protect (that an unreachable-classified run publishes *no* watermark marker at all, and
  that a no-op publishes exactly `0:incremental` with no manifest). The code itself was
  already correct — this was a test-coverage gap, not a bug — confirmed by re-running the
  strengthened suite (56/56 still pass). Pushed as a follow-up commit, still not merged.

Nothing here should change what you were already planning to do — just flagging the extra
review pass happened and both branches have one more commit each since the original note.
