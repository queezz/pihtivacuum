# Recording plots and manual Baratron zero

## Owner request and source

Read Fleet letter 20260915-ec9708ab-ef1123 from code/ControlUnit. Implemented
its recorded-file plotting/export work: Pu2, same-run Kikusui and available PID
files, original exports, explicit units and gaps. Live hardware measurement
integration remains outside this change. Producer source and docs checked for
ion-gauge range conversion and MFC/setpoint units.

Owner refined the UI through the scratch preview: combine Pu/Bu/Pu2, Pu/Pd,
Ic/Ip, and pressure with MFC signal/setpoint; move export to the right rail;
remove explanation and put curve selection over the main plots. Owner chose
manual offset only for Bu. No baseline detection is provided. Displayed value
is recorded value minus the manually entered offset. Browser memory is per
recording, and original files remain untouched.

## Implementation

File-specific GET plot documents replace global last-plot mutation in the page.
The old POST/last-document routes remain compatible. A stdlib recording reader
handles column preambles, quoted CSV, telemetry statuses, off markers and
explicit units. All original same-stamp companions export byte-for-byte.
Unknown numeric columns remain selectable with unknown units.

Plotly runs in a same-origin frame. The parent offers a main-column curve
picker, dual-unit comparisons, axis scales/order, pan/zoom, fit and exports.
The renderer now uses CSS-safe trace identifiers; a colon in the earlier
identifier broke Plotly purge when moving curves. Manual zero corrections
apply to hover, plots and displayed-curve export, with original values included.
Plots stay mounted but transparent/inert while the picker covers them.
Intermediate scratch asset versions were bumped to defeat immutable browser
cache during review; the consolidated release is 0.24.5.

## Verification

- 170 pytest tests pass; 14 Node tests pass; both plot scripts pass node --check.
- Parser tests exercise units, mode/range conversion, off/status gaps, CSV
  variants, multiple sources and path confinement. Route tests prove exact ZIP
  bytes, file-specific reads, malformed responses and cache policy.
- New renderer tests prove signed Bu, negative offset subtraction, null gaps,
  corrected CSV values, per-file persistence and independent Torr/V axes.
- Scratch Lab service uses synthetic recordings and external write paths only.
  Rendered Pu/Bu/Pu2, Pu/Pd, Ic/Ip and pressure/MFC signal/setpoint comparisons;
  manual negative offset, reset/defaults, reload and an older recording;
  scientific pressure ticks and linked time zoom. No new rendering errors.
- Perimeter Walk: pressed all top tabs and brand/operator links, own Plot tab,
  archive month/day/file links, Back/Forward and deep-link reload. Malformed
  synthetic CSV shows a readable error; latest restores a valid plot. Source
  inventories/data notes remain available. There are no fragment anchors.
- Rails measured at y=76 at rest and full-page scroll at 1280x700 and
  1280x1000. Picker toolbar stays at y=76 beneath a 56px bar at list end.
  At 390x844 the picker is 354.67px wide with no horizontal overflow; drawer
  closes when picker opens, and Escape/Back return to the plots. Repeated
  real use exceeded two minutes. First action is choose a recording, then
  Compare & arrange; explanation is in one short zero-control hint and
  collapsed data notes.
- Original download routes are byte-verified by tests and were pressed in the
  browser. Displayed CSV values are verified in renderer tests. PNG export was
  pressed without a new console/status error; IAB did not deliver a download
  completion event, so downloaded PNG bytes were not independently inspected.
- SSH deployment preflight failed: pihti hostname does not resolve here.
  No Pi deployment attempted after that failure.

## Handoff

Release/push and scratch shutdown outcomes recorded below after completion.

Scratch Lab process tree stopped successfully; port 48937 has no listener. Fleet letter was marked collected after this evidence was written. The final handoff reports the commit/push result; Pi deployment remains blocked by DNS.
