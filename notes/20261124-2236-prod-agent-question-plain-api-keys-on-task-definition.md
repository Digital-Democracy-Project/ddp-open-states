# QUESTION from Ramon (relayed by me): why are VA_API_KEY and CONGRESS_GOV_API_KEY hard-coded as plain values in the task definition?

Ramon, 11-24 ~22:50 UTC: "it's supposed to be reading from the aws secrets manager. i'm not sure why these keys are hard-coded into a task definition". Context: in `ddp-scrapers-db:19` (his paste, my note on the step 1 result) both names sit under `environment` with plain values; I repeat no value here.

## What I can see (read only, this host's checkout of ddp-open-states; I cannot read AWS history)
- `deploy-scrapers-image.sh` builds each new revision by **copying the current revision forward** and changing only the image tag (`next_revision()`: deepcopy of the previous task definition, `image` rewritten, ECS's read-only fields dropped). It only touches `secrets`/`environment` for the RDS names when `TASK_RDS_SECRET_ARN` is given. So any plain `environment` entry that was ever on a revision is carried into every later one, silently, until someone removes it. That matches what Ramon saw on revision 19 (registered 21:15 UTC by the `ddp-scraper` user).
- OPEN-126 (jurisdiction credentials, 08-22) says `va` needs `VA_API_KEY` "in `.env`" and that Secrets Manager was not available to the scrape path at the time; RUNBOOK.md says `os-update va` fails until `VA_API_KEY` is set. So the design for these two keys was environment variables, and the Fargate path inherited that. I did not find in the repo where the values were first put on the task definition (probably a hand-registered early revision), and the script has no step that reads them from Secrets Manager.

## What I ask you
1. Do you know who set the two keys on the first revision of `ddp-scrapers` / `ddp-scrapers-db`, and are both needed on the **db** family at all (it runs `cloud_loader.py` and `cloud_archiver.py`, not the scrapers)? A task started from a definition gets every entry in it.
2. Can `deploy-scrapers-image.sh` take the same route as the RDS login for these two (a `secrets` entry with `valueFrom`, set by a `TASK_*` variable, and the plain entries dropped), in the same release as step 2 of d8df145? Then the keys stop riding along in every revision. Rotation of the two keys themselves is Ramon's call; I told him to treat them as exposed (the paste is in my session transcript).
3. Please also say whether the older, still-ACTIVE revisions of both families hold them; I cannot list revisions (this host's role is denied `ecs:DescribeTaskDefinition`).

I change nothing. Not part of step 3 or 4.
