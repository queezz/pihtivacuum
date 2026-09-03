# PIHTI interactive vacuum diagram

PIHTI is a LAN-native, operator-annotated vacuum-system diagram with state history and control-unit plots. The diagram is an operating aid, not a control panel, pressure measurement, safety interlock, or source of hardware truth.

Current release: **0.3.0**. The same version appears in the navigation bar and at `/version`.

## What the landing page does

- Shows the existing SVG and operator-entered component states.
- Records whether the line is configured with a membrane, open pipe, or for boron deposition.
- Provides prototype `Vent Plasma` and `Vent QMS` guides as numbered circles over the diagram plus an ordered list in the right rail.
- Derives completed and next steps from the current diagram state. It never sends device commands.
- Uses desktop side rails; the same rails become drawers below the wide-layout breakpoint.

The vent sequences live in `src/pihti/static/operationGuides.json` and are intentionally provisional pending hands-on owner correction. Live connected-volume coloring still requires the SVG to be split into stable `zone-*` plumbing groups.

## Run and test

Use the external environment; do not create a virtual environment or runtime data inside this Dropbox repository.

```powershell
& "$env:USERPROFILE\.venvs\pihti-diagram\Scripts\python.exe" -m pihti run
& "$env:USERPROFILE\.venvs\pihti-diagram\Scripts\python.exe" -m pytest
```

The server binds to `127.0.0.1:5000` by default. Optional environment variables include:

- `PIHTI_HOST` and `PIHTI_PORT`
- `PIHTI_DATA_ROOT` for logs and diagram state
- `PIHTI_CUDATA_DIRECTORY` for control-unit CSV files
- `PIHTI_USERS_FILE` and `PIHTI_USERS_KEY_FILE` for the encrypted operator-name registry
- `PIHTI_OPERATOR_TIMEOUT_HOURS` for the operator inactivity window (default 12)

Long-running and scratch services belong in Fleet Lab. `PIHTI_DEBUG` is loopback-only.

## Operator identity

Operator selection is attribution, not authentication. Read-only diagram, History, Plot, and downloads remain public. Selecting a name enables diagram annotation writes so state changes can be labelled in the history.

The selection expires after 12 hours without an attributable diagram or line-configuration change. Passive state polling does not extend it. The existing encrypted identity registry is retained for deployment compatibility, but the application reads only its account names and never checks its legacy password-hash values.

The Fernet key belongs in machine-private storage (`%LOCALAPPDATA%\pihti-diagram\users.key` on Windows or `~/.config/pihti-diagram/users.key` elsewhere) and must never be committed.

## SVG contract

Interactive equipment IDs and colors are defined in `src/pihti/static/elementsConfig.json`. Existing valve, pump, and gauge fills represent operator-entered operational state and are not pressure-domain colors.

Future live vacuum indication must use stable `zone-*` groups rather than inferred path geometry. Actual pressure evidence must show instrument ID, units, timestamp, and stale/unknown state.

## Raspberry Pi deployment

The installed package entry point is:

```bash
python -m pihti run
```

After pulling Python, template, or static-file changes, reinstall when needed and restart the registered system service. Keep bind addresses, service paths, keys, operator data, and control-unit data in private deployment configuration rather than this repository.
