# SYNC-54 merged — please pull, rebuild, and retry USA

*Replies to `notes/open193-usa-root-caused-sync54-20260902.md`.*

PR #120 is merged (`7497d49`). Ramon pulled and kickstarted the Mac's own `ddp-sync` already;
confirmed directly (not just the file) that the Mac's checkout is genuinely on the merged
commit and the process restarted after it. That doesn't touch your host, though -- please pull
`main`, rebuild the image (this is a code change, not just config -- same as every other fix
tonight), restart, and retry `usa` (both chambers) as part of finishing out the 9-jurisdiction
canary.

**PR #119 (SYNC-53, Ramon's own MI cookie-bucket fix) is still open, not merged yet** -- the
manual cookie I uploaded directly to `ddp-openstates-scraper-memory` earlier tonight should
still be valid/fresh for now, so this shouldn't block retrying MI if you haven't gotten to it
yet. Will let you know separately once #119 merges.
