# PIHTI interactive diagram agent guide

## Purpose and boundary

This repository provides the local PIHTI vacuum-system state diagram, operator guidance, and control-unit plots. It replaces the earlier static diagram workflow. The diagram is an operator aid, not a pressure measurement, safety interlock, control panel, or source of hardware truth.

## Environment

- External venv name: `pihti-diagram`.
- Windows interpreter: `C:\Users\queez\.venvs\pihti-diagram\Scripts\python.exe`.
- macOS/Linux interpreter: `~/.venvs/pihti-diagram/bin/python`.
- Never create a venv, cache, test scratch, credential key, or decrypted user file inside this Dropbox repository.

## Entry points and gates

```powershell
& "$env:USERPROFILE\.venvs\pihti-diagram\Scripts\python.exe" -m pihti run
& "$env:USERPROFILE\.venvs\pihti-diagram\Scripts\python.exe" -m pytest
```

On macOS/Linux, use `~/.venvs/pihti-diagram/bin/python` for the same script and module arguments.

The server binds to `0.0.0.0:5000` by default: it answers on the LAN because it is served from one machine (the lab Raspberry Pi) and read on a laptop or a phone (owner decision 2026-09-04, "always LAN"). `PIHTI_HOST=127.0.0.1` or `--host 127.0.0.1` narrows a run to its own machine; debug mode remains loopback-only regardless. Long-running and scratch instances belong in `lab-cli/services.toml`; do not start a background shell process. Scratch runs must set `PIHTI_DATA_ROOT` and every other application write path outside Dropbox.

## Identity and security invariants

- Operator choice is attribution only, never authentication or access control. Read-only diagram, history, plot, and download routes remain public; diagram annotation writes require a selected operator.
- Operator selection expires after 12 hours without an attributable diagram change. Passive polling must not extend it.
- Operator names live in the gitignored roster `operators.json` in the data root (`PIHTI_OPERATORS_FILE`); manage it with `python -m pihti operators`. The encrypted legacy identity store may be tracked; its Fernet key may not, and it is read only as a fallback for account names. The default key lives at `%LOCALAPPDATA%\pihti-diagram\users.key` on Windows and exists only on machines where it was generated.
- Never print, paste, log, or commit keys, legacy password hashes, decrypted identities, session cookies, local data paths, or control-unit data.
- `PIHTI_DEBUG` is loopback-only. Network binding must never imply debug mode.
- Control-unit file selection stays within the configured directory.

## Diagram invariants

- **Four line configurations, and the fourth is drawn rather than deduced**
  (owner decision 2026-09-08, letters `20260908-b429ce4b-2ad897` and
  `20260908-520505af-9047d4`, built in 0.16.0). The card offers exactly
  *Membrane installed*, *Pipe open*, *Blank* and *Boron deposition*, in that
  order, each with a one-line meaning in its More, all read from
  `plumbing.json` rather than typed into the template. **Blank** — "the bellows
  is not connected and a blank flange closes the crossover" — is vacuum-wise a
  membrane and so appears beside `membrane` in the linked valve's
  `closed_modes`; what differs is the drawing, so `plug_mode` names the one
  configuration that draws a plug and `flange_element` names the segment
  (`probe-pipe`, from the membrane position to the cross) that wears the
  blank-flange tone instead. A stored configuration is read through the map's
  own `aliases` table, so an older spelling still names its mode and an
  unreadable one falls back to `unknown` rather than to a guess.
- **A pipe's name is what says which volume it belongs to.** queezz named every pipe, cross and T in `diagram.svg` by the volume it carries (`plasma-vacuum-*`, `qms-vacuum-*`, `bypass-manifold-*`, `gasline-*`, `*-vent-air-side`, and the rest), and `static/plumbing.json` is the map built from those names: which elements each volume owns, which two volumes each valve joins, which pump sits where. Connectivity is read from that file and never inferred from path geometry. This replaces the `zone-*` group plan of 0.5.0 — a name survives an edit that regroups the drawing (0.11.0). Ask the owner to name or split ambiguous pipework; never rename his ids without his say-so — the spelling and oddity corrections of 0.11.1 (owner decision 2026-09-08, letter 20260907-b9fddf7b-4768ce) are the one exception, and `src/pihti/server.py`'s `ID_ALIASES` keeps every old id from real history resolving to its current one on read.
- **The 18 `pipes-*` groups are the drawing's own filing, not a data structure.** They exist so a person can find a pipe by name in Inkscape's object list and so pipes paint below valves, gauges and labels. Group membership mirrors `plumbing.json` and nothing reads it at runtime. Regrouping must leave the render byte-identical: three opaque white junction shapes (`probe-pipe-cross`, the two `bypass-manifold-t-*`) sit on top of the lines they join, so alphabetical order inside a group is bent wherever a filled shape overlaps a line, and the two vessel bodies stay at their own depth. Prove it by exporting both SVGs to PNG and comparing the hash.
- Live component colors may be derived from the operator-entered diagram state (owner decision 2026-09-03), but must be labelled as a diagram connectivity prediction, not measured pressure or an interlock. Pipe colour (0.11.0) is that prediction: air beats gas beats high vacuum beats rough vacuum beats isolated, pumps are boundaries rather than connections, and the key sits under the drawing saying "predicted from the valve positions, not measured" — once per page, never twice.
- Pump and gauge fill colors remain operational state and must not be reused as
  pressure-domain colors. **Amended 2026-09-08 for valves alone** (owner review,
  letters `20260908-6819c50d-04e4ba` and `20260908-06105d79-6b7535`, applied in
  0.15.0). The rule existed to keep two vocabularies apart — bright pastel for
  what an operator entered, dark and saturated for what the prediction thinks —
  and it was right until it made a shut gate valve invisible. queezz, on the
  deployed drawing: *"GVU is closed, so TMP is not pumping plasma-vacuum. Yet at
  a glance it seems that it does."* And, on the small ones: they read *"too
  quietly... a green wedge against a grey wedge at that size."* So a valve now
  says its position with its own body — an open one wears the colour running
  through it, a closed one wears white — which makes a closed valve a visible
  break in the colour on both sides and an open GVBD readable from arm's length.
  Only valves moved. Pumps stay yellow when running, gauges keep their own
  colours, the gas bottles keep theirs, and `elementsConfig.json` keeps every
  valve's `colors` entry so nothing that has not moved is broken.
  **Amended twice more the same evening, by his review of the shipped release
  (applied in 0.16.0).** First, the outline: an *open* valve no longer keeps the
  black he drew. His words (letter `20260908-3308e02d-3021dd`): *"I think I like
  the valves edge to be same color as the fill. When closed, black border white
  fill is good. Stands out."* So an open valve is one colour, fill and edge
  alike, and reads as part of the pipe; a closed one is white with a black
  outline and is the single dark-rimmed shape on the drawing. Second, the pumps
  moved after all (letter `20260908-3688eabd-587dfe`): *"why don't we change the
  TMP on color to its HV color? Same for rough pumps. Rotaries and Scroll?"* A
  running turbo now wears the high-vacuum colour of the side it serves —
  `serves` in `plumbing.json`, a fact about the rig rather than about today's
  valve positions — and a running rotary or scroll wears rough vacuum. Gauges
  and the gas bottles still keep their own colours, and every pump and valve
  keeps the confirmed on/off an operator presses and history records.
  **Corrected within the hour, in 0.16.1** (letter `20260908-93fb84a6-5a69cf`):
  **a stopped pump carries no ink of the app's at all** and keeps the grey
  queezz drew it in. 0.16.0 made it yellow, on a relayed line reading "stays as
  drawn (yellow)" — the drawing's own fill is grey and yellow was the app's own
  *on* colour, so the release turned the off signal into the on one. His answer:
  *"No, no! Blue and yellow, yellow reads like on. Gray for off was lost. Why?
  WHY???"* Neither the prediction nor the operator palette paints a stopped
  pump now, and the pumps carry no `colors` entry in `elementsConfig.json`.
- **A high-vacuum volume takes its colour from the vessel it is joined to
  (2026-09-08).** Upstream and downstream are two colours, not one — queezz: *"I
  think I'd rather have two high vacuum colors. Upstream and downstream. To see
  mixing clearly."* A volume a turbo reaches but no vessel does is neither: it is
  the seventh state, *pumped, sealed off*, which is what the pipe between a
  closed gate and its own turbo wears. Mixing — a rough pump reaching a
  turbo-pumped volume, or the two vessels joined — is shown on the drawn
  **shapes** alone, as a two-colour gradient from the dominant colour to the
  contributing one.
  **Amended 2026-09-08 (owner, letter `20260908-aed40a4e-c9a286`, applied in
  0.16.0):** air and gas no longer suppress that second tone. They did, and it
  threw away the case worth a glance — queezz, on a frame with the plasma vessel
  vented while the roughing bypass still reached it: *"Rotary from bypass is
  pumping, but I see no gradient."* The dominant colour is unchanged; the second
  tone is now whatever *else* reaches the vessel that is not the dominant thing,
  in every state, so a vented vessel with a rotary still pumping into it shows
  red with an amber tone. One second tone only, chosen in a written order: a gas
  under vent air, then the best pump that is not already the dominant reading,
  then the other vessel when the two chambers are joined.
  **Corrected 2026-09-10 (owner live review, 0.20.6):** joining the two
  vessels alone does not activate a mixed-pumping gradient. Both running
  turbo sides must actually reach the connected volume. A downstream turbo
  behind closed GVD contributes nothing to the joined vessels' gradient;
  opening GVD admits it and closing GVD removes it again. Genuine reachable
  rough-pump contributions and air/gas mixtures retain their existing rules.
  This supersedes the earlier chamber-join-only trigger above.
  **Completed 2026-09-10 (owner mirrored GVU case, 0.20.7):** the dominant
  high-vacuum colour follows the reachable running turbo's served side too.
  TMPD alone reaching joined vessels makes them green, TMPU alone makes them
  blue, and both reaching makes the two-tone fill. A vessel's rank only
  orders multiple reachable pumping colours; it cannot introduce a colour
  from a blocked pump. This replaces the vessel-membership colour rule above.
  A pipe still wears one colour and only one, because an SVG
  gradient is painted across a bounding box rather than along a path and would
  streak the wrong way on a bend (queezz: *"we have shapes in all important
  places"*).
- **A turbo has two states in the map: running, when it is a pump, and stopped,
  when it is a piece of pipe** (owner ruling 2026-09-09, letter
  `20260908-948b8dbc-b1eb0d`, built in 0.17.1). queezz, watching TMPD stopped
  with the QMS rotary running on its backing line: *"The rough pump pumps, it
  can really do that."* Gas goes through a stationary rotor, so a stopped turbo
  joins its own inlet line to its `backed_by` line exactly as an open valve
  would — the vessel above a stopped TMPD with GVD open is rough vacuum, pumped
  by the QMS rotary through it, and the readout names that pump. A running turbo
  is the pump and the boundary again, with the rough pump behind it as its
  backing. **Only a closed valve blocks.** The passage is declared in
  `plumbing.json` (`stopped: "passage"`) rather than inferred from `kind`, and a
  rough pump carries neither field because it exhausts to the room. The knock-on
  is deliberate: venting a backing line under a stopped turbo now reaches the
  vessel above it, so the 0.13.0 press warning has something to warn about.
- Turbo-pump and gauge warnings derived from toggle state are advisory operator warnings, never proof of hardware state or safety (owner decision 2026-09-03). Actual pressure evidence must use Raspberry Pi fields with explicit instrument IDs, units, timestamps, and stale-data handling, and must fail to “unknown.”
- Operation guides only annotate the diagram and list operator steps. They never perform device mutations. The four sequences in `static/operationGuides.json` stopped being provisional on 2026-09-08, when queezz corrected them line by line (letter `20260908-7a3c9ac3-bbd7aa`); a route none of them names is a question for him, never a guess. A step may check the diagram (`targets`), ask the prediction whether two volumes are still joined (`separates`), place a beacon without judging it (`marks`), or apply only on a rig where something is plugged in (`onlyWhen`, answered by the machine-local settings file). Every id a step names, in `targets` or in `marks`, is read out loud in the rail, so it must carry a `label` in `elementsConfig.json`.
- **The beacon pulses under `prefers-reduced-motion: reduce` too.** Windows with its animation effects switched off makes Chromium — so queezz's Brave — answer *true* to that query, and a `@media` block that said `animation: none` left the beacons dead on his desk for two releases while the CSS read as correct. Under `reduce` the ring keeps a slow opacity pulse at one fixed radius: less motion, never less information. Proving a beacon means measuring it in a rendered browser — `element.getAnimations()` non-empty on the current step's ring, computed `animation-name` not `none`, and two frames a half period apart that differ — never reading the stylesheet.
- **A beacon stands beside what it points at, never on top of it (2026-09-08,
  letter `20260908-3688eabd-587dfe`).** queezz, with Vent Plasma running:
  *"venting plasma works. But numbered circles are obstructing the
  interactions."* A disc centred on a valve hides the very valve the step is
  asking you to press. The disc now stands at the element's top-right corner,
  stepped further out along the diagonal, and a step's own authored
  `markerOffset` still applies on top of it; every part of a beacon declares
  `pointer-events: none` rather than relying on inheritance, so the press
  underneath always lands on the valve. Proving this means pressing a beaconed
  valve in a rendered browser with a guide active, never reading the CSS.
- **Practice is a local copy of the state, and it records once** (owner,
  2026-09-08, letters `20260908-9d38bf34-8415c7` and `20260908-e460b66f-616b53`,
  built in 0.19.0). queezz: *"You open the valve, and see where color
  (vacuum/air) goes. Then you can undo... That way one state jump, less history
  spamming. And better operational safety."* While the Practice switch is on,
  the page's own `vacuumState` **is** the practised copy, so the colours, the
  marks, the sealed readout, the 0.13.0 press warnings and the guides' beacons
  all run over it without knowing anything about practice; `POST
  /practice/prediction` answers about that copy, carrying the volume memory out
  and back so the recorded memory never moves, and `POST /press-warnings` takes
  the same copy. **Neither writes a byte.** The five-second poll is skipped
  while practising, or it would paint the record over the rehearsal. Undo steps
  back one press; Discard restores the recorded state and cancels the timer.
  **Save records the whole sequence as one event** — one row in `logs.csv`, one
  entry on the timeline, one jump on replay — signed by the operator, with every
  press in order in the log's `changes` column and a `note` saying what it was.
  Those two columns were added in 0.19.0; an older four-column log is widened
  once, atomically, keeping every row (`widen_log_header`), and an ordinary
  press leaves both empty and reads exactly as it always did.
- **A record nobody pressed Save on says so.** The fallback timer counts down
  visibly from the last press and saves the sequence by itself as the same one
  event, whose note ends *"saved by the timer"*. It never fires while a confirm
  box is open (`isInteracting` is held from before the box appears until after
  the press lands), Discard cancels it, and the interval is
  `PRACTICE_AUTOSAVE_SECONDS` in the machine-local settings file — three minutes
  by default, held between 30 and 1800 seconds so a typo can neither turn the
  fallback off nor make it fire mid-press. Leaving the page with unsaved
  practice asks first.
- **A change costs one request and one redraw.** `/update` and the
  `/operation-context` write both answer with the new prediction, so the page
  repaints from the answer that made the change rather than asking
  `/predicted-vacuum` for it afterwards (0.15.0; queezz on 0.13.0: *"membrane
  installed to open pipe is VERY slow. And no reason for it to be slow."*).
  A route that changes the diagram carries its own consequence back; adding a
  second round trip to find out what just happened is the defect.
- **A volume's body is one colour; equipment keeps its outline.** The two vessels, the two bypass tees and the cross take the state colour as fill *and* stroke (owner decision 2026-09-08: "All one color... Color speaks vacuum. Black border speaks... shapes?"). Valves, pumps and gauges keep the black queezz drew. Both halves come from `predict()`, so `/state.svg` and the page cannot disagree.

## Web UI invariants

- Every page uses the one `.page` grid: left rail for controls, main column for content, right rail for context. Rail widths and the sticky offset (`--bar` + `--content-gap`) are shared, so rails stand at the same address on every tab and never move on scroll.
- The palette is Fleet's dark paperlib set; lecturedeck is never the model for this UI. The authored SVG keeps its own colours.
- Any UI change runs Fleet's Perimeter Walk on a scratch `lab` service before it ships.
- **No surface shows a person a component key.** A reader sees the equipment's name; `GVU`, `gaspanel-valve-n` and the rest stay in the files, the log and the SVG. The names are the `label` beside each `id` in `static/elementsConfig.json`, read through `window.pihtiElementName` (0.10.0), and History marks a component the current diagram no longer carries rather than passing its recorded key off as a name. Fleet `WEBUI.md`: what a viewer sees is for the viewer.
- **The top bar wraps; it never overflows.** Below about 470 px the five tabs and the operator selector cannot share one row, so the selector drops to a row of its own at the same right-hand corner and the tabs wrap before they can be pushed off screen (0.10.0, after the Mac audit found the selector clipped at 390 px). One DOM in a different placement — never a second phone-only control. The bar is taller when it wraps, which only rails below the 1199 px breakpoint would care about, and those are fixed drawers rather than sticky rails.
- **One legend; appearance switches lead More after the dark-mode review** (owner
  correction 2026-09-09, letter `20260908-c03c1788-9def42`, applied in 0.19.1).
  queezz on the first build of the state card: *"Why do we need two legends?
  pic 2, the thick pipes is too far hidden. Do we need that much text in a rail
  card??"* The chips in the card **are** the swatches — two to a row so seven
  fit a 16 rem rail — and the second board of bigger ones inside More is gone
  with the thirteen sentences that followed it. More holds one short line per
  chip, read from the map's own `meaning`, plus three lines for the drawing's
  own rules; anything longer belongs on a help page, never in a rail card
  (Fleet `WEBUI.md`, Teaching: the surface states, the rail teaches once at a
  glance, the rest sits behind one press). The **Draw thick pipes** switch
  stood directly under the chips and above More, on both pages that draw.
  **Amended 2026-09-08, owner live review of dark mode (0.20.2):** the exposed
  checkboxes are too easy to press by mistake. Dark diagram and Draw thick
  pipes now lead the contents of More, before the meanings, on both pages.
  The earlier placement kept the width switch findable; this order makes both
  preferences deliberate while keeping them one press away.
- **On the Vacuum page the predicted state is a right-rail card; on History the
  key stays under the drawing** (owner order 2026-09-08, letters
  `20260908-aa2558c2-f3d03e` and `20260908-50f93f77-8e8a28`, built in 0.18.0).
  queezz: *"I think the bottom card deserves a proper place in the rail, no? And
  not hiding in small sizes, shying away. Proper. With proper groups, not a
  long-line which is a list."* The right rail is where context lives, so the
  state card, the legend swatches and More all moved there, present at every
  width the rail exists and in the drawer where it does not — never dropped by a
  breakpoint. What made room for it is the collapse rule below, not a taller
  rail: the two earlier attempts at a third card were measured out because both
  cards insisted on their full height at once. **History keeps the key under the
  drawing**, because that page's right rail already carries its own cargo (the
  selected moment and the export), and a rail answers for its own tab.
- **Both right-rail cards collapse to a headline and neither ever vanishes.**
  Collapsed, the state card is one line per vessel — colour chip and state word;
  the guide card is the guide's name and the current step with its number. The
  default follows the situation: with a guide running the guide is open and the
  state compact, with no guide the state is open. The reader's own press is
  remembered per browser and always wins over that default. A press on the
  card's header toggles it, and the header is a thumb-sized target in the drawer.
- **The guide card grows, then folds, then scrolls — in that order** (owner,
  2026-09-08, letter `20260908-8853f919-4c54b6`: *"the right procedure card gets
  a nasty scroll bar.. Would be nice if we can avoid that"*). It takes its
  natural height first; when the list is still longer than the rail's room,
  every step but the current one and the one after it folds to a single line
  (its full wording moving to that row's own title); only then does the list
  take a thin, quiet bar of its own. Below a floor the card is never crushed —
  the **rail** takes the overflow and scrolls inside its own box, which is Fleet
  `WEBUI.md`'s 2026-09-08 amendment. The page never scrolls for the rail.
  Everything is measured in the rendered DOM, and measured **after** the layout
  settles: called straight out of a resize the fit read a height from a layout
  that was still moving, folded one step and stopped, so every caller goes
  through one short timer and one pending flag. A timer rather than an animation
  frame, because a browser stops handing frames to a tab nobody is looking at.
- **Change a static file and you must bump the version**, or a browser that saw the previous release keeps the old copy for a year. Static files are cached by release, everything else is `no-store` (0.9.0). A template writes a static URL with `asset('css/styles.css')`, never `url_for('static', ...)`, and JavaScript that fetches a static file stamps it with `document.body.dataset.assetVersion`. An unstamped or stale-stamped static URL is deliberately uncacheable, so a stale asset cannot outlive its release.
- The last control-unit plot is served as its own document (`/plot/last.html`) and framed, never injected into the page: Plotly's bundle is measured in megabytes and injecting it froze the tab. `X-Frame-Options` is `SAMEORIGIN` for that frame alone. The served document is prefixed with the frame's own reset, so a plot saved by an older release still fills the frame without white margins.
- The recording archive travels one month at a time (`/plot/recordings?month=`), never as one payload in the page. A month that has passed does not change, so the answer carries an ETag and is revalidated rather than re-sent.

## Deployment

The lab Raspberry Pi (`pihti:5000`) serves this diagram from an editable install of `/home/pi/pihtivacuum` on Python 3.9, run by `deploy/pihti.service`; laptops and phones read it. It deploys by pulling `master` from GitHub, so a shipping session pushes after committing (owner decision 2026-09-04, see `.agents/README.md`) and then pulls and restarts on the Pi. Keep the package importable on Python 3.9.

Read `.agents/README.md` for workflow, `.agents/directions.md` for open owner decisions, and `.agents/log/` for session evidence. Fleet-wide policy remains in Fleet's `RULES-BRIEF.md` and routed references.

## Dark diagram (owner review, 2026-09-08; 0.20.2)

The appearance switch changes no SVG geometry or connectivity. Dark uses a lifted
slate ground, electric blue and bright green vacuum, quieter amber roughing and
vivid vent red. Closed valves use pale fill and a light rim in dark mode; this
is the theme-specific amendment to the black-rim rule above, after the owner
found the black borders unsuitable. The empty membrane marker keeps its dashed
outline but uses that visible light rim at 90% opacity. Light mode keeps the
previous inks. Stopped pumps remain grey. Sealed tones fade toward the selected
ground. Theme and thickness travel into historical SVG image links.
