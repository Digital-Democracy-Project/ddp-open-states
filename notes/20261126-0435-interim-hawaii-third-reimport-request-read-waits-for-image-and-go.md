# Interim 11-26 04:35 UTC: Hawaii third re-import request read (OPEN-900); waits for the image and Ramon's go

* Read the request (`2ee04caf`). Nothing started. It waits for two things: scrapers #297 merged into an image Ramon builds (v96 does not carry it), and Ramon's go in this session naming the note.
* When both exist I will follow your order: read `DDP_SCRAPERS_COMMIT` in the new image and stop if it does not contain #297; `ddp:pipeline_lock:hi` empty; trigger `hi?full=true&sessions=2026` (expect 202 with `"full": true`); then start Hawaii's archive by hand; then report the pass numbers you listed (6 labels changed, 12,828 vote events, 6,728 bills).
* Same constraint as my other runs: my role cannot read ECS task definitions or the image, so the recorded commit has to come from your side or Ramon's build output.
* BROKER-605 (motion text over 200 characters) is a broker release and not part of this; I have changed nothing for it.
* Nothing else changed since my 02:15 status: Georgia 2025_26 and Maine are still collecting; v96 rebuilds wait for them.
