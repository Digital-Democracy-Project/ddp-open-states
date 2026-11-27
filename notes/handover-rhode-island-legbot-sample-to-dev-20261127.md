# HANDOVER (prod agent to dev agent): the Rhode Island LegBot sample is yours now. 2026-11-27 (production host)

Ramon's rule from today: **LegBot data-quality samples are the dev agent's work; the production agent only deploys.** He drew that line after I ran the Rhode Island sample from OPEN-910 against the production broker.

**What happened.** I read the OPEN-910 wave 2 request as asking for a production 100-bill sample, and started Rhode Island (run `legbot-session-8592eff842ea`, started 03:36 UTC) with the production environment header. My go-ahead pop-up to Ramon did not say "production"; that was my omission. By about 03:45 UTC the production broker held 160 Rhode Island artifacts. Ramon then saw most Rhode Island bills failing and is stopping the run himself.

**Not started:** Missouri and North Dakota. I stopped the runner before they began and will not start them. I did not read the Rhode Island totals or make the 15-bill export.

**What I need from you**
1. Take over the Rhode Island sample: read its results and failure reasons (the broker's bill artifact table by jurisdiction and generated time), and find out why most bills fail.
2. Decide whether the Rhode Island rows already written to the production broker should stay or be cleaned up. Nothing public reads them. I will not delete anything without Ramon's explicit go naming the rows.
3. Run any Missouri and North Dakota samples in dev. If you still want a production sample for any state, say so in a note for Ramon to approve; I will not start one on a note alone.

**Still mine, unchanged:** the v99 request (`231f011`) steps, each on Ramon's go, after the Iowa re-import finishes.

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
