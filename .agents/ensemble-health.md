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

## Built (0.7.0, 2026-09-04)

`GET /api/health` answers `{service, version, status, detail}` with the
detail "diagram changed N min ago" or "no diagram changes recorded yet";
`GET /api/neighbours` returns this service plus the two neighbours as rows
`{alias, name, url, state, version, detail}` in ControlUnit's five states
(`ok`, `degraded`, `down`, `unreachable`, `not configured`), probed
server-side with a two-second timeout and a ten-second cache, exactly as
`controlunit/web/neighbours.py` does; the Services tab renders them. Neighbour
addresses live only in the machine-local settings file (`NEIGHBOURS` key) or
`PIHTI_NEIGHBOURS`. On the Pi the diagram answers at port 5000, ControlUnit's
web view at 4187; PIHTI Log serves from the office PC at 4310.

## The board as the ensemble's reference (0.8.0, 2026-09-07)

queezz, 2026-09-07: *"I like the pihti-diagram way for the services. And we
need to sync that in all 3 syblings."* PIHTI Log said the same in letter
`20260907-f4233fa8-a494c0` and is adopting this card board. Two things this
release settles for all three:

- **The four state meanings, as PIHTI Log proposed and this project already
  implemented:** an explicit refusal or an HTTP error is `down`; a timeout,
  a DNS failure or silence is `unreachable`; a malformed health response is
  `degraded`; an address this machine was never given is `not configured`.
  ControlUnit read a refusal as `unreachable`; that is the one real drift,
  and `src/pihti/neighbours.py` is the reference for it.
- **The explainer teaches once, at a glance.** The right rail carries one
  lead line, then the same five chips the cards render, each with its meaning
  in a few words, and the rest of the explanation behind a `More` press.
  Three muted paragraphs were "too long and too quiet" (queezz, 2026-09-07),
  and the page is read by people whose English is a second language, which is
  a reason for short parallel lines rather than prose. Cards **state**; the
  rail **teaches**, once (Fleet `WEBUI.md`, Teaching).
- **Start rows lead with meaning; the command waits behind a toggle** and
  survives the board's thirty-second refresh, so a disclosure never closes
  under the reader.

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
- **A card says how its service starts, and invents nothing.** Lab knows
  `pihti-diagram` and `pihti-log`, so those cards carry a `lab` line. Lab has
  no `controlunit` alias anywhere in this lab: that web server is opened by
  the rig's own launcher on the Raspberry Pi, and until 0.8.0 the card printed
  `lab controlunit`, a command nobody can run (queezz, 2026-09-07: "we should
  teach that the rig's GUI starts the webserver"). A start line is a fact
  about a machine, never an alias guessed from a name. The exact chain, read
  in the ControlUnit checkout on 2026-09-07 after `code/pihti-log` letter
  `20260907-c39f87ab-3afa0a` named it: the Pi's `~/Desktop/aktest.sh` calls
  that repository's `scripts/run_controlunit.sh`, which runs
  `python -m controlunit.main --web`, so the control unit serves its own web
  view. 0.8.1 says "the desktop launcher on the rig's Raspberry Pi" on the
  card, because that is the thing a person at the rig actually presses.
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
