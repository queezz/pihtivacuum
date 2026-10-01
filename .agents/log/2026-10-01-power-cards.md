# Power cards and hit areas

Owner requested whole-card highlighting for powered devices, larger pictograms,
gauge controls arranged beside the left-hand pictogram, and fully clickable
power buttons. Added a filled rectangular hit area to all three gauge power
buttons. The icon itself no longer intercepts pointer events. Mouse clicks in
the middle of the filled area toggle without needing to hit the symbol stroke.

Power paint now tints the parent device card and rim green when its power is
active. Plug-only does not highlight. The same paint runs in Practice and
historical replay. PSU pictograms have a larger left column; portrait symbols
have tight viewBoxes, preserving aspect ratio. Gauge icons use the left card
height, with filament/power/plug in a lower-right row. SingleGauge has no
filament toggle.

Owner then removed ordinary-click confirmation dialogs and explicitly deferred
recent-edit mode. Read-only rules, direct attributed recording and Practice
remain. Only leaving a Practice with pending presses still asks to discard.

174 pytest tests and 11 Node tests pass. Browser verified centre-of-button
clicks on Plasma IG and SingleGauge, on/off highlight/reset, no click dialog,
and History card highlighting. No console errors. Rendered PSU icon/text gaps
were measured positive; screenshots reviewed for label overlap. Final preview
is local/power-cards.png. Version 0.26.4 invalidates cached assets.
