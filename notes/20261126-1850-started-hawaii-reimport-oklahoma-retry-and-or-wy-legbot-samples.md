# Started 11-26 18:50 UTC: Hawaii third re-import, one Oklahoma 2026 retry, and the Oregon and Wyoming LegBot samples

Ramon's go in this session, by name: Hawaii, Oklahoma, Oregon, Wyoming (he chose the three actions in a pop-up). For Oregon and Wyoming he gave the scope: **a random sample of 100 bills each**.

## Hawaii `hi?full=true&sessions=2026` (OPEN-900) - triggered 18:44:20 UTC, 202, `full: true`
* Gate: `ddp:pipeline_lock:hi` was empty. Image: new tasks launch v98 (`ddp-scrapers:100`); that image was built from scrapers `main`, which contains #297 (merge `d0bd1826`, in the v97 pin too). I could not read `DDP_SCRAPERS_COMMIT` in the image (the image records none and this role cannot read it), so that is from history, not read from the image.
* Next: when it finishes I start Hawaii's archive by hand, then report: the 6 changed labels, vote events 12,828, bills 6,728 (I will read production's counts before and after).

## Oklahoma `ok?full=true&sessions=2026` - ONE attempt, triggered 18:44:22 UTC, 202
* No third try after this and no workaround (no user agent, address or pace change). The v97 and v98 images log the egress address and connect timing (OPEN-892), so the result should name them either way.

## Oregon and Wyoming LegBot samples (OPEN-897 wave 1)
* **Sample:** 100 random bills each, drawn from production (Oregon `2026R1`, Wyoming `2026`), saved as a list of bill ids and numbers. The same flow as the automated trigger: the nine standard artifact types, concept statements as the automated flow has it (on), **org research off**, **no policy-statement step** (`include_policy_statement` not sent; the flag is still absent on this host), `retry_failed` false, not a dry run.
* **Route:** the Mac's ddp-sync (`/ddp-sync/v1/trigger/bill-artifact-generation`, background mode, `X-DDP-Environment: prod`), the same hop the archive hook uses; the Mac's MLX was free (Ramon said so; `cams status` and `ddp-sync status` were clean earlier).
* **Oregon: accepted 18:45:45 UTC, run `legbot-session-bccd617bfe5d`, running.** Wyoming starts after Oregon finishes (one at a time; MLX serializes anyway).
* I will report each run's counts: bills considered and processed, artifacts generated and failed, and the failure types, so you can compare against your dev samples. I do not judge summary quality; that is yours.

## Not changed
No ddp-sync restart (it waits for Iowa, Hawaii and Oklahoma to release their locks); no switch; no other state.
