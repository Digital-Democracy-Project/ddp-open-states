# UPDATE to `a9fbb18` (the next scrapers image after v78): it now also carries OPEN-771 (Rhode Island repeated bills). **Deadline: in a registered image before Sun 11-29 02:00 UTC.** Scrapers main is `3be4dfce`; core main is still `3ac06b6a`. 2026-11-22 (Mac side, State Specific Handling)

**Not a GO.** Everything in `9e2caaa` and `a9fbb18` stands.

## Added since `a9fbb18` (scrapers main now `3be4dfce0380fd90751091044c9550da478e1573`)
| Merge | What |
|---|---|
| #224 (OPEN-771, `3be4dfce`; Onboard New States) | Rhode Island's bill-number search ranges no longer overlap, so a bill on a range boundary is not collected twice |

* **Deadline:** Ramon: "Stay on, fix by Saturday". Rhode Island stays switched on, so this must be in an image registered before RI's run on **Sun 11-29 02:00 UTC**. Without it, that run repeats the bill again.
* No migration and no new setting. The core change and release order in `a9fbb18` are unchanged.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
