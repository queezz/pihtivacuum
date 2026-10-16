# The browser reads recordings; the Pi only sends them (0.29.0)

## Owner request

queezz, live: plotting "a bit longer files doesn't even finish"; his hunch was
that the Pi does too much, so "outsource the plotting to the browser client.
First fetch the data, then plot."

## What was actually slow

Plotly already drew in the browser. The Pi parsed the whole CSV in Python and
pasted it into the frame document as JSON, with every channel carrying its own
copy of the time column. Measured on this PC with the largest local recording
(38.6 MB, 86,667 rows, 25 channels): `load_recording` 3.4 s and 104 MB of JSON.
The Pi's single core is roughly ten to twenty times slower, with little memory
beside acquisition and a second Flask server.

## Change

- `/plot/view` names the recording's companion files with their sizes; the new
  `/plot/source` serves each byte for byte (`send_file`, ETag, `no-cache`, so a
  finished recording answers 304 and the one still being written is resent).
  The server no longer parses samples. `recordings.py` keeps pairing and a
  header-only reader for the legacy POST `/plot` meta.
- `static/js/recording-reader.js` is the Python reader's rules in JavaScript:
  columnar Float64Arrays with NaN gaps, one shared time column per file kept
  as recorder wall-clock text. Plotly reads numeric times through
  `new Date`, which would shift them into the viewer's timezone.
- The frame fetches the files (streamed, progress posted to the page), reads
  them and plots. A plot document saved before 0.29.0, which carries inline
  samples, still renders.
- A recording still being written that ends mid-row drops that row and says
  so in Data notes; Python refused the whole file.
- Pre-existing defect found by the walk and fixed: assigning the frame's `src`
  gave it its own history entry, so Back rewound the plot alone while the rail
  named the newer recording. The frame is now replaced with
  `location.replace`.

## Parity before the Python reader was removed

Both readers were run over the nine synthetic cases of the old Python tests
plus edge cases (BOM, CRLF, quoted multiline sidecars, `true`/`False`, `0x10`,
`1_000`, `1e-400`, an impossible date, Z/+00:00/-00:00, IG modes and ranges),
four error cases, and three real local recordings (38.6, 13.4 and 2.9 MB).
Every label, unit, group, x, y, note and error message was identical after one
fix (`-0` in the IG range summary). The JS read the 38.6 MB file in 0.42 s
where Python took 3.3 s on the same PC.

## WebGL tried and withdrawn

Long curves first drew as `scattergl`. Measured with 4 x 250,000 points:
first draw about the same as SVG (~0.5 s), zoom 85-90 ms for SVG and ~1 ms for
WebGL. But the walk then caught "Too many active WebGL contexts. Oldest
context will be lost." after image exports, with the first chart blank. SVG
stays: zooms are 21-42 ms after the first on 4 x 86,667 points, and the PNG
export of four charts takes 1.9 s.

## Verification

- Gates: pytest 175 passed (exit 0); `node --test tests/*.test.cjs` 32 passed,
  including the new `tests/recording-reader.test.cjs` and two workspace tests
  for the fetch path and an unreadable file.
- Scratch Lab service, `lab start pihti-diagram --port 48961/48962 --host
  127.0.0.1`, scratch `LAB_CONFIG`/`LAB_RUNTIME_ROOT`/`LAB_LOG_ROOT` and every
  `PIHTI_*` path (data root, settings, operators, users file and key, inline
  session secret, recordings) in this session's temp scratchpad, outside
  Dropbox. Listener confirmed as a child of Lab's tracked PID each start.
  Recordings: synthetic 250,000-row cu file (41.6 MB) with Kikusui and PID
  companions, a malformed file, a file cut mid-row, and temporary copies of
  two real recordings, deleted afterwards.
- Loopback timings to plot-ready: real 38.6 MB file 0.6-0.9 s; synthetic
  44.8 MB set 1.5 s. On the Pi over Wi-Fi the transfer dominates and the
  status line shows "Receiving ... x of y MB", then "Drawing ...".
- Perimeter Walk: every top tab and the brand from inside Plot land at their
  tops, Plot's own tab reopens the remembered recording; calendar day, file
  list and Latest recording; Back/Back/Forward keep address, rail and frame
  aligned (after the fix above); `location.reload()` on the deep link restores
  file, recorded time and day. Rails at 76 px at 0/25/50/75/100 % scroll at
  1280x1000 and 1280x700, document 1265 wide. At 375x812 no overflow, the
  progress line wraps. Used for well over two minutes: compare (Torr + V on
  two axes), Bu zero offset (CSV value = recorded minus offset, no NaN
  cells, 1.55 M rows in 1.6 s), axis scale, Fit, PNG export. Malformed file
  reads "This recording could not be read. The recording needs a unique
  column header." in the frame and status. No anchors on this surface.
  Teaching: the status line states each stage once; the partial-row note is
  in Data notes only.
- Not verified: the Pi itself (Python 3.9, its Flask), and a real phone on the
  lab Wi-Fi. The 0.24.5 log records `pihti` not resolving from this machine.
- Scratch stopped with `lab stop`; tracked processes gone, ports 48961 and
  48962 free, 4186 and 5000 untouched (free before and after).

## Mail

- ControlUnit `20261002-dfcaefd6-0d53d6` and `20261007-677c6c98-ca9550`:
  queezz's direct ask to quiet the turbo warning during metered process gas and
  clear it when the gas closes. Recorded as the top open item in
  `directions.md`; collected.
- PIHTI Log `20260904-9aba8329-1c35cd` (posted since 2026-09-04): their
  unstyled LAN page fixed in 0.23.0 by inlining CSS, `--lan` shipped in
  0.22.0, `/api/health` carries `detail`; no `/api/neighbours` or Services tab
  there yet; this diagram's permalink and `/state.svg` recorded there as ready
  but not wired in. Nothing asked of this repository; collected.

## Push

On queezz's go-ahead, pushed exactly `5b9e31d` and `e092d55` to GitHub
`master` (884b2bb..e092d55). Pi deployment is his: pull and restart in
`/home/pi/pihtivacuum`, then confirm `/version` reads 0.29.0.
