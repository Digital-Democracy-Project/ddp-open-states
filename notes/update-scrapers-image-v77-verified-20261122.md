# UPDATE to `42c2df4`, `ca7d744` and `e0b93e6`: image v77 is built and checked. It holds scrapers main `d657f665` exactly (#208–#213), at core `7f531958`. 2026-11-22 (Mac side, State Specific Handling)

**Not a GO** for any run. This only reports what is in the image.

## What was checked (read only, on the Mac)
* **The image:** `ddp-scrapers:v77`, digest `sha256:688f6448c808…`, built 2026-11-22 19:33 UTC (Ramon).
* **Task definitions `ddp-scrapers:79` and `ddp-scrapers-db:6`** both name `ddp-scrapers:v77` (`aws ecs describe-task-definition`).
* **Core** inside the image is `7f5319583f9d30684ef3f042ea308554f1cc0676`, unchanged.
* **Scrapers:** the image's whole `/opt/openstates-scrapers/scrapers` tree was compared file by file with `git archive d657f665 scrapers`: **0 differences** (compiled files ignored). So it holds:
  * WY #208;
  * MI #209;
  * ID #210;
  * RI #211;
  * OK #212;
  * ND #213.
* **Not in it:** OPEN-758 (#214, not merged), as intended.
* The build's own check passed: the Utah one-bill run exited 0 (PM session).

## What this frees (each still on Ramon's go)
* **North Dakota (OPEN-757):** the fix for the HB 1015 roll-call collision is in v77, ahead of ND's weekly run (Sun 11-29 02:00 UTC). Confirm that run uses revision 79 or later.
* **Michigan full run (`eb3e203`, OPEN-648):** gate 1 is met. Gate 3 (nothing Michigan running) is checked at the time.
* **First scrapes of Wyoming, Idaho and Rhode Island:** the image they waited on is here. They are requested by Onboard New States.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
