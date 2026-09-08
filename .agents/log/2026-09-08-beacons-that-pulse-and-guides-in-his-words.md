# Beacons that actually pulse, and four guides in his own words (0.14.0)

Commander-dispatched ship in the coordinated PIHTI trio run, on the work
Windows PC, 2026-09-08 afternoon JST — queezz awake, reading the deployed
0.13.0 on his office PC in Brave. He reported a defect that a previous ship had
already been dispatched to fix, and his sentence is the whole reason this
release exists: *"I know, I wrote it here. But I wrote it before and you
dispatched the fix... to no avail."*

## The letter

`20260908-7a3c9ac3-bbd7aa`, from `code/fleet`, his full review relayed by the
Commander in his own words: beacons still dead; the membrane not following
*Pipe open*; the two vent guides corrected line by line; two new pump-down
guides; no black shape borders. Read in full, recorded here and in
`directions.md`, then collected.

## The beacon, and why the last fix could not have worked

**Watched before a line changed, in a rendered browser, as `WEBUI.md` demands.**
With *Vent Plasma* open on 0.13.0, the current step's ring measured:

    matchMedia('(prefers-reduced-motion: reduce)').matches  ->  true
    getComputedStyle(halo).animationName                    ->  "none"
    halo.getAnimations().length                             ->  0
    getComputedStyle(halo).r                                ->  "26px"  (frozen)

That is the cause. `styles.css` carried

    @media (prefers-reduced-motion: reduce) {
      .operation-marker.current .halo { animation: none; r: 26; opacity: 0.6; }
    }

and **Windows with its animation effects switched off makes Chromium — so
Brave — answer true to that query.** It is his ordinary desktop setting, not an
accessibility need. Everything above that block was correct, which is exactly
why 0.12.0's repair of the ring's *fill* (a real defect, correctly fixed) left
the beacon just as dead: the session measured `fill: none` and stopped, and
`animation-name` was never asked.

The fix does not delete the media query. Under `reduce` the beacon keeps a
pulse and loses the **motion**: one fixed radius, nothing growing or
travelling, only opacity breathing over 2.4s (`marker-halo-quiet`). Less
motion, never less information. The ordinary keyframes keep the growing ring
for a browser that does not report `reduce`, and their `r: 18`/`r: 34` are now
written `18px`/`34px`, a real CSS length.

One thing found on the way and fixed with it: `renderGuideMarkers` tore the
overlay down and rebuilt it on every five-second refresh whether anything had
changed or not, so even a working pulse was cut off mid-breath twice a cycle.
The overlay now carries a signature of the guide id and its step states and is
left alone when neither moved.

**Proof on 0.14.0, measured live at 1280x1000 with *Vent Plasma* selected:**

- `halo.getAnimations().length` = **1**; `animation-name` =
  `marker-halo-quiet`; `animation-duration` = `2.4s`; `reduce` still true.
- Two screenshots a half period apart **differ**: the animation's own
  `currentTime` stepped 0 -> 1200 ms, rendered opacity `0.9` -> `0.12`, and the
  dark rings around both current-step markers are plainly there in the first
  frame and all but gone in the second.
- The full-motion path still grows: with the media query overridden, the same
  real animation stepped 0/400/800/1200 ms gives `r` = 18px / 24.05px /
  28.95px / 32.50px and opacity 0.9 / 0.56 / 0.28 / 0.08.
- Across a five-second refresh the halo is the **same DOM element and the same
  `Animation` object** — the pulse is no longer restarted.

**Write this check into the walk.** A beacon is proved by rendering, never by
reading CSS: `getAnimations()` non-empty on the current step's ring, computed
`animation-name` not `none`, and two frames a half period apart that differ. If
the instrument cannot render, say so and hand the check on.

*Instrument note, honestly:* this Browser pane does not tick
`requestAnimationFrame` (measured: 0 frames in 700 ms with the pane fronted and
`document.visibilityState` "visible"), so a CSS animation stays `pending` there
and never advances on its own. The two frames above were produced by seeking
the real animation's own `currentTime` and screenshotting — the same animation,
the same rendered pixels, driven by hand because the pane will not drive it.

## The membrane

Measured on 0.13.0: switching the Line configuration to *Membrane installed*
left the drawn symbol green (open) **5.9 seconds later**, and the server had
already recorded the mode. `setupLineModes` repainted only the rail's own text;
nothing repainted the drawing, so the change waited for the next five-second
poll — and in a background tab, where the browser throttles that timer, far
longer than that. That is what he saw.

Two changes. The mode press now repaints the drawing immediately, and the
symbol says **present or absent** rather than a different shade of the same
blob: under *Membrane installed* a solid plug in the closed colour, under *Pipe
open* and *Boron deposition* an empty dashed outline at 45% opacity, so the
line reads straight through it. Measured live: the press changed both, in
350 ms, in all three configurations.

## The four guides

`operationGuides.json` is now his procedure rather than 0.5.0's guess, and it
gained four small vocabulary words: `targets` (the diagram can tell whether it
is done), `separates` (ask the prediction whether two volumes are still
joined), `marks` (put a beacon on a part without judging it), and `onlyWhen`
(apply only on a rig where something is plugged in).

**Vent Plasma.** 1 — switch off the ionization gauges that see the plasma
vessel. 2 — close the plasma gate valve; stopping the turbo is the operator's
choice, and leaving it running means the pump-down has to go through the
bypass. 3 — isolate from the QMS side: closing GVBU is enough on its own, and
with a membrane installed and the bypass shut, closing GVBD as well costs
nothing. 4 — check the valve to bypass pumping is closed. 5 — let nitrogen in
through the big manual needle valve on the argon line, not the mass-flow
controllers: the nitrogen valve, the gas panel argon valve, the argon gas line,
the main gas line. 6 — watch the Pfeiffer single gauge climb to atmosphere,
then open; the Baratron does not read atmosphere.

**Vent QMS.** 1 — switch off the QMS ionization gauge. 2 — close the QMS gate
valve, turbo again the operator's choice. 3 — isolate: close GVBD, and that is
the whole isolation. 4 — with the flow-calibration pipe plugged in, nitrogen
through it (nitrogen valve, gas panel argon valve, flow-calibration valve, then
GVBD — a route that comes in *through* GVBD, so the isolation moves to GVBU
while it flows); without it, which is the rig today, vent with air through the
vent valve, acceptable here because this side is pumped a long time and holds a
good base pressure. 5 — watch the Ulvac absolute gauge on the bypass line, or
the Pfeiffer Pirani, then open.

**Pump down Plasma.** 1 — shut the gas off: main gas line, argon gas line, gas
panel argon valve, nitrogen valve. 2 — leave the ionization gauges off until
the pressure is low. 3 — read the pressure before anything opens to a turbo:
the Ulvac absolute gauge covers roughly 13 kPa down to about a kPa, `----`
means over range and is effectively atmosphere, near zero is safe; the Pfeiffer
single gauge reads the same sort of span; the Baratrons do not read atmosphere
and are not the check. 4 — choose the way: turbo stopped, open GVU and pump out
through it, start TMPU when the gauge is low; or turbo running, rough through
the bypass first (roughing bypass on, valve to bypass pumping and GVBU open)
and open GVU only after reading the gauge. 5 — switch the ionization gauge back
on once it is pumping.

**Pump down QMS.** The same five, mirrored: close whatever you vented through;
gauge off until the pressure is low; read the Ulvac absolute gauge; choose the
way (TMPD stopped and open GVD, or rough through the bypass with GVBD and open
GVD after the gauge); gauge back on.

The isolation steps in both vent guides use `separates`, so they are satisfied
by the prediction rather than by a list of valves — the "read the guides from
the predicted state" direction of 0.12.0, shipped here, and the reason one
closed GVBU finishes the step exactly as he described it.

The QMS air step is the one step in all four guides with **no beacon**: the
volume map carries no vent valve on the QMS vessel, and the guide will not
point at a handle he has not named. That is now an owner question rather than a
guess.

## The machine-local fact

Whether the flow-calibration pipe is plugged in is a fact about a rig, not
about a drawing, so it lives in `settings.json` beside `CUDATA_DIRECTORY`:
`FLOW_CALIBRATION_PIPE_CONNECTED`, **false by default**, read live by
`/operation-guides` and sent to the page with the guides. Proved both ways on
the scratch rig: false shows the air step and hides the nitrogen one, true
shows the nitrogen route with its four parts and hides the air step. Documented
in `README.md`.

## No black borders

`predict()` now gives a body the state colour as its **stroke** as well as its
fill, so the two vessels, the two bypass tees and the cross read as one colour
rather than as an outlined shape. Valves, pumps and gauges keep the black he
drew — they are equipment, not volumes. `/state.svg` writes both from the same
place, so the saved render cannot disagree:
`#plasma-vacuum{stroke:#7f7b75 !important;fill:#7f7b75 !important}`.

**The isolated grey still reads on the stone field without its outline.**
Measured: `#7f7b75` on `#e3dfd6` is 3.16:1, above the 3:1 the palette was
chosen against, and confirmed by eye with the plasma vessel driven to
*isolated, unknown* on the live page. No darker neutral was needed and none was
invented.

## Verify: scratch Perimeter Walk

`lab start pihti-diagram --port 48977 --host 127.0.0.1` under scratch
`LAB_CONFIG`/`LAB_RUNTIME_ROOT`/`LAB_LOG_ROOT`, with every `PIHTI_*` write path
inside a marked `fleet-scratch-2024-interactive-diagram-guides` root in this
session's own scratchpad — outside Dropbox, outside `%LOCALAPPDATA%` — and a
copy of the real state, context, roster and history files. Listener PID 35716
confirmed as the child of Lab's tracked PID 27920. The owner's `4186` was
listening before, during and after and was never addressed (its PID changed on
his side mid-session, which is his own service restarting, not this one); the
Pi's `5000` was never touched.

- **The beacons**, both measurements above, at 1280x1000.
- **The membrane**, all three configurations, changing within 350 ms of the
  press.
- **The guides**: all four selected and read; step states advancing with real
  presses; `separates` marking the isolation steps complete when the prediction
  says the two vessels are apart; the flow-calibration fact flipped both ways
  with a reload between.
- **A press still works end to end**: `GVU` pressed on the real drawing and
  pressed back, `/elements-state` following both times, `/press-warnings`
  untouched by this release.
- **Rails at 76 px** at 0/25/50/75/100 % of the scroll range at 1280x700
  (range 189) and 1440x900 (range 111, left x20, right x1149) — every reading
  identical, both rails. At 1280x1000 the page does not scroll at all
  (range 0) and both rails read 76 px. Document width 1265 at 1280, 1425 at
  1440: no page-width overflow.
- **At 390x844** the document is exactly 390, no horizontal scroll, and the
  guide drawer opens and renders (`visibility: visible`, `transform: none`) —
  the check the 0.13.0 ship had to report unmeasured because its pane never
  rendered.
- **Every top tab** pressed and each landed at its own top (`scrollY` 0) with
  rails at 76 px; Browser Back and Forward each landed where a reader would
  expect.
- **History deep link** `/history?at=2026-09-08 10:15:11` opened cold and
  survived a true `location.reload()`: the same moment, the same fills (plasma
  isolated `rgb(127,123,117)` fill *and* stroke, QMS `rgb(17,80,204)`), the
  same two readout lines.
- **Teaching check**: the honesty sentence renders exactly once per page,
  "measure pressure" appears nowhere, and the word "Prototype" is gone. Each
  guide's summary frames and its steps state — the turbo-and-atmosphere rule,
  the nitrogen route and the isolation rule were each written twice on first
  draft and trimmed to once.
- **Console clean** — not one message on any page or any press.
- `lab stop` killed the tree; PIDs 27920 and 35716 are gone and port 48977 has
  no listener. Scratch root marked `superseded`.

## The drawing on disk is untouched

`diagram.svg` does not appear in `git status` — nothing in this release touches
the SVG — so the byte-identical Inkscape PNG hashes recorded by the 0.11.0 and
0.12.0 ships (`224d40b8…` at 1683 px, `b78f7692…` at 3366 px) still hold
without re-exporting.

## Gates

`pytest` 53 passed, exit 0. `node --check` clean on `diagram.js`. `git diff
--check` clean. There is no ruff configuration in this repository, and no
`CHANGELOG.md` either: this repository records shipped work in `.agents/log/`,
so this entry is the release note.

Test changes: the guide test now proves the four guides, the corrected shape of
*Vent Plasma* step by step, that `valve_qms` and `Rough-Bypass` appear nowhere,
that an isolation step asks the prediction rather than carrying a
`desiredStatus`, and that both pump-downs name the atmosphere-reading gauge and
never a Baratron. A new test proves the machine-local fact gates the two QMS
venting steps and flips with the settings file. The marker-CSS test now fails
if a `prefers-reduced-motion` block ever writes `animation: none` on the halo
again, if the quiet keyframes move the ring, or if the growing keyframes lose
their units. The body test proves stroke equals fill and that `/state.svg`
carries both. And the readable-name test now covers `marks` as well as
`targets`, because both are read out loud in the rail.

## Version

0.14.0 — a minor bump: two new guides, two corrected ones, and a beacon that
moves are all user-visible. In `pyproject.toml`, `src/pihti/__init__.py`,
`README.md` and the three assertions in `tests/test_server.py`. Static files
changed (`styles.css`, `diagram.js`, `operationGuides.json`), so the bump is
also what keeps a browser that already saw 0.13.0 from serving stale copies.

## Not pushed, not deployed

Told not to push and not to touch the Pi, which crosses this repository's own
`.agents/README.md` (owner decision 2026-09-04). The commit sits on local
`master`, now eight ahead of `origin`. To get it live, in an ordinary terminal:

```powershell
git -C "$env:USERPROFILE\Dropbox\20-Code\2024-interactive-diagram" push
```

then on the Pi: `git pull --ff-only` in `/home/pi/pihtivacuum`, `sudo
systemctl restart pihti`, and confirm `/version` says 0.14.0.

## Mail

`20260908-7a3c9ac3-bbd7aa` read in full, recorded here and in `directions.md`,
and collected. Nothing else posted; nothing owed.

## Directions

The vent-route question is closed with `(owner decision 2026-09-08)` and his
own words, and the "read the guides from the predicted state" item it blocked
shipped with it, so both are pruned. Two items added: which valve lets air into
the QMS vessel, and whether the plasma vessel carries an ionization gauge the
drawing does not show — the one line of the 0.13.0 proposal his review did not
answer. Everything else stands.

## Usage receipt

Provider Anthropic, model Claude Opus 5. Task: commander run round 4: pihti
trio / Diagram guides and beacons. Child agents: 0. Provider usage:
unavailable — no meter was shown to this session.
