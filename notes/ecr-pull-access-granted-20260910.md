# ECR pull access granted -- switch off the throwaway-build workaround

Ramon has updated this host's IAM role policy with:

```json
{
    "Sid": "ECRAuthToken",
    "Effect": "Allow",
    "Action": "ecr:GetAuthorizationToken",
    "Resource": "*"
},
{
    "Sid": "ECRPullScrapersRepo",
    "Effect": "Allow",
    "Action": [
        "ecr:BatchCheckLayerAvailability",
        "ecr:GetDownloadUrlForLayer",
        "ecr:BatchGetImage"
    ],
    "Resource": "arn:aws:ecr:us-east-1:350941939790:repository/ddp-scrapers"
}
```

Read-only pull, scoped to just the `ddp-scrapers` repo -- everything else on the role is
unchanged.

## What this means for the remaining backfill (va/wa/us)

You should now be able to:

```bash
aws ecr get-login-password --region us-east-1 | docker login --username AWS \
  --password-stdin 350941939790.dkr.ecr.us-east-1.amazonaws.com
docker pull 350941939790.dkr.ecr.us-east-1.amazonaws.com/ddp-scrapers:v20
```

and run the remaining `os-text-extract` commands against that real pulled image instead of a
fresh local build from `main` each time -- guaranteed identical to what's actually registered
as task-definition revision 24, no drift risk. Worth a quick sanity check first (confirm
`python --version` / `pdftotext -v` inside the pulled image match what you already verified in
the throwaway build: 3.10.21 / 22.12.0) before relying on it for `va`.

The long-term question of whether `os-text-extract` itself should eventually run as its own
Fargate task (rather than in this host's venv/pulled-container) is still open and unrelated to
this -- flagging that this ECR grant doesn't resolve that, just removes the local-build
workaround for now.
