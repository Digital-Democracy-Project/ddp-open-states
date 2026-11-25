# status: OK 2025 RETRY LOADED (clean, no timeout); OK archive started by hand 04:09:26; UT archive done; HI second re-import loading; read cf05875

- **OK 2025 retry (ok-1dc8b007733e, ddp-scrapers:96 = v94, resumed after the 01:30 restart, loaded on core a7035d68):** collection done 03:50:58, "done" 03:59:48, duration **8,943.3 s**; **no ConnectTimeout this time** (the first attempt, ok-1d84ac39c6ba, timed out at 22:50). Resumed run, so no archive of its own: **I started openstates-archive/ok by hand at 04:09:26 (202).** End line to come; then the v95 OK re-import (Ramon's pop-up: "Oklahoma re-import after the retry"), one run only, 2025 and 2026.
- **UT archive (by hand 03:40:39):** task done 91.1 s at 03:42:10; knowledge-base embedding `bills=0 chunks=0 complete=True` at 03:42:25 (1,021 listed).
- **HI second re-import (hi-2f911b3924d1, rev 96 = v94):** collection done 03:48:47; it is in its load phase on core a7035d68 (no "done" line yet at 04:09). The load of the first HI run took about 29 minutes.
- PA nightly (04:00 UTC, rev 97) and IA 2025 (rev 95) collecting. The USA pipeline lock was still held at 04:09 (its follow-ups).
- Read cf05875 (OK 2025 retry load verified on the replica): thanks. The v95 ddp-sync restart (narrow rule) waits for HI's load, the OK archive and the other locks.
