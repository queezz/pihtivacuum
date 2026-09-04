# PIHTI interactive vacuum diagram

PIHTI is a LAN-native, operator-annotated vacuum-system diagram with state history and control-unit plots. The diagram is an operating aid, not a control panel, pressure measurement, safety interlock, or source of hardware truth.

Current release: **0.4.0**. The same version appears in the navigation bar and at `/version`.

## What the landing page does

- Shows the existing SVG and operator-entered component states.
- Records whether the line is configured with a membrane, open pipe, or for boron deposition.
- Provides prototype `Vent Plasma` and `Vent QMS` guides as numbered circles over the diagram plus an ordered list in the right rail.
- Derives completed and next steps from the current diagram state. It never sends device commands.
- Uses Fleet's web UI grammar: a sticky tab bar, a calm dark palette, and one three-track grid on every page. Controls stand in the left rail, context in the right rail, and the rails never move on scroll. Below 1200 px the same rails open as drawers.
- History picks a day in the calendar and a moment in the timeline, both in the left rail, and replays the diagram in the main column. The address bar carries the selection, so `/history?at=YYYY-MM-DD HH:MM:SS` is a stable link to a moment.
- Plot picks a control-unit file in the left rail and states which file and channels the plot shows in the right rail.

The vent sequences live in `src/pihti/static/operationGuides.json` and are intentionally provisional pending hands-on owner correction. Live connected-volume coloring still requires the SVG to be split into stable `zone-*` plumbing groups.

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

- `/state.svg` returns the authored diagram with the operator-entered fills applied. `/state.svg?at=YYYY-MM-DD HH:MM:SS` renders the state at that moment.
- `/history/state-at?ts=YYYY-MM-DD HH:MM:SS` returns the absolute element state at that moment as JSON.
- Both are operator-entered annotation, never a pressure measurement.

## SVG contract

Interactive equipment IDs and colors are defined in `src/pihti/static/elementsConfig.json`. Existing valve, pump, and gauge fills represent operator-entered operational state and are not pressure-domain colors.

Future live vacuum indication must use stable `zone-*` groups rather than inferred path geometry. Actual pressure evidence must show instrument ID, units, timestamp, and stale/unknown state.

## Raspberry Pi deployment

The installed package entry point is:

```bash
python -m pihti run
```

After pulling Python, template, or static-file changes, reinstall when needed and restart the registered system service. Keep bind addresses, service paths, keys, operator data, and control-unit data in private deployment configuration rather than this repository.
