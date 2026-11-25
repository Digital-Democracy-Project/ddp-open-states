# status: Hawaii people LOADED (OPEN-879 alias "Lee, C")

Ramon's go in my session (pop-up ~00:14 UTC 11-25: "HI people load now", before the ddp-sync restart; the other two options, after the restart and the second re-import, were not chosen).

- people checkout fast-forwarded to c59386b98b2a00bb1b9aad3fca04a5f3d40d4dc9 (in main; the only data change is data/hi/legislature/Chris-Lee-3484e323-....yml, +1 line).
- Safe run: "updated person from .../hi/legislature/Chris-Lee-3484e323-....yml", `processed 194 person files, 0 created, 1 updated`, no "went missing" or retirement line, no error. Real run: same lines, exit 0.
- **Not started: the second Hawaii re-import.** Ramon did not give that go in this pop-up, and the core rollout (ddp-sync restart onto a7035d68, image 60478a8fdc7a) has not happened yet: the HI archive (since 22:29:58) and the IA archive (since 23:29:23) are still running, so the guarded restart waits. Your order puts the re-import after that restart (its load must run on core a7035d68); I ask him for the go then.
- Still running: RI (rev 94, since 23:48), UT (rev 92), OK 2026 (rev 93): collecting. The db:22 first-launch watcher is running.
