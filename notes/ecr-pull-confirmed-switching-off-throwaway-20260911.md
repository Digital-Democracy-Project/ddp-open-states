# ECR pull confirmed working — switching off the throwaway-build workaround

Verified end-to-end: `docker login` to ECR succeeded, `docker pull --platform linux/arm64
350941939790.dkr.ecr.us-east-1.amazonaws.com/ddp-scrapers:v20` succeeded, digest
`sha256:26e545b980713bbca2330c539f484af958216fa970bd06ab5f4ba0f95e6cbf0b` — exact match to
what was reported when `v20` was registered as task-def revision 24. Confirmed inside the
pulled image (via QEMU emulation, this host being x86_64): Python 3.10.21, `pdftotext`
22.12.0 — exact match to the throwaway local build used for `fl` and the corrected go/no-go
check.

Switching to this real pulled image for the remaining backfill steps (`va -> wa -> us`)
instead of a fresh local build each time. No drift risk now — this is the literal bits
running in production.

Currently holding on `fl --commit` itself (spot-check confirmed clean, your go-ahead noted)
pending Ramon's explicit confirmation directly in this conversation, per the standing
discipline of not proceeding on a plausible next-step alone.
