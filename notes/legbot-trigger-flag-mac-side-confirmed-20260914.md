# Mac side confirmed already live -- both sides now flipped

Checked directly: the Mac's `.env` has had `LEGBOT_SCRAPE_COMPLETION_TRIGGER_ENABLED=true`
set since yesterday (file mtime 2026-09-13 16:58:43), well before today's OPEN-290 pull +
restart (11:54:59 EDT). Env vars load once at process startup via `_load_from_env()`'s
`load_dotenv()`, and today's restart happened after that edit -- so the currently-running
process already has it loaded. No action needed here; it was already done.

(One cosmetic loose end: there's a stale comment nearby in the `.env` still saying
"LEGBOT_SCRAPE_COMPLETION_TRIGGER_ENABLED left false above pending Ramon's own..." that no
longer matches the real value -- harmless, just worth a cleanup pass sometime.)

Both hosts are genuinely flipped on now. Go ahead and watch for AZ's real scheduled archive
run tomorrow (Tue 2026-09-15, 05:00 UTC) as the first fully unattended end-to-end test.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
