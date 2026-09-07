# The pipes have names, and now a colour (0.11.0)

Commander-dispatched session in the coordinated PIHTI trio run, on the work
Windows PC, overnight 2026-09-08. queezz did the half nobody else could: he
opened `diagram.svg` in Inkscape and gave every pipe, cross and T a name, then
dropped the result in `local/diagram-update.svg`. This session adopted it,
grouped it, and built the colour on top of it.

## What he changed, measured

173 ids in his file against 155 in the shipped one — 172 real element ids each
way plus one grep artefact (below). He replaced 38 Inkscape ids (`path1464-1-2-8`
and friends) with 57 named ones, all prefixed by the volume the pipe belongs to:
`plasma-vacuum-*`, `qms-vacuum-*`, `bypas-manifold-*`, `bypas-pumpline*`,
`gasline-*`, `gaspanel-*`, `upstream-tmp-to-rotary-pipe*`,
`downstream-tmp-to-scroll-pipe*`, `probe-pipe*`, `qms-sensor-pipe`,
`upstream-to-downstream-narrow-pipe`, and `*-vent-air-side` for the ends that
open to atmosphere. **Every id `elementsConfig.json`, `operationGuides.json`,
`diagram.js`, `history.js` and the state file refer to still exists.** All 38
configured components are present; nothing vanished and nothing was renamed.

## The zone question is closed, in his own way

`directions.md` had asked him to wrap each plumbing volume in a `zone-*` group.
He did something better for the same purpose: he named the pipes. A volume is
now a *prefix*, not a group, and that is the more durable answer — a name
survives an edit that regroups the drawing, and Inkscape shows it in the object
list where he works.

## Grouping, and the proof that nothing moved

The 52 named pipes now sit in 18 `<g>` wrappers, one per volume
(`pipes-plasma-vacuum`, `pipes-qms-vacuum`, `pipes-bypass-manifold`,
`pipes-vent-air`, …), placed together low in the document so a pipe can never
paint over a valve, a gauge or a label. Inside each group the ids are
alphabetical; the groups themselves are alphabetical.

**Blind alphabetical sorting would have broken the drawing**, so it is not
blind. Three of his shapes are opaque white junction boxes — `probe-pipe-cross`
and the two `bypas-manifold-t-*` tees — that are *meant* to sit on top of the
lines they join. Sorting them under those lines would have printed 18px of
black pipe inside a white tee. The regroup therefore keeps a "stays before"
constraint for every overlapping pair where either shape carries a fill, and
sorts alphabetically within those constraints: 23 constraints held, everything
else alphabetised.

Three elements were deliberately left where they were and are still coloured:
the two vessel bodies `plasma-vacuum` and `qms-vacuum` (their ports would
otherwise be drawn over the vessel fill — `qms-vacuum-gauges-port` runs 7px
inside the QMS rectangle), and `downstream-tmp-to-scroll-pipe-to-vent`, which
lives inside a translated group and would have moved if lifted out of it.

**The proof: the two SVGs render byte-identically.** Inkscape exported both to
PNG at 1683px and at 3366px wide; the SHA-256 of before and after matches at
both sizes (`224d40b8…` and `b78f7692…`). Separately, a stdlib script that
applies every ancestor transform reports a maximum bounding-box difference of
**0** across all 149 measurable elements. Nothing moved, nothing changed colour,
nothing changed z-order visibly.

## Colour by predicted vacuum state

`static/plumbing.json` is the new file and the whole model: 18 volumes with the
elements each one owns, 24 valves saying which two volumes each joins, 6 pumps
with their kind and their volume, 5 gas sources, 6 gauges, and the five states
with their colours. It is read from his names, never from where a line happens
to sit on the page.

`src/pihti/plumbing.py` walks it: open valves join volumes into one space, and
the space is named **air** if it reaches a vent, else **gas** if a bottle or the
nitrogen valve is open into it, else **high vacuum** if it reaches a running
turbo, else **rough vacuum** if it reaches a running rough or scroll pump, else
**isolated, unknown**. Air beats everything, because that is the reading an
operator needs first. Pumps are boundaries, not connections: a turbo separates
its high-vacuum side from its backing line, which is why venting the plasma
backing line leaves the vessel above it blue.

Pump running state is the diagram's own — TMPU, TMPD, RoughU, RoughD,
Rough-Bypass and the gas-panel pump are all toggles already, so nothing had to
be assumed.

`GET /predicted-vacuum` answers with the volumes, a colour per element, and the
list of volumes predicted to hold air. `?at=` answers for a past moment, so a
replayed History diagram is coloured by the state it is replaying rather than by
now. `/state.svg` carries the same prediction as stroke rules. The page paints
strokes only; the authored fills are untouched and the file on disk keeps its
own colours.

**Three vent valves joined `elementsConfig.json`** so his `*-vent-air-side`
lines can actually be opened: `GVU-6`, `GVU-6-9` and `Rough-bypass-vent`. They
were already drawn as valves in the right places; they simply had no state. See
the id questions below — those first two names are Inkscape copy-ids and read
as if they were the plasma gate valve, which they are not.

## The legend, and where it ended up

It began as a third rail card and was measured out of the rail again. At a
700px window the right rail is 604px and the guide card alone needs it: with
Vent Plasma selected the summary is 127px, the alert 85px and the steps 230px.
Both left-rail cards leave 94px. There is no room for a fifth card anywhere in
the rails that does not crush something a reader needs, and the first two
attempts proved it — one squeezed the guide to 85px and painted 113px of its own
words over the card below, the next crushed the legend to a 26px stripe.

So the key sits **under the drawing**, where a map's legend goes, on both pages
that draw the diagram. Fleet `WEBUI.md`'s own rail law puts it there anyway: it
is read, not pressed. Five wrapping chips, each a 14px sample of the diagram's
own coral ground with the colour laid across it, and the meanings behind More —
the same shape the Services rail already wears here.

Two repairs fell out of the same walk. `.rail-card--growing` carried
`min-height: 0`, which let a squeezed card shrink under its own words and paint
them over its neighbour; it now clips instead. And the guide's prototype note
said "does not operate hardware, **measure pressure**, or replace an interlock"
while the legend said "not measured" — one honesty point told twice on one
screen, which is `WEBUI.md`'s textbook defect. The legend owns that sentence now
and the guide's note lost those two words. A test counts it.

## Perimeter Walk

Scratch `lab start pihti-diagram --port 48941 --host 127.0.0.1` under scratch
`LAB_CONFIG`/`LAB_RUNTIME_ROOT`/`LAB_LOG_ROOT` with every `PIHTI_*` write path
in a marked `fleet-scratch-2024-interactive-diagram-*` TEMP root; nothing
written inside Dropbox. Listener confirmed by `OwningProcess` as the child of
Lab's tracked PID. The owner's 4186 was up before and after and was never
touched; the Pi's 5000 was never touched.

- **The dev test, all six steps.** Everything closed: every volume `isolated`,
  only the air stubs red. TMPU + GVU + RoughU on: plasma vessel and turbo line
  blue (`rgb(31,79,168)`), backing line teal (`rgb(15,155,142)`), QMS still
  black. Vent open (`GVU-6`): backing line goes red (`rgb(140,11,18)`) and the
  vessel above the turbo stays blue; closed: back to teal. QMS side follows
  GVD/TMPD/RoughD/valve_qms, bypass follows bypass-l2 and Rough-Bypass, each
  independently. Gas panel: hydrogen bottle on turns the hydrogen line violet,
  and a real click on `gaspanel-valve-h` in the drawing turned it green and the
  gas panel manifold violet, while the upper gas manifold stayed black because
  its cutoff valve is shut. All read off the live DOM's computed strokes, not
  off the API.
- Rails at **76px at 0/25/50/75/100% of the scroll range**, at 1280×1000 and
  1280×700, on Vacuum and History, with and without a guide open. Left rail
  x20, right x989, both 256px wide, 904px and 604px tall — identical to the
  readings in the 0.10.0 walk.
- No card in either rail paints outside its own box at either height, with a
  guide open and with More open. No page-width overflow at 1280 (1265px) or at
  390 (390px). The drawer opens and Escape closes it at 390 with no overflow.
- Every top tab pressed from inside Vacuum, including Vacuum itself, which
  returns home at scroll 0. Back landed on Services at its top, Forward
  returned to Vacuum with the pipes still painted. Deep link
  `?at=2026-09-08 00:55:12` reloaded with its moment, its component name and its
  colours; an earlier moment inside the all-closed sweep replayed black, which
  is the honest answer for it.
- Console clean on every page.
- `lab stop` killed the tree; 48941 has no connections at all, scratch root
  marked `superseded`.

**The stale-asset hazard bit again, exactly as `AGENTS.md` warns.** Editing
`styles.css` more than once inside 0.11.0 served the browser its cached copy,
so a fix read as not applied — twice, until each measurement was preceded by
`fetch(url, {cache: 'reload'})` and a reload. It is a walk artefact, not a
shipping defect: no browser has ever seen a different 0.11.0. Worth repeating
in the log because it cost two wrong diagnoses tonight. The template needed a
service restart for the same reason — Flask compiles templates once outside
debug mode.

## Gates

`pytest` 34 passed (exit 0), `node --check` on `diagram.js` and `history.js`,
`git diff --check` clean. There is no ruff configuration in this repository.
Three new tests: every element and group in `plumbing.json` really is in the
SVG and every valve, pump, source and gauge it names is a configured component;
the prediction over four valve configurations including the honest order of the
five states; and the route, its `?at=` form, and the legend appearing once per
page with no second "measure pressure".

## Version

0.11.0 in `pyproject.toml`, `src/pihti/__init__.py`, `README.md` and the three
assertions in `tests/test_server.py`.

## Not pushed, not deployed

This run was told not to push and not to touch the Pi, which crosses this
repository's own `.agents/README.md` (owner decision 2026-09-04). The commits
sit on local `master`. To get it live, in an ordinary terminal:

```powershell
git -C "$env:USERPROFILE\Dropbox\20-Code\2024-interactive-diagram" push
```

then on the Pi: `git pull --ff-only` in `/home/pi/pihtivacuum`, `sudo systemctl
restart pihti`, and confirm `/version` says 0.11.0.

## Mail

Three notes logged, nothing owed: `20260907-e795be58-e0ac52` and
`20260907-db04b74c-2b20e7` (ControlUnit 4.4.0 and 4.5.0 took this board's
geometry and its four break numbers) and `20260907-8a1d8586-805692` (PIHTI Log
0.38.0 did the same and stopped degrading its own health for a pending draft).
Nothing was changed here on account of any of them. PIHTI Log's one open
question — its page caps at 1920px where this one caps at 1600, and would we
match — is not this session's to answer and is recorded in `directions.md`.

## Usage receipt

Provider Anthropic, model Claude Opus 5. Task: commander run, PIHTI trio /
Diagram, pipes by vacuum. Child agents: 0. Provider usage: unavailable — no
meter was shown to this session.
