# Colours you can see, and a membrane that blocks (0.11.2)

Commander-dispatched follow-up ship in the coordinated PIHTI trio run, on the
work Windows PC, overnight 2026-09-08 (03:30 JST — queezz was awake and
reviewing). It answers his first look at the deployed 0.11.1 pipe colouring,
three findings in one letter.

## The letter

`20260907-88d95b60-1585e4`, code/fleet -> code/2024-interactive-diagram,
"Owner review of 0.11.1 pipe colour: membrane flipped, colours invisible,
vessels should fill", relayed by the Commander from two screenshots of the
Vacuum page. Collected with `fleet letters --collected 20260907-88d95b60-1585e4`.
His three sentences:

1. "Good. But membrane open/closed is flipped."
2. "And it's impossible to see colors. Too similar? Need bigger pipes (that's
   on me)."
3. "I'd say the plasma-vacuum and qms-vacuum shapes should change the fill
   color, too."

## 1. The membrane, and what it turned out to be two of

**The Line configuration was never read by the prediction at all.** The card
offering *Membrane installed* / *Pipe open* / *Boron deposition* wrote an
annotation into `operation_context.json` and stopped there, so the narrow pipe
between the two vessels was a route in every configuration — including the one
where a membrane is sitting in it. That is the flip he saw: with a membrane
installed the two vessels read as one space.

`plumbing.json` now carries a `line_configuration` block naming the volume that
pipe belongs to (`vessel-crossover`) and, per mode, whether it is a connection.
**Only `open` connects.** `predict()` takes the mode; when it does not connect,
each valve on that volume gets its own private side of the barrier, so the two
vessels never join through it, and the one drawn pipe takes the state both
sides agree on or `isolated` when they differ — a single line cannot honestly
carry two answers. In practice that means the pipe still reads blue when both
vessels are pumped and goes neutral only when the two sides genuinely disagree,
which is the honest answer for a line with a membrane across the middle.

**What Boron deposition means for that pipe: not a connection.** Nothing in the
repository says what is mounted during boron deposition, and *Pipe open* is the
only one of the three labels that says the pipe is open, so the other two are
read as "something is in the line". An unrecorded configuration (`unknown`) is
not a connection either: the prediction does not claim a route nobody has told
it about. Both readings are recorded as an owner question in `directions.md`;
flipping boron is one word in `line_configuration.modes`.

**Second membrane, second flip.** The drawing also carries an ellipse with the
id `Membrane` up on the probe line, coloured with the same green/grey as every
valve. 0.11.0 had recorded it inverted — `open_when: "inactive"`, a barrier
that let gas past only when marked *off* — on the reasoning that "membrane
installed" means a barrier. That reasoning now belongs to the Line
configuration, which owns the real membrane; so the inversion is gone and the
element opens when it is green, the way every other green element on this
drawing opens. `directions.md` asks what that ellipse actually is: the vent
guides speak of an "Ulvac membrane gauge", and a gauge is not a route.

**A replayed moment gets the configuration of that moment.** `line_mode_at()`
reads `operation_context_log.csv`, so `/predicted-vacuum?at=` and
`/state.svg?at=` colour History by what was mounted then, not by what is
mounted now. Before the first recorded change the answer is `unknown`.

## 2. The five colours, measured against the ground

The drawing sits on coral (`--diagram-ground: coral`, `#ff7f50`), whose
luminance is 0.370. That fixes the whole problem: the most contrast anything
can have against it is 8.40 (black) going dark and 2.50 (white) going light, so
every state colour has to be dark, and they cannot be told apart by lightness.
They have to be told apart by hue, and the hue has to be wide enough to see.
The 0.11.1 set failed on both counts — the teal stood at **1.38:1** against the
field, which is why "gas and high vacuum look alike" and "air and isolated look
alike" were both true.

| state | 0.11.1 | vs coral | 0.11.2 | vs coral | hue | vessel tint | tint vs its own stroke |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Air | `#8c0b12` | 3.87 | `#8a0036` | **3.94** | 336° | `#e8ccd7` | 6.58 |
| Gas | `#7a4fd0` | 2.18 | `#6a00b0` | **3.75** | 276° | `#e1ccef` | 6.29 |
| High vacuum | `#1f4fa8` | 3.06 | `#003bc4` | **3.47** | 219° | `#ccd8f3` | 6.06 |
| Rough vacuum | `#0f9b8e` | 1.38 | `#00544a` | **3.55** | 172° | `#ccdddb` | 6.31 |
| Isolated, unknown | `#000000` | 8.40 | `#463f3b` | **4.13** | neutral | `#dad9d8` | 7.32 |

Every colour now clears the 3:1 that WCAG asks of a graphical object, where two
of five did not before. The hues are 60°, 57° and 47° apart and the nearest one
to the background's own hue (16°) is 40° away, so none of them is a dark
version of the field. Air moved from red toward crimson-magenta for exactly
that reason. Isolated stopped being pure black and became a warm charcoal at
the *lowest* contrast of the five: he asked for "the absence of a claim, a
neutral, not a colour that competes", and that is what a quiet grey-brown does
next to four saturated ones. `tests/test_server.py` computes these ratios and
fails below 3.0, so the check is in the suite rather than in someone's eye.

**The band behind each pipe.** Contrast alone does not rescue a 2 px line, and
pipe width is his. So each coloured pipe now has a clone of itself drawn
underneath at 2.8 times the width and 60 per cent opacity, in its own
transform-free `<g class="pipe-halo-layer">` at the front of that pipe's own
parent — same parent means the same coordinate system, so nothing moves, and
first child means it paints below everything else in that group. `diagram.svg`
is not touched, and `git diff` proves it: the render is byte-identical because
the file is unchanged. The switch is in the key under the drawing, behind
*More* — "Wide band behind each pipe" — and the choice stays in that browser's
own storage, so he can turn it off and judge the colours again once he has
widened the pipes himself. `directions.md` holds that decision open.

**`/state.svg` was shipping an uncoloured drawing, and nobody had noticed.**
Every pipe carries `stroke:#000000` in an inline `style` attribute, and an
inline style beats a stylesheet, so the plain `#id{stroke:…}` rules 0.11.0
wrote into the saved render lost to the drawing's own black every time. Proved
in the browser rather than assumed: the same rule without `!important` computed
`rgb(0,0,0)` and with it computed the colour. The rules are `!important` now,
and a test reads the rendered file. The page never had this bug — it sets
inline styles of its own.

## 3. The two vessels

A volume you can see into should say its state by its fill, so `plumbing.json`
declares which element is a volume's vessel and the prediction emits a `fill`
for it. **There are exactly two**, and they are the two he named: the plasma
cross `plasma-vacuum` and the QMS rectangle `qms-vacuum` — the only elements in
the whole map with a light authored fill. The other filled shapes in the map
are three opaque white junction boxes that exist to mask crossings, and a long
list of straight lines carrying a `fill:#808080` that paints nothing, and
neither kind is a vessel. The tints keep the outline and sit in the same
lightness band as the fills he drew (`#ffe8fa`, `#bdd6ff`), so the drawing
still looks like his. The key says so once, in *More*.

## Verify: scratch Perimeter Walk

`lab start pihti-diagram --port 48947 --host 127.0.0.1` under scratch
`LAB_CONFIG`/`LAB_RUNTIME_ROOT`/`LAB_LOG_ROOT`, every `PIHTI_*` write path
inside a marked `fleet-scratch-2024-interactive-diagram-colour` TEMP root, with
a hand-built state file forcing all five states onto the drawing at once.
Nothing written inside Dropbox. Listener confirmed by `OwningProcess` (2628) as
the child of Lab's tracked PID (21636). The owner's 4186 was up before and
after and never addressed; the Pi's 5000 was never touched.

- **All five states, live off the DOM.** Air `rgb(138,0,54)` on the plasma
  backing line, gas `rgb(106,0,176)` on the hydrogen run, high vacuum
  `rgb(0,59,196)` around the QMS, rough vacuum `rgb(0,84,74)` on the bypass,
  isolated `rgb(70,63,59)` everywhere else. 56 mapped elements, 2 filled as
  vessels, 54 halo clones — nothing missing.
- **The three configurations, pressed on the real card.** *Pipe open*: plasma
  vessel and QMS vessel both high vacuum, both tinted `rgb(204,216,243)`, the
  narrow pipe blue. *Membrane installed*: plasma vessel isolated and tinted
  `rgb(218,217,216)`, QMS vessel still blue, narrow pipe neutral. *Boron
  deposition*: identical to membrane. Back to *Pipe open* and the two rejoin.
- **The band's switch**: `More` → checkbox on, layer `display: inline`; off,
  `display: none` with the pipe keeping its colour; back on; `localStorage`
  carries the choice.
- **Rails at 76 px** at 0/25/50/75/100 % of the scroll range, on Vacuum and on
  History, at **1280×1000** and at **1440×900** — every reading identical, both
  rails. Document width 1265 at 1280 and 1425 at 1440; no page-width overflow.
  At **390×844** the document is exactly 390: no horizontal scroll, the tabs
  wrap, and the key reads at full size.
- **History.** `/history?at=2026-09-08 03:28:17` opened cold, and a true
  `location.reload()` on it restored the moment, its component name, its
  colours, its halos and the tinted vessels. The replayed moment used the line
  configuration recorded at that moment.
- **`/state.svg`** parsed and measured in the browser: the backing line is
  air-crimson, the vessels carry their tints, and the valve fills are still the
  operator-entered greys.
- Every top tab pressed from inside another, including Vacuum from History;
  each landed at its own top. Browser Back returned to Services, Forward to
  Plot.
- **Console clean** on every page — not one message.
- `lab stop` killed the tree; port 48947 has no connections at all and PID 2628
  is gone. Scratch root marked `superseded`.

## Gates

`pytest` 42 passed (35 plus seven new), exit 0. `node --check` clean on
`diagram.js` and `history.js`. `git diff --check` clean. There is no ruff
configuration in this repository. The new tests: the line configuration over
all four modes plus the both-sides-agree case; the `Membrane` element opening
the way every other valve opens; the two vessels and only those two carrying a
tint; every state colour and tint measured against the coral ground; the saved
render really carrying the prediction; the band living under the pipes with a
switch and never inside `diagram.svg`; and `line_mode_at` over a context log.

## Version

0.11.2 in `pyproject.toml`, `src/pihti/__init__.py`, `README.md` and the three
assertions in `tests/test_server.py`. Static files changed, so the bump is what
keeps a browser from serving last release's CSS and JavaScript against this
release's markup.

## Not pushed, not deployed

Told not to push and not to touch the Pi, which crosses this repository's own
`.agents/README.md` (owner decision 2026-09-04). The commits sit on local
`master`, now four ahead of `origin`. To get it live, in an ordinary terminal:

```powershell
git -C "$env:USERPROFILE\Dropbox\20-Code\2024-interactive-diagram" push
```

then on the Pi: `git pull --ff-only` in `/home/pi/pihtivacuum`, `sudo systemctl
restart pihti`, and confirm `/version` says 0.11.2.

## Mail

`20260907-88d95b60-1585e4` collected. Nothing owed to anyone else; the older
trio letters were already collected or logged by earlier sessions.

## Usage receipt

Provider Anthropic, model Claude Opus 5. Task: commander run follow-up:
Diagram colour readability and membrane sense. Child agents: 0. Provider usage:
unavailable — no meter was shown to this session.
