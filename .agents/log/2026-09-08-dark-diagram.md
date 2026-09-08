# A dark ground for the same drawing - 0.20.0

Owner request: build dark mode on the diagram as it stands, with brighter blue
and green vacuum, quieter forevacuum and alarming vent air. Geometry is his;
`diagram.svg` is byte-unchanged.

The Dark diagram checkbox sits with Draw thick pipes on Vacuum and History.
It is a read-only browser preference remembered in localStorage. Switching
repaints the cached prediction without a request or history write, including
Practice. Light remains the default until the reader chooses dark.

`plumbing.json` holds the dark palette and gas-panel backing-surface inks.
The server supplies the browser the same colour conversion used for exports,
including sealed tones. History image links carry theme and width. Sealed pipes
blend halfway toward charcoal; hatching stays on vessel bodies only. Pumps stay
grey when stopped, shut valves white with black rims. Brightness supplies the
luminous appearance without adding blurred halos across pipe gaps.

## Verification

Scratch Lab instance on loopback 48936; every application write path outside
Dropbox, synthetic operator/state only. Listener child was confirmed under the
tracked Lab parent. No owner service was used for testing.

Browser: preference persistence on reload and between Vacuum/History; Practice
press, switch with one pending press, Undo and Discard; grey stopped pumps and
white/black shut valves; downstream vent through stopped turbo showed red/amber
body mixing; sealed blue body had charcoal hatch. Historical SVG link matched
theme/width; standalone SVG displayed on charcoal. Back/Forward and deep-link
reload preserved the selected historical moment.

Perimeter: all four top tabs, History from its deep link, moment/image links,
disclosures, phone drawer theme switch at 390x844 without horizontal overflow.
History rails measured 76px at rest and at scroll 112px (1280x1000), 350px and
412px (1280x700). No new anchors. More than two minutes of synthetic operator
use. The preference adds no explanatory prose or duplicate legend.

Two animation-property errors appeared in the browser instrument while reading
the standalone SVG, which contains no application JavaScript. No corresponding
error occurred in the normal application theme/Practice flows.

Gates: 93 tests passed, including colour/connections parity in all four modes,
live mixing and actual sealed memory, XML-valid themed export and unchanged
state/history after theme reads. node --check passed for both modified scripts;
git diff --check passed. Ruff core E4/E7/E9/F passed. Full Ruff reports 38
pre-existing findings: compared source-by-source with HEAD, zero new findings.
Ruff was installed only in the existing external project environment.

No delegated agents. Shipping and scratch cleanup results follow.

## Owner review corrections and final release

The owner reviewed the preview live: the field was too black, the blue wanted
more fluorescence, the exposed checkboxes were easy to press accidentally,
the empty membrane marker was invisible and valve black rims were unsuitable.
Final 0.20.2 uses slate #293440, electric blue #42c5ff, pale shut-valve fill
#dfe7ef with #aebfce rims and 90% opacity for the empty dashed membrane marker.
The nitrogen source valve has its independently drawn rim themed too; only the
rim is changed, so its operational fill survives theme switches. Both switches
lead More, ahead of the meanings. AGENTS.md records the owner's amendments to
the earlier exposed-width-switch and black-valve-rim rules.

The earlier notes above describe the first preview. Final palette, placement
and valve treatment are those in this correction. Version increments ensure
browsers that saw either preview request fresh assets.

Final verification: 93 tests passed after owner corrections; core Ruff and both
JavaScript syntax checks passed. Browser verified active nitrogen fill unchanged
through light/dark switches, membrane rim rgb(174,191,206) at opacity 0.9,
closed valve pale/light, and switches hidden until More. With More open, rails
stayed at 76px across scroll 0 to 656px at 1280x700 and 0 to 356px at 1280x1000.
At 390x844 both switches worked without horizontal overflow. Scratch service
stopped through Lab; tracked process absent and port 48936 confirmed free.
