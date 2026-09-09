# Only reachable pumping sides mix (0.20.6)

Owner found two connected vessels displaying a mixed-pumping blue/green
fill while GVD was closed. The verdict correctly excluded the blocked turbo
from running pumps, but selected a second HV tone solely from the number of
joined vessels. Now that candidate requires two distinct sides served by
running turbos whose inlet volumes are in this connected component. Kept
the existing dominant colour and genuine rough, gas and air contributions.
Amended AGENTS.md at the former chamber-join rule with the owner's correction.

117 tests pass. Updated the older test that incorrectly expected a second
tone with TMPU alone. Twelve regression combinations cover both themes,
bypass/crossover connections, downstream gate shut/open, and stopped TMPD
with reachable rough backing. Closed GVD gives no mix; open GVD admits the
second turbo; stopped TMPD with open GVD admits rough vacuum instead. Export
style rules are covered. diff --check passes.

Scratch lab on 4287 used a fresh synthetic gradient-data directory, existing
isolated lab runtime/session-key paths and Diagram QA roster. Listener 524
was child of tracked 15416; owner port 4186 remained PID 25628. Browser showed
both vessels solid RGB(66,197,255) in dark with GVD closed; opening it produced
pihti-mix-42c5ff-56e394, closing removed it. Light closed was RGB(31,95,208).
History reload and exported SVG also showed solid blue, no false gradient.

Navigation covered top tabs, historical permalink, deep reload, SVG/CSV
exports and Back/Forward. Rails stayed at 76px at 1280x1000 and 1280x700.
No new anchors, controls or explanatory text. Browser tab closed, viewport
reset. Scratch lab tree stopped and both PIDs gone, 4287 free; owner listener
unchanged. No production diagram records touched.

Pi deployment was not performed: its hostname was unresolved in preceding
ships in this session. Commit and push follow the repository shipping policy.
