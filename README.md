# PIHTI interactive vacuum diagram

PIHTI is a LAN-native, operator-annotated vacuum-system diagram with state history and control-unit plots. The diagram is an operating aid, not a control panel, pressure measurement, safety interlock, or source of hardware truth.

Current release: **0.18.0**. The same version appears in the navigation bar and at `/version`.

## What the landing page does

- Shows the existing SVG and operator-entered component states.
- Records which of **four** line configurations the rig is in, and colours the diagram accordingly. They are queezz's own, in his order (owner decision 2026-09-08): *Membrane installed* — the membrane separates the two vessels at the crossover; *Pipe open* — the membrane probe is in, or the bellows, either way a vacuum connection; *Blank* — the bellows is not connected and a blank flange closes the crossover, vacuum-wise like a membrane; and *Boron deposition* — the sample holder is installed and the pipe is a plasma-side dead end, never joined to the QMS vessel. Only *Pipe open* makes the narrow pipe a route joining both vessels. The card's More prints the one-line meaning of each. The drawn `Membrane` symbol on the probe line follows this same annotation rather than its own press, and it redraws the moment the annotation changes: a solid plug across the line under *Membrane installed*, an empty dashed outline under the other three, where nothing of the app's is mounted there. Under *Blank* the probe segment itself — from the membrane position to the cross — is drawn in a blank-flange tone of its own, neither a state colour nor the closed grey. A configuration recorded under an older spelling still resolves, through the map's own alias table.
- Provides four operator guides — `Vent Plasma`, `Vent QMS`, `Pump down Plasma` and `Pump down QMS` — as numbered beacons over the diagram plus an ordered list in the right rail. The current step's beacon pulses, under `prefers-reduced-motion: reduce` as well: that setting takes the motion out of the ring, never the beacon itself.
- Derives completed and next steps from the current diagram state. It never sends device commands.
- Uses Fleet's web UI grammar: a sticky tab bar, a calm dark palette, and one three-track grid on every page. Controls stand in the left rail, context in the right rail, and the rails never move on scroll. Below 1200 px the same rails open as drawers.
- History picks a day in the calendar and a moment in the timeline, both in the left rail, and replays the diagram in the main column. The address bar carries the selection, so `/history?at=YYYY-MM-DD HH:MM:SS` is a stable link to a moment.
- Plot picks a control-unit file in the left rail and states which file and channels the plot shows in the right rail.

The four sequences live in `src/pihti/static/operationGuides.json`, in queezz's own words after his review of 2026-09-08. A step names the parts the diagram can check in `targets`; `separates` asks the prediction whether two volumes are still joined, so an isolation step cannot go stale when the plumbing map is corrected; `marks` places a beacon on a part the step names without claiming the diagram can judge it, such as a turbo whose stopping is the operator's own choice. `onlyWhen` gates a step on a fact about this rig that no valve position carries — today only `FLOW_CALIBRATION_PIPE_CONNECTED`, below.

Pipes are coloured by the volume map in `src/pihti/static/plumbing.json`, which is read from the names on the drawing's own pipes. There are **seven** states since 0.15.0 — air, gas, high vacuum on the plasma side, high vacuum on the QMS side, rough vacuum, *pumped, sealed off*, and isolated — and they were redrawn in 0.16.0 on a different brief: "design nice, not color blind nice" (owner, 2026-09-08), after gas and rough vacuum came out indistinguishable on a thin line. Six of the seven now sit at nearly one lightness and are told apart by hue rather than by weight; *isolated* stays the deliberately grey one, because it is the absence of a claim. Every colour still clears 3:1 both on the stone field and against the one green valve the prediction does not paint, and a test computes the CIEDE2000 distance of every pair — the closest is about 21 units, where the palette this replaced had a pair at 11.6.

Three rules decide which colour a volume wears. **High vacuum takes its colour from the vessel it is joined to**, so a pipe running from a *closed* gate valve up to its own spinning turbo reaches no vessel at all and wears the seventh colour instead — pumped, and sealed off — rather than the vessel's blue (owner report 2026-09-08: "GVU is closed, so TMP is not pumping plasma-vacuum. Yet at a glance it seems that it does"). **A valve says its position with its own body**: an open one wears the colour running through it as fill *and* outline, so it reads as part of the pipe, and a closed one is white with a black outline — the single dark-rimmed shape on the drawing — so a colour never runs through a shut valve and a small open valve is readable from arm's length. And **mixing shows on the shapes alone**: when a rough pump also reaches a turbo-pumped volume, or when the two vessels are joined, the drawn bodies — the plasma cross, the bypass tees and cross, the QMS box, the probe cross — carry a two-colour gradient from the dominant colour to the contributing one, while every pipe stays one colour. From 0.16.0 that second tone appears in **every** state, air and gas included: a vented vessel with a rotary still pumping into it shows red with an amber tone, which is the case worth a glance (owner, 2026-09-08: "Rotary from bypass is pumping, but I see no gradient"). A vessel holding gas also carries that gas's bottle symbol (Ar, O2, H2, He, N2) drawn large inside it, one circle per gas.

The two vessels, the two bypass tees and the cross take the state colour as their fill and as their outline, so they read as one colour rather than as an outlined shape (owner decision 2026-09-08: "Color speaks vacuum. Black border speaks... shapes?"); pumps and gauges keep the black he drew, because they are equipment rather than volumes. A pump's *fill* says what it is doing from 0.16.0: a running turbo wears the high-vacuum colour of the side it serves, and a running rotary or scroll wears rough vacuum. A **stopped** pump is left exactly as queezz drew it, in his own grey — 0.16.0 made it yellow and he corrected that within the hour, because yellow was the app's own *on* colour and grey already meant off. Each gauge's stem takes the colour of the volume it reads. Coloured lines and bodies are drawn with round caps and joins, which closes the notches a butt end leaves where a gauge stem meets its pipe. The widening switch in the key under the drawing is **off by default from 0.15.0** — queezz's own stroke widths are the widths he wants — and can still be turned on per browser.

Under the drawing, one line per vessel says in words what the prediction finds it joined to: the other vessel, a gas, vent air through a named valve, a pump, or nothing. All of it is a prediction from the entered valve positions, never a measurement.

The same prediction also warns before a press. When a press would newly let gas or vent air reach an ionization gauge that is switched on, or vent air reach a turbo pump that is marked running, the confirm box carries a sentence saying so above the question — and an element with no confirm box of its own still asks when there is something to say. The answer is read from a copy of the entered state with the press applied, so only what the press makes *worse* is mentioned. **It is a prediction from the valve positions, never an interlock:** it reads no pressure, refuses no press, and protects no hardware.

## Run and test

Use the external environment; do not create a virtual environment or runtime data inside this Dropbox repository.

```powershell
& "$env:USERPROFILE\.venvs\pihti-diagram\Scripts\python.exe" -m pihti run
& "$env:USERPROFILE\.venvs\pihti-diagram\Scripts\python.exe" -m pytest
```

The server binds to `0.0.0.0:5000` by default, so any laptop or phone on the LAN can open it; pass `--host 127.0.0.1` (or set `PIHTI_HOST`) to answer only on the machine it runs on. Optional environment variables include:

- `PIHTI_HOST` and `PIHTI_PORT`
- `PIHTI_DATA_ROOT` for logs and diagram state
- `PIHTI_CUDATA_DIRECTORY` for control-unit CSV files
- `PIHTI_OPERATORS_FILE` for the operator roster (default `operators.json` in the data root)
- `PIHTI_USERS_FILE` and `PIHTI_USERS_KEY_FILE` for the legacy encrypted registry, used only when no roster exists
- `PIHTI_OPERATOR_TIMEOUT_HOURS` for the operator inactivity window (default 12)

The machine-local `settings.json` (`PIHTI_SETTINGS_FILE`) carries facts about the rig this copy serves, beside `CUDATA_DIRECTORY` and `NEIGHBOURS`:

- `FLOW_CALIBRATION_PIPE_CONNECTED` — `false` by default. When it is `false`, `Vent QMS` says to vent with air; set it to `true` on a rig where the flow-calibration pipe is plugged in and the same guide offers nitrogen through it instead.

Long-running and scratch services belong in Fleet Lab. `PIHTI_DEBUG` is loopback-only.

## Operator identity

Operator selection is attribution, not authentication. Read-only diagram, History, Plot, and downloads remain public. Selecting a name enables diagram annotation writes so state changes can be labelled in the history.

The selection expires after 12 hours without an attributable diagram or line-configuration change. Passive state polling does not extend it.

Operator names come from `operators.json` in the data root: a plain list of names, no passwords, ignored by git and synchronized with the other runtime data. Manage it from a PowerShell prompt:

```powershell
& "$env:USERPROFILE\.venvs\pihti-diagram\Scripts\python.exe" -m pihti operators list
& "$env:USERPROFILE\.venvs\pihti-diagram\Scripts\python.exe" -m pihti operators add "Name"
& "$env:USERPROFILE\.venvs\pihti-diagram\Scripts\python.exe" -m pihti operators import-history
& "$env:USERPROFILE\.venvs\pihti-diagram\Scripts\python.exe" -m pihti operators import-legacy
```

`import-history` adds every operator who appears in the history log. `import-legacy` adds the account names from the encrypted legacy registry and needs its Fernet key in machine-private storage (`%LOCALAPPDATA%\pihti-diagram\users.key` on Windows or `~/.config/pihti-diagram/users.key` elsewhere). That key must never be committed. When no roster exists the application falls back to the legacy registry, and when neither can be read the operator page says so and shows the command that fixes it.

## The three-service ensemble

PIHTI's three web surfaces — ControlUnit, PIHTI Log, and this diagram — are
meant to run together, each showing the health of all three with links to the
others, so any laptop on the lab network can reach the whole set from any one
of them. The proposed contract and this project's invariants are recorded in
[`.agents/ensemble-health.md`](.agents/ensemble-health.md); the health endpoint
and the ensemble tab are not built yet. No surface depends on another to run,
and a neighbour that is down or unreachable is shown as such rather than as an
error.

## Machine-readable state

- `/state.svg` returns the authored diagram with the operator-entered fills applied, and the predicted vacuum state as pipe strokes, valve and body fills, two-colour gradients where two things reach one volume, and the gas symbols inside a vessel holding gas. `/state.svg?at=YYYY-MM-DD HH:MM:SS` renders the state at that moment, with the line configuration recorded then; `?wide=1` matches a browser whose widening switch is on.
- `/history/state-at?ts=YYYY-MM-DD HH:MM:SS` returns the absolute element state at that moment as JSON.
- Both are operator-entered annotation, never a pressure measurement.

## SVG contract

Interactive equipment IDs and colors are defined in `src/pihti/static/elementsConfig.json`. Pump and gauge fills represent operator-entered operational state and are not pressure-domain colors. **Valves are the one exception, by owner decision of 2026-09-08** (letters `20260908-6819c50d-04e4ba` and `20260908-06105d79-6b7535`): a valve's fill is the prediction's, because a closed valve that does not visibly break the colour lets a shut gate read as open, and a small open valve in pale green against grey could not be read at arm's length. Their `colors` entries stay in the file for the history replay and for any surface that has not moved.

Connectivity is read from `plumbing.json`, which maps the names queezz gave the pipes in `diagram.svg`, never from inferred path geometry. Actual pressure evidence must show instrument ID, units, timestamp, and stale/unknown state.

## Raspberry Pi deployment

The installed package entry point is:

```bash
python -m pihti run
```

After pulling Python, template, or static-file changes, reinstall when needed and restart the registered system service. Keep bind addresses, service paths, keys, operator data, and control-unit data in private deployment configuration rather than this repository.
