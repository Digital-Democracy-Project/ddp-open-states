# SYNC-66's fix is merged, not deployed yet -- please deploy to EC2

PR #159 (`ddp-sync`) is merged to `main` (commit `a2c4437`), reviewed and closed by you already.
Checked directly: it isn't running anywhere yet.

**This Mac's own local `ddp-sync` checkout is one commit behind** (`4caf8bd`, not `a2c4437`) --
confirmed via `git fetch` + `git log origin/main`. Not pulling/restarting it myself; that's a
LaunchDaemon-managed live service on this Mac and restarting it isn't mine to do.

**Please deploy to EC2**, per `ddp-sync`'s own README ("Deployment" section):

```bash
cd /home/ubuntu/ddp-sync
git pull origin main
source .venv/bin/activate
pip install .
sudo systemctl restart ddp-sync
```

Per that same README, a change to this repo is meant to be deployed to **both** hosts (EC2
systemd + the Mac's LaunchDaemon) -- the Mac side needs `sudo`/an admin account too
(`sudo launchctl kickstart -k system/com.ddp.ddp-sync`), so that half is Ramon's to do, not
something to route through you. Flagging so the Mac side doesn't get lost, not asking you to
find a way around it.