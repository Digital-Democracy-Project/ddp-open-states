# UPDATE (not a GO) to `7788700` (Idaho acting senators): step 2 is **a new image, v82**, built from scrapers main at **`02ba6f4e` or later**. v81 doesn't carry the fix. 2026-11-23 (Mac side, Onboard New States)

**What changed:**
* v81 is already built and pushed (about 05:4x UTC, task revision **83**) from scrapers main **`d8e1bf5d`**. Per the PM session's check inside the image, it **doesn't** contain Idaho's #234 (`02ba6f4e`, OPEN-781) or North Carolina's #233 (`29be4a1b`, OPEN-783).
* So in `7788700` step 2, ignore "if v81 is built from main now". **Step 2 is v82, built from scrapers main at `02ba6f4e` or later.** It carries #233 and #234; core is unchanged at `42b48982`.
* The Mac side checks that v82's scrapers tree contains `02ba6f4e`. Prod side: please report v82's task-definition revision; step 3's gate 2 is that revision or later.

**Unchanged:**
* Step 1, the people refresh for `id` (people `febf9fc1`, expect created 7 / updated 4). It is still best done before v82 is live.
* Step 3, the Idaho 2026 re-import and its pass/fail SQL.
* "Not authorized".

**Note for Wyoming's request (`795a93b`):** it asked for v81 at `d8e1bf5d` or later, and v81 at `d8e1bf5d` (rev 83) carries all three Wyoming fixes. So Wyoming's re-import gate 1 is **rev 83 or later**.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
