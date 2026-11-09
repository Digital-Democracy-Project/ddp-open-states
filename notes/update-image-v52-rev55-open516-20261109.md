# Update: image v52 / task-definition revision 55 is registered (OPEN-516). 2026-11-09, about 20:45 UTC (Mac side)

This adds to request `281dd01` (api-v3 on EC2 to `7b66e66`, plus the read-only report on tonight's Pennsylvania archive).

**The image:**
* Ramon registered **`ddp-scrapers:v52`** as **revision 55**. Its digest is `sha256:4679831b039baffa4c549362fcd5966692fca3e83f6d638fa10b38bc8eb41acf`.
* It carries openstates-core `main` at `28226658` (OPEN-516, #88), on top of v51.
* The image's own checks passed: imports and the Utah smoke scrape.

**My check inside v52:**
* Pennsylvania's `application/msword` link uses `handle_pennsylvania_odt`;
* Pennsylvania's PDF is `DoNotDownload`;
* the printer's-number pattern drops `PRIOR PRINTER'S NOS. 912, 934`.

**For the report (Part 2 of `281dd01`):** tonight's 04:00 UTC Pennsylvania scrape and archive should launch on **revision 55**. Please report the revision they actually ran on.

The Massachusetts run already in progress (`ma-749060e3960b`, revision 53 / v51) is not affected.

Nothing new is authorized by this note.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
