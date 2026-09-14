# MI Tier 1: the specific 47 missing bills (OPEN-191's own tally regenerated with identifiers, not just a count)

OPEN-191's own log (`logs/quality-check/mi_2025-2026.log`, 2026-09-13) only ever recorded the
count -- 47 real bills missing locally -- never the actual identifiers, since
`run_coverage_check()`'s own result dict was never printed anywhere. Regenerated the real list
just now using OPEN-289's new govbot-backed check (fast, no live-API rate limit) against MI's
current govbot-data clone, cross-checked against the local DB directly.

**One real gotcha found and corrected before trusting this**: govbot's MI data zero-pads
resolution-type identifiers ("HR 0001", "SCR 0001") while DDP's local DB doesn't ("HR 1",
"SCR 1") -- HB/SB numbered bills aren't affected, confirmed directly (`HB 4001` matches on both
sides exactly). Un-normalized, this inflates the apparent gap to 1555 "missing" bills, almost
all of them a false positive from the padding mismatch alone. After normalizing both sides'
identifiers the same way (strip leading zeros from the trailing number), the real gap comes
back to **exactly 47** -- matching OPEN-191's own figure precisely, which is what gives me
confidence this list is the real one, not an artifact of my own tool.

**The 47, with each one's real latest_action** (from govbot's own data, so this is "what MI's
site itself last recorded," not a guess):

- **4 House bills, all filed 2026-09-01**: HB 6323, HB 6324, HB 6325, HB 6326 -- all still at
  `"bill electronically reproduced 09/01/2026"`, the very first real action a MI bill gets.
- **38 Senate bills, SB 1142 through SB 1179** (contiguous) -- every one still at just
  `"INTRODUCED BY SENATOR <name>"`, no further action.
- **5 Senate resolutions, SR 136 through SR 140** -- same, still at introduction only.

**The pattern across all 47**: every single one is at the *first* recorded action of its kind
(bare introduction, or the House's "electronically reproduced" pre-introduction step) --
nothing here has had a committee referral, a reading, a vote, anything. They're also the
*highest-numbered* bills/resolutions in each category (SB tops out locally around 1141, these
start at 1142; same shape for HB and SR) -- i.e., these are specifically the most recently
filed bills in the session, not a scattered gap across the whole session. That's consistent
with a scrape-recency lag (the local scraper hasn't caught up to the newest filings yet) rather
than a systematic defect silently dropping older bills -- but that's my read from the pattern,
not something I can confirm without knowing exactly when MI's scraper last ran vs. when each of
these was filed.

Full annotated list (identifier, title, latest_action) available on request if useful for a
closer look -- kept this note to the summary + pattern since that's most of the diagnostic
value.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
