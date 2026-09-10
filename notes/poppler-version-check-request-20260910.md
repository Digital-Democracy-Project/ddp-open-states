# One more check on the 5 "genuinely unextractable" MA rows -- 2 of them might not actually be dead

*Follow-up to `notes/sr123-upload-needs-mac-access-20260910.md`'s note on the 5 MA rows that came
back malformed after the archive_location fix.* Looked at the actual files myself (I have DDP-HOT
access) before accepting all 5 as a uniform accepted-loss case, since 3 of them were part of the
9-row batch and their bytes are sitting right there.

## 3 of the 5 are genuinely scanned documents -- confirmed, not guessed

`HD 4496`, `HD 4478`, `SD 2680` are all real office-scanner output (`Creator: TOSHIBA
e-STUDIO7527AC`, `Producer: SECnvtToPDF V1.0` -- a physical copier's scan-to-PDF feature). Ran
`pdftotext -layout` against each (same flags `pdfdata_to_text()` uses) -- 31-55 characters back,
essentially nothing. No text layer exists to extract; this needs OCR or nothing. Accepting these
3 as dead, same as before.

## 2 of the 5 (`SD 2674`, `SD 3423`) extracted real text for me, using the same tool

Ran the exact same `pdftotext -layout <file> -` this codebase's own `pdfdata_to_text()` calls,
against the exact same bytes (verified via checksum against what's in S3) that your `reextract
ma --commit` run reported as failed:

- `SD 2674`: 938 characters of real text, zero errors of any kind.
- `SD 3423`: 9,198 characters of real text, with one non-fatal warning printed to stderr
  (`Syntax Error: Expected the optional content group list, but wasn't able to find it, or it
  isn't an Array`) -- poppler recovered and extracted the content anyway.

This Mac's `pdftotext` is poppler **26.04.0** (Homebrew, current as of today). If your
`reextract` run genuinely failed on these same two files, that's most consistent with an older
poppler build on whatever host ran it -- older poppler versions are known to be stricter/less
forgiving about exactly this class of minor PDF structural defect.

## Ask

Could you check the poppler/`pdftotext` version on the host that ran `reextract` (`pdftotext -v`,
or `dpkg -l poppler-utils` if it's Debian-based)? I don't have EC2/SSM access to check this
myself -- confirmed directly, not assumed (`ec2:DescribeInstances` and
`ssm:DescribeInstanceInformation` both come back `AccessDenied` for this credential).

If it's meaningfully older than 26.04.0, that's worth knowing on its own -- not just for these 2
documents, but because an under-strict/over-strict poppler mismatch between environments could be
silently affecting other documents fleet-wide the same way, not only these two. Not proposing an
upgrade yet -- that would touch the same Dockerfile OPEN-263's rev22 regression came from, and
deserves its own deliberate look rather than a reflexive version bump. Just gathering the fact
first.

Once you have the version, I'll flag it on OPEN-266 (or a new ticket if it turns out to be a
real, broader gap) rather than deciding anything about upgrading here.
