# UT's 6,270 refused docs: not an extractor regression -- this EC2 host is missing pdftotext

*Replies to `notes/docs-refused-reason-reporting-fix-20260909.md`.* Pulled `openstates-core`
main (`5c79b47d`, PR #42/OPEN-259+OPEN-258) into this checkout and re-ran `refresh-extraction ut
--dry-run` against RDS. The fix works exactly as described — 8 lines of output total, one
harmless `DEBUG` line (`openstates.stats: Stat emission is not enabled`), no token leak, and an
actual reason this time:

```
ut: [DRY RUN] bills_with_stale_docs=1021 stale_docs=3100 diffs_would_change=2079 docs_skipped=0 docs_refused=6270
  refused 6270: extraction raised: error running pdftotext, missing executable? [[Errno 2] No such file or directory: 'pdftotext']
```

All 6,270 are the same root cause: **this EC2 host doesn't have `pdftotext` (poppler-utils)
installed.** Not an extractor logic regression on real content — every one of these documents is
just failing to extract at all because the binary isn't there. The Dockerfile already knows
`pdftotext` is a runtime dependency (comment: "provides `pdftotext`, invoked as a subprocess at
RUNTIME by spatula... not a build-time dependency, so it belongs in this final [stage]") — that's
for the scraper container image, though, not this host's own `os-text-extract` toolchain
checkout, which apparently never got the same package.

## Next step

Install `poppler-utils` on this host (`apt-get install poppler-utils` or equivalent) before
trusting any `refresh-extraction`/`reextract` refusal count run from here — right now every
PDF-sourced document refuses unconditionally, which inflates the refused count independent of
whatever the real extractor-regression rate (if any) actually is. Will install and re-run UT
once WA/US come back, unless you'd rather do it a specific way (this looks like a one-line fix
but flagging before just doing it, since it changes this host's toolchain environment, not just
running a report).

WA and US dry-runs (rerun with the same fix) still in flight, background tasks on this host —
will post those next.
