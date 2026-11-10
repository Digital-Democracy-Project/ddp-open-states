# Verified (Mac side): `relabel-non-bills ma` commit on RDS (OPEN-517). 2026-11-10, about 06:15 UTC

Answers `f45169e`. **Verified. Nothing more is asked of you for OPEN-517.**

**Checked on the Mac replica (`openstates_rds_repl_20260911`), read-only:**
* **Massachusetts labels:**

  | Label | Count |
  |---|---|
  | `{bill}` | 8,440 |
  | `{report}` | 1,538 |
  | `{communication}` | 998 |
  | `{proposed bill}` | 339 |
  | `{study request}` | 332 |
  | `{order}` | 264 |

  These are exactly your after-counts. The saved-label key is on 3,132 rows.
* **The 8 voted papers** (S 14, S 15, S 18, S 19, H 2024, H 2025, H 2026, S 3083) still read `{bill}`.
* **Real measures are untouched:** of the 8,613 Massachusetts items whose title opens like a measure (An Act, Resolve, Resolutions, Joint Resolution, Proposal), **0** carry anything but `bill` or `proposed bill`.
* **The Mac api-v3 (port 8002) serves the new labels:** `GET /bills?jurisdiction=ma&classification=` totals are report 1,538, communication 998, study request 332, order 264, bill 8,440 and proposed bill 339.

**Next, Ramon's step (not yours):** he builds and registers scrapers image v53 (OPEN-518) before Sunday 11-15 02:00 UTC. Nothing in this note authorizes anything.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
