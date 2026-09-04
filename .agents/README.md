# Agent workflow

Read `../AGENTS.md`, then Fleet's required brief. For any web UI change, read Fleet `RULES.md` §10, `WEBUI.md`, and `WEBUI-COOKBOOK.md`, then run the cookbook's full Perimeter Walk on a scratch `lab` service.

- Open owner choices live in `directions.md` and use the Fleet directions dialect.
- Session evidence lives in `log/YYYY-MM-DD-<topic>.md`; logs record what happened and never become policy.
- Keep changes cohesive, run the documented gates, stage named paths, and use an imperative commit title with the final trailer `agent: Codex`.
- Pushing `master` to `origin` is part of shipping here (owner decision 2026-09-04: "you can push when needed. You are pulling anyways"). This is a deliberate, repository-local exception to Fleet RULES.md §1's "leave pushes to queezz", granted because the Raspberry Pi deploys by pulling from GitHub and queezz hops sessions. Push only a committed, gate-green change, and say in the handoff what was pushed. Tags remain queezz's.
- Deploying to the Pi: `git pull --ff-only` in `/home/pi/pihtivacuum`, then `sudo systemctl restart pihti`, then confirm `/version`; reachable keys-only with `SSH_AUTH_SOCK=$HOME/.ssh/agent.sock ssh pi@pihti` on the work PC.
