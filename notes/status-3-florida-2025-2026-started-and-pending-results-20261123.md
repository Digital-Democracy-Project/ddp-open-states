# STATUS 3 (2026-11-23 16:25 UTC): Florida 2025 and 2026 re-import running; results still owed

No new dev request is unanswered; everything I have read has either a reply or a status from me (`b3717e7c`/`0e5f5731` status 2, replies `0e6e84c9` WY, `eae721f0` MI, `283c7426` Georgia, `49c41b8e` OPEN-634, `6e0c1577` NE/LA part A).

- **Florida (OPEN-642), the part your cause note `c506b00a` asked to re-run:** the resumed 2024 run `fl-adde183a9a34` loaded at 14:41:43 UTC (25,361 s). I started **2025 and 2026** at 14:42:47 UTC: `POST openstates-scrape/fl?full=true&sessions=2025,2026` returned **202 with `"full": true`**, run **fl-d54af3a05c37**, task revision **83** (the 2025 session task started 14:43; flhouse.gov answered 200 first; Ramon's overnight pre-approval). Still collecting at 16:05 UTC (saving 2025 votes). Not retried; if a session fails I report the error and minute. Florida's archive will be triggered by hand after both sessions load, since the resumed run would not do it.
- **Utah 2026 `ut-1777beb302dc` and Arizona 57th-2nd-regular `az-183293f2bebd`** (started 14:16:49 and 14:16:51 UTC, rev 83): both still collecting at 16:05; their reports and your SQL come when they load.
- **Idaho** `c77027a` (also OPEN-787 House substitutes: people `d1acd229`, expect created 17 / updated 5, image v82 at scrapers `a49913ae` or later): read, not started; needs Ramon's go and v82. **NE/LA part B, NM 2026 and the Nebraska/Louisiana links** wait for v82 (rev R above 83), per `06a707d`.
- **Michigan's LegBot hand-off** (accepted 14:56:42, `legbot-session-65be83984745`) still holds Michigan's pipeline lock on this side; I cannot see the Mac.

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
