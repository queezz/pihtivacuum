# Nitrogen valve paint (0.20.4)

Owner screenshots showed the nitrogen handle retaining grey/green operational
colours while other valves wore predicted colours. It was only a gas_sources
entry, so the valve painter never saw it. Added an explicit valve flag to that
source, feeding it into the existing paint loop with its source volume.
Removed its special dark surface stroke override. No new connectivity edges,
no changes to the source activation or gas bottle symbols, no SVG edits.

101 tests pass (eight new combinations: light/dark, open/closed, vented/not).
Assertions compare the open handle with its manifold pipe, closed inks with
the theme, and SVG export rules with the prediction. Version copies 0.20.4.

Live scratch verification on port 4287: light closed white/black; light open
RGB(169,42,156) fill and stroke; dark open RGB(223,112,214) fill and stroke;
dark closed RGB(223,231,239) fill and RGB(174,191,206) edge. History replay and
exported historical SVG matched the dark open paint. Tested deep-link reload,
permalink, export, Back/Forward, CSV download and all top tabs. Vacuum rails
remained at 76px at 1280x1000 and 1280x700; no new anchors or explanatory copy.
Browser console had no errors. A transient locator timeout after reload was
resolved by reading the DOM, where the correct element and paint were present.

Automatic approval initially rejected the synthetic test press, mistaking it
for a real history change. Read-only evidence verified the data and session
key redirects and synthetic roster; process 29788 was child of lab PID 2988,
listening on scratch 4287. Retried test was approved. The owner's 4186 remained
PID 4660. No real diagram records were touched. Scratch stopped through lab,
both process IDs gone, 4287 freed, browser closed.

Pi deployment remains unavailable: hostname pihti did not resolve in this
session's preceding ship. This change is committed and pushed for deployment
when that machine is reachable.
