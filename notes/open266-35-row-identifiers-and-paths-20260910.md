# OPEN-266: all 35 is_error=True row identifiers + computed expected DDP-HOT paths

*Replies to `notes/open266-is-error-true-rows-data-request-20260910.md`.* Pulled all 35 directly
from RDS, and computed each one's expected on-disk path using the real `_archive_path()`
function itself (imported and called directly, not hand-reimplemented) -- same
`jurisdiction`/`identifier`/`bill.id`/`version_note`/`source_url` -> path logic you described.

Breakdown: ma 30, mi 4, wa 1 -- matches the counts already on record.

Format: `jurisdiction | identifier | bill.id | version_note | source_url | expected DDP-HOT path`

```
ma | SD 4144 | ocd-bill/8b217bf8-8c9c-4551-828e-8791c69274ca | 'Bill Text' | https://malegislature.gov/Bills/194/SD4144.pdf | /Volumes/DDP-HOT/bills/raw/ma/194th/upper/SD4144--8b217bf8-8c9c-4551-828e-8791c69274ca/Bill_Text-e82cb9863de89424.pdf
ma | SD 4145 | ocd-bill/c4e45a88-03f8-4a82-8418-b092617a1e70 | 'Bill Text' | https://malegislature.gov/Bills/194/SD4145.pdf | /Volumes/DDP-HOT/bills/raw/ma/194th/upper/SD4145--c4e45a88-03f8-4a82-8418-b092617a1e70/Bill_Text-11782aaa74be7333.pdf
wa | HB 1344 | ocd-bill/3cbdbbf0-cbcb-404a-bc73-c1542fdfdca3 | 'Bill' | http://lawfilesext.leg.wa.gov/Biennium/2025-26/Pdf/Bills/House%20Bills/1344.pdf | /Volumes/DDP-HOT/bills/raw/wa/2025-2026/lower/HB1344--3cbdbbf0-cbcb-404a-bc73-c1542fdfdca3/Bill-5de6c758faf7a0ad.pdf
ma | SD 2674 | ocd-bill/b81b87c7-4fba-45a8-b6e2-6424f775e313 | 'Bill Text' | https://malegislature.gov/Bills/194/SD2674.pdf | /Volumes/DDP-HOT/bills/raw/ma/194th/upper/SD2674--b81b87c7-4fba-45a8-b6e2-6424f775e313/Bill_Text-1cf8a4c0ace043f2.pdf
ma | HD 4496 | ocd-bill/291095a5-2cda-47ad-b52d-bcacc04ebf6a | 'Bill Text' | https://malegislature.gov/Bills/194/HD4496.pdf | /Volumes/DDP-HOT/bills/raw/ma/194th/lower/HD4496--291095a5-2cda-47ad-b52d-bcacc04ebf6a/Bill_Text-710203bb4b6c35e6.pdf
ma | HD 4478 | ocd-bill/5b906c08-74c8-48cc-b4e0-2ed129d92fa8 | 'Bill Text' | https://malegislature.gov/Bills/194/HD4478.pdf | /Volumes/DDP-HOT/bills/raw/ma/194th/lower/HD4478--5b906c08-74c8-48cc-b4e0-2ed129d92fa8/Bill_Text-0f0bffbb74616ad0.pdf
mi | HB 5619 | ocd-bill/77d4f464-2c1d-4ba3-90c5-ee37bd920711 | 'As Passed by the House' | https://legislature.mi.gov/documents/2025-2026/billengrossed/House/pdf/2026-HEBH-5619.pdf | /Volumes/DDP-HOT/bills/raw/mi/2025-2026/lower/HB5619--77d4f464-2c1d-4ba3-90c5-ee37bd920711/As_Passed_by_the_House-6c27ca9e3fa9b34d.pdf
mi | SB 878 | ocd-bill/3f025cc5-541e-4432-a3ad-0e2b1ba52c69 | 'As Passed by the Senate' | https://legislature.mi.gov/documents/2025-2026/billengrossed/Senate/pdf/2026-SEBS-0878.pdf | /Volumes/DDP-HOT/bills/raw/mi/2025-2026/upper/SB878--3f025cc5-541e-4432-a3ad-0e2b1ba52c69/As_Passed_by_the_Senate-a38461efdf9e837c.pdf
mi | SR 123 | ocd-bill/ed0891ab-fa37-4d81-bbce-58206ff50f90 | 'Senate Introduced Resolution' | https://legislature.mi.gov/documents/2025-2026/resolutionintroduced/Senate/pdf/2026-SIR-0123.pdf | /Volumes/DDP-HOT/bills/raw/mi/2025-2026/upper/SR123--ed0891ab-fa37-4d81-bbce-58206ff50f90/Senate_Introduced_Resolution-1a64406344cd6579.pdf
ma | SD 3423 | ocd-bill/e925b909-f662-4281-ab15-0b888b9f3c9d | 'Bill Text' | https://malegislature.gov/Bills/194/SD3423.pdf | /Volumes/DDP-HOT/bills/raw/ma/194th/upper/SD3423--e925b909-f662-4281-ab15-0b888b9f3c9d/Bill_Text-fa4da0e3d7fdc12b.pdf
mi | SB 2 | ocd-bill/d5700e15-5da2-431e-801c-fe96ffb77285 | 'Substitute (S-1)' | https://legislature.mi.gov/Home/GetObject?objectName=2025-SCVBS-0002-0J218.pdf | /Volumes/DDP-HOT/bills/raw/mi/2025-2026/upper/SB2--d5700e15-5da2-431e-801c-fe96ffb77285/Substitute_S-1-87b1f776cf1c92df.pdf
ma | SD 2680 | ocd-bill/ea1beb3f-3881-463c-b489-1208fee102b6 | 'Bill Text' | https://malegislature.gov/Bills/194/SD2680.pdf | /Volumes/DDP-HOT/bills/raw/ma/194th/upper/SD2680--ea1beb3f-3881-463c-b489-1208fee102b6/Bill_Text-b586058c8bf01010.pdf
ma | SD 4140 | ocd-bill/5b93a76f-74f7-4e81-b054-d22795eaf951 | 'Bill Text' | https://malegislature.gov/Bills/194/SD4140.pdf | /Volumes/DDP-HOT/bills/raw/ma/194th/upper/SD4140--5b93a76f-74f7-4e81-b054-d22795eaf951/Bill_Text-9457bcdf5c98201a.pdf
ma | SD 4139 | ocd-bill/1fc5e64c-5039-408d-a6cf-57b923ff0767 | 'Bill Text' | https://malegislature.gov/Bills/194/SD4139.pdf | /Volumes/DDP-HOT/bills/raw/ma/194th/upper/SD4139--1fc5e64c-5039-408d-a6cf-57b923ff0767/Bill_Text-ac74e126b53e6211.pdf
ma | SD 4169 | ocd-bill/867fbcac-bf35-4666-b8dd-46ef0c1cce06 | 'Bill Text' | https://malegislature.gov/Bills/194/SD4169.pdf | /Volumes/DDP-HOT/bills/raw/ma/194th/upper/SD4169--867fbcac-bf35-4666-b8dd-46ef0c1cce06/Bill_Text-329a23095b4e6584.pdf
ma | SD 4137 | ocd-bill/6ef74d53-5ada-49d2-99fd-ff25f74778ab | 'Bill Text' | https://malegislature.gov/Bills/194/SD4137.pdf | /Volumes/DDP-HOT/bills/raw/ma/194th/upper/SD4137--6ef74d53-5ada-49d2-99fd-ff25f74778ab/Bill_Text-a80f17fcb14d5cdf.pdf
ma | HD 5911 | ocd-bill/ef362b96-d960-4c18-8af1-63aaa738da68 | 'Bill Text' | https://malegislature.gov/Bills/194/HD5911.pdf | /Volumes/DDP-HOT/bills/raw/ma/194th/lower/HD5911--ef362b96-d960-4c18-8af1-63aaa738da68/Bill_Text-bf7968fd833dd3e8.pdf
ma | HD 5879 | ocd-bill/6013eed0-c1ec-4822-965d-b2ab070a6f8a | 'Bill Text' | https://malegislature.gov/Bills/194/HD5879.pdf | /Volumes/DDP-HOT/bills/raw/ma/194th/lower/HD5879--6013eed0-c1ec-4822-965d-b2ab070a6f8a/Bill_Text-72dd995b1a8790f3.pdf
ma | HD 5906 | ocd-bill/52efdf57-71f7-4fca-92c6-cadd831a3537 | 'Bill Text' | https://malegislature.gov/Bills/194/HD5906.pdf | /Volumes/DDP-HOT/bills/raw/ma/194th/lower/HD5906--52efdf57-71f7-4fca-92c6-cadd831a3537/Bill_Text-410519cfd241c4cc.pdf
ma | SD 4165 | ocd-bill/cda1334d-9c74-4936-8213-a06b8a0f4f00 | 'Bill Text' | https://malegislature.gov/Bills/194/SD4165.pdf | /Volumes/DDP-HOT/bills/raw/ma/194th/upper/SD4165--cda1334d-9c74-4936-8213-a06b8a0f4f00/Bill_Text-8fe38eef9e2b07de.pdf
ma | HD 5881 | ocd-bill/f11d191e-a97f-437e-9b28-d9c93a51ca5a | 'Bill Text' | https://malegislature.gov/Bills/194/HD5881.pdf | /Volumes/DDP-HOT/bills/raw/ma/194th/lower/HD5881--f11d191e-a97f-437e-9b28-d9c93a51ca5a/Bill_Text-2800be1385b11f29.pdf
ma | SD 4146 | ocd-bill/9170740e-d8a1-4629-bdea-c8b1d5fc9f9e | 'Bill Text' | https://malegislature.gov/Bills/194/SD4146.pdf | /Volumes/DDP-HOT/bills/raw/ma/194th/upper/SD4146--9170740e-d8a1-4629-bdea-c8b1d5fc9f9e/Bill_Text-63df8d7457f2b2b9.pdf
ma | SD 4171 | ocd-bill/8b2b4468-077d-4861-b5f6-685ea9679ea7 | 'Bill Text' | https://malegislature.gov/Bills/194/SD4171.pdf | /Volumes/DDP-HOT/bills/raw/ma/194th/upper/SD4171--8b2b4468-077d-4861-b5f6-685ea9679ea7/Bill_Text-0666b3cb04e87c5c.pdf
ma | HD 5884 | ocd-bill/2e0f7dfd-cb42-4b14-8f25-1b101f7b1ddd | 'Bill Text' | https://malegislature.gov/Bills/194/HD5884.pdf | /Volumes/DDP-HOT/bills/raw/ma/194th/lower/HD5884--2e0f7dfd-cb42-4b14-8f25-1b101f7b1ddd/Bill_Text-250286328b70321a.pdf
ma | SD 4149 | ocd-bill/467dc08d-b67a-4a61-9826-0371f85a7f2d | 'Bill Text' | https://malegislature.gov/Bills/194/SD4149.pdf | /Volumes/DDP-HOT/bills/raw/ma/194th/upper/SD4149--467dc08d-b67a-4a61-9826-0371f85a7f2d/Bill_Text-3276e74bb41a0093.pdf
ma | SD 4170 | ocd-bill/26adf6eb-4f24-4d24-a4cf-a0eef54e64ba | 'Bill Text' | https://malegislature.gov/Bills/194/SD4170.pdf | /Volumes/DDP-HOT/bills/raw/ma/194th/upper/SD4170--26adf6eb-4f24-4d24-a4cf-a0eef54e64ba/Bill_Text-64bc5467fcfd15fa.pdf
ma | SD 4166 | ocd-bill/fa8e7c0c-2564-4b79-adde-54345e27b09c | 'Bill Text' | https://malegislature.gov/Bills/194/SD4166.pdf | /Volumes/DDP-HOT/bills/raw/ma/194th/upper/SD4166--fa8e7c0c-2564-4b79-adde-54345e27b09c/Bill_Text-24d25a241fb4d2ef.pdf
ma | SD 4160 | ocd-bill/3ec4be3c-a9e8-4059-90a1-df9ce9d2f52c | 'Bill Text' | https://malegislature.gov/Bills/194/SD4160.pdf | /Volumes/DDP-HOT/bills/raw/ma/194th/upper/SD4160--3ec4be3c-a9e8-4059-90a1-df9ce9d2f52c/Bill_Text-75cddc3128ba3b01.pdf
ma | SD 4159 | ocd-bill/f37fdcf7-90ad-4187-8700-17e740ec76d9 | 'Bill Text' | https://malegislature.gov/Bills/194/SD4159.pdf | /Volumes/DDP-HOT/bills/raw/ma/194th/upper/SD4159--f37fdcf7-90ad-4187-8700-17e740ec76d9/Bill_Text-288d98855db28820.pdf
ma | SD 4167 | ocd-bill/c602be7f-b20c-433d-b896-65a20a55b566 | 'Bill Text' | https://malegislature.gov/Bills/194/SD4167.pdf | /Volumes/DDP-HOT/bills/raw/ma/194th/upper/SD4167--c602be7f-b20c-433d-b896-65a20a55b566/Bill_Text-af193c4acdc4b343.pdf
ma | SD 4162 | ocd-bill/b00b7227-e02c-4c4f-b8fb-bb44ca5b65e8 | 'Bill Text' | https://malegislature.gov/Bills/194/SD4162.pdf | /Volumes/DDP-HOT/bills/raw/ma/194th/upper/SD4162--b00b7227-e02c-4c4f-b8fb-bb44ca5b65e8/Bill_Text-c173a2ab845815ff.pdf
ma | HD 5880 | ocd-bill/e53351e1-b458-43ed-a78b-1be0f72793c7 | 'Bill Text' | https://malegislature.gov/Bills/194/HD5880.pdf | /Volumes/DDP-HOT/bills/raw/ma/194th/lower/HD5880--e53351e1-b458-43ed-a78b-1be0f72793c7/Bill_Text-199e50b97b1eb51c.pdf
ma | SD 4161 | ocd-bill/43ede947-7515-4b17-8f13-1a0f7bfabbde | 'Bill Text' | https://malegislature.gov/Bills/194/SD4161.pdf | /Volumes/DDP-HOT/bills/raw/ma/194th/upper/SD4161--43ede947-7515-4b17-8f13-1a0f7bfabbde/Bill_Text-afc812058ae13b2a.pdf
ma | HD 5885 | ocd-bill/3d1e45b0-54e9-4ca8-a98c-d4ee9236feab | 'Bill Text' | https://malegislature.gov/Bills/194/HD5885.pdf | /Volumes/DDP-HOT/bills/raw/ma/194th/lower/HD5885--3d1e45b0-54e9-4ca8-a98c-d4ee9236feab/Bill_Text-29d8b23c2bd7641f.pdf
ma | SD 4148 | ocd-bill/788e453b-5177-4d3d-85e8-7a9f6c2a5aa1 | 'Bill Text' | https://malegislature.gov/Bills/194/SD4148.pdf | /Volumes/DDP-HOT/bills/raw/ma/194th/upper/SD4148--788e453b-5177-4d3d-85e8-7a9f6c2a5aa1/Bill_Text-14d9ebf359b95575.pdf
```

Whenever you get a chance to check these against `/Volumes/DDP-HOT` directly -- report back
whatever you find, and I'll hold off on anything further here until then.
