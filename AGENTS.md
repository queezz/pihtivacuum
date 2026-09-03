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

The server binds to `127.0.0.1:5000` by default. Long-running and scratch instances belong in `lab-cli/services.toml`; do not start a background shell process. Scratch runs must set `PIHTI_DATA_ROOT` and every other application write path outside Dropbox.

## Identity and security invariants

- Operator choice is attribution only, never authentication or access control. Read-only diagram, history, plot, and download routes remain public; diagram annotation writes require a selected operator.
- Operator selection expires after 12 hours without an attributable diagram change. Passive polling must not extend it.
- The encrypted legacy identity store may be tracked; its Fernet key may not. Only account names are used. The default key lives at `%LOCALAPPDATA%\pihti-diagram\users.key` on Windows.
- Never print, paste, log, or commit keys, legacy password hashes, decrypted identities, session cookies, local data paths, or control-unit data.
- `PIHTI_DEBUG` is loopback-only. Network binding must never imply debug mode.
- Control-unit file selection stays within the configured directory.

## Diagram invariants

- The SVG's stable `zone-*` groups define plumbing volumes. Do not infer connectivity from path geometry; ask the owner to split or identify ambiguous pipework.
- Live component colors may be derived from the operator-entered diagram state (owner decision 2026-09-03), but must be labelled as a diagram connectivity prediction, not measured pressure or an interlock.
- Valve/pump fill colors remain operational state and must not be reused as pressure-domain colors.
- Turbo-pump and gauge warnings derived from toggle state are advisory operator warnings, never proof of hardware state or safety (owner decision 2026-09-03). Actual pressure evidence must use Raspberry Pi fields with explicit instrument IDs, units, timestamps, and stale-data handling, and must fail to “unknown.”
- Operation guides only annotate the diagram and list operator steps. They never perform device mutations. Prototype sequences remain explicitly provisional until the owner corrects them.

Read `.agents/README.md` for workflow, `.agents/directions.md` for open owner decisions, and `.agents/log/` for session evidence. Fleet-wide policy remains in Fleet's `RULES-BRIEF.md` and routed references.
