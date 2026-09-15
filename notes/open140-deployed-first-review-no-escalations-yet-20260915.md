# OPEN-140 (PRs #154/#155/#156) deployed on EC2, first real review result: nothing escalated yet

Deployed on this host via its own real process (git pull -> rebuild the Docker image, since
`scheduler.py` changed -> recreate the container) -- not the generic README steps in the deploy
note, which describe a different (bare venv/systemd) setup than what actually runs here. No
in-flight Fargate tasks at deploy time, clean restart, no errors.

Confirmed live: `openstates_cadence_review: registered escalate_window=2 excluded=[]
quiet_window=4 review_time=00:30 startup_catch_up=True` -- MI's exclusion is genuinely gone.

**The startup catch-up review already ran (00:22 UTC) -- real, honest result: nothing
escalated.** `openstates_cadence_review: completed cadences={'fl': 'weekly', 'va': 'weekly',
'mi': 'weekly', 'ma': 'weekly', 'ut': 'weekly', 'az': 'weekly', 'nc': 'weekly'} changed=0
demotion_advice=[] rescheduled=False reviewed=7`. Confirmed via `/schedule`'s own
`openstates_cadence` field too, matches exactly. Every one of the 7 eligible jurisdictions
stayed on its floor -- not just MI.

This matches your own note's honest framing ("a real unknown, not a 'nothing will happen'
assurance") -- with `escalate_window: 2`, a single review right after enabling doesn't have
enough accumulated productive-run history to escalate anything yet, MI included. Not a bug,
just needs more daily review cycles to accumulate the evidence the mechanism requires before
it'll actually promote anything. Will check back over the next few days rather than assume
this means it's not working.

**Still separately open, not addressed by this PR set**: the archive-side ask (MI's archive
job itself becoming nightly, and running strictly after the scrape actually finishes rather
than a fixed clock offset) -- confirmed via the actual diff this only touches
`openstates_scrape`'s dynamic_cadence, `openstates_archive`'s schedule/registration code is
completely untouched. `/schedule` still shows `openstates_archive_mi` on its old fixed
Thursday 05:00 UTC slot. Flagging so this doesn't get marked done by mistake -- it's a real,
separate piece of the original ask still needing its own fix.
