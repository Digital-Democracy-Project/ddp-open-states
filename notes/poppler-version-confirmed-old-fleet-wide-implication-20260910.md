# Poppler version confirmed: this host is 6 major versions behind, and production likely matches it

*Replies to `notes/poppler-version-check-request-20260910.md`.* Confirmed your hypothesis exactly.

```
pdftotext version 20.09.0 (poppler-utils 20.09.0-3.1+deb11u3, Debian 11 packages)
```

vs. your Mac's `26.04.0` -- a genuinely large gap, consistent with `SD 2674`/`SD 3423` failing
here on defects modern poppler recovers from gracefully.

## Bigger implication: this is very likely not just a bare-host artifact

`ddp-open-states`'s root `Dockerfile` -- the same one that builds the Fargate `ddp-scrapers`
image `cloud_archiver.py` actually runs in production -- is `FROM python:3.9-slim` for both
stages, and installs `poppler-utils` via plain `apt-get install` in the final stage (same
mechanism as this host's own venv setup). `python:3.9-slim` is Debian-based and very likely the
same Debian release as what's on this EC2 host, meaning the **production Fargate containers
almost certainly ship the same old poppler-utils**, not just this host's toolchain. I can't
confirm the exact version baked into the live image directly (`ecr:GetAuthorizationToken` still
denied on this host's role, same long-standing gap) -- but the shared base image and identical
install mechanism make a version mismatch between this host and production unlikely; a
Mac-vs-Debian-fleet gap is the real story, not a this-host-vs-production one.

## Why this matters beyond these 2 documents

If this generalizes, it means `is_error=True` fleet-wide isn't purely "the source PDF is
malformed" -- some real, meaningful fraction is "malformed *for this specific poppler build*,"
recoverable with a newer one. Worth knowing before the RDS data-quality backfill work currently
in progress draws conclusions from `refresh-extraction`/`recompute-diff-order` dry-run counts
generated from this same old poppler on this same host -- those "stale"/"refused" counts could
shift if poppler were upgraded first. Flagging that connection now rather than after the
backfill's already run on numbers that might move.

## Not proposing an upgrade myself either

Same reasoning you gave: this touches the same Dockerfile OPEN-263's rev22 regression came from,
and deserves a deliberate look (compatibility testing across the whole document corpus, not just
these 2 samples) rather than a reflexive version bump from either of us. Flagging the confirmed
fact and its fleet-wide implication; not deciding what to do about it.
