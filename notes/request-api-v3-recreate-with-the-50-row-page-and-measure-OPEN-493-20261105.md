# Request: recreate api-v3 from `main` once api-v3 PR #51 (OPEN-493, a page of 50 bills) is merged, and measure one call of 50 against three of 20 (OPEN-493, BROKER-431), 2026-11-05

**Do not start until Ramon has merged api-v3 PR #51** (`Digital-Democracy-Project/api-v3`, "the bill list allows 50 a page without include= (20 with it)"); his go in your session after that is the go. Thank you for the page-size count (`ca40971`): in about 196,000 retained requests nothing asks `/bills` for more than 20, so no caller relies on the refusal (with the two-day hole around 10-31 you named). That settles acceptance line 2.

## What changes in production
Only api-v3's answer to `GET /bills?per_page=N` for N from 21 to 50, **when there is no `include=`**: it answers 200 instead of a 400. With `include=` the limit stays 20, and every other list keeps its own limit. **No schema change, no `ensure`, no refresh, no setting, no `.env` change.** It is live as soon as the api container runs the new image. Nothing asks for more than 20 yet: the broker changes after this is live and measured (BROKER-431, a `/broker-deploy`, Ramon's step), and **must not ask for 50 before then (it would get a 400)**.

## Gates and limits
No ECS task, no scrape or import writing bills, a quiet moment, no ddp-sync job in the last 10 minutes (as for `9a4db24`). A recreate makes api-v3 unavailable for a few seconds. Stop and report on any failed gate, health check or unexpected output; no rollback beyond the image re-tag below without telling me. **Not asked:** a broker release, any restart of anything else, a plain `ensure`, a `refresh`.

## Steps (the script is `notes/api-v3-speed-20261104/page50_vs_three20.py`: read it first; GET only, key from the environment, never printed)
1. **BEFORE.** From the broker web container, as in `9a4db24`: `V3_BASE=<api-v3 address> V3_KEY=<the broker's own key> python3 -I page50_vs_three20.py "BEFORE" 15`. Expected: three calls of 20 at once (the number we want to beat; production showed about 247 ms for the slowest in `a4b65f52`), and `per_page=50` answers **HTTP 400** (reported, not an error). Save the running image id and the api log first.
2. **Recreate from `main`** (the merge commit of #51 or later; `python -c "import api.bills as b; print(b.BillPagination.max_per_page_without_includes)"` inside the new container must print **50**), `api` only, `--no-deps`, as for `9a4db24` / `a5e35ac`; wait for healthy. Checks as in `9a4db24` step 3 (image id changed, `/healthz` 200, no key 403, `/ddp/enrollment` 13 jurisdictions, no traceback since the restart).
3. **AFTER:** `python3 -I page50_vs_three20.py "AFTER" 15`. It prints the three-calls-of-20 median again, the **one-call-of-50 median**, the fingerprint of the first 50 ids from each way (**must match**), `total_items`, `max_page`, and that `per_page=51` and `per_page=50` with `include=` are 400 (the limits). Also the broker's list rows (`bills list p1`, `bills list US`, as before) for the record; they will not change yet, because the broker still asks for 20.
4. **Reply** `reply-api-v3-recreate-with-the-50-row-page-and-measure-OPEN-493-20261105.md`: BEFORE and AFTER side by side, image ids, times (UTC), what you did not run. Rollback if needed: re-tag the saved image and recreate `api` the same way (nothing else depends on the change).

**What the numbers decide:** OPEN-493's acceptance line 3 (one 50-row page costs about one call), and whether the broker half of BROKER-431 (ask for 50) is worth releasing.
**Expectation, not a measurement:** on the Mac copy one call of 50 was 62 ms against 105 ms for three of 20 in a 15-run test, and 50 ms against 50 ms in a quieter 5-run repeat, so the Mac does not reproduce the production slowdown reliably; production's own before and after is the proof.

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
