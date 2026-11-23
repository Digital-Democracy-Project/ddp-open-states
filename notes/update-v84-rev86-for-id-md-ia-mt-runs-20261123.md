# UPDATE (not a GO): **image v84 is built**: **ddp-scrapers:86** (db 13), core **`9157b6b5`**, scrapers main **`6f9a1464`**. The four v84 runs in GO `fe2bb48` (section 3) can use it. 2026-11-23 (Mac side, Onboard New States)

**Checked:** scrapers `6f9a1464` contains each fix (GitHub compare, all "ahead"):
* `a49913ae` (Idaho substitutes, OPEN-787);
* `6d269b21` (Idaho session page, OPEN-798);
* `b2438149` (Maryland, OPEN-799);
* `0a9d57bd` (Iowa timeouts, OPEN-797);
* `2c29d8a1` (Montana versions, OPEN-801).

It also carries OPEN-802 (#251, Oklahoma name parsing, output identical to before). Core `9157b6b5` holds OPEN-801's "Bill Draft" rule.

| Run (GO `fe2bb48`) | Gate now |
|---|---|
| Idaho 2026 re-import (`7788700` / `c77027a` step 3) | rev **86** or later |
| Maryland first scrape again (ddp-sync `2672ac8`) | rev **86** or later |
| Iowa 2025 (`…/ia?sessions=2025`) | rev **86** or later |
| Montana 2027 re-import (`ce0bf8b` step 3) | rev **86** or later, **after** `ce0bf8b` step 1: api-v3 and EC2 ddp-sync at core `9157b6b5` |

**Order note:** core main has since moved to `58205e01` (OPEN-800, certificate checks). That release has its own request and is **not** a gate for these four runs. Run them on rev 86 as planned.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
