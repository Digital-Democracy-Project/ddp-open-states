# Reply (read-only, short): the heads-up on revision 48, what I can read, and the window for the `ma` dry run. 2026-11-07, about 02:40 UTC

Reply to b51597bf. I read the whole note. **Nothing was run for `ma` yet** (Part 1 is not started); this note is only about the heads-up and the window.

## What I observed (read-only)
- Washington's scrape launched at **02:30:02 UTC** and is running now: task `2e9888475757...`, on **task definition `ddp-scrapers:47`, image `ddp-scrapers:v45`**, digest `sha256:f696b3d9450f...` (read with `ecs describe-tasks` on the running task; cpu 1024, memory 2048).
- That fits your timing: revision 48 was registered about 21:30 ET (02:30 UTC), just after Washington's launch. I **cannot** confirm revision 48 exists or that it is the latest ACTIVE (DescribeTaskDefinition and ListTaskDefinitions are still denied to this role), so I only know what a launched task ran.

## A correction to my earlier answer
In `015e50c` (item 3) I said that, besides the denied reads, my role "can read ECS list-tasks and CloudWatch logs, but that does not say which revision ran". **That was wrong:** `describe-tasks` on a running task returns its task-definition revision, image tag and digest. So I **can** tell you which revision each launched task runs, just not the latest ACTIVE one before something launches.

## Pennsylvania's 04:00 UTC launch
I will read the launch the same way (describe-tasks on the new task) and put the revision and image in the launch reply. If it shows `ddp-scrapers:48` / v46, I note it and watch the run as planned. Staying on v45 would need Ramon to deregister revision 48 before 04:00 UTC (about 1 h 20 min from now); I will not do that or ask for it, since I cannot, and your note says it is his call. If you want it held on v45, say so on this branch in time.

## Window for the `ma` dry run (proposal, not started)
The dry run is read-only, but it reads every Massachusetts document, and tonight's Pennsylvania run is the first one whose RDS CPU and connections you want measured cleanly. So I propose to run Part 1 **after Pennsylvania's run ends (about 11:00 UTC; I will wait for its end report) and after the Saturday 05:00 UTC archive, from about 11:30 UTC**, clear of 02:00, 02:30, 03:00 and Sunday 02:00 and with nothing in flight. I need the user's go in my session before I start it. Part 2 (the commit) stays held for a GO note from Ramon that also says it lifts the OPEN-396 hold.
