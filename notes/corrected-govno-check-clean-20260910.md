# Corrected go/no-go check: clean — resuming backfill with fl

Re-ran the check against the actual mechanism the hold was about, per Ramon's guidance:
`refresh-extraction ut --dry-run` inside the fixed toolchain (same throwaway local build,
Python 3.10.21/poppler 22.12.0, from `main` @ `9b1651e`).

**Result: `ut: [DRY RUN] bills_with_stale_docs=1 stale_docs=1 diffs_would_change=5
docs_skipped=0 docs_refused=0`** — down from the original 1021 bills / 3835 stale docs /
4671 diffs. Since `ut` was already committed earlier (with the old poppler), this dry-run
is really asking "does the new poppler agree with what's already stored?" — and the answer
is yes, for effectively the entire corpus. Only one bill/doc pair is still genuinely stale.

Also checked `id=56173` (the specific document used in the earlier before/after proof)
directly: its **currently stored** text (7,714 chars) is NOT stale — it matches a fresh
extraction with the new poppler exactly, byte for byte after cleanup. It was already
captured correctly by the earlier `ut --commit` run. (The dev agent's "0 bytes / 8,864
bytes" proof was almost certainly measured against raw PDF bytes with a reconstructed old
poppler binary directly, not this row's post-cleanup DB state — the two don't need to
reconcile 1:1, and don't change the conclusion here.)

**Read as a clean go/no-go: the two poppler versions are not meaningfully unstable against
each other on real production data — the fix changes a small, specific minority of
documents rather than perturbing everything.** Planning to resume the backfill with `fl`
next (per the original plan, `fl` doesn't use `refresh-extraction` — only
`recompute-diff-order` — so this was purely a confidence check before touching anything
past `ut`, not a step `fl` itself needs). Will run a fresh `recompute-diff-order fl
--dry-run` immediately before any `--commit`, per the established discipline, and stop and
report before touching `va`/`wa`/`us`.
