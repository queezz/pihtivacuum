# A quieter field, loud vessels, and a readout in words (0.12.0)

Commander-dispatched follow-up ship in the coordinated PIHTI trio run, on the
work Windows PC, 2026-09-08 late morning JST — queezz awake and reviewing. It
answers six letters written while he watched the 0.11.2 colour work land, plus
one older decision that had never been collected.

## The mail

All seven from `code/fleet`, all his own words relayed by the Commander.
Collected with `fleet letters --collected <id>` after the work.

| id | what he said | what happened |
| --- | --- | --- |
| `20260907-b9fddf7b-4768ce` | the id-rename decision | already applied by 0.11.1; the renames were re-verified against `diagram.svg` and the letter collected (an earlier ship reported collecting it but it was still posted) |
| `20260907-5ccb4a98-115ee7` | "all gauges stems don't have colors" | all six stems recorded and coloured; **none had to be named** |
| `20260907-30f02358-976853` | the orange field may change | it did — the whole palette was rechosen |
| `20260907-7b746768-c9c2c3` | "more readable, yes. Also way more ugly"; beacons broken | the glow is gone; the beacons are repaired |
| `20260907-9a18c84c-e1fcff` | the bypass Ts and cross stay white | they take the volume's colour as a fill |
| `20260907-1ec7c373-a45f8c` | vessels loud, full colour, not a tint | done, and the Ts and cross with them |
| `20260907-d5386824-f57dfd` | say what upstream and downstream are joined to | built; the three later items are in `directions.md` and were not built |

## The palette, chosen as one thing

The 0.11.2 note ended with the real diagnosis without acting on it: coral
(`#ff7f50`, luminance 0.370) leaves **8.4:1** of headroom between the field and
black, so all five state colours had to be dark, all five sat at nearly the same
lightness, and they could differ only by hue. That is why they kept reading
alike, and why they needed a glow to be seen at all. He gave permission to
change the field — "no harm in that if it helps readability" — so the field and
the colours were chosen together.

**Field: `#e3dfd6`, a quiet warm stone.** Luminance 0.740, saturation 19%,
**15.8:1** to black. Recorded twice on purpose — `--diagram-ground` in
`styles.css` paints it, `drawing.ground` in `plumbing.json` documents it — and a
test fails if the two drift apart.

| state | 0.11.2 | vs coral | 0.12.0 | vs `#e3dfd6` | hue | luminance |
| --- | --- | --- | --- | --- | --- | --- |
| Air | `#8a0036` | 3.94 | `#8a0026` | **7.49** | 343° | 0.055 |
| Gas | `#6a00b0` | 3.75 | `#6a1fb5` | **6.38** | 270° | 0.074 |
| High vacuum | `#003bc4` | 3.47 | `#1150cc` | **5.19** | 220° | 0.102 |
| Rough vacuum | `#00544a` | 3.55 | `#0a7268` | **4.36** | 174° | 0.131 |
| Isolated, unknown | `#463f3b` | 4.13 | `#7f7b75` | **3.16** | neutral | 0.200 |

The worst of the five is now better than the best of 0.11.2. More important
than the numbers: the five no longer share a lightness. Each step up the table
is at least 1.15:1 lighter than the one below it, so the four claims and the
one non-claim differ **twice over** — by hue and by weight — and a reader who
cannot separate a dark blue from a dark violet can still separate them by how
heavy they look. Isolated is deliberately the quietest of the five, and a test
asserts that it is: it is the absence of a claim, not a sixth thing competing
for the eye. The tests check every ratio, the ordering, and the lightness steps,
so none of this is anyone's eye.

The furniture still reads on it: the drawing's black at 15.8, the gas panel's
pale yellow box by hue rather than by luminance (it is warm against a
near-neutral field, and keeps its own `#c4c4c4` border), the white bottle
circles by their black outlines, the pale-green open valves and yellow running
pumps as the brightest things on the page. That is the whole scheme in one
sentence: **operator state is bright and pastel, predicted vacuum is dark and
saturated**, and the two vocabularies cannot be confused.

## The band: candidates, and the two rejected

He named the fault exactly — "that's more readable, yes. Also way more ugly" —
and the Commander's letter listed four candidates. Three were built and looked
at side by side on the real page, in the browser, before a line was written.

- **Kept: a solid widening of the pipe's own stroke, 1.6x, no second layer.**
  A coloured pipe is simply drawn 1.6 times as wide as queezz drew it, at full
  opacity. His hierarchy survives — 2 px gas tubing becomes 3.2, 3.78 px vacuum
  pipe becomes 6.05 — and switching the band off restores exactly the width he
  authored. No clone, no opacity, nothing in `diagram.svg`.
- **Rejected: 2.6x.** Chunky. It flattened his own thin-tubing/thick-pipe
  distinction into one heavy weight, which is a different drawing, not a
  clearer one.
- **Rejected: the dark core with a colour jacket** — the pipe kept its authored
  black line and a solid colour band was drawn beneath it. It looked good, and
  it lost on two counts: every pipe becomes two visual weights instead of one,
  and it cannot be reproduced in the saved `/state.svg`, which can only write
  CSS. Keeping the page and the saved render identical was worth more than the
  small gain.
- **Rejected outright: the 0.11.2 halo** — a 2.8x translucent clone at 60%
  opacity in its own layer. That is the neon he vetoed.

**An isolated line is not widened at all.** He asked for that one directly, and
it is right: the absence of a claim should not be the loudest thing on the
drawing.

The switch survives, renamed to what it now is — *Draw coloured pipes wider*,
`localStorage` key `pihti.pipeBand` — so he can still judge the colours with his
own widths once he widens the pipes himself. The `directions.md` item that asks
him to decide stays open.

**The saved render matches the page now.** `plumbing.authored_stroke_widths`
reads each element's inline `stroke-width` out of the drawing and
`style_rules` writes `stroke-width:<authored x 1.6> !important` beside the
colour, so `/state.svg` carries the same band. Nothing else is read from the
SVG there.

## Bodies: two vessels, two tees, one cross

"We can go very loud, why not? Color it the color of the vacuum I say. Or gas.
Or air." So the fill is the **full state colour**, not the tint 0.11.2 gave it,
and the `tint` field is gone from `plumbing.json` entirely.

The same rule now covers the three shapes he complained were white. A volume may
declare `junctions` beside its `vessel`: `bypass-manifold` owns the two tees,
`probe-line` owns the cross. Those three are the only elements in the whole
drawing authored with an opaque white fill — a test asserts that set is exactly
the five bodies and nothing else, so a fourth white shape cannot appear
unnoticed.

**A body says its state with its body, and keeps the outline he drew.** The
prediction emits no `stroke` for a filled shape at all, so the authored black
4 px outline survives untouched — that is "an outline dark enough that the shape
still reads" without inventing a colour for it. Measured live: with all five
states forced, the only white fills left anywhere on the drawing are the three
gas bottles, which are white because their operator state says so.

## Gauge stems: six, and none of them a guess

"They are inside a gauge group. If we can work with that, fine. If not, I'll
name them." It could be worked with, so **there is no owner work item here.**

Three gauges sit inside a two-or-three-child group whose only plain line is the
stem; three sit at the top level with their stem drawn immediately before them.
Each gauge in `plumbing.json` now carries a `stem`:

| gauge | stem | volume |
| --- | --- | --- |
| Bypass absolute gauge | `path1464-1-2-8-9` (in `g7`) | bypass-manifold |
| Bypass ionization gauge | `path1464-1-2-8-9-3` (in `g8`) | bypass-manifold |
| QMS ionization gauge | `path1464-1-2-8-9-3-8` (in `g8-9`) | qms-vessel |
| Upstream single gauge | `path1464-1-2-8-9-3-9` | plasma-vessel |
| Upstream Baratron | `path1464-1-2-8-9-7` | plasma-vessel |
| Downstream Baratron | `path1464-1-2-8-9-7-3` | qms-vessel |

The guard matters more than the table. `tests/test_server.py` asserts each stem
is a `path`, is not already mapped to a volume, and is the **element
immediately before its own gauge inside the same parent**. A regroup in Inkscape
that moved a stem away from its gauge fails the suite instead of quietly
colouring the wrong pipe. If queezz would rather name them himself later, the
ids are one line each in `plumbing.json`.

## The beacons, and the one line of CSS that broke them

Watched before it was changed, as WEBUI.md demands. With *Vent Plasma*
selected, the current step's ring computed `fill: rgb(224, 81, 62)` — the
step's own red — where the rule says `fill: none`.

`.operation-marker .halo` is two classes (0-2-0). `.operation-marker.current
circle` is two classes **and an element** (0-2-1), so it won the cascade and
filled the ring. The ring is a `<circle r="18">` behind a disc of the same
radius, breathing outward to `r: 34` — so instead of a white ring pulsing off
the marker, a coloured disc bloomed out of it. Every disc rule now reads
`circle:not(.halo)`, and a test walks every `.operation-marker` rule in the
stylesheet and fails any that fills a circle without excluding the ring.

Two honest notes. First, this was **not** caused by the colour layer: the rule
has been wrong since 98a7d9d, well before 0.11.0. What the colour layer did was
give him a reason to look at the beacons again, and on a loud drawing the bloom
finally read as broken. Second, the ring's white stroke was invisible on the
field that replaced coral, so it is drawn in the marker's own dark ink
(`#1c1f26`) now — the only deliberate departure from the 0.10.0 look, and it is
what keeps the 0.10.0 *behaviour* legible. Everything else is as it was: dark
navy disc, white rim, white numeral, red for current, green for done. Measured
live at 1280x1000 and 1440x900 with all ten markers placed, and the guide
overlay confirmed to be the SVG's last child, so nothing the colour layer fills
can ever paint over a beacon.

## The readout

"I'd like to see if upstream and downstream are connected to a) each other b)
gas c) vent air." Two lines under the drawing, one per vessel, plasma first:

> **Plasma vessel — gas.** Argon is open into it.
> **QMS vessel — high vacuum.** Pumped by the QMS turbo pump (TMPD).

and, with the crossover open and the gas panel vented:

> **Plasma vessel — air.** Open to the QMS vessel. Hydrogen and argon are open
> into it. Vent air through the gas panel vent valve. Pumped by the plasma
> turbo pump (TMPU), QMS turbo pump (TMPD) and roughing bypass.

His question's own order is the sentence's order: the other vessel, then gas,
then vent air, then the pumps; "Nothing open to it." when none of the four
applies. Every component is named the way a person names it at the rig, through
`window.pihtiElementName` — no key reaches the page. The facts come from
`predict()`, the same walk the colours come from, so the sentence and the
drawing cannot disagree.

**One thing the readout must do differently from the colouring, and it is the
subtle part.** `atmosphere` is a single volume in the map, so two separately
vented lines land in the same component — correctly painted red, both of them.
But they are not plumbed to each other, and a readout whose whole purpose is to
answer *"are these two joined"* would be lying if it said so. The reach behind
the readout therefore drops every edge that runs through open air, and a vent
valve is named for a vessel only when its **other** side is really in that
vessel's space. A test proves both vessels can read `air` with `joined == []`.

Pumps stay boundaries here as everywhere: opening the plasma backing line's
vent valve does not make the plasma vessel vented, because a running turbo sits
between them. That surprised the first draft of the test, not the model.

Where it lives: the main column, under the drawing, in the card that already
carried the colour key — read, not pressed, which is where WEBUI.md's rail law
puts it, and the right rail was measured out of the running in 0.11.0. The card
is renamed *Predicted state*; its one honesty sentence still appears exactly
once per page, and a test counts it. History carries no prediction until a
moment is chosen, so it says so in words rather than showing an empty list.

## Verify: scratch Perimeter Walk

`lab start pihti-diagram --port 48951 --host 127.0.0.1` under scratch
`LAB_CONFIG`/`LAB_RUNTIME_ROOT`/`LAB_LOG_ROOT`, every `PIHTI_*` write path
inside a marked `fleet-scratch-2024-interactive-diagram-palette` TEMP root, with
a hand-built state file forcing all five states onto the drawing at once.
Nothing written inside Dropbox. The owner's 4186 was listening before and after
and was never addressed; the Pi's 5000 was never touched.

- **All five states at once, read off the live DOM.** Plasma vessel filled gas
  `rgb(106,31,181)`, QMS vessel filled high-vacuum `rgb(17,80,204)`, the two
  bypass tees and the probe cross filled rough-vacuum `rgb(10,114,104)`, the
  plasma backing line air `rgb(138,0,38)` at 6.05 px, isolated lines
  `rgb(127,123,117)` at their authored 3.78 px. All six gauge stems carrying
  their volume's colour and band. **No white tee or cross anywhere** — a sweep
  of every element in the SVG for a computed white fill returned only the three
  gas bottles, which are white because they are switched off.
- **The readout, live.** Opening GVU moved the plasma vessel from "isolated,
  unknown. Nothing open to it." to "high vacuum. Pumped by the plasma turbo
  pump (TMPU)." Opening both VCR valves joined the two vessels in both lines;
  switching the Line configuration to *Membrane installed* separated them again
  and the "Open to" clause vanished from both; argon added "Argon is open into
  it."; the gas panel vent valve added "Vent air through the gas panel vent
  valve." and turned both lines to air.
- **The beacons**, *Vent Plasma* selected, at 1280x1000 and 1440x900: ten
  markers, the ring computing `fill: none`, the disc `rgb(224,81,62)` for
  current and `rgb(47,125,79)` for done, the overlay last in the SVG.
- **The band switch**: *More* -> off, the pipe returns to 3.77953 px and keeps
  its colour; on, back to 6.04725 px; `localStorage` carries the choice.
- **`/state.svg`** parsed: it carries `stroke:#0a7268 !important;
  stroke-width:6.4 !important` on the bypass lines, `fill:#1150cc !important`
  on the QMS vessel, and a rule for each gauge stem — the saved render finally
  reads the same as the screen it was saved from.
- **Rails at 76 px** at 0/25/50/75/100% of the scroll range, on Vacuum and
  History, at **1280x1000** (left x20 w256, right x989) and at **1440x900**
  (right x1149) — every reading identical. Document width 1265 at 1280 and 1425
  at 1440; no page-width overflow.
- **At 390x844** the document is exactly 390: no horizontal scroll, the tabs
  wrap, the readout and the key read at full size, the drawer opens over a scrim
  and Escape and Close both shut it.
- **Every top tab pressed from inside Vacuum with a guide open**, including
  Vacuum itself, which returned home at scroll 0 with the guide cleared. Back
  landed on Services, Forward returned to Vacuum with the vessel still gas
  violet.
- **History deep link.** `/history?at=2026-09-08 04:01:49` opened cold and then
  survived a true `location.reload()`: the same moment, the same fills, the same
  band, the same two readout lines.
- **Console clean** — not one message on any page.
- `lab stop` killed the tree; port 48951 has no connections at all. Scratch root
  marked `superseded`.

## The drawing on disk is untouched

`diagram.svg` is not in the diff. Inkscape exported it to PNG at 1683 px and
3366 px anyway, and the SHA-256 prefixes are `224d40b8` and `b78f7692` — the
same two hashes the 0.11.0 and 0.11.1 ships recorded. Everything in this release
is the app painting over his file, never editing it.

## Gates

`pytest` 45 passed, exit 0. `node --check` clean on `diagram.js` and
`history.js`. `git diff --check` clean. There is no ruff configuration in this
repository. Three tests were rewritten for the superseded behaviour (the vessel
tint, the halo layer, the coral ground) and four are new: every body filled with
its full colour and no white tee or cross left; every gauge stem coloured, and
still its own gauge's neighbour; the solid band and the untouched isolated line;
the beacon ring against every marker rule; and the readout across five valve
configurations including the two-vents-are-not-a-connection case.

## Version

0.12.0 — a minor bump rather than a patch, because the readout is a new thing on
the page rather than a repair — in `pyproject.toml`, `src/pihti/__init__.py`,
`README.md` and the three assertions in `tests/test_server.py`. Static files
changed, so the bump is also what keeps a browser from serving last release's
CSS and JavaScript against this release's markup.

## Not pushed, not deployed

Told not to push and not to touch the Pi, which crosses this repository's own
`.agents/README.md` (owner decision 2026-09-04). The commits sit on local
`master`, now five ahead of `origin`. To get it live, in an ordinary terminal:

```powershell
git -C "$env:USERPROFILE\Dropbox\20-Code\2024-interactive-diagram" push
```

then on the Pi: `git pull --ff-only` in `/home/pi/pihtivacuum`, `sudo systemctl
restart pihti`, and confirm `/version` says 0.12.0.

## Directions

Three later-pass items from `20260907-d5386824-f57dfd` are recorded and were
deliberately not built: the vent guides reading the prediction instead of a
fixed element list, a warning before a press connects gas or air to a volume
whose ionization gauge is on, and a warning before vent air reaches a volume
whose turbo pump is marked running. Both warnings are predictions, never
interlocks. The Boron deposition question stays open exactly as 0.11.2 left it.
The wide-band item is rewritten for what the band now is.

## Usage receipt

Provider Anthropic, model Claude Opus 5. Task: commander run follow-up: Diagram
palette, fills, stems, beacons, readout. Child agents: 0. Provider usage:
unavailable — no meter was shown to this session.
