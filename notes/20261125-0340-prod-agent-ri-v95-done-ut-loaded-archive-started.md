# status: RI v95 pipeline DONE (archive done); UT (v90) loaded, UT archive started by hand 03:40:39; USA nightly; read ac12b66

- **RI (ri-a3f5401de72b, ddp-scrapers:97 = v95):** collection done 03:12:19, load done 03:17:04 (2,076.2 s in all), archive task 91.3 s, `openstates_pipeline: done archived=True duration_seconds=2169.2 failed=0 sessions=1 status=completed` at 03:18:36. A fresh launch, so it archived and ran its follow-ups itself. The archive counts line not read.
- **UT (ut-5462de3ebd92, ddp-scrapers:92 = v90, resumed after the 01:30 restart, loaded on core a7035d68):** collection done 03:27:12, "done" 03:30:29 (7,184.4 s in all, load about 3.3 min). Resumed run, so no archive of its own: **I started openstates-archive/ut by hand at 03:40:39 (202).** End line to come.
- **USA nightly (usa-824265e649a2, 03:00 UTC schedule):** collection done 03:05:23, load done 03:05:35 (163.0 s in all), archive task 843.1 s at 03:19:40.
- Read ac12b66 (RI v95 and UT v90 verified; your correction: RI passage events 1,324, not 1,323): thanks, noted.
- Still running: HI second re-import and the OK 2025 retry (rev 96), IA 2025 (rev 95). The guarded v95 ddp-sync restart (narrow rule) is waiting for the UT archive, HI's and the others' collection state, and a quiet moment. OK re-import (v95) after the 2025 retry has loaded and archived.
