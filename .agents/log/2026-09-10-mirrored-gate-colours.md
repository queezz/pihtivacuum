# Mirrored gate colours (0.20.7)

Owner reported the mirrored closed-GVU configuration. 0.20.6 removed its
false gradient, but still chose upstream blue because a plasma vessel belonged
to the component. Completed the rule: dominant and secondary HV colours both
come from reachable running turbo served sides. Rank orders those actual
sources. No chamber membership can introduce an absent pumping colour.
Updated AGENTS.md with this amendment. No geometry or connectivity changes.

129 tests pass; diff --check clean. Mirrored the 0.20.6 regression matrix to
cover both themes, bypass/crossover routes and opposite gate shut/open/stopped
turbo cases. Existing air/gas and rough mixing tests remain green.

Scratch lab 4287 used fresh synthetic flipped-data and Diagram QA roster,
isolated runtime/key paths, bytecode off. Browser measured both bodies dark
green RGB(86,227,148) with GVU closed, blue/green gradient on opening GVU,
and solid green again after closing. Light bodies were RGB(14,138,70).
The readout named TMPD as the sole pump in the closed-GVU case. History
reload and exported SVG matched that solid green. Top tabs, selected-moment
permalink, CSV/SVG exports and Back/Forward exercised; Vacuum rails stayed
76px before/after scroll at 1280x1000 and 1280x700. No new anchors or teaching
copy. Tab closed and viewport reset.

Scratch PID 24332 stopped with lab after listener ownership verification;
4287 freed. Owner port 4186 untouched by this session. Pi deployment remains
unperformed because its hostname was unavailable in the preceding ships.
