# History landing and rail room - 0.23.3

Owner asked for a cleaner timeline card, a useful initial recorded state with
remembered selection, and wider rails that remain usable on a laptop. The
attached orientation packet was context, not the live request.

Changed the History card to natural height with one rail-edge scroll area,
added a local Find, and widened the shared rail track with a 17-20rem clamp.
History restores an exact stored timestamp, prioritizes explicit URLs, defaults
to latest, and selects the last recorded event at or before a chosen day's end.
Empty/unreachable/before-history states are distinct. Concurrent History
prediction requests use a generation number so an older response cannot repaint
a newer selection. Recording and grouping semantics are unchanged.

Validation: 155 pytest passed; 7 Node tests passed (grouping plus selection,
missing/blocked storage, deep-link priority, empty days, empty/error loads).
Perimeter Walk on an isolated lab service using 100 synthetic events: top tabs,
self-tab return, group expansion and inner event, remembered selection, permalink
reload, SVG and Back/Forward, theme/thickness export, CSV/audit links, calendar
months and days, local Find, and mobile drawers with Close/Escape. At 1280px
rails measure 272px and the diagram about 641px; rail tops stay 76px at 700px
and 1000px heights. At 1440px rails measure 285px. At 390x844 the diagram fits
without horizontal overflow. First upgrade from 0.23.2 requested 0.23.3 assets
on ordinary reload; subsequent development edits were checked on a fresh
scratch origin to avoid reusing intermediate 0.23.3 assets.

Scratch is outside Dropbox. Lab's launcher PID and socket child relationship
were verified; scratch shutdown and shipping outcomes appear in task tool log.
