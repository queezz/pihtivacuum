# Four configurations, a brighter seven, and pumps that say what they are doing (0.16.0)

Commander-dispatched ship in the coordinated PIHTI trio run, on the work
Windows PC, 2026-09-08 evening JST — queezz awake, reading each release in his
browser and sending corrections as letters. Eleven of them landed on the
drawing, and nearly all of them are his review of 0.15.0, shipped a few hours
earlier: the release answered him, and looking at it gave him the next round of
answers.

## The mail

| id | what he said | what happened |
| --- | --- | --- |
| `20260908-b429ce4b-2ad897` | the four configurations, named and ordered | the card offers exactly those four |
| `20260908-520505af-9047d4` | *Blank*, and the probe line split at the cross | built; the new segment is in the map |
| `20260908-76e09ee2-e322b2` | his 10:29 SVG, *Pipe open* a real connection | already adopted byte-identical in 0.15.0; verified again |
| `20260908-630efd50-e4c7ab` | "design nice, not color blind nice" | the ladder of weight retired; hue does the work |
| `20260908-92656592-3a679a` | "gas and rough vacuum are indistinguishable" | a new seven, checked pairwise in CIEDE2000 |
| `20260908-3308e02d-3021dd` | an open valve's edge is its fill | built |
| `20260908-aed40a4e-c9a286` | "rotary from bypass is pumping, but I see no gradient" | the second tone appears in every state now |
| `20260908-3688eabd-587dfe` | beacons obstruct; pumps should wear their state | both built |
| `20260908-cbf115b3-448390` | a second SVG for power and water | recorded as owner work; nothing built |
| `20260908-26182762-7cca25` | the black gas disc; open/closed valves inverted | already fixed in 0.15.0; verified, see below |
| `20260908-95db0d13-2d979c` | the gas symbol's size and paint order | already right in 0.15.0; verified, see below |

The five for the ship after this one — practice mode (`9d38bf34`, `e460b66f`),
the right-rail state card (`aa2558c2`, `50f93f77`) and the guide card's scroll
bar (`8853f919`) — were read so as not to build a corner, and left posted.

## A: the four line configurations

His own list, his own order: **Membrane installed**, **Pipe open**, **Blank**,
**Boron deposition**. The card builds its buttons from `plumbing.json` rather
than from the template, so the order and the labels live in one place, and each
carries a one-line meaning that the card's own *More* prints.

**Blank** is the new one. Vacuum-wise it is a membrane — the crossover is closed
at the flange — so it joins `membrane` in the linked valve's `closed_modes` and
connects nothing. What differs is the picture, and that needed the linked valve
to answer two questions instead of one: *is it shut* and *is a plug drawn*. So
`plug_mode` names the one configuration that draws a plug, and `flange_element`
names the segment that says the blank instead. Under *Blank* the probe
segment — `probe-pipe`, from the membrane position to the cross — wears
`#9aa7b5`, a light steel that is no state's colour and not the closed grey, and
the membrane position is drawn empty and dashed like every other
nothing-is-mounted case.

**The segment he split off was drawn but unmapped.** `probe-pipe-cross-to-GVBD`
existed in the SVG since his 10:36 save and was in no volume, so nothing
coloured it at all — it stayed black while the line either side of it was
painted. It is in `probe-line` now. The letter asked for it "in the volume the
adjacency says (the cross-to-GVBD segment belongs with the bypass side of the
cross; probe-pipe with the crossover/probe side)", and the honest answer to
that is one volume, not two: the cross joins all four segments and there is no
valve between them to split them at. The parenthetical describes which physical
side each segment is on, which is what the flange painting needed to know, and
that is exactly what it is used for. Written down here rather than silently
done differently.

The three-way meaning of the state is unchanged and measured live at each
configuration, on a rig with both sides pumped and every valve on both routes
open:

| configuration | narrow pipe | `probe-pipe` | `…-cross-to-GVBD` | plasma | QMS |
| --- | --- | --- | --- | --- | --- |
| Membrane installed | plasma HV | QMS HV | QMS HV | plasma HV | QMS HV |
| Pipe open | plasma HV | plasma HV | plasma HV | plasma HV | plasma HV |
| Blank | plasma HV | **flange `#9aa7b5`** | QMS HV | plasma HV | QMS HV |
| Boron deposition | plasma HV | QMS HV | QMS HV | plasma HV | QMS HV |

Only *Pipe open* joins the two vessels through the narrow pipe; the readout says
so and says nothing else in the other three.

**Old stored values are read through an alias table.** `resolve_line_mode` maps
a stored annotation through `line_configuration.aliases` on every read — the
live context, the replayed moment, and the press — and anything the map does not
recognise becomes `unknown` rather than a guess. `/operation-context` accepts
exactly the modes the map offers, so the list of buttons and the list of
accepted writes cannot drift apart.

## B: a brighter seven

Two letters wrote this. The first retired the constraint the 0.15.0 palette was
built under — *"I don't want muted, actually. No color blind people here...
design nice, not color blind nice. Tol inspired is still fine"* — and the second
said what had gone wrong without it: *"Gas color and rough vacuum color are
indistinguishable."*

They were: a plum at L\* 31 and an ochre at L\* 46, both warm, both dark. They
were dark because the old rule made all seven climb one ladder of weight, which
was the colour-vision aid, and under a luminance ceiling of about 0.2 a
seven-rung ladder crowds everything into the bottom. **That rule is gone.** Six
of the seven now sit at nearly one lightness and are separated by hue; chroma is
spent rather than saved.

| role | hex | L\* | C\* | Lab hue | on the stone `#e3dfd6` | on the green valve `#9bf08d` |
| --- | --- | --- | --- | --- | --- | --- |
| Air | `#c81d24` | 43.2 | 76.1 | 34 | 4.32 | 4.17 |
| Gas | `#a92a9c` | 42.0 | 71.1 | 332 | 4.51 | 4.36 |
| High vacuum, plasma side | `#1f5fd0` | 42.8 | 67.7 | 290 | 4.38 | 4.23 |
| High vacuum, QMS side | `#0e8a46` | 50.3 | 54.6 | 150 | 3.33 | 3.21 |
| Rough vacuum | `#a86a00` | 50.3 | 60.4 | 73 | 3.34 | 3.22 |
| Pumped, sealed off | `#00798f` | 46.5 | 28.3 | 225 | 3.82 | 3.69 |
| Isolated, unknown | `#7f7b75` | 51.8 | 3.8 | — | 3.16 | 3.05 |

Every pair, in CIEDE2000, the six closest:

| distance | pair |
| --- | --- |
| **21.3** | plasma high vacuum / pumped, sealed off |
| 23.0 | pumped, sealed off / isolated |
| 23.4 | rough vacuum / isolated |
| 25.1 | QMS high vacuum / isolated |
| 28.4 | gas / plasma high vacuum |
| 28.4 | air / rough vacuum |

**The smallest pair is 21.3** — the plasma blue against the sealed teal. The old
palette's smallest was **11.6**, and the pair he named by hand, gas against
rough vacuum, is now 90 degrees of hue and well clear of the six above.
`isolated` is still the quietest thing on the field, deliberately, and the only
grey: it is the absence of a claim rather than an eighth thing competing for the
eye.

What the floor cost, honestly: 3:1 against the stone field *and* against the gas
panel's green valve caps a colour's luminance at about 0.204, so none of these
is Tol's own lightness. They are that hue family darkened to the ceiling and no
further. No maxed primary and no greyish mud; the test asserts both.

The legend chips are full swatches now (26×16 rather than a five-pixel bar), and
the top of *More* carries the seven in a row on the drawing's own ground with
their names beneath, so they can be compared against each other rather than one
at a time against the drawing.

## C: an open valve has no black edge

*"I think I like the valves edge to be same color as the fill. When closed,
black border white fill is good. Stands out."* 0.15.0 had the fill right and the
outline still black, so the answer was half there. Now `predict()` gives an open
valve the same colour for fill and stroke, and a closed one white with an
explicit black outline, and both the page and `/state.svg` write it, so a saved
render cannot disagree with the screen.

Measured live on every valve the map knows, in a real browser: 30 of them, each
either `fill == stroke ==` the colour flowing through it, or `#ffffff` on
`#000000`. Same rule at every size, gas panel included.

## D: the second tone, corrected

*"Rotary from bypass is pumping, but I see no gradient."* Air and gas used to
return no contribution at all, which threw away the case worth a glance. The
dominant colour is unchanged — air, then gas, then the best pump, turbo before
rough — and the second tone is now **whatever else reaches the space that is not
the dominant thing**, in every state. One tone only, chosen in a written order:
a gas under vent air, then the best pump that is not already the dominant
reading, then the other vessel when the two chambers are joined.

His own case, staged and measured: the plasma vessel vented through the bypass
pumping line's vent valve with the roughing bypass still running gives
`volumes.plasma-vessel = air`, `mixes.plasma-vessel = rough-vacuum`, and the
cross filled `url(#pihti-mix-c81d24-a86a00)` — red into amber. Pipes stay one
colour; the four pipes leaving that vessel carry no `mix` at all.

## E: beacons that step aside, and pumps that say what they are doing

*"venting plasma works. But numbered circles are obstructing the
interactions."* The beacons already declared `pointer-events: none`, so the
press was never actually blocked — what was blocked was the **eye**: the disc
sat on the middle of the very valve the step was asking him to press, and a
valve you cannot see is a valve you cannot aim at. So the disc now stands at the
element's top-right corner, stepped 14 units further out along the diagonal away
from the shape's own middle, and a step's own authored `markerOffset` still
applies on top of that. Every part of a beacon says `pointer-events: none` now
rather than inheriting it, belt and braces.

Verified in the browser with *Vent Plasma* running: 11 beacons, every one of
them `pointer-events: none` on the group and on the disc, `elementFromPoint` at
each beacon's own centre returning the drawing underneath and never a marker.
Each of the eleven beaconed elements is hit at its own centre by its own id. And
every beaconed **valve** was pressed and pressed back with the guide
active — GVU, GVBU, GVBD, bypass-l2, the gas panel argon valve, the argon line,
the main gas line and the nitrogen valve — each one changing state and returning
to it.

**Pump on/off did not have to be added.** All five he named — TMPU, TMPD,
RoughU, RoughD and the bypass rotary — were already ordinary confirmed toggles
recorded in history like a valve, and `predict()` has always read them, so a
stopped turbo has never made high vacuum here. What was missing was the
*colour*. A running turbo now wears the high-vacuum colour of the side it
serves, which is a fact about the rig rather than about today's valves — new
`serves` in the map, so TMPU is the plasma vessel's turbo whether or not GVU is
open — a running rotary or scroll wears rough vacuum, and a stopped pump keeps
the yellow.

The yellow deserves a sentence. His letter said a stopped pump "stays as drawn
(yellow)"; the drawing's own fill is in fact grey, and yellow was what a
*running* pump wore before this release. It was read the way it was written, and
the result is good: yellow now means "not pumping", so a stopped turbo is the
loud thing rather than the quiet one, which is exactly what that sentence was
for. A directions item asks him to confirm it, with keeping it as the
recommendation.

Measured live: TMPU `rgb(31,95,208)`, TMPD `rgb(14,138,70)`, RoughU and RoughD
and the gas panel pump `rgb(168,106,0)`, the bypass rotary `rgb(255,255,0)`
because it was not running. Every pump keeps the black outline it was drawn
with.

## The two already answered

- `20260908-26182762-7cca25` — "injected nitrogen, got a black hole", and open
  valves white with closed ones coloured. Both were mid-build frames of the
  0.15.0 tree. Verified on 0.16.0: nitrogen into the plasma vessel draws one
  white disc with a thin dark rim and `N2` in dark inside the vessel, and the
  valve inks are the right way round — an open GVBD is green, a closed one is
  white. Collected.
- `20260908-95db0d13-2d979c` — the symbol's size and paint order. Verified: the
  disc is about a third of the vessel's width, centred in the authored
  `symbol_box`, painted above the vessel's state fill and below the guide
  beacons, several gases side by side and smaller. No square, no black.
  Collected.

## One defect found on the way, and fixed

The left rail overflowed its own box at 1280×700 — measured before any of this
release's own work: content 674 px in a 604 px rail with `overflow: hidden`, so
the last guide button and *Clear guide* were painted 70 px past the rail's
bottom edge and could not be reached. The fourth configuration button and the
new *More* would have made it worse. Both left-rail cards now use the
`rail-card--growing rail-card--fit` pattern the right rail's guide card already
had, with only the part inside `.scrolls` giving ground. After: `604/604`
exactly, both cards inside the rail's box, every control reachable, with the
*More* open and closed.

## Verify: scratch Perimeter Walk

`lab start pihti-diagram --port 48993 --host 127.0.0.1` under scratch
`LAB_CONFIG`/`LAB_RUNTIME_ROOT`/`LAB_LOG_ROOT`, every `PIHTI_*` write path
inside a marked `fleet-scratch-2024-interactive-diagram-round6` root in this
session's own temp — outside Dropbox — with a copy of the real state, context,
roster and log. Listener PID confirmed as the child of Lab's tracked PID. The
owner's `4186` was listening before and after and was never addressed; the Pi's
`5000` was never touched.

Screenshots taken for him to compare:

- **The four configurations, one by one**, with both sides pumped — the probe
  segment green under *Membrane installed*, blue under *Pipe open* and *Boron
  deposition*, and the steel `rgb(154,167,181)` under *Blank*, measured at each.
- **The seven swatches** in a row at the top of the legend's More, with the
  inline chips beside them.
- **GVBD open beside closed** — open, the whole probe line and cross above the
  QMS vessel are green and GVBD is green with no black edge; closed, everything
  above is grey and GVBD is the one white bowtie with a black rim.
- **A vented vessel with the rotary running** — the plasma cross red fading to
  amber, the vent line red, the bypass rotary amber.
- **Vent Plasma active with a beaconed valve pressed** — eleven beacons standing
  at their shapes' corners, GVU pressed underneath one of them.
- **A stopped turbo beside a running one** — TMPD yellow and the QMS vessel
  grey, TMPU blue and the plasma vessel blue.

The rest of the walk:

- **Rails at 76 px** at 0/25/50/75/100 % of the scroll range at 1440×900
  (range 144), 1280×1000 (range 0) and 1280×700 (range 223) — every reading
  identical, both rails. Document width 1425 at 1440 and 1265 at 1280: no
  page-width overflow. Left rail `804/804`, `904/904` and `604/604` — it fits
  its own box exactly at all three, with the More open.
- **At 390×844** the document is exactly 390 with no horizontal scroll, the
  drawer opens with all four configuration buttons and closes, the seven legend
  chips wrap, and the swatch row is 341 px inside a 390 px page.
- **Every top tab pressed** from the Vacuum page — History, Plot, Services and
  Vacuum itself — each landing at its own top with both rails at 76 px. Browser
  Back landed on Plot and Forward returned to Services.
- **History deep link** `?at=2026-09-08 11:43:20` opened cold and survived a
  true `location.reload()`: the same moment, the same two-tone plasma cross, the
  same `Ar`, the same green QMS vessel, the same blue TMPU.
- **The beacons under reduced motion** — this machine still answers *true* to
  `prefers-reduced-motion: reduce`, and with *Vent Plasma* selected the current
  step's ring measured `getAnimations().length` **1**, `animation-name`
  `marker-halo-quiet`, duration `2.4s`, `r: 26px`, and two frames a half period
  apart differing (opacity 0.24 → 0.78).
- **Teaching check**: the honesty sentence renders exactly once, "measure
  pressure" appears nowhere, each of the four legend sentences renders once,
  each of the four configuration meanings renders once, and no raw component key
  reaches the page.
- **Console clean** — not one message on any page or any press.
- `lab stop` killed the tree; the tracked PID is gone and port 48993 has no
  listener. Scratch root marked `superseded`.

## Gates

`pytest -q` 62 passed, exit 0. `node --check` clean on `diagram.js`. There is
no ruff configuration in this repository, and no `CHANGELOG.md`: this repository
records shipped work in `.agents/log/`, so this entry is the release note.

Four tests are new — the four configurations, the alias table, the pumps, and
the beacon placement — and the palette test was rewritten around CIEDE2000 and
a hue-family rule in place of the retired colour-vision ladder. Seven existing
tests were updated for the fourth configuration, the valve outline, the pump
inks and the corrected second tone.

## Version

0.16.0, then 0.16.1 for the pump correction below — a minor bump: a fourth configuration, a different palette, a new rule
for what a valve's edge and a pump's body look like, and a gradient that appears
where it never did. In `pyproject.toml`, `src/pihti/__init__.py`, `README.md`
and the three assertions in `tests/test_server.py`. Static files changed
(`plumbing.json`, `styles.css`, `diagram.js`), so the bump is also what keeps a
browser that already saw 0.15.0 from serving stale copies. `diagram.svg` is
untouched: his 10:36 save is still byte-identical to what is committed.

## Not pushed, not deployed

Told not to push and not to touch the Pi, which crosses this repository's own
`.agents/README.md` (owner decision 2026-09-04). The commit sits on local
`master`, now eleven ahead of `origin`. To get it live, in an ordinary terminal:

```powershell
git -C "$env:USERPROFILE\Dropbox\20-Code\2024-interactive-diagram" push
```

then on the Pi: `git pull --ff-only` in `/home/pi/pihtivacuum`, `sudo systemctl
restart pihti`, and confirm `/version` says 0.16.1.

## Mail

Eleven letters collected — `20260908-b429ce4b-2ad897`,
`20260908-520505af-9047d4`, `20260908-76e09ee2-e322b2`,
`20260908-630efd50-e4c7ab`, `20260908-92656592-3a679a`,
`20260908-3308e02d-3021dd`, `20260908-aed40a4e-c9a286`,
`20260908-3688eabd-587dfe`, `20260908-cbf115b3-448390`,
`20260908-26182762-7cca25` and `20260908-95db0d13-2d979c` — after their work was
recorded here. The five for the next ship stay posted, unread by this release's
code.

## Directions

The configuration question is closed by his own list, dated. The palette item is
rewritten for the seven he has not seen yet. Two are new: whether a stopped pump
should keep the yellow it now wears, and the second SVG for power and water,
which is his own hands' work and waits for a file in `local/`.

## Corrected an hour later: the pump yellow (0.16.1)

He read the release in his browser while this handoff was being written, and the
first thing back was the pump: *"No, no! Blue and yellow, yellow reads like on.
Gray for off was lost. Why? WHY???"* (letter `20260908-93fb84a6-5a69cf`). He is
right, and the mistake is traceable: the dispatching letter said a stopped pump
"stays as drawn (yellow)", the drawing's own fill is **grey**, and yellow was
the app's own *active* colour from `elementsConfig.json`. Reading the words
rather than checking the drawing turned the off signal into the on one.

Fixed in 0.16.1, and the fix is a deletion: a stopped pump now carries no ink
from this app at all. The prediction emits no fill and no stroke for it, the
pumps have no `colors` entry left in `elementsConfig.json`, `pump_idle` is gone
from the map, and both `/state.svg` and the page skip it — so his own grey
stands, untouched, which is what it always meant. A running pump is unchanged:
its side's high vacuum for a turbo, rough vacuum for a rotary or a scroll, over
the black rim he drew. The test asserts the word `yellow` appears nowhere in a
saved render.

**One trap on the way, worth writing down: clearing an inline fill deletes his
own.** The first attempt at leaving a stopped pump alone set
`element.style.fill = ""`, which looks like "put it back". It is not: his fill
lives in that very `style` attribute, so clearing the property removes it and
the shape falls through to the CSS default — every stopped pump came back
**black**, measured in the browser. The page now captures each shape's authored
fill once, before anything of ours has been written over it, exactly as it
already does for stroke widths, and writes that value back. `/state.svg` never
had the bug: it writes no rule for a stopped pump at all, so the authored style
survives untouched.

**And a second one, my own test loop rather than the app.** The version was
already bumped when the black pumps were measured, so the browser held the
previous `diagram.js` at the *same* `?v=0.16.1` URL and served it back after the
fix. The release-keyed cache was doing exactly what it is for; a check that
changes a static file twice under one version has to force the fetch
(`fetch(url, {cache: "reload"})`) before reloading, or it is measuring the file
it replaced.

Verified after the fix, in the browser: TMPU running `rgb(31,95,208)`, RoughU
running `rgb(168,106,0)`, and the four stopped pumps back on his own greys —
`#888888`, `#868686`, `#828282`, `#989898`. Stopping TMPU returns it to
`#979793`, its own authored fill, and restarting it turns it blue again. The
saved render writes no rule for a stopped pump and the word `yellow` appears
nowhere in it. Console clean.

## Five letters left posted for the next ship

Five more arrived in the same few minutes, and they are one coherent piece of
work rather than corrections that can be picked off:

- `20260908-fe94c769-493d71` — **sealed off means pumped, then closed and
  holding.** The pipe between a running turbo and its closed gate is *high
  vacuum* in that turbo's side colour, not sealed; *sealed off* becomes a
  **remembered** state, kept per volume in the state file with the time it
  became isolated, restored on load and replayable from history, and *isolated,
  unknown* is left only for a volume that has no remembered state at all. It
  also has to work inside the practice mode the next ship builds.
- `20260908-425e4cdb-09c038` — the frame that found it; superseded by the above.
- `20260908-e2498698-5c9c50` — a stopped pump's rim and inner lines go dark grey
  as well, so the whole pump recedes.
- `20260908-8eaaa7a9-334955` and `20260908-e6ada507-7aa064` — the gas mark
  inside the QMS vessel is oversized, and H2 and O2 want a real subscript.

Only the pump colour was acted on here, because it was an isolated correction to
a line shipped an hour earlier. The rest was left posted deliberately: doing half
of the sealed-off letter would ship a legend colour that nothing on the drawing
can ever be in, and that is a worse release than an honest handoff.

## Usage receipt

Provider Anthropic, model Claude Opus 5. Task: commander run round 6: pihti trio
/ Diagram configurations, palette, pumps. Child agents: 0. Provider usage:
unavailable — no meter was shown to this session.
