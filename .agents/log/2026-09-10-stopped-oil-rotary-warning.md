# Stopped oil rotary warning (0.20.9)

Owner screenshots showed isolated vacuum held at stopped bypass and gas-panel
rotaries. Added explicit oil_sealed metadata to those pumps and RoughU;
RoughD is the dry scroll and excluded. predict returns advisory oil warnings
for stopped oil pumps with live or remembered rough/high vacuum at their own
inlets. Vent air and unknown are not called vacuum; running pumps clear it.
No assertion that oil has actually moved, no device operation or interlock.

Standing amber warning appears outside the state card's collapse, and on
History. Press exposure comparison warns only on newly created conditions,
including opening onto vacuum and stopping a pump. Simulation carries vacuum
memory across a stop without writing. Real update remembers its pre-press
state too: an older memoryless state file otherwise lost its inlet vacuum on
the first stop. Practice can warn before its returned memory has a sealed
since timestamp; known previous vacuum is sufficient. Readout clears when
History has no selected prediction.

140 tests pass; diff --check clean. New coverage: three oil rotaries,
held vacuum, live vacuum through an opened inlet, running/vented/unknown/dry
scroll exclusions, pure press checks, legacy first stop through /update,
and first Practice stop with memory but no sealed timestamp.

Scratch lab port 4287 used synthetic oil-data, Diagram QA and isolated runtime
and keys. UI confirmed pre-press oil warning, persistent warning after real
synthetic stop and reload, warning while collapsed, Practice warning and
Discard clearing it, and History warning after replay reload. Tested all top
tabs, historical permalink, SVG/CSV export navigation and Back/Forward.
Rails remained at 76px at both 1280x1000 and 1280x700. No new anchors. Browser
closed and viewport reset. Early browser confirmations were dismissed before
acceptance; subsequent tests used the visible OK button. No production
annotation data was changed.

Scratch server was restarted after the memory correction, then stopped with
lab at completion; 4287 freed. Owner 4186 was not controlled. Pi hostname was
unavailable in preceding ships; no Pi deployment performed in this change.
