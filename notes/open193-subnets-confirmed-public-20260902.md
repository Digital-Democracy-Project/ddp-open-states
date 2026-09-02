# OPEN-193 — the three candidate subnets are confirmed public; last blocker on item 3 is closed

*Replies to `notes/open193-candidate-subnets-found-in-env-20260902.md`.*

Ran `ec2:DescribeSubnets` (live-verified read from this role) on all three:

| Subnet | AZ | CIDR | MapPublicIpOnLaunch |
|---|---|---|---|
| `subnet-0fdc71c33a5cb60bc` | us-east-1c | 172.31.16.0/20 | **True** |
| `subnet-0dbb01bb8fd1cd1e8` | us-east-1a | 172.31.0.0/20 | **True** |
| `subnet-087136704d428e5f2` | us-east-1f | 172.31.64.0/20 | **True** |

Same VPC (`vpc-094e2b729f120ef62`) as everything else already confirmed. All three are
**public**, `MapPublicIpOnLaunch: True` — matching `infra/fargate-spike/variables.tf`'s
documented "Option A" decision (public IP per task, deliberately avoiding a shared NAT gateway
egress IP), not the original request's "private subnets" phrasing. No NAT gateway or VPC
endpoint check needed as a result — the concern in the last note only applied if these had come
back private.

Combined with the `.env` circumstantial evidence (same block as the already-verified security
group and role ARNs), this closes the subnet question. `sync_schedule.yaml`'s
`cloud_path.fargate.subnets` can be filled with these three:

```yaml
subnets: ["subnet-0fdc71c33a5cb60bc", "subnet-0dbb01bb8fd1cd1e8", "subnet-087136704d428e5f2"]
```

That's every value OPEN-193 item 3 needed. Item 4 (the canary run) is next — same procedure as
the original request: pick one small non-MI jurisdiction, `enabled: true` + that jurisdiction
listed, restart the `ddp-sync` service, trigger, watch it through to completion.
