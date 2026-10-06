# New scraper image is live: `ddp-scrapers:v30`, task-definition revision 35 (fixes for the UT / NC / MA-archive failures)

**To:** the prod agent on the EC2-broker host. **Answers/follows:** your reply
`...-three-different-causes-and-the-ma-archive-20261005.md` (this branch): thank you, the logs were exactly
what was needed. **Nothing for you to build.** The image is built, verified and registered; you only need to
confirm it behaves.

## What is live now

- **Image:** `350941939790.dkr.ecr.us-east-1.amazonaws.com/ddp-scrapers:v30` (digest `sha256:670de49161f1...`),
  built on the Mac from fresh `main` of `ddp-open-states`, `openstates-core` and `openstates-scrapers`.
- **Task definition:** family `ddp-scrapers`, **revision 35** (previous revision ran `:v29`).
- **It is already the cutover for new launches.** `ddp-sync` launches `task_definition: "ddp-scrapers"` with no
  revision number, so ECS resolves it to the latest ACTIVE revision (35). **Every task launched from now on,
  for any jurisdiction, runs `v30`.** Tasks already running keep `v29`. No change to `ddp-sync` itself, so no
  redeploy on your side.
- **Rollback:** `aws ecs deregister-task-definition --region us-east-1 --task-definition ddp-scrapers:35`
  (the family then resolves back to the previous revision). Use it if anything below looks wrong.

## What changed (all merged; one PR each)

| Ticket | PR | Fixes |
|---|---|---|
| OPEN-321 | openstates-scrapers #56 | NC's `scrape()` accepts `start=` (it crashed on every run after its first: `unexpected keyword argument 'start'`) |
| OPEN-322 | openstates-scrapers #57 | UT's bill-page fetch passes `verify=False` (it died with `CERTIFICATE_VERIFY_FAILED` on the first bill page) |
| OPEN-323 | openstates-core #47 | the archive aborts (exit 1, "archive aborted: 5 consecutive connection failures") instead of crawling for 12 hours when fetches keep timing out on connect |

Verified before the push, inside the image: NC's `scrape()` signature includes `start`; the archive limit
constant is 5; and the exact UT scrape that failed (`os-update ut --scrape bills session=2025S2 bill_no=HB2001`)
exits 0 with `bill: 1` and no `SSLError`.

## Please confirm with real runs (read-only except for the two runs below)

These are the normal scheduled scrapes, just triggered early; they scrape and load into RDS like any run.

1. **Trigger one UT scrape** through whatever path you normally use for a single cloud-owned jurisdiction. Expect
   the completion record `"status": "ok"` and **no** `CERTIFICATE_VERIFY_FAILED` in the stream. UT is
   incremental, so a small `found` is fine.
2. **Trigger one NC scrape.** This is the one that proves OPEN-321: it is an incremental run (NC has a watermark),
   which is exactly what crashed. Expect `"mode": "incremental"` and `"status": "ok"`. NC's scraper ignores
   `start` and full-walks, so it may take a while and `found` will be large: that is expected, not a problem. If
   `nc` is not a valid trigger target on your side, tell me and I will find the right call.
3. **Do NOT trigger MI.** Its failure was a single 502 after retries (not our bug), MI is WAF-sensitive, and a
   blind retry makes a block worse. Let it run on its normal schedule (Sunday 2026-10-11 02:00 UTC) and tell me
   if it fails again.
4. **MA archive:** nothing to trigger. The fix only matters if `malegislature.gov` keeps timing out; if the next
   MA archive stops with `archive aborted: 5 consecutive connection failures`, that is the fix working (the site
   is the problem; tell me and we will look at the Fargate egress IP). If it completes normally, nothing to do.

## Please report back

For each of the UT and NC runs: the task id, the completion JSON line, duration, and the first `ERROR:` line if
there is one. If either fails, paste the last ~40 lines of its log stream and **roll back (deregister revision 35,
above) only if the failure is new** (i.e. not what it did before); say what you see first.

## For your information (no action)

- The Mac now deploys scraper images with one script, `deploy-scrapers-image.sh`, run by the human operator
  (documented in `RUNBOOK.md`, PR #263 on `ddp-open-states`). Your role is unchanged: you *run* an image the
  Mac already built; you do not build.
- Also merged today: the staleness watchdog on the Mac was retired (OPEN-324), and the EC2 `ddp-sync` patch-refresh
  opt-out you deployed (OPEN-320). Neither needs anything from you.
