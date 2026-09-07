# A word before the press, and the routes the map already knows (0.13.0)

Commander-dispatched ship in the coordinated PIHTI trio run, on the work
Windows PC, 2026-09-08 midday JST — queezz awake. It builds the two warnings
`directions.md` had designed and left unbuilt in 0.12.0, and prepares the
answer sheet for the vent-guide question rather than guessing at it again.

## The two warnings

queezz, 2026-09-08 (letter `20260907-d5386824-f57dfd`, collected by the 0.12.0
ship): *"create warning when putting gas/air on to IG"* and *"and when vent
goes on to TMP"*. Both are the same mechanism and they are built as one.

Before a press reaches `/update`, the page asks `GET /press-warnings?id=…&
status=…`. The server predicts twice — once from the entered state and once
from a **copy** of it with the press applied — and returns only what the press
makes *worse*. Two things on this rig mind what arrives:

- an **ionization gauge that is switched on**, which minds gas and vent air
  alike;
- a **turbo pump that is marked running**, which minds vent air. A running
  turbo is a boundary in the prediction, so the volume tested for it is the
  pump's own — the one the vent would actually join — never everything behind
  it, exactly as the directions item specified.

`plumbing.py` gains `exposures()` and `press_warnings()`. Exposure is **ranked**
rather than listed: nothing is 0, gas is 1, vent air is 2, and a warning is
owed only when a press raises that number for the same gauge or pump. That one
decision buys three behaviours for free — closing a vent is an improvement and
never warns, an unrelated press while a gauge already stands in air does not
cry twice, and switching a gauge *on* into a volume that already holds air is
the same mistake from the other side and does warn.

**Which gauges count is not a guess.** `plumbing.json` marks exactly two with
`kind: "ionization"`, and they are the two whose own names say so; queezz
settled the rest on 2026-09-04 — when venting, "only ionization gauges go off
(Baratron, Pirani, the Pfeiffer single gauge and the Ulvac membrane gauge work
at one atmosphere)". A gauge with no `kind` is never warned about, and a test
walks all six.

**A warning is a confirm.** An element whose `confirmToggle` is `false` — the
flow calibration valve, the gas panel valves — has no box of its own, and now
asks anyway whenever there is something to say. Nothing else about those
elements changed: with nothing to say they still press straight through.

The sentence the box carries, measured live off the real page:

> Warning, predicted from the valve positions: this would let vent air reach
> the QMS ionization gauge (downstream), which is switched on.
>
> Mark Bypass gate valve, downstream (GVBD) active?

The warning stands above the question, because the question is what the two
buttons answer. Every part is named the way a person names it at the rig,
through `window.pihtiElementName`; no key reaches the box.

**It is a prediction and never an interlock.** It reads no pressure, refuses
no press, and protects no hardware — the confirm box is a modal of its own and
says "predicted from the valve positions" once, in the warning itself, so a
reader about to touch the rig knows which kind of statement this is. The key
under the drawing still carries the page's one honesty sentence, and a test
still counts it exactly once per page.

If the check cannot be run at all, the box says so ("This press could not be
checked against the diagram just now.") and asks anyway. An unchecked press is
not a safe one.

One incidental repair: `isInteracting` is now held from before the question
rather than after it, so the five-second refresh cannot repaint the drawing
under an open box.

## The vent-guide routes: the map's own answer, written out

Task C of the dispatch, and deliberately no code. The guides' hand-written
route list dates from 0.5.0, when nothing here knew the plumbing; `plumbing.
json` knows it now, so it was asked, and its answer is written into the
`directions.md` owner question as something queezz can answer with "yes" or a
correction. In short, and in the same words the item uses:

- **Four routes between the vessels**, ignoring anything that runs out into the
  room: the two bypass VCR valves on the narrow pipe (only under *Pipe open*);
  the upstream bypass gate valve → bypass line valve 1 → the downstream bypass
  gate valve; the same two gate valves through the drawn `Membrane` instead;
  and the long way round — main gas line → argon gas line → flow calibration
  valve → downstream bypass gate valve.
- **Two of the 0.5.0 guesses are not routes at all.** The QMS valve opens the
  QMS vessel onto its own sensor branch, a dead end; the roughing bypass is a
  pump, and every pump in this map is a wall.
- **Ionization gauges:** the QMS one sits on the QMS vessel itself; the bypass
  one sits on the bypass manifold, one gate valve from the plasma vessel rather
  than on it. By the map the plasma vessel carries no ionization gauge at all —
  its two are the upstream single gauge and the upstream Baratron — which is
  put to queezz as a question rather than assumed.
- **Nitrogen** enters at the gas panel nitrogen valve. To the plasma vessel the
  shortest path is four valves, not the two the guide names: nitrogen valve →
  gas panel argon valve → argon gas line → main gas line. To the QMS vessel:
  nitrogen valve → gas panel argon valve → flow calibration valve → downstream
  bypass gate valve, or across from the plasma vessel through the two VCRs.

## One thing found while building, and handed back

Every pump in the map is a wall, running or stopped. That is why a backing-line
vent valve raises no warning even under a spinning turbo — the map has no path
from a foreline to the vessel above its pump, so there is nothing to warn
about. For the *vessel* side that is right and is what the colours were built
on; whether a **stopped** turbo should still be a wall, and whether venting a
spinning turbo from its exhaust side deserves a warning this map cannot
currently see, is a new owner question in `directions.md`. Nothing was changed
on a guess.

## Verify: scratch Perimeter Walk

`lab start pihti-diagram --port 48973 --host 127.0.0.1` under scratch
`LAB_CONFIG`/`LAB_RUNTIME_ROOT`/`LAB_LOG_ROOT`, with every `PIHTI_*` write path
inside a marked `fleet-scratch-2024-interactive-diagram-warnings` root in this
session's own scratchpad — outside Dropbox, outside `%LOCALAPPDATA%` — and a
hand-built state file: the gas panel vented, its argon valve and the main gas
line open, the QMS ionization gauge on, TMPU running, GVU and GVBD shut.
Listener PID 26140 confirmed as the child of Lab's tracked PID 34332. The
owner's `4186` was listening under PID 27612 before, during and after and was
never addressed; the Pi's `5000` was never touched.

- **The gauge warning**, pressed on the real drawing: `GVBD` produced the
  sentence above. The gauge switched off, the identical press produced the
  ordinary `Mark Bypass gate valve, downstream (GVBD) active?` and nothing
  else.
- **The turbo warning**: with TMPU running, `GVU` produced "this would let vent
  air reach the plasma turbo pump (TMPU), which is marked running." TMPU
  stopped, the same press produced the ordinary box.
- **A warning is a confirm**: the flow calibration valve (`confirmToggle:
  false`, read live off `/elements-config`) produced the full warning box; the
  bypass line valve 2 produced **no box at all**, which is the right answer for
  a press that joins nothing dangerous.
- **The backing-line vent** under a stopped turbo produced the ordinary box, as
  the map says it should.
- Cancelling a warned press left `/elements-state` byte-identical, and
  `/press-warnings` never wrote: the stored state file after a run of asks was
  the file that went in.
- **Rails at 76 px** at 0/25/50/75/100 % of the scroll range at 1280×700 on
  Vacuum (guide open, scroll range 189) and History (range 165), and at 76 px
  on Plot and Services; identical every reading, both rails. Document width
  1265 at 1280 — no page-width overflow — and 1265 at 1280×1000.
- **At 390×844** the document is exactly 390, no horizontal scroll, and a
  warned press still asks its question there.
- Every top tab pressed from inside Vacuum with a guide open; each landed at
  its own top (`scrollY` 0). Browser Back from Vacuum returned to Plot,
  Forward returned to Vacuum at the top with the colours and both readout
  lines intact.
- **History deep link** `/history?at=2026-09-08 08:04:07` opened cold and
  survived a true `location.reload()`: the same moment, the same fills (plasma
  vessel air `rgb(138,0,38)`, QMS isolated `rgb(127,123,117)`), the same two
  readout lines. The diagram there is not clickable, so no warning path exists
  on that page.
- The honesty sentence renders exactly once per page and "measure pressure"
  appears nowhere.
- **Console clean** — not one message on any page or any press.
- `lab stop` killed the tree; PIDs 26140 and 34332 are gone and port 48973 has
  no connections at all. Scratch root marked `superseded`.

**One walk step could not be completed honestly and is reported rather than
waived.** The Browser pane stayed hidden for this session, so nothing was
rendered: layout and computed styles read correctly (that is where every
number above comes from) but a CSS transition never runs, and the 390 px
drawer's open state therefore could not be measured — it reported
`visibility: hidden` with the `drawer-open` class applied, which is the hidden
pane rather than the page. No CSS, template or rail code changed in this
release, and the 0.12.1 walk measured that drawer on a rendered page; the
overflow half of the check (390 exactly, no horizontal scroll, with and
without the drawer class) was measured here and is clean.

## The drawing on disk is untouched

`diagram.svg` does not appear in `git diff` — nothing in this release touches
the SVG — so the byte-identical Inkscape PNG hashes recorded by the 0.11.0 and
0.12.0 ships (`224d40b8…` at 1683 px, `b78f7692…` at 3366 px) still hold
without re-exporting.

## Gates

`pytest` 52 passed (48 plus four new), exit 0. `node --check` clean on
`diagram.js`. `git diff --check` clean. There is no ruff configuration in this
repository. The four new tests: the gauge warning in both its air and its gas
form, each proved twice with the only difference being whether the gauge is
switched on; the turbo warning, its stopped-turbo negative, and the
backing-line vent that the boundary rule keeps quiet; the quiet cases —
non-ionization gauges, a harmless press, closing a vent, and a second press
into standing air; and the route itself, including an aliased old id, three
shapes of junk refused with 400, and the stored state untouched by asking.

## Version

0.13.0 — a minor bump rather than a patch, because a warning before a press is
a new thing on the page — in `pyproject.toml`, `src/pihti/__init__.py`,
`README.md` and the three assertions in `tests/test_server.py`. Static files
changed (`plumbing.json`, `diagram.js`), so the bump is also what keeps a
browser that already saw 0.12.1 from serving stale copies against this
release's server.

## Not pushed, not deployed

Told not to push and not to touch the Pi, which crosses this repository's own
`.agents/README.md` (owner decision 2026-09-04). The commit sits on local
`master`, now seven ahead of `origin`. To get it live, in an ordinary
terminal:

```powershell
git -C "$env:USERPROFILE\Dropbox\20-Code\2024-interactive-diagram" push
```

then on the Pi: `git pull --ff-only` in `/home/pi/pihtivacuum`, `sudo
systemctl restart pihti`, and confirm `/version` says 0.13.0.

## Mail

Nothing posted to `code/2024-interactive-diagram`; nothing owed. The letter
that asked for both warnings was collected by the 0.12.0 ship, which recorded
them in `directions.md` instead of building them.

## Directions

The two warning items are pruned, having shipped. The vent-guide item stays,
now carrying the map's own answer as a proposal queezz can confirm with one
word, and the guides-read-the-prediction item stays blocked on it. One item was
added: whether a stopped pump should still be a wall.

## Usage receipt

Provider Anthropic, model Claude Opus 5. Task: commander run round 3: pihti
trio / Diagram warnings. Child agents: 0. Provider usage: unavailable — no
meter was shown to this session.
