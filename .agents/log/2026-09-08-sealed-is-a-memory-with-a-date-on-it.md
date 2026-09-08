# Sealed is a memory with a date on it, and a stopped pump recedes (0.17.0)

Commander-dispatched ship in the coordinated PIHTI trio run, on the work
Windows PC. This one **resumed a ship that a provider rate limit cut off
mid-sentence**, and the first job was reading what it had left behind.

## What the cut-off ship left, and what was kept

It had committed nothing. The worktree held 755 added and 119 removed lines
across four files — `plumbing.py`, `server.py`, `plumbing.json`,
`test_server.py` — and no handoff. Read whole, it turned out to be the honest
backend half of all four letters, written carefully and stopped mid-test: the
suite failed on exactly two stale assertions it had not reached, and nothing in
it contradicted the mail.

**All of it was kept.** Nothing was reverted. What was checked before trusting
it:

- The six pump `parts` lists are new ids in the map, and a guessed id here would
  grey out the wrong shape. Every one of the twenty exists in `diagram.svg`, and
  every one sits inside or on its own pump's 40-unit circle — measured, not
  assumed. They are siblings of the pump body rather than children of it, which
  is why the map has to name them at all: a group's stroke cannot reach a child
  that carries its own inline one.
- `_gas_symbols` carried a `plumbing` argument it never used. Dropped.
- `duration_words` stepped from weeks to months at nine weeks, so 31 days read
  as "4 weeks". queezz's own sentence is "the downstream was under air for a
  month", so the step moved to thirty days.

Then the two stale assertions were corrected — a stopped pump *does* now write a
stroke rule into `/state.svg`, and the turbo stub is `upstream-high-vacuum`
rather than the retired `sealed` — and the whole front half, which the cut-off
ship never reached, was written.

## A: sealed off is a remembered, dated state

queezz took the seventh colour back the same evening it shipped (letters
`20260908-fe94c769-493d71` and `20260908-2c3d9837-37ab4a`): *"between the turbo
and its gate, the vacuum is High, not pumped sealed off. Not sealed. Pumped
sealed off means I pump, close the valve. Vacuum holds, and degrades per the
vessel's leak rate."*

So **the teal is gone from the map**, six states remain, and:

- A volume with a running pump on it is that pump's state now. The stub between
  a shut gate and its spinning turbo is high vacuum in that turbo's own side
  colour — from `serves`, a fact about the rig — and a running rotary's line is
  rough. What says the colour stops at the gate is the gate: white, with the one
  black rim on the drawing.
- An isolated volume that **remembers** something wears the colour of what it was
  last under, hatched, and the readout says what and for how long. `isolated`
  grey is left only for a volume with no memory at all.

### The memory's shape

Under `_volumes` in `elements_state.json`, beside the valve positions, one entry
per volume: `{state, since, symbols}`. `state` is the last non-isolated verdict,
`since` is the moment it became isolated (`null` while something still reaches
it), `symbols` are the bottle marks if that state was gas — so a closed vessel
full of nitrogen still draws its N₂.

Three properties were built for on purpose:

- **It never re-stamps.** "Since when" means since it was closed, not since the
  last time anybody looked. Proved by a test that updates twice a day apart.
- **It is derivable, not only stored.** A state file can be new, copied to
  another machine, or older than the log beside it. `memory_timeline` replays
  every recorded press from the beginning through the same predictor, cached
  against both logs' mtime and size, so one walk serves a page that asks about
  ten historical moments. A replayed *moment* reads the memory as it stood
  **then**, so a history deep link says how long a vessel had been shut by that
  moment rather than by today.
- **It is an argument, never a file read.** `predict(plumbing, state, mode,
  memory=…, now=…)` is still state in, prediction out, so the practice mode the
  next ship builds can run the same predictor over its own local copy of both.
  `now` is the clock for the same reason: a test advances it rather than waiting
  a fortnight.

`_volumes` is not an element id and never will be — every id on the drawing comes
from Inkscape and none starts with an underscore — and `/elements-state` still
answers with valve positions alone, so no page has to know to skip it.

### The thresholds, said out loud

They live in `plumbing.json` under `hint_thresholds`, and here is why each one is
what it is:

| threshold | days | why |
| --- | --- | --- |
| `bake_air_days` | 2 | air brings water vapour in; it is the shortest for that reason |
| `bake_gas_days` | 7 | dry nitrogen does not, so it buys a week |
| `fresh_vacuum_days` | 3 | how long a vacuum stays fresh enough that opening the turbo straight in may be fine |

The readout names **that vessel's own gauges** from the map and gives his own next
move: under air or nitrogen past its threshold, "Consider baking"; under vacuum,
whether the turbo may open straight in or it is safer to rough through the
bypass. The pump-down guides' own question — *which of the two ways* — is
answered from the same memory: `way` is `bypass` while the turbo is still
spinning behind its shut gate, `gate` once it is stopped.

### The hatch, and why not a lighter treatment

His letter offered either. A lighter treatment cannot hold the palette's own 3:1
floor against the stone field — lightening the six by 20 per cent toward white
drops the QMS green to 2.42 and rough vacuum to 2.38, measured — so a hatch was
chosen: stripes of the drawing's own ground cut through the state colour at 45
degrees, every coloured pixel at full strength, one mechanism for a filled body
and a drawn line alike. The page builds the pattern from the same three numbers
in the map that `/state.svg` builds it from, so a saved render and the screen
cannot disagree.

**One thing for queezz's eye, and it is his call.** On a rig that is sitting
fully shut down, a great deal of the drawing is now hatched — 47 of 113 painted
elements in the frame this session measured, where all of it used to be one quiet
grey. That is exactly what his letter asks for, and it may still be louder than
he wants. A directions item asks him to look.

## B: the whole stopped pump recedes

*"In diagram, we can also gray out pump edges and lines. Dark gray. So it speaks
more loudly that that is closed."* A stopped pump keeps his own grey body — the
app still writes it no fill — and its rim and inner symbol lines go `#5f5f5f`; a
running one keeps the black rim and lines he drew, over its state colour.

Measured live: TMPU running `rgb(31,95,208)` with a black rim and black inner
lines; TMPD stopped on his own `#888888` with rim and inner lines at
`rgb(95,95,95)`. The page writes the parts' **stroke only** — their fill and
their dashes are his, and `path9368` really does carry an authored dash array
that clearing would have destroyed.

## C and D: the marks

**Size.** *"The qms-vacuum gas circle is bigger for some reason."* It was one
absolute size in both vessels, which is nearly the whole width of the narrower
QMS box. The diameter is now 0.45 of the **smaller side** of the body it sits in,
capped at the widest chamber's own mark, and smaller again with several gases in
a row. Measured: both vessels 13.28 with one gas; the QMS box 10.45 with three.
The radius travels with the mark from the prediction, so the page and a saved
render cannot size one differently.

**Subscript.** H₂, O₂, N₂ are drawn as an SVG `tspan` dropped by 0.22 of the
mark's radius at 0.62 of its size — never a Unicode subscript glyph a font may
lack. Measured in the browser at the plasma size: `N` at 11.95px with `2` at
8.23px, its box sitting below the letter's. In the legend and the readout the
same formula is written with an ordinary HTML `<sub>`.

## One defect found on the way

The readout's colour chips had been drawing **empty** since 0.16.0. Their colour
went on an `<i>` inside the swatch — a leftover from the thin-bar chip the
legend replaced with a full swatch — and that `<i>` has had no CSS rule since.
The colour goes on the swatch itself now, as it does in the legend, and a test
asserts nothing writes an `<i>` inside a swatch any more.

A second, smaller one, and worth writing down: the swatch colour is written as
`style.backgroundColor`, never the `background` shorthand. The shorthand resets
`background-image`, which is where the hatch lives, and an inline shorthand beats
the stylesheet.

## A wording correction the walk forced

The first build printed the whole three-sentence advice under *each* vessel. With
both vessels in the same state that is the same paragraph twice on one screen —
Fleet `WEBUI.md`'s "textbook in disguise" exactly. The hint now comes back in
pieces (`advice`, `gauges`, `bake`) and the page joins them into **one** sentence
naming that vessel's own gauges, so the two lines differ by their own equipment
rather than repeating a lecture:

> Plasma vessel — sealed, was high vacuum, 3 days. Read the upstream single
> gauge, upstream Baratron and upstream ionization gauge; then rough through the
> bypass rather than opening the turbo straight in.

## Verify: scratch Perimeter Walk

`lab start pihti-diagram --port 48994 --host 127.0.0.1` under scratch
`LAB_CONFIG`/`LAB_RUNTIME_ROOT`/`LAB_LOG_ROOT`, every `PIHTI_*` write path inside
a marked `fleet-scratch-2024-interactive-diagram-round7` root in this session's
own temp — outside Dropbox — with a copy of the real state, log, context and
roster. Listener PID confirmed as the child of Lab's tracked PID both times it
was started.

Screenshots taken for him to compare:

- **GVU closed with TMPU running** — the turbo blue with its black rim, the stub
  between them solid blue (`rgb(31,95,208)`), the gate the one white shape with a
  black rim, both vessels hatched blue and the readout saying *sealed, was high
  vacuum, 3 days* with each vessel's own gauges.
- **The plasma vessel vented with nitrogen and shut** — magenta hatched, the N₂
  mark still drawn inside it with its subscript, *sealed, under nitrogen*.
- **A stopped pump beside a running one** — a running rough pump in ochre with a
  black rim beside four stopped pumps on his own greys with `#5f5f5f` rims and
  inner lines.
- **Three gases in both vessels** — H₂, O₂ and Ar at 13.28 in the plasma cross
  and at 10.45 in the narrower QMS box, subscripts legible at both sizes.
- **The seven swatches** in a row at the top of More, the seventh the hatch, and
  the inline chips beside them.

The rest of the walk:

- **Rails at 76 px** at 0/25/50/75/100 % of the scroll range at 1280×700 (range
  304), 1280×1000 (range 4) and 1440×900 (range 185) — every reading identical,
  both rails, and both fit their own box exactly: `604/604`, `904/904`,
  `804/804`. Document width 1265 at 1280 and 1425 at 1440: no page-width
  overflow.
- **At 390×844** the document is exactly 390 with no horizontal scroll, the two
  drawers open, the seven legend chips wrap, and the readout rows sit at 340 px
  inside a 390 px page.
- **Every top tab pressed** — History, Plot, Services and Vacuum — each landing
  at its own top with both rails at 76 px. Browser Back landed on Plot and
  Forward returned to Services.
- **A history deep link** `?at=2026-09-08 11:44:02` opened and survived a true
  `location.reload()`: the same replayed memory both times, *sealed, under argon*
  on the plasma vessel and *sealed, was high vacuum* on the QMS one. That is the
  letter's own fourth test, proved in a browser rather than only in pytest.
- **The beacons under reduced motion** — this machine still answers *true* to
  `prefers-reduced-motion: reduce`, and with a guide running the current step's
  ring measured `getAnimations().length` 1, `animation-name` `marker-halo-quiet`,
  duration `2.4s`, `r: 26px`, and three samples across the period differing:
  opacity 0.418 → 0.619 → 0.401.
- **A beaconed valve pressed and pressed back** — `elementFromPoint` at a
  beacon's own centre returns the drawing underneath, never a marker; every part
  of every one of the eleven beacons computes `pointer-events: none`; a real
  click at GVU's own centre opened it (magenta fill *and* edge) and a second
  closed it (white on black).
- **Teaching check**: the honesty sentence renders exactly once, "measure
  pressure" appears nowhere, each state's meaning renders once, the hatch
  sentence renders once, and no raw component key reaches the page beyond the rig
  designations his own labels carry in brackets.
- **Console clean** — nothing on a fresh load with a guide running. The only
  console errors seen all session were a connection-refused burst while the
  scratch service was deliberately restarted, and one 404 on `/logs` from this
  session's own exploratory fetch, not from the page.
- `lab stop` killed the tree; the tracked PID is gone and port 48994 has no
  listener. Scratch root marked `superseded`.

**Two things to say plainly about the owner's own services.** The Pi's 5000 was
never addressed. His 4186 was listening before and after and was never started,
stopped, or controlled — but its PID changed from 10828 to 20604 during the
session, and the honest answer is that this session does not know why. The only
contact of any kind was the scratch Services page's own read-only health GET,
which cannot restart anything; he was awake and reading releases at the time.

## Gates

`pytest -q` 69 passed, exit code 0 captured explicitly. `node --check` clean on
`diagram.js`. There is no ruff configuration in this repository, and no
`CHANGELOG.md`: this repository records shipped work in `.agents/log/`, so this
entry is the release note.

Seven tests are new — the sealed vessel and its high-vacuum stub, the nitrogen
memory, the fake clock and the thresholds, the fresh-versus-replayed record, the
state file's own shape, the mark sizing, and the subscript. Five existing tests
were updated for the retired seventh state, the recessed pump edges, and the
legend's new chip.

## Version

0.17.0, a minor bump: a state that is remembered rather than derived, a new file
shape inside `elements_state.json`, a marking nothing on the drawing wore before,
and a colour retired from the map. In `pyproject.toml`, `src/pihti/__init__.py`,
`README.md` and the three assertions in `tests/test_server.py`. Static files
changed (`plumbing.json`, `diagram.js`, `styles.css`), so the bump is also what
keeps a browser that already saw 0.16.1 from serving stale copies.
`diagram.svg` is untouched.

**Two commits, and why not the four the packet asked for.** The dispatch asked
for A to land on its own before B to D, so a second cut-off would lose less. A
and B are not separable in this tree: the cut-off ship had written them into the
same functions of `plumbing.py`, the same `drawing` block of the map, and the
same test — splitting them would have meant hand-cut patches on a Dropbox-synced
index and an intermediate commit that was not green. So the whole body went in as
one commit **as soon as the gates passed and before the browser walk**, which is
what the instruction was for, and the walk's own correction is the second.

## Not pushed, not deployed

Told not to push and not to touch the Pi, which crosses this repository's own
`.agents/README.md` (owner decision 2026-09-04). The commits sit on local
`master`, now thirteen ahead of `origin`. To get it live, in an ordinary
terminal:

```powershell
git -C "$env:USERPROFILE\Dropbox\20-Code\2024-interactive-diagram" push
```

then on the Pi: `git pull --ff-only` in `/home/pi/pihtivacuum`, `sudo systemctl
restart pihti`, and confirm `/version` says 0.17.0.

## Mail

Six letters collected — `20260908-fe94c769-493d71`, `20260908-2c3d9837-37ab4a`,
`20260908-425e4cdb-09c038` (superseded by the first two; read and recorded
here), `20260908-e2498698-5c9c50`, `20260908-8eaaa7a9-334955` and
`20260908-e6ada507-7aa064` — after their work was recorded here.

The five for the ship after this one stay posted, unread by this release's code
but read by this session so the memory built here serves them: practice mode
(`20260908-9d38bf34-8415c7`, `20260908-e460b66f-616b53`), the right-rail state
card and its collapse (`20260908-aa2558c2-f3d03e`, `20260908-50f93f77-8e8a28`),
and the guide card's scroll bar (`20260908-8853f919-4c54b6`). The predictor was
kept pure with the memory as an argument precisely so the practice mode can run
it over a local copy; and the scroll bar the last letter names was seen again in
this walk, on the six-step *Vent Plasma* card at 1440×900.

## Corrected within the session: the hatch was making dashed pipes

Five more letters arrived while this was being written — queezz was watching the
tree on his own service — and three of them are one correction to the release
above, which is why it went in before this session ended rather than into the
next ship's pile.

His words, in order: *"The predictor is inventing something hallucinogenic...
for some reason lines broke down. Inventive destruction."* Then, plainly: *"I
don't like the broken lines. They are pipes. That reads like a breakage."* And
on a close-up of the plasma cross, the tee above it and the gate valve between
them all under one blue hatch: *"the dashed valve, it's like 'guess what shape
this is and what this blob does'."*

He is right and the cause is simple: **a hatch painted onto a 4 px stroke is a
dashed line.** The pattern was applied to fills and strokes alike, so every pipe,
tee, gauge stem and open valve in a sealed volume came out gapped. On a rig
sitting shut down that is most of the drawing.

The rule now, and it is a standing one:

- **The hatch is on the two chamber bodies and nowhere else.** Not a tee, not a
  cross, not a pipe, not a gauge stem, and never a valve. His own letter offered
  the escape — *"drop it from tees too and hatch the two vessels alone"* — and
  that is what was taken, because the blob he photographed was the tee and the
  valve sharing the cross's hatch.
- **Every pipe is a solid stroke in every state.** Nothing anywhere is given a
  dash pattern; measured in the browser, zero elements in the whole SVG carry a
  `stroke-dasharray`, and the only one a saved render writes is the explicit
  `none` on the drawn valve the Line configuration governs.
- **A sealed volume's pipes, tees, crosses, gauge stems and open valves are
  solid in a paler tone** of what the volume is holding — 35 % of the way toward
  the drawing's own ground, `sealed_pale` in the map so it can be dialled without
  touching code.
- **A valve keeps its own two looks in every state**: open, filled and rimmed in
  the colour flowing through it; closed, white with a black rim.

Measured after the fix, at 1440×900, with both vessels sealed: the two chamber
bodies carry the pattern and no other element does; pipes solid at
`rgb(100,140,210)`, tees solid at `rgb(189,105,176)`, GVU white on black; zero
dashed elements anywhere in the drawing.

**The honest cost, so he knows what he asked for.** The paler tones sit below
the palette's own 3:1 floor against the stone field, deliberately — a sealed pipe
is not a live claim:

| state | live | on the field | sealed pale | on the field |
| --- | --- | --- | --- | --- |
| Air | `#c81d24` | 4.32 | `#d16162` | 2.82 |
| Gas | `#a92a9c` | 4.51 | `#bd69b0` | 2.72 |
| High vacuum, plasma side | `#1f5fd0` | 4.38 | `#648cd2` | 2.54 |
| High vacuum, QMS side | `#0e8a46` | 3.33 | `#59a878` | 2.16 |
| Rough vacuum | `#a86a00` | 3.34 | `#bd934b` | 2.12 |
| Isolated, unknown | `#7f7b75` | 3.16 | `#a29e97` | 2.01 |

The floor still governs every live colour and every legend chip; only the sealed
tone goes under it, which is the whole signal.

**And live still beats the memory**, which his first letter also asked to be
sure of. It always did — a sealed reading is only ever produced for a volume the
walk finds isolated — and it is now pinned by a test and was proved in the
browser: with the plasma vessel sealed, opening GVU onto the running turbo made
it full-strength high vacuum immediately, with no sealed flag and no hatch. What
his frame actually showed is the *next* letter's subject: the rough pump could
not reach that vessel because **the map treats a stopped turbo as a wall**, and
he has now ruled that it is a passage. That is a change to the connectivity model
rather than to the drawing, and it is recorded in directions for the next ship
with his ruling attached — it also closes the standing question this repository
had been holding open about exactly that.

Two more tests: one that the hatch touches a chamber body and nothing else, in
the prediction and in a saved render alike, and one that live always beats the
memory. 71 passing.

## Usage receipt

Provider Anthropic, model Claude Opus 5. Task: commander run round 7 resumed:
pihti trio / Diagram sealed memory and marks. Child agents: 0. Provider usage:
unavailable — no meter was shown to this session.
