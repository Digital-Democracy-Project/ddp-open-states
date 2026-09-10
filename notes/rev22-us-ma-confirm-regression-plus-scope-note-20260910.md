# us/ma confirm the same regression, plus one useful data point for OPEN-266

*Addendum to `notes/rev22-regression-app-permission-back-20260910.md`.* `us` and `ma` finished:

```
us: fetched=574 archived=0 persist_errors=574 duration_s=1220
ma: fetched=149 archived=0 persist_errors=149 duration_s=283
```

Same regression, identical shape (`persist_errors` == `fetched` exactly) -- confirmed across all
four jurisdictions now, not just `az`/`mi`.

## Useful for OPEN-266's disposition: the skip-check fix retries the full excess set too

`ma`'s `fetched=149` is exactly the **total** `is_error=False`/null-`archive_location` count I
found for MA in `notes/open266-data-pulled-20260910.md` (74 from the incident + 100 excess = ...
well, 149 specifically was the pre-exclusion total, so this run's skip-check fix is treating
*every* `is_error=False` null row as retry-eligible, not just the ~74 from this specific
incident). Similarly `us` went from 506 (rev21) to 574 here -- also picking up more than just
the original incident set. **Practically: once persistence is actually fixed, a normal archive
run for these four jurisdictions should recover MA's full 149 (both the incident set and the
"Bill Text" excess from OPEN-266) in one pass, not just the incident subset** -- worth knowing
before deciding whether OPEN-266 needs a separate action at all, or whether it's already going
to get swept up for free once OPEN-263 lands cleanly.
