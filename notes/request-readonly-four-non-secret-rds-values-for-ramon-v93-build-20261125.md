# REQUEST (read-only, not a GO): **please give Ramon the four NON-SECRET values ddp-sync already uses for RDS, for the v93 build.** Give them to him **in your session**, not in a note. 2026-11-25 ~02:05 UTC (Mac side, Onboard New States)

**What I need from you (read-only; nothing is written or changed):**
1. **Tell Ramon, in your own session,** these four values from the EC2 host's existing configuration, so he can set them for the v93 build (`deploy-scrapers-image.sh`):
    * the RDS credentials **secret's address** (`RDS_CREDENTIALS_SECRET_ARN`; the address of the secret, **never its contents**) → his `TASK_RDS_SECRET_ARN`;
    * the RDS **host** (`RDS_HOST`) → `TASK_RDS_HOST`;
    * the **port** (`RDS_PORT`) → `TASK_RDS_PORT`;
    * the **database name** (`RDS_DBNAME`) → `TASK_RDS_DBNAME`.
2. **Do not read, print or write the secret's contents** (the username and password), anywhere, ever. The addresses are enough.
3. **Please do not write the four values into a note.** This branch is on a **public** repository (ddp-open-states). Some old notes already show the database endpoint; I would not add the secret's address or anything more here. In your reply note, just say "given to Ramon in session" (and the **names** `RDS_CREDENTIALS_SECRET_ARN`, `RDS_HOST`, `RDS_PORT`, `RDS_DBNAME`, never their values).

**Who builds v93: Ramon, on the Mac,** as for every image (`bash ~/Developer/repos/ddp-open-states/deploy-scrapers-image.sh` with the four `TASK_RDS_*` variables set). Your host cannot launch the scrapers image or build it (ECS is denied to your role, and the Mac builds; EC2 only runs), so there is no choice to make here. **What I ask of you for v93 is the watch afterwards:** the first task launched from the new `ddp-scrapers-db` revision (the next archive) must reach RUNNING and exit 0, and a names-only read-back of the new revision (`secrets`: `RDS_USERNAME`, `RDS_PASSWORD`; `environment`: `RDS_HOST`, `RDS_PORT`, `RDS_DBNAME`; and none of the five on `ddp-scrapers`), as in `277c191` Step 1. If ECS cannot read the secret every launch from that revision fails to start: deregister that revision and the previous one is latest again.

**Order (unchanged, `f9f1b5f`):** the core rollout at `a7035d68`, then the Hawaii people load and the second re-import, **then** v93. Nothing here is started before that, and this request itself changes nothing.

## Not authorized
Reading or printing the secret's contents; writing the four values into any note, log, ticket or chat; building or releasing an image from the EC2 host; anything beyond reading the four values and telling Ramon.

Tickets: OPEN-633, OPEN-639.

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
