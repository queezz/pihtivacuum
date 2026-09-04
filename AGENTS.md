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

- The SVG's stable `zone-*` groups define plumbing volumes. Do not infer connectivity from path geometry; ask the owner to split or identify ambiguous pipework.
- Live component colors may be derived from the operator-entered diagram state (owner decision 2026-09-03), but must be labelled as a diagram connectivity prediction, not measured pressure or an interlock.
- Valve/pump fill colors remain operational state and must not be reused as pressure-domain colors.
- Turbo-pump and gauge warnings derived from toggle state are advisory operator warnings, never proof of hardware state or safety (owner decision 2026-09-03). Actual pressure evidence must use Raspberry Pi fields with explicit instrument IDs, units, timestamps, and stale-data handling, and must fail to “unknown.”
- Operation guides only annotate the diagram and list operator steps. They never perform device mutations. Prototype sequences remain explicitly provisional until the owner corrects them.

## Web UI invariants

- Every page uses the one `.page` grid: left rail for controls, main column for content, right rail for context. Rail widths and the sticky offset (`--bar` + `--content-gap`) are shared, so rails stand at the same address on every tab and never move on scroll.
- The palette is Fleet's dark paperlib set; lecturedeck is never the model for this UI. The authored SVG keeps its own colours.
- Any UI change runs Fleet's Perimeter Walk on a scratch `lab` service before it ships.

Read `.agents/README.md` for workflow, `.agents/directions.md` for open owner decisions, and `.agents/log/` for session evidence. Fleet-wide policy remains in Fleet's `RULES-BRIEF.md` and routed references.
