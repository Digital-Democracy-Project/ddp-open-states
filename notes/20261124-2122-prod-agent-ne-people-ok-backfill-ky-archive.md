# status: NE people LOADED (OPEN-877 fix); OK roll-call backfill APPLIED (8,767); KY archive started by hand; read 943b1bb, ebd7c94, e6a8927

Ramon's go in my session (pop-up ~21:15 UTC): Nebraska people load, OK backfill preview and apply.

## Nebraska people (step 2 of 85ce7f0)
- people checkout fast-forwarded 37bcb364 -> 26f4ad0dad89f314b0a02fa54b97a1df71e09308. Safe run: "updated person from .../ne/legislature/Fred-Meyer-5868ed3b-....yml", `processed 165 person files, 0 created, 1 updated`, no "went missing" or retirement line, no error. Real run: same lines, exit 0. (Maine's Theriault load was done earlier at 20:00 UTC: 623 files, 0 created, 1 updated.)

## OK roll-call numbers (step 4 of 85ce7f0)
- /opt/ddp-open-states fast-forwarded b7dbefb1 -> 3d1801a4 (git merge-base: in main). Dry run (run from the ddp-sync container's openstates env, since the old host venv is deleted): 8,767 vote events (house 5,125, senate 3,642), list md5 **ce1039b50c43c9a00d3259731c690551 = yours**, already numbered 0.
- `--apply-list ... --expect 8767 --list ...committed`: "Done. Updated 8,767 records." Second dry run: already numbered 8,767, would update 0. Lists for --undo: ops/rollcall-ok-dry-20261124.csv (md5 above) and ops/rollcall-ok-committed-20261124.csv.
- OK 2026 (ok-3f164c3f15c1) was still collecting; its load will write the same numbers.

## KY archive
- KY loaded 20:34 UTC (ky-89d23d661f7a, 1,094 s, core 70146fac). A resumed run starts no archive, so I started openstates-archive/ky by hand at 21:00:59 (202), as for PA and FL. End line to come.

## Read, no action needed from your side
- 943b1bb (ND/RI verified; the 3 not-adopted engrossments are the ND recompute flag changes; commit waits on Ramon's second go; not run), ebd7c94 (v90 = ddp-scrapers:92 / db:19, core 70146fac; RI re-import on hold for the header-shape follow-up), e6a8927 (inventory; the correction that a running archive matters for a restart: noted. My restart at 20:15:40 had 0 ddp-scrapers-db tasks up, checked twice).
- **Re-imports (WY, NE, UT; OK after its current run):** I take Ramon's remark "v90 is now built and registered" as information, not as a go, and ask him in a pop-up.
