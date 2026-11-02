# Request: add the 2025 district outlines for Pennsylvania, Nebraska and Louisiana to the production map folder (OPEN-463, pilot #2), 2026-11-02

Ramon's go (this session, /ask-me, 2026-11-02): **yes, make the map outlines for the three pilot states now, on the production host and on the dev Mac.** The dev side is done (below). This is the **same procedure you ran on 10-31 (BROKER-345; your report `15459b7b`, the playbook `fa9de3bd`)**, for three new states. **Nothing here changes any broker code, `.env`, container or nginx file, and no existing state's outlines.**

## What I rehearsed on the dev Mac (so these are not guesses)
Tool at **`1b6dc154660d4d323e92e6464dfce555504331de`**, the same commit you used. I checked that the tool is **unchanged** between that commit and what you run now (`a2cc2beb`): `git diff` of `apps/geoprocessing`, `infra/docker/Dockerfile.geoprocessing`, `common/util/fileio.py` and `infra/requirements/geoprocessing.txt` is empty. Same base image `ghcr.io/osgeo/gdal:ubuntu-small-3.9.3`. One run, exit 0, **18 s**, `{"status": "success"}`, **11 files**. Not tested: an x86 host (the Mac is Apple-chip; your 10-31 run matched byte for byte, so I expect the same).

## The request, one run
```
{"cd_session_code": 119, "census_year": 2025, "jurisdictions": [
 {"name": "Pennsylvania", "iso2": "PA", "ansi": 42}, {"name": "Nebraska", "iso2": "NE", "ansi": 31},
 {"name": "Louisiana", "iso2": "LA", "ansi": 22}]}
```
Use your 10-31 commands unchanged (scratch clone at the SHA above in a scratch folder, `docker build -f infra/docker/Dockerfile.geoprocessing`, the `docker run` with the broker's own `fileio.py` mounted over the tool's copy, one request file). The tool writes **11** files: `LA/2025/{cd,sldl,sldu,state}`, `NE/2025/{cd,sldu,state}`, `PA/2025/{cd,sldl,sldu,state}`, all `.geojson`.

## What differs from 10-31 (read these)
1. **Nebraska has no `sldl.geojson`, on purpose.** Nebraska has one legislative chamber; the Census publishes no state house file for it. The log shows a 404 for `TIGER2025/SLDL/tl_2025_31_sldl.zip`; the tool goes on and exits 0. **Do not treat it as a stop.** (The broker's `--check` is being fixed to match: ddp-broker-py PR #652, not merged.)
2. **404 lines in the log: 8 on my run** (three `TIGER2025/CD/CD119/tl_2025_{22,31,42}_cd119.zip` fallback lines as on 10-31, the Nebraska SLDL one, and four `www2.census.gov:443` retries of the same). Exit 0 and the hashes below are the check.
3. **Louisiana's state senate file has 40 features, not 39.** The extra one is `LA0ZZZU`, the Census's "no district" placeholder. It is the tool's normal output: the same placeholder is already in the dev copies of `MA/2025/sldl.geojson` and `MI/2020/sldl.geojson`. **Not a stop.** If your count differs from 40, that is.
4. Clean-up needs `sudo` (the container runs as root), as you found.

## The 11 expected hashes (save as `expected.sha256`; `sha256sum -c` on the out folder, and again on the live copies)
```
27c0332581c82847a09ce7eae4b46766974bd8474d3a73d21b5f7265727e77b9  LA/2025/cd.geojson
7919069215fc4cafa051ed226d282ea0a99c7d43abe5351a3295f92839220b12  LA/2025/sldl.geojson
83379616b9036256303a61d8c247fd1a22c5623ad8938d265e911d6138c39bbf  LA/2025/sldu.geojson
51e5393478df99773621edc82d6aab77877993949b7e01207351b03254f0d468  LA/2025/state.geojson
532f0b5832424860f2c04eb08a2810b4d6ab1d5188ca5ac3368ca24535308c75  NE/2025/cd.geojson
96ecea0694a8beea3898e658cc0ddd229f0aac845916c24a9c63e5b84fc8de67  NE/2025/sldu.geojson
9814148c62f4395140d32053f7ba8e5b06edab0447dd5e4fe093c3ed714e8711  NE/2025/state.geojson
adb215b089b7ce5e8cfc09d4479f81764196c13f4290d098fc981a3dc91d2a62  PA/2025/cd.geojson
b3c33cd22344057fa11c7165d36d8490b73b9fc4326bbf67efa2626057fcf39e  PA/2025/sldl.geojson
bd76396c4961ef53859acec4dead51dc04dc78d1520a14d44d868326d0d2141b  PA/2025/sldu.geojson
38fef48b092ccd4aea18752d9dd4a36d4ea5ce1a16c52caf257cb99d8035bc01  PA/2025/state.geojson
```
**Feature counts** (cd/sldl/sldu/state): **PA 17/203/50/1; NE 3/none/49/1; LA 6/105/40/1**. Ids look like `PA0138L`, `PA0046U`, `PA0017L-US`, `PA0000`. Nothing is public until the website asks for these years (the broker's `years` route says the default for a state is its newest year), so nothing public changes on its own.

## Before you copy (new folders only, exactly as on 10-31)
Under `/srv/ddp-static-assets/mapapp-data/geojson`: **`PA/2025`, `NE/2025`, `LA/2025` must not exist** (the existing `PA/2020`, `NE/2020`, `LA/2020` hold only `cd` and `state`; they stay as they are). If any of the three exists, stop. Take the before/after `find . \( -type f -o -type l \)` listing and `comm` check as on 10-31 (added = exactly these 11 paths, removed = none), the totals (`-type f` and `*.geojson`, expected before + 11), and read the three folder names back to Ramon before copying. `cp -n` only; new folders 755, files 644, owner `bitnami`. After the copy: `sha256sum -c` on the live copies (all 11 OK) and one nginx check, `/map/assets/geojson/PA/2025/sldl.geojson` answers 200 with 203 features.

## Stop conditions (as on 10-31)
The image will not pull or build; the run exits non-zero; any hash differs; a target folder already exists; anything that would overwrite or delete; more than 2 GB used or 20 minutes of CPU. Report to Ramon; do not work around it. **Rollback:** remove exactly `PA/2025 NE/2025 LA/2025` after the before-listing shows they did not exist. **Timing:** any hour except 03:50 to 07:15 UTC. **Clean up** the scratch folder, container and scratch image when done, and say what you removed.

## Reply
The revision used, times (UTC), the exit codes, the hash result (11 of 11), the counts, the before/after totals, the nginx check, and anything not as above.

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
