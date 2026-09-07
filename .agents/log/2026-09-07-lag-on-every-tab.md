# The lag on every tab: cached assets, and a plot that stops blocking the page

Continues `2026-09-07-services-explainer-and-own-icon.md`, same session.
queezz: "Plot tab blocks UI until it loads. Bad. We should be able to go there
and it's ok for the plotly to update, not UI lag. History, same thing, a lag.
Main page, the diagram. Same, always the lag."

## Measured first, on the Pi with the real archive

Server render time was never the problem: `/history` 13 ms, `/services` 13 ms,
`/` 14 ms warm, `/plasmaplots` ~210 ms with 1318 recordings. Two client-side
causes, both measured in the browser against the Pi:

1. **`Cache-Control: no-store` on every response, static files included.** One
   `after_request` set it for the whole application, so each tab switch
   re-fetched `diagram.svg` (185 kB), `styles.css` (20 kB) and every script.
   Nothing the browser had was ever reused. That is the lag on all three tabs,
   and it is worst over WiFi, which is where queezz reads it.
2. **The Plot tab fetched 6.8 MB before it would show anything**, injected it
   into the page's own document (re-creating each `<script>` so it executed
   there), and covered the whole viewport — tab bar and both rails — with a
   fixed modal overlay while it did. Timing from the Pi: `get_last_plot`
   6842 kB, starting at 319 ms.

## Fixed (0.9.0)

- **Static URLs carry the release and may be cached.** `asset()` in the page
  context writes `?v=<version>` on every static URL a template emits, and
  `diagram.js` stamps its own `diagram.svg` fetch the same way. `after_request`
  answers `public, max-age=31536000, immutable` only when a `static` request
  carries the running version, and `no-store` otherwise — so an unstamped or
  stale URL can never be cached, and a new release is a new URL. Pages, data
  and the plot document stay `no-store` exactly as before.
- **The plot is its own document, framed.** New `GET /plot/last.html` serves
  the stored plot as `text/html` (404 when there is none) and `GET /plot/meta`
  answers a few hundred bytes saying what the last plot is. The page reads the
  meta, then points an `<iframe>` at the document. `POST /plot` no longer
  returns the plot in its JSON. The full-page overlay is gone: status is a line
  above the frame, and the previous plot stays on screen while a new one draws.
- `X-Frame-Options` moves from `DENY` to `SAMEORIGIN` so the tab can frame its
  own plot; other origins still may not frame this application.

## Perimeter Walk

Scratch `lab start pihti-diagram --port 48934 --host 127.0.0.1`, all `LAB_*`
and `PIHTI_*` roots in the session scratchpad, three synthetic but genuinely
plottable `cu_*.csv` recordings written there. Listener confirmed as the child
of Lab's tracked PID; the owner's 4186 was empty before and after; the Pi was
not touched.

- **The measurement that answers the complaint:** arriving on Vacuum after
  visiting other tabs transferred **0 kB** of static assets — `diagram.svg`,
  `styles.css`, `diagram.js` and `rails.js` all served from cache
  (`transferSize` 0, `encodedBodySize` intact) where the same navigation used
  to move about 250 kB. A stamped stylesheet answers `public, max-age=31536000,
  immutable`; the same file without a stamp answers `no-store`.
- Plot opens in 224 ms with `/plot/meta` costing under a kilobyte, no overlay
  in the DOM at all, rails at 76 px. Plotting a recording put 4.99 MB into the
  frame's own document, where `Plotly` is defined and the plot rendered (331
  nodes inside the frame), while the page's own document stayed at its four
  small assets.
- `?file=` deep link on a fresh tab: day 6 pressed, that recording selected and
  plotted, download armed, 140 ms to load, console clean. Pressing Services and
  coming Back restored the deep link with the frame showing, at scroll 0.
- At 1280x700 the frame is 504 px, rails at 76 px, no rail overflow, no
  horizontal overflow.
- **Not measured, and not claimed:** whether the browser's main thread janks
  while Plotly parses inside the frame. A same-origin frame shares the page's
  main thread, and this pane's page reports `document.hidden`, which throttles
  `requestAnimationFrame` and timers, so no honest responsiveness figure could
  be taken here. What is proven is that arriving at the tab no longer waits for
  megabytes and no longer veils the page.

## Gates

`pytest` 26 passed (exit 0), `node --check` on `plasmaplots.js` and
`diagram.js`, `git diff --check` clean. A new test pins the cache rule from
both sides — stamped is cacheable, unstamped and stale-stamped are not — and
the plot tests moved to the new routes.
