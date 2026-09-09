# Visible bottle stems (0.20.5)

Owner asked for gas bottle stems to stop disappearing in dark mode, choosing
connected line or active bottle colour. Used connected line colour consistently
in both themes. Declared the five existing stem IDs beside their gas_sources
entries and reused the gauge-stem painter, including sealed tone and width
behaviour. No SVG edits, renames, regrouping or connectivity changes. Bottle
symbols retain their operational colours; nitrogen retains its shared valve
paint from 0.20.4.

105 tests passed, diff --check clean. New tests validate each stem immediately
precedes its own bottle symbol, shares its parent, matches its connected line
in light/dark with sources off/on, appears in exported style rules and does
not repaint bottle symbols.

Isolated scratch lab on 4287: PID 30828 child of tracked 29884. All writes use
the previous session's scratch roots and synthetic Diagram QA roster. In dark
mode the inactive H2/O2/Ar/He stems were RGB(119,127,137), nitrogen's manifold
held a sealed tone RGB(132,82,139). Switching hydrogen on made its line and
stem RGB(223,112,214); bottle stayed red. Light mode line and stem both became
RGB(169,42,156). Viewed screenshot and measured rendered strokes.

Browser checks exercised all top tabs, History replay, deep-link reload,
moment permalink, SVG and CSV exports, and Back/Forward. History and exported
SVG matched the dark hydrogen stem. Vacuum rails were 76px before/after
scroll attempts at 1280x1000 and 1280x700. No new anchors or teaching copy.
Two known undefined-animation console errors appeared during standalone SVG
navigation; origin unproven, as recorded in the earlier SVG integration log.
They did not prevent reading the exported SVG's correct computed strokes.

Scratch process tree stopped, both IDs gone and 4287 freed; tab closed and
viewport reset. Owner service 4186 observed as PID 25628 at verification and
cleanup; this session did not control it. Pi hostname resolution was unavailable
in the preceding ships; no deployment to Pi performed here.
