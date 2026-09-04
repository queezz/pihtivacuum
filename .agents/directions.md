# Open directions

- Split `diagram.svg` at valve boundaries and wrap each continuously connected plumbing volume in a stable `zone-*` group without changing the existing valve, pump, or gauge IDs — owner work pending.
  Done when: every volume whose connectivity can change independently has one unambiguous group ID, so the application can derive connected components without guessing from path geometry.
- Review and correct the prototype `Vent Plasma` and `Vent QMS` sequences in `static/operationGuides.json`, including exact valve names, ordering, and marker placement — owner guidance pending after hands-on use.
  Done when: each step matches the physical operating procedure and the owner accepts the diagram markers and rail wording.
- Answer PIHTI Log's ensemble proposal (`.agents/ensemble-health.md`, letter `20260904-651a603e-d29c3c`): add `GET /api/health` returning `{service, version, status, detail}` with `status` one of `ok`, `degraded`, `down`, then reply to `code/pihti-log` with the shape and the port this project settles on.
  Done when: `/api/health` answers unauthenticated on the same origin with `Cache-Control: no-store` and no path, secret, or instrument address in its body; a test covers the contract; and the reply letter has been posted.
- Grow the ensemble tab: one surface listing all three PIHTI services — ControlUnit, PIHTI Log, this diagram — each with its health, its link, and the `lab <alias>` that starts it, with neighbour addresses read from machine-local configuration rather than the repository.
  Done when: a neighbour that is down and one that is unreachable from this machine render as two distinct states, neither of them an error page, and this surface still serves normally with both neighbours stopped.
