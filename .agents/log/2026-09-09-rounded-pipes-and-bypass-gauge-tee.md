# Rounded pipes and bypass gauge tee (0.20.3)

Integrated the owner's local/diagram-update.svg, including his second save
with rounded corners. The source remains untouched. Static copy SHA-256:
BFC474D8BA585068A58FE2FBFA80D913CF0558D3C6A5555571728B277A05BB68.
The static copy is byte-identical to the source; no regrouping or SVG edits
were necessary. Existing IDs remain. The new tee and vertical segment are
already in pipes-bypass-manifold, and the opaque junctions follow the lines
in paint order. Vessel depth and the existing nested gauge stems stay as drawn.

Added bypass-manifold-t-downstream-t-abs to the bypass volume's elements and
junctions, and bypass-manifold-downstream-line-two-t to its elements. No
connectivity, gauge ownership or hardware assumptions changed. The existing
prediction now paints both on Vacuum, History and state.svg. Version copies,
release assertions, authored width assertion and junction checks were updated.

## Verification

93 pytest tests passed. git diff --check passed. No duplicate SVG IDs.
Bypass group membership exactly matches the expanded map. Original source
and adopted copy hashes match, preserving the entire authored render.

Scratch lab service on loopback port 4287 with isolated LAB config, runtime,
logs, diagram state, operator roster, session key and control-data location;
bytecode disabled. Listener 17824 was confirmed a child of tracked PID 21732.
The owner's port 4186 remained on PID 4660 throughout.

Browser checks: selected a synthetic operator, set Membrane installed, marked
upstream bypass gate and bypass rough pump/valve, and saw the new tee and
segment take rough-vacuum colour. Dark/wide gave RGB(198,146,66) on both,
tee fill and stroke matching; pipe width 12.8px from authored 8px. Light/normal
reload gave RGB(168,106,0), with release asset key 0.20.3.
History replay, deep-link reload and exported SVG showed the same geometry
and prediction; exported dark/wide computed paints and width matched the page.

Perimeter checks exercised top tabs, the selected moment permalink, SVG and
CSV export links, Back/Forward between replay and SVG, appearance controls,
and phone drawer. No new anchors. History rails stayed at 76px while scrolling
at 1280x1000 and 1280x700; Vacuum rails also stayed 76px (page had no scroll
range). At 390px the page width was 375px, with no horizontal overflow.
Used the diagram and replay interactively across the checks; first action
is operator choice, and next work starts with a diagram press or operation.
Prediction explanation appears once on each drawing page.

Two console TypeErrors about an undefined animation property were captured
while navigating the standalone SVG via the browser tooling. Their source
was not identified; application JS has no matching expression, and subsequent
normal Vacuum reload produced no additional errors. Do not describe this as
a completely clean console or as a proven application defect.

Stopped lab scratch process tree and verified both PIDs gone and port 4287
free; owner's 4186 listener unchanged. Browser tab closed.

## Deployment

Pi deployment blocked: keys-only SSH to pi@pihti failed because hostname pihti
could not resolve, including outside the sandbox. No Pi changes made.

## Scope

The pasted orientation packet was background, not the live work request.
The owner explicitly requested SVG integration and then the rounded-corner
save. No source edits or unrelated orientation actions were performed.
