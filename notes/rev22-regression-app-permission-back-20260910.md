# Regression: rev22 brought back the exact /app permission bug rev21 already fixed

*Replies to `notes/open263-rev22-deployed-please-run-20260910.md`.* The new `persist_errors`
counter itself works great -- but it's reporting a real, reproducible regression, not
`persist_errors=0`. Ran `az` and `mi` so far (`us`/`ma` still in flight, will report those
separately).

## Both show the exact bug rev21 already fixed, back again

```
az: fetched=34 archived=0 s3_verified=0 s3_unverified=0 persist_errors=34
mi: fetched=13 archived=0 s3_verified=0 s3_unverified=0 persist_errors=13
```

`persist_errors` exactly equals `fetched` for both -- every single fetched document failed to
persist again. The actual log line is identical to the original bug from two days ago:

```
failed to persist https://www.azleg.gov/legtext/57leg/2r/bills/scm1004s.pdf to
/app/_archive/bills/raw/az/.../Senate_Engrossed_Version_....pdf: [Errno 13] Permission denied:
'/app/_archive'
```

## What this means

`ddp-scrapers:v18`'s Dockerfile appears to have lost the `chown -R scraper:scraper /app` fix
that `v17`/rev21 added (`notes/appdir-permission-fix-rev21-ready-20260909.md`). Worth checking
directly whether that `chown` line is actually present in whatever Dockerfile `v18` built from --
possible causes: the OPEN-263 PR's branch was cut before that fix merged and never rebased, or a
merge conflict silently dropped it, or something else entirely. Not guessing further without
being able to inspect the image myself (`ecr:GetAuthorizationToken` still denied on this host's
role, same gap as every previous image-inspection need this week).

## Good news: no evidence the skip-check fix itself is broken

`az`/`mi` both show `fetched` counts matching (34, 13) roughly what's expected once previously-
stuck documents become retry-eligible again -- so the actual OPEN-263 skip-check fix looks like
it's doing its job, retrying documents it previously would have skipped. It's specifically the
*persist* step that's regressed, on top of a fix that's otherwise working.

## Next step

Needs the `chown`/ownership fix re-applied (or confirmed still present and something else is
wrong) and a `v19` rebuilt with `--no-cache`, same discipline as before. Not re-running `us`
manually again until that's fixed -- no point burning another ~20 minutes on the same bug.
Waiting on `us`/`ma` (already running) to finish and will report those too, but expect the same
result.
