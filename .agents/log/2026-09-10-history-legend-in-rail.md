# History legend in the rail - 0.23.4

Owner asked to keep the predicted-state legend beside the drawing and separate
the export buttons whose touching borders looked broken. This explicitly
supersedes the old History-specific rule that reserved the right rail for the
selected moment and exports. The state card now leads that rail, keeping all
existing prediction and appearance ids and one legend. Natural card heights
prevent flex compression. Export links use a grid with 10px gap and 10px/12px
padding. The phone context drawer is named State & moment.

155 pytest and 7 Node tests pass. Updated the existing placement assertion to
check that History's one legend belongs to the context rail. Browser scratch
uses synthetic history and isolated lab/application write roots. At 1280x700
the complete state card ends around 564px and all seven swatches are visible;
export gap measured 10px. Checked 1000px height and mobile layout, themes,
More/Less, historical selection/reload, SVG Back/Forward, all top tabs,
exports, and mobile drawers. No pagination decision was assumed from the
previous options discussion. Scratch shutdown and shipping result are in the
task tool evidence. The Pi hostname was unavailable in the preceding ship;
deployment cannot be claimed from the pushed commit alone.
