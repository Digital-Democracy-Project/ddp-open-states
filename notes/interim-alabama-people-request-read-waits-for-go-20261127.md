# INTERIM (prod agent): Alabama people request `2bc1578` (OPEN-931) read; nothing started. 2026-11-27 (production host)

Read in full. Not a go, so nothing runs. It needs Ramon's go in my session per part (the people load, then the Alabama re-import). Alabama's manifest rollout is done (`66ed1713e`); its first embedding and search-refresh pass is running inside ddp-sync, so I will not start the re-import while it runs (your gate), and I will tell you which people-load path I used (ddp-sync's people refresh, read from this host) and report the exact output lines, stopping if anything beyond the two people changes.

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
