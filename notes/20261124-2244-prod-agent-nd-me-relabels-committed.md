# status: ND relabel (520) and ME relabel (5,177) COMMITTED, core 70146fac (22:43 UTC)

Ramon's go in my session (pop-up ~22:42 UTC: "North Dakota relabel (520), Maine relabel (5,177)"). Notes re-fetched first (nothing new beyond what I had read).
I paused my pending ddp-sync restart job while these ran so a restart could not land mid-commit; it is re-staged.

- **ND:** dry run again: actions changed=520, list md5 5d70a71755530078607fa0a0d8f9dae3 (same as before). `relabel nd --commit --expect 520 --list ...`: `nd: [COMMITTED] actions changed=520 unchanged=14975 | bills changed=0 unchanged=0`; `reading-2 -> reading-2, failure: 438`; `reading-2 -> reading-2, passage: 82`; computed fields latest_passage_date=43, the others 0; exit 0. List ops/nd-relabel-commit-core70146fac-20261124.csv (520 rows, same md5, the --undo path). Second dry run: actions changed=0 unchanged=15495.
- **ME:** dry run again: actions changed=5177, list md5 011ba6f8556adb5d0f4fc29da67cfd03 (same). `relabel me --commit --expect 5177 --list ...`: `me: [COMMITTED] actions changed=5177 unchanged=39649 | bills changed=0 unchanged=0`; `passage -> (none): 2307`; `reading-3 -> reading-3, passage: 1561`; `reading-2, reading-3 -> reading-2, reading-3, passage: 1246`; `(none) -> passage: 63`; latest_passage_date=1083, the others 0; exit 0. List ops/me-relabel-commit-core70146fac-20261124.csv (5,177 rows, same md5). Second dry run: actions changed=0 unchanged=44826.
- ME recompute: not committed (nothing to commit). No other writes.
- Other: OK 2026 (ok-3f164c3f15c1) loaded, done 22:35:16 (8,359.6 s); resumed run, so I started its archive by hand at 22:41:54, still running. OK 2025+2026 on v90 starts after it. NE and UT (v90) and IA still collecting.
