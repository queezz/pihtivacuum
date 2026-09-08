# Seven colours, a valve that says so, and his own drawing (0.15.0)

Commander-dispatched ship in the coordinated PIHTI trio run, on the work
Windows PC, 2026-09-08 late morning JST — queezz awake and reading every
release in his browser. Eight letters from `code/fleet`, all his own words
relayed by the Commander, all about one thing: at a glance, the drawing was
telling him something that was not true.

> "GVU is closed, so TMP is not pumping plasma-vacuum. Yet at a glance it
> seems that it does."

## The mail

| id | what he said | what happened |
| --- | --- | --- |
| `20260908-c8ef7df5-5f5e40` | his updated SVG; the upstream IG moved to the gauge manifold | adopted; the map follows the drawing; the widening switched off by default |
| `20260908-a8d13202-c3830f` | "membrane installed to open pipe is VERY slow" | measured again and made one request instead of three |
| `20260908-6819c50d-04e4ba` | rules for forevacuum / upstream HV / downstream HV; a colour-blind-safe palette | seven colours, the vessel rule, the closed-valve break |
| `20260908-06105d79-6b7535` | "didn't see that GVBD open! And that's the issue!"; small valves too quiet | the prediction was left alone; a valve now says its position with its body |
| `20260908-7c9a8993-de36fd` | two high-vacuum colours; the gas symbol drawn inside the vessel | both built |
| `20260908-bb4311d6-04a3c1` | mixing as a gradient | built, then narrowed by the next letter |
| `20260908-e2278db6-6b3f89` | "we have shapes in all important places" | mixing on the shapes only; pipes wear one colour |
| `20260908-24449dc3-962775` | seams where stems meet pipes | round caps and joins; measured, and no SVG edit is needed |

The four letters for the ship after this one — practice mode
(`9d38bf34`, `e460b66f`) and the right-rail state card (`aa2558c2`,
`50f93f77`) — were read so as not to build a corner, and left posted.

## A: his drawing, adopted

`local/diagram-update.svg` copied over `src/pihti/static/diagram.svg`; the two
are byte-identical (`4b2cc2dc…`). Checked before anything was built on it:

- **190 ids each way, and the same 190.** Nothing added, nothing dropped,
  nothing renamed.
- **Every named pipe is still in its `pipes-*` group.** Every id
  `plumbing.json`, `elementsConfig.json`, `operationGuides.json`, `diagram.js`
  and `history.js` refer to still exists. Each gauge stem is still the element
  drawn immediately before its own gauge inside the same parent, which the
  suite asserts.
- **Six elements moved, and only six.** The group `g8` — the ionization gauge,
  its stem and its label — moved by `translate(-72.49, 65.01)`; the single
  gauge and the upstream Baratron shifted 12 px down with their labels; the
  plasma vessel's gauge manifold grew 6 px upward to meet the newcomer.
  Everything else in the file is identical.

**The upstream ionization gauge is `bypass-ionization-gauge`**, and it now
reads `plasma-vessel` rather than `bypass-manifold`. Its own drawn stem runs
from y 157.8 to y 186.9 at x 422.9, and the plasma vessel's gauge manifold runs
down the same x from y 171.0 — they overlap, so the gauge really does hang on
that manifold. Its id and its stem id are unchanged, because an id is queezz's
to rename and this was a move; the name a person reads is now **"Upstream
ionization gauge"**, his own word for it, so the vent guide no longer says
"bypass" while pointing at the plasma vessel. **The bypass manifold is left
with one gauge and no ionization gauge at all:** `bypass-absolute-gauge`, the
Ulvac both pump-down guides already send you to read. The standing directions
question — whether the plasma vessel carries an ion gauge the drawing did not
show — is closed by that move, and the 0.13.0 gas-or-air warning now fires for
the plasma side, which it never could before.

**One correction to the letter, honestly.** It said his strokes were "now
4 px". They are not changed at all: the width table is identical in the two
files — 4 px on the vessels, the bypass manifold, the probe line and the QMS
ports; 3.78 px (1 mm) on most vacuum pipe; 2 px on gas tubing. The instruction
that followed from it — widening off by default — was carried out anyway,
because it is his own geometry either way and it is one press to undo: More →
*Draw coloured pipes wider*. `plumbing.json` keeps `band = 1.6` as what the
switch offers and `band_default = false`. If he liked 0.14.0's wider pipes,
that switch is the whole answer, and the standing directions item that asks him
to judge the drawing with the band off is now answered by simply opening it.

## B: the slow configuration switch

Measured on this build, in a real browser, with a `MutationObserver` rather
than a timer — the first attempt used `setTimeout` polling in a hidden pane and
reported a flat ~1000 ms, which is the browser's background-tab clamp and not
the app at all. Worth writing down: **a hidden Browser pane clamps timers to
about a second, so any measurement made with `setTimeout` in one is measuring
the clamp.**

With the pane fronted, from the click to the last style change on the drawing:

| gesture | measured |
| --- | --- |
| Line configuration press (`Membrane installed` ↔ `Pipe open`), 4 runs | **10, 11, 11, 12 ms** (≈24 mutations each) |
| First visible change of the membrane symbol, 6 runs | 7–16 ms |
| Valve press (GVU, GVBD, bypass-vcr-u), 6 runs | **9, 9, 10, 10, 10, 11 ms** |

Well under the quarter second asked for. What was still there to fix was the
*shape*, not the local number: the press cost three round trips — the write,
then a full re-read of `/elements-state`, then `/predicted-vacuum`. On loopback
that is 10.4–11.3 ms against 4.8–9.7 ms for one; over the LAN to the Pi it is
three round-trip times against one. So `/update` and the `/operation-context`
write now answer **with the new prediction**, and the page repaints from the
answer that made the change. `/predicted-vacuum` is unchanged and still answers
the five-second refresh and every `?at=` replay.

For the Pi's sake, the server's own share of that: `/predicted-vacuum`
2.4–3.0 ms per call including the round trip, `/press-warnings` 2.3–3.2 ms.
The walk is a few hundred dictionary lookups; no file is read and the drawing
is never parsed.

## C: seven colours

**The field is unchanged** — `#e3dfd6`, the warm stone of 0.12.0. Clearing 3:1
against it caps a colour's own luminance at about 0.21, which is why none of
these is its source palette's own lightness: they are Tol's and Okabe-Ito's
hues, darkened as far as the field demanded and no further.

| role | hex | source | contrast on `#e3dfd6` | luminance |
| --- | --- | --- | --- | --- |
| Air | `#701225` | Tol muted wine, darkened | **8.76** | 0.040 |
| Gas | `#752f69` | Tol muted purple, darkened | **6.67** | 0.068 |
| High vacuum, plasma side | `#005e92` | Okabe-Ito blue, darkened | **5.24** | 0.101 |
| High vacuum, QMS side | `#117733` | Tol muted green, unchanged | **4.26** | 0.136 |
| Rough vacuum | `#936500` | Okabe-Ito orange, darkened | **3.85** | 0.155 |
| Pumped, sealed off | `#6d7786` | cool neutral | **3.41** | 0.182 |
| Isolated, unknown | `#7f7b75` | warm neutral, kept from 0.12.0 | **3.16** | 0.200 |

They also climb one ladder of weight in that order, air darkest and isolated
lightest, so two of them differ by hue *and* by how heavy they look. Seven
colours under a luminance ceiling of 0.21 cannot climb in big steps — the
smallest is 1.08 — so the ladder is a second signal rather than the main one,
and the main one is measured: **every pair is compared again through simulated
protanopia and deuteranopia** (Viénot's transform, then CIE L\*a\*b\*), and the
closest pair anywhere is **14.0** units apart. The test in the suite does that
arithmetic, so none of this is anyone's eye. The one honest weakness:
tritanopia, which is very rare, brings air and gas close (4.9); they still
differ in weight by 1.31, and a vessel holding gas now carries its bottle
symbol, which no colour distance can take away.

**Where the colours come from.** Three rules, all in `predict()`:

1. **A high-vacuum volume takes its colour from the vessel it is joined to.**
   Plasma side or QMS side, and the map says which by naming a `high_vacuum`
   colour on each vessel. A turbo-pumped volume that reaches *no* vessel —
   exactly the pipe from a closed GVU up to a spinning TMPU — is the seventh
   colour, *pumped, sealed off*, which is neither vessel's. Measured live with
   the plasma vessel roughed through the bypass and GVU shut: the vessel
   `rgb(147,101,0)`, the turbo line `rgb(109,119,134)`. That is the glance he
   reported, and it now reads correctly.
2. **A valve says its position with its own body.** Open, it wears the colour
   running through it; closed, it is white, so the colour visibly stops on both
   sides. This crosses `AGENTS.md`'s own rule that valve fills are operational
   state and never pressure-domain colours — the rule is amended at its source
   with the two letters that overrode it and the reason it existed. Only valves
   moved: pumps stay yellow when running, gauges and the gas bottles keep
   theirs, every valve keeps the black outline he drew, and
   `elementsConfig.json` keeps every valve's `colors` entry. One consequence
   worth knowing: `diagram.js` used to decide a press by reading the element's
   own fill, which no longer says whether it is open, so it reads the recorded
   state instead.
3. **Mixing shows on the shapes and nowhere else.** The dominant state is the
   best pump reaching the volume — turbo before rough, with gas and air beating
   both — and the contributing one is painted as a two-stop gradient across the
   drawn body only: the plasma cross, the two bypass tees, the probe cross, the
   QMS box. A pipe wears one colour. Two cases produce it: a rough pump
   reaching a turbo-pumped volume (blue body, amber contribution) and the two
   vessels joined (plasma blue leading, QMS green contributing — `rank` in the
   map says which leads, and it is the plasma vessel).

**Gas symbols.** A vessel whose predicted state is gas carries the bottle
symbol drawn large inside it — `Ar`, `O2`, `H2`, `He`, `N2` — one white circle
with a black rim per gas, the same sign the bottles wear. The symbol is written
beside its bottle in the map rather than derived from the gas's name. Where it
may stand is written beside the vessel as a `symbol_box`, because the plasma
vessel is a cross and the middle of its bounding box is not the middle of
anything a circle fits in; a test proves each box really lies inside the shape
it names, and a box that has wandered draws nothing rather than a symbol
floating in the wrong place.

**One rule had to bend, and it is written down.** Since 0.12.1 a pipe with a
barrier partway along it may only claim a state both its sides agree on. With
high vacuum split in two, both sides of a membrane-installed crossover would
"disagree" the moment both vessels were pumped, and the line would go grey —
claiming *less* than the truth. Sides of the same *kind* are now allowed, and
the line takes whichever the map lists first, which is the plasma side. Sides
of different kinds still read isolated, exactly as before.

**The saved render matches the page.** `/state.svg` writes the valve inks, the
round caps and joins, a `<defs>` with the gradients a two-tone body points at,
and the gas symbols — placed from the same authored box, with a small
path-bounding-box reader that understands only the `M m H h V v Z z` subset the
five bodies are drawn with and returns nothing for anything else. `?wide=1`
matches a browser whose widening switch is on; off is the default on both
sides, so they agree without asking.

## D: the seams

Round caps and joins are set on every line and body the prediction paints —
inline on the page and in `/state.svg`, so exactly the painted set and nothing
of queezz's own drawing that we do not colour.

Then every endpoint was measured rather than eyeballed: for each of the 52
painted lines, the distance from each end to the nearest drawn shape, against
half its own stroke (which is how far a round cap reaches). **Four endpoints
looked short and none of them is.** Each lands *inside* the filled body it
meets, which a distance-to-outline measurement cannot see:

| endpoint | meets | apparent gap | really |
| --- | --- | --- | --- |
| `bypass-manifold-upstream-t-to-pipe` | `bypass-manifold-t-upstream` | 9.7 px | inside the tee's fill |
| `qms-vacuum-gauges-port` | `qms-vacuum` | 6.8 px | inside the vessel |
| `bypass-manifold-main` | `bypass-manifold-t-downstream-t` | 3.8 px | inside the tee's fill |
| `qms-vacuum-upstream-port` | `qms-vacuum` | 2.6 px | inside the vessel |

Every other endpoint either touches its neighbour or stops at a valve, where
the gap is drawn on purpose. Confirmed by eye at 1440×900 on the exact close-up
he photographed — the CC/Pi and Baratron stems meeting the gauge manifold, with
the moved IG above them — and at the two bypass tees and the QMS vessel.
**So there is nothing for him to redraw: no SVG edit is needed.**

## Verify: scratch Perimeter Walk

`lab start pihti-diagram --port 48991 --host 127.0.0.1` under scratch
`LAB_CONFIG`/`LAB_RUNTIME_ROOT`/`LAB_LOG_ROOT`, every `PIHTI_*` write path
inside a marked `fleet-scratch-2024-interactive-diagram-colours` root in this
session's own scratchpad — outside Dropbox — with a copy of the real state,
context, roster and history files. Listener PID 9284 confirmed as the child of
Lab's tracked PID 36232. The owner's `4186` was listening before and after and
was never addressed (its PID changed on his side mid-session, which is his own
service restarting); the Pi's `5000` was never touched.

Screenshots taken at 1440×900 for him to compare:

- **GVBD closed** — QMS vessel green, plasma vessel amber through the roughing
  bypass, GVBD white. This is his own second screenshot, and the prediction
  agrees with it exactly, as the amendment letter asked.
- **GVBD open** — GVBD `rgb(17,119,51)` and the whole probe line and cross
  above the QMS vessel green with it. The two frames side by side are the
  arm's-length test.
- **GVU closed with the bypass open** — plasma vessel `rgb(147,101,0)`, the
  TMPU line `rgb(109,119,134)`, GVU white. Three different things, three
  different colours.
- **A rotary opened into the turbo-pumped plasma volume** — the cross filled
  `url(#pihti-mix-005e92-936500)`, blue into amber, with every pipe on the
  single blue.
- **GVBU and GVBD open together** — both vessel bodies and both bypass tees on
  `url(#pihti-mix-005e92-117733)`, and the readout saying "Open to the QMS
  vessel."
- **Argon into the plasma vessel** — one large `Ar` circle inside the purple
  vessel; with nitrogen too, `Ar` and `N2` side by side.
- **The beacons, under reduced motion** — this machine still answers *true* to
  `prefers-reduced-motion: reduce`, and with *Vent Plasma* selected the current
  step's ring measured `getAnimations().length` **1**, `animation-name`
  `marker-halo-quiet`, duration `2.4s`, `fill: none`, `r: 26px`; two frames a
  half period apart differ, opacity `0.9` → `0.12`, and the dark rings are
  plainly there in the first and gone in the second.

The rest of the walk:

- **Rails at 76 px** at 0/25/50/75/100 % of the scroll range at 1440×900
  (range 141, left x20, right x1149), 1280×1000 (range 0) and 1280×700
  (range 220) — every reading identical, both rails, and no rail card paints
  outside its own box. Document width 1425 at 1440 and 1265 at 1280: no
  page-width overflow.
- **At 390×844** the document is exactly 390 with no horizontal scroll; the
  seven legend chips wrap to three rows and the drawer opens and closes.
- **Every top tab pressed**, including Vacuum from inside Vacuum, each landing
  at its own top with rails at 76 px. Browser Back landed on Services and
  Forward returned to Vacuum with the gas symbols still drawn.
- **History deep link** `?at=2026-09-08 11:02:51` opened cold and survived a
  true `location.reload()`: the same moment, the same purple vessel, the same
  `Ar` and `N2`, the same white GVU, the same two readout lines.
- **The widening switch**: off by default (`3.77953px`), on gives `6.04725px`,
  off again restores it, and `localStorage` carries the choice.
- **A press still works end to end**: GVU, GVBD and a small VCR pressed and
  pressed back, `/elements-state` following each time.
- **All four guides** selected and read, with 11, 5, 13 and 9 beacons placed.
- **Teaching check**: the honesty sentence renders exactly once, "measure
  pressure" appears nowhere, and each of the three new sentences — the filled
  body, the two-tone body, the two valve inks — renders once.
- **Console clean** — not one message on any page or any press.
- `lab stop` killed the tree; PIDs 36232 and 9284 are gone and port 48991 has
  no connections at all. Scratch root marked `superseded`.

## Gates

`pytest` 58 passed, exit 0. `node --check` clean on `diagram.js`. `git diff
--check` clean. There is no ruff configuration in this repository, and no
`CHANGELOG.md`: this repository records shipped work in `.agents/log/`, so this
entry is the release note.

Five tests are new: the closed gate that never lends its turbo's colour to the
vessel; a valve saying its position with its own body, at both sizes and for
every valve in the map; mixing on the shape and never on the pipe, through the
prediction, the CSS and the gradient markup; the gas symbols, their authored
boxes and the guard that catches one that has wandered outside its shape; and
the one-request change on both routes. The palette test was rewritten to
compute contrast, the ladder of weight, and every pair's separation under
simulated protanopia and deuteranopia. Nine existing tests were updated for the
seven states, the moved gauge, the valve inks, and the widening now being off.

## Version

0.15.0 — a minor bump: seven colours, a new rule for what a valve looks like,
gas symbols and the adopted drawing are all user-visible. In `pyproject.toml`,
`src/pihti/__init__.py`, `README.md` and the three assertions in
`tests/test_server.py`. Static files changed (`diagram.svg`, `plumbing.json`,
`elementsConfig.json`, `styles.css`, `diagram.js`), so the bump is also what
keeps a browser that already saw 0.14.0 from serving stale copies.

## Not pushed, not deployed

Told not to push and not to touch the Pi, which crosses this repository's own
`.agents/README.md` (owner decision 2026-09-04). The commit sits on local
`master`, now nine ahead of `origin`. To get it live, in an ordinary terminal:

```powershell
git -C "$env:USERPROFILE\Dropbox\20-Code\2024-interactive-diagram" push
```

then on the Pi: `git pull --ff-only` in `/home/pi/pihtivacuum`, `sudo systemctl
restart pihti`, and confirm `/version` says 0.15.0.

## Mail

Eight letters collected — `20260908-c8ef7df5-5f5e40`, `20260908-a8d13202-c3830f`,
`20260908-6819c50d-04e4ba`, `20260908-06105d79-6b7535`,
`20260908-7c9a8993-de36fd`, `20260908-bb4311d6-04a3c1`,
`20260908-e2278db6-6b3f89` and `20260908-24449dc3-962775` — after their work
was recorded here. The four for the next ship stay posted, unread by this
release's code.

## Directions

The ion-gauge question is closed by the move itself, in his own hand. The
wide-pipes item is rewritten as a judgement of the seven colours with the
widening now off, which is the state that item asked him to look at. One new
item: whether the moved gauge's id should be renamed in the drawing to match
where it now hangs — nothing is broken by it, and an id is his. Everything else
stands.

## Usage receipt

Provider Anthropic, model Claude Opus 5. Task: commander run round 5: pihti
trio / Diagram colours and SVG. Child agents: 0. Provider usage: unavailable —
no meter was shown to this session.
