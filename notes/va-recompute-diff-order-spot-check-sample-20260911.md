# va recompute-diff-order spot-check sample — for the Mac-side check

Good hypothesis on the Mac-vs-production gap — I don't have independent evidence either
way, but it fits everything I saw. Here's the same document-level sample already pulled
via `recompute_bill_diff_order()` (pure/read-only, no DB writes), same shape as mi/fl's
earlier spot-checks — I had already generated it while investigating why va's correction
rate looked high, before your note asked for it.

Note: this sample was pulled from the **first 512 va bills scanned** (in whatever order
the ORM iterator returns them), not a random/representative sample across all 4380 -- worth
keeping in mind if you want a broader cross-section later.

## The nulled example ("House Amendment")

- `bill_id=ocd-bill/7fe78fa3-0465-4ad2-ad97-734171b7ef44` (`SJ 60`, session `2026`)
- `doc_id=23753`, `version_note='House Amendment'`, `media_type=text/html`
- currently stored `diff_from_previous_version` is 8,568 chars; recompute says this should
  become `None`

(A second nulled example turned up in the same bill, for completeness:
`doc_id=23756`, `version_note='Privileges and Elections Amendment'`, `media_type=text/html`,
currently 152 chars, also proposed `None`.)

## 5 corrected doc samples

| bill | doc_id | version_note | media_type | old diff len | new diff len |
|---|---|---|---|---|---|
| HR 2002 (2026S1) | 70534 | Enrolled | application/pdf | 6871 | 6468 |
| HR 2002 (2026S1) | 70535 | Enrolled | text/html | 9249 | 897 |
| HR 2041 (2026S1) | 70578 | Enrolled | application/pdf | 3731 | 3329 |
| HR 2041 (2026S1) | 70579 | Enrolled | text/html | 4204 | 754 |
| HB 1027 (2027) | 200314 | Courts of Justice Substitute | text/html | 2466 | 2944 |

Full bill UUIDs, in the same order:
- `ocd-bill/50abaa9e-7ce9-483d-ae2e-76c7fd6fd0ca` (HR 2002, doc 70534 & 70535)
- `ocd-bill/d5e71e61-b299-4d11-a1c5-85e19308e006` (HR 2041, doc 70578 & 70579)
- `ocd-bill/eb78eece-3aae-4507-ab7a-c4c07537a06a` (HB 1027, doc 200314)

Once these check out against the Mac's copy, standing by for the go-ahead on `va`'s commit.
