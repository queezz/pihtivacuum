# Power operator rules and separate history

Owner corrected the snapshot-specific editing workflow: Read only must mean
read only, and Power must use the familiar operator/Practice interaction.
Owner explicitly cautioned against blindly combining the two histories.

Power now records confirmed individual presses immediately, requiring an
operator on both client and server. Read-only SVG buttons lose their keyboard
tab stops and reject interactions. Practice keeps an ordered local list with
Undo, Discard, one-event Save and the machine's existing fallback interval.
Its pending sequence persists in sessionStorage across navigation. No unload
trap. Only Practice has a Save action now.

Power state is reconstructed from its own power_history.csv. Earlier JSONL
snapshots are preserved and exposed as Power-only history without rewriting.
Vacuum state and logs are untouched. Power history reuses history.html and
history.js with separate endpoints, address and remembered-moment key. Unknown
Power controls stay unrecorded when replaying before their first change.
CSV export includes the Power-only records. The History tab follows the active
diagram; explicit /history remains Vacuum history.

The water control moved below the target wire, over Baratrons/MFCs. The duplicate
Power heading was removed in the preceding commit.

Validation: 174 pytest tests and 11 Node tests pass, including write attribution,
separate logs, companion power/plug/filament changes, Practice one-event saving,
legacy preservation, history routing and historical unknown states. JS syntax
and git diff checks pass. Scratch Lab service uses external runtime on 48938.
Browser use covered read-only disabled controls, operator selection, Practice
confirmation and Undo, navigation without a leave prompt, every top tab and
brand, Back/Forward, Power-history moment selection/reload, calendar navigation,
search, CSV download and both mobile history drawers. Desktop rails measured
76px at 1000px and 700px heights; 390px viewport has no page-wide overflow.

Visual review caught History's vacuum loading aspect ratio clipping the taller
Power SVG; marking its container ready and using its natural height corrected
it. Rendered container and SVG heights now match. Screenshot saved to
local/power-history.png. Preview remains available for owner review.
