# Request (read-only): please also commit each state's `sample.tar.gz` (and Delaware's output when it ends), 2026-10-31 about 19:15 UTC

Thank you for the all-states read (`612c647`, `02b49a1`). Ramon read the colours and asked me to run the **Mac half** (`verify-jurisdiction <st> --from-dir <folder> --import`, dev database only) on every state that reported. That half needs each state's **`sample.tar.gz`**, and it refuses a folder whose files are not exactly the ones `result.json` lists, so I cannot use the `result.json` and `report.md` alone. I told you to skip the samples earlier; the prefix is only about 0.9 MB in all (155 objects), so committing them is small. **Nothing here changes anything: do not stop, restart, re-run or launch anything.** No secrets are in the samples (you scanned the reports; please run the same scan on the tarballs' file names and a sample of their contents).

## What I need
1. **`sample.tar.gz` for each of the 52 states already committed**, unchanged, to this branch next to the existing files: `notes/probe-all-20261031/<st>/sample.tar.gz`. (ak al ar az co ct dc fl ga gu hi ia id il in ks ky la ma md me mn mo mp ms mt nc nd ne nh nj nm nv ny oh ok or pa pr ri sc sd tn tx us ut va vi wa wi wv wy). For the 14 RED states the tarball may be small or empty of bills; commit whatever is there.
2. **Delaware (`de`)**, when its task ends: `result.json`, `report.md` and `sample.tar.gz` under `notes/probe-all-20261031/de/`, plus a one-line note of how it ended (it had run more than 30 minutes at 19:04 UTC). If it is still running at your next read, say so and the current last log line.
3. If a state's `result.json` and `sample.tar.gz` do not match each other (a hash mismatch), tell me which; I will see it myself because the tool refuses it.

## What I will do with them
Run the Mac half for every state that reported (dev database only; people loaded first with `os-people` where the dev people checkout has the state), then bring Ramon the full colour list for the pilot #2 choice. California and Vermont crashed before writing a report and are tracked in new tickets (OPEN-471 and OPEN-470); there is nothing to read for them.

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
