# Metered process gas is not an unroughed-gas warning (0.30.0)

## Owner request

queezz, journal 2026-10-07 18:09 (ControlUnit letter `20261007-677c6c98-ca9550`):
"it needs to fix the 'unroughed gas enters TMP' warning. We inject gas via
precision needle valves or MFCs to make plasma, which is the designed mode of
operation." On 2026-10-02 (letter `20261002-dfcaefd6-0d53d6`): "Ha, gas is
off, but the warning doesn't go." ControlUnit measured a few mTorr of argon
during the discharge and 1e-5 Torr within a minute of closing.

## What was wrong

Read off the run's own `/state.svg` snapshots in the vault: argon bottle,
gas-panel argon valve, `gasline-ar` (the big manual needle valve), the main
gas line and GVU open, TMPU running. 0.28.x warned on any live gas at a
running turbo, and it kept the warning after the needle closed because the
gas manifold, between the needle valve and the main gas line, remembered
argon; with no rough pump reaching it that memory counted as unroughed, and
`unroughed` retention kept the memory, so the banner held itself up. The
0.29.0 code reproduced both screenshots from that state; the new code shows
neither.

## Change

- `plumbing.json` `metered_gas`: `gasline-ar` and the two MFC cutoffs
  (`gasline-o`, `gasline-h`), each cutoff standing for its controller so the
  outlet section counts as metered (0.23.1 left its trapped pressure to the
  cutoff-opening reminder).
- `plumbing.py`: a walk with those valves left out (`_beside_meters`). A
  running turbo warns for live gas only when a bottle is on its own side of
  the meters (`unmetered: true`), for remembered air anywhere it reaches, and
  for remembered gas on its own side that no turbo was pumping. Gas memory
  entries carry `turbo_pumped`, from the prediction's new `turbo_pumped`
  list. The vessel readout gets `metered` per gas and `metered_only`.
- `server.py`: a stored memory with gas but no `turbo_pumped` is replayed
  from the log once at start; with an empty log it is kept and read strictly.
- `diagram.js`: banner words "unmetered gas" / "unroughed gas" / "air"; the
  state word "gas · metered".
- AGENTS.md: dated amendment in the 0.28.0 section, and that section's
  duplicate copy folded into one. The History and Power-card sections at the
  top are still duplicated (not touched).

## Decisions

- Air keeps warning through any valve, including the needle valve: the
  existing "vent through the gas line" test stays exact.
- The flow calibration valve is not listed as a meter; gas through it warns
  as unmetered. Asked in `directions.md`.
- Nitrogen through the needle valve is metered like argon (his words name the
  valve, not the gas). Asked in `directions.md`.
- A vessel filled through the needle valve while GVU was shut still warns
  when GVU opens onto a running TMPU, even with the needle still open.

## Verification

- Gates: pytest 184 passed (175 before; 9 new including the full 2026-10-02
  sequence through `/update` and the 0.28.9 state-file replay), exit 0;
  `node --test tests/*.test.cjs` 34 passed (new
  `tests/turbo-warning-text.test.cjs`).
- Scratch Lab, `lab start pihti-diagram --port 48971 --host 127.0.0.1`,
  then 48972 for the restart; `LAB_CONFIG`/`LAB_RUNTIME_ROOT`/`LAB_LOG_ROOT`
  and every `PIHTI_*` write path in this session's temp scratchpad, inline
  session secret, a nonexistent users key, `BROWSER` pointed at a no-op so
  `open_on_start` opened nothing. Listener confirmed as a child of Lab's
  tracked PID each time. Seeded with the 2026-10-02 16:43 rig state.
- Walk, built-in browser: Pipe open, argon bottle, needle valve pressed on
  the drawing: recorded directly, no banner, no pulse, readout "gas ·
  metered". Needle closed: no banner after the poll, vessel high vacuum.
  Gas-panel vent then needle: loud "air reaches ... TMPU", automatic
  Practice, TMPU pulsing (`equipment-warning-pulse`). Flow calibration
  valve: loud "unmetered gas reaches ... TMPU", Undo cleared it. In Practice,
  GVU shut, needle open, GVU reopened: loud "unroughed gas reaches ... TMPU".
  History at the needle-open and needle-closed moments: no warning, "gas ·
  metered" then "high vacuum"; `location.reload()` on the deep link restored
  the moment. Every top tab and the brand from Vacuum land at scrollY 0;
  Back/Forward correct. Rails 76 px at 0/25/50/75/100 % at 1280x1000 and
  1280x700, including with the banner up (54 px page scroll at 700). Phone
  375x812: document 375 wide, State drawer reads "gas · metered" in full.
  Collapsed card headline "Plasma vessel gas · metered". Restart with the
  memory rewritten as 0.28.9 left it: no warning, no console errors. Teaching:
  "metered" appears once per vessel line and is not explained elsewhere.
- Scratch stopped with `lab stop` both times; PIDs gone, 48971/48972 free;
  4186 and 5000 free before and after (not running on this PC).
- Not verified: the Pi itself (Python 3.9) and a real phone. Not pushed.

## Next

Push `master` and deploy on the Pi (`git pull --ff-only`, `sudo systemctl
restart pihti`, `/version` reads 0.30.0); then confirm on the rig that the
banner is gone and the plasma vessel reads "gas · metered" during the next
discharge.
