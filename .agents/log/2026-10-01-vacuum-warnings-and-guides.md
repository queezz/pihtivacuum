# Vacuum warnings and withdrawn guides

Owner requested checking missing TMP warnings and removing incorrect operations. Found turbo warnings restricted to air and remembered exposure considered only when the current verdict was isolated. Turbo prediction could therefore mask remembered air/gas as high vacuum.

Added reachable-component memory checks for unroughed air/gas, excluding remembered exposure when a rough pump reaches the component. Prediction returns unroughed volumes; memory retains prior air/gas there while the turbo warning persists. Closed gates exclude disconnected contents. Gas receives warning wording rather than being described as vent air. Operations and Current guide cards removed; live initialization no longer fetches guide data. Historical source guide files retained without UI exposure.

181 pytest and 11 Node tests pass, including unroughed air/gas gate opening, warning persistence, closed-gate exclusion, rough-memory clearance and live gas exposure. Managed scratch Lab synthetic gas case renders warning above diagram and equipment-warning-pulse on TMPU. Desktop rails stay at 76px before/after scroll at 1280x700; 390px viewport has 375px document width and visible warning. Screenshot local/vacuum-turbo-warning.png. Scratch synthetic state restored after stopping preview.
