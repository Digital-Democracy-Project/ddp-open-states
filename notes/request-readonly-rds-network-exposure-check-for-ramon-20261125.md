# REQUEST (read-only, not a GO): **a read-only check of how exposed the openstates database is, for Ramon.** Report it to him **in your session**, not in a note. 2026-11-25 ~04:20 UTC (Mac side, Onboard New States)

**Why:** Ramon asked to check the database's exposure first, because some old notes on this (public) branch show the database's host name. A host name alone is not a credential, but he wants to know what could reach it.

**What I need from you (read-only; nothing is written or changed):**
1. Whether the RDS instance behind the openstates database host is **publicly accessible** (`PubliclyAccessible` true or false) (`rds:DescribeDBInstances`).
2. **Which security group(s)** it uses.
3. For each group, the **inbound rules on port 5432**: which CIDR ranges or source security groups are allowed, and **specifically whether `0.0.0.0/0` or any other broad range appears** (`ec2:DescribeSecurityGroups`).

**If your role is denied** `rds:DescribeDBInstances` or `ec2:DescribeSecurityGroups`: **say so** (in your session and in a one-line note), and Ramon will run the two `aws` commands himself (he has them from the PM). Do not look for another way in.

**Where to report: to Ramon, in your session. Do not write the host name, any ARN, any security group id, any CIDR range or any rule into a note, log, ticket or chat that leaves your session.** This branch is on a **public** repository. In your reply note write only: "given to Ramon in session", plus:
* if there is **no** `0.0.0.0/0` (and no other broad range): a plain **"no 0.0.0.0/0"**;
* **if there IS one (or the instance is publicly accessible): do not write that in the note at all.** Tell Ramon in session only and write "given to Ramon in session". A public note saying the database is open before it is fixed would be an announcement.

**Never** read, print or write any credential (the database's username or password, or the secret's contents), and change nothing: no rule, no setting, no instance. Any fix (closing a rule, making the instance private) is Ramon's decision and a production change that needs his own go.

## Not authorized
Any write or change to RDS, a security group, a route or IAM; reading any secret's contents; putting any identifier, address or rule into this public branch.

Tickets: none yet (Ramon will decide whether a ticket follows).

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
