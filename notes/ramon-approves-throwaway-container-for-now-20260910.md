# Go-ahead: proceed with the throwaway local container for the remaining backfill steps

Ramon's answer: **proceed using the throwaway local Docker build** (built from `main` on this
EC2 host, same approach as the go/no-go check) for the rest of the RDS backfill
(`fl -> va -> wa -> us`), rather than waiting on the ECR pull-access grant first.

## Why we're confident the dependencies are right

Your throwaway build and the real pushed `ddp-scrapers:v20` image are built from the exact same
commit (`main` @ `9b1651e`) using the same `Dockerfile` and the same pinned
`requirements-openstates.txt` (exact-version pins, not ranges) -- they should be dependency-
identical modulo Debian's own security-patch-level apt drift (e.g. a `-deb12u4` point release
landing between builds), which wouldn't touch poppler's actual fix. You already reported your
throwaway build showed Python 3.10.21 / poppler-utils 22.12.0, which is an exact match for what
was verified inside the real pushed `v20` image before it was registered as task-def revision
24. Good enough to trust for this work.

## Still true, not superseded by this

- The ECR pull-access request stands as the real long-term fix (a fresh throwaway build every
  time isn't a great permanent habit, and it doesn't need to block progress today).
- Please still re-specify the go/no-go check against the actual mechanism the hold was about --
  `refresh-extraction`/`recompute-diff-order` content-sensitivity, not `reextract`'s disjoint
  `is_error=True` population -- before resuming `fl`. Re-run something like
  `refresh-extraction ut --dry-run` inside the throwaway container and compare against the
  original 4671/4110 discrepancy, or re-locate `id=56173` and confirm which command now flags it
  fixed.
- The 676-row MA `is_error=True` population is root-caused (wrong-extractor-for-document-type,
  not a poppler issue) but still not dispositioned/ticketed -- separate follow-up, not blocking.
