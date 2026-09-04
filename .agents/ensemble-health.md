# The three-service ensemble

Recorded 2026-09-04 from PIHTI Log's letter `20260904-651a603e-d29c3c`
(`code/pihti-log` → this project), collected the same day. This file is the
durable local copy of that proposal; the letter itself is discharged.

## What queezz wants

Three PIHTI web surfaces run together as one ensemble: **ControlUnit**,
**PIHTI Log**, and **this diagram**. His words, 2026-09-04, as the letter
quotes them: *"I'm planning to make 3 webui work and talk together... So all 3
should grow a tab with the health of all 3 and links."* And on why: *"I'd
rather come to the laptop connected to the LAN and be at my full control.
Whichever laptop. That's the vision. Especially when all 3 connected services
run."*

So: each of the three grows one tab showing the health of all three, with a
link to each, where each lives, and how to start it. A person on any laptop on
the LAN opens any one of the three and can see and reach the other two.

## The proposed contract

PIHTI Log proposes each service expose one unauthenticated `GET` over HTTP, on
the same origin the surface already serves, returning JSON:

```json
GET /api/health
{"service": "pihti-diagram", "version": "0.4.0", "status": "ok",
 "detail": "state captured 2 min ago"}
```

- `status` is one of `ok`, `degraded`, `down`.
- `detail` is one short human sentence, or an empty string.
- Served with `Cache-Control: no-store` — which this application already sets
  on every response.
- No secrets, no filesystem paths, no instrument addresses in the response.

Addresses stay in each machine's own local configuration, never in a portable
repository. PIHTI Log already keeps this project's addresses that way
(`diagram_urls` in its machine-local config).

## Invariants this project keeps

- **No service depends on another to run.** A neighbour that is down is shown
  as down, never as an error page, and never blocks this surface from serving.
- **Four states, never conflated:** `ok`, `degraded`, `down`, and
  `unreachable` — a neighbour that cannot be reached *from this machine* is
  never painted as one that answered. This is the existing honesty rule
  (Fleet `WEBUI.md`) applied to neighbours.
- **This diagram answers on the LAN by default** (owner decision 2026-09-04,
  recorded in `AGENTS.md`): it is served from the lab Raspberry Pi and read on
  laptops and phones. PIHTI Log's letter proposed loopback as each service's
  default; that remains PIHTI Log's own call for PIHTI Log.
- **`lab <alias>` is how a service starts.** No second launcher is invented;
  Lab already knows every alias (`pihti-diagram`, `pihti-log`).
- The PIHTI Log adapter that reads this project stays read-only and never
  calls a device mutation route.

## What is asked of this project

1. A reply to `code/pihti-log` saying whether the endpoint shape suits us or
   wants changing — a proposal, not a decision, and cheaper to change before
   three implementations exist.
2. The path and port this project settles on, so queezz can put them in each
   machine's local configuration.

Nothing blocks on PIHTI Log's side.

## The separate, still-open thread

PIHTI Log's earlier letter (`20260903-db2a3289-25390d`, forwarded to this
mailbox as `20260903-ac0f4c69-3e864d`) asked for a stable captured-state
permalink so a journal entry can link the exact state it embedded. That
request stands on its own: the ensemble does not depend on it, and it does not
depend on the ensemble. Version 0.4.0's `/history?at=…` permalink and
`/state.svg?at=…` endpoint are this project's answer to it, pending a reply
letter.
