# Changelog

## 0.28.3

- Make the whole water valve card prominent: light blue for ON, pale grey for OFF, with dark lettering and a contrasting valve outline. Unrecorded stays dark and dashed.

## 0.28.2

- Arrange Setup equipment cards with dedicated left pictograms, middle labels and right controls. Add simple NI logger and Langmuir supply pictograms; retain the compact two-row grid.

## 0.28.1

- Improve Power diagram contrast on its dark ground: lift cathode housing, restore readable assembly labels, and brighten the existing potential colours consistently across wires, electrodes, junctions and labels. Preserve all geometry and pictograms.

## 0.28.0

- Withdraw Operations and Current guide from Vacuum; retain Practice, line configuration and predicted state.
- Warn when running turbos reach gas or air, including remembered unroughed contents. Preserve that warning across prediction/memory updates instead of allowing the turbo's high-vacuum colour to erase it. Show accurate gas/air wording in the shared warning banner.

## 0.27.6

- Preserve the existing plug state when switching a gauge off from Vacuum or switching power off. Capture the pre-press state so legacy implied plugs cannot fall back to older unplugged records. Activation records its implied plug explicitly. Unplugging remains an operator press.

## 0.27.5

- Keep History's selector and calendar fixed while only timeline events scroll. Selection reveal scrolls the event list; heading and Find stay visible. Tighten short-window spacing and remove redundant timeline explanation. 0.27.4 was a local layout preview.

## 0.27.3

- Link Vacuum CC Pi to Power SingleGauge power in both directions, including Practice saves. Power on also plugs it in; unplugging switches the linked gauge off. Each history keeps its own names.

## 0.27.2

- Remove small break marks from unplugged pictograms; separated plug halves and muted colour communicate disconnection.

## 0.27.1

- Dim unplugged device cards while keeping controls readable.
- Select Vacuum or Power History in the left rail, retaining separate logs and remembered moments. Remove redundant history links and breadcrumbs; redirect old Power-history URLs with their moment preserved.

## 0.27.0

- Link Plasma/QMS IG filament state between Power and Vacuum. Vacuum-on implies
  controller power and plug; Power unplug/off clears the Vacuum IG. Each
  diagram records its own related changes in its separate history.
- Apply the existing Vacuum exposure check to Power IG activation, including
  Practice review and blocked automatic saving of warned sequences.
- Colour a powered IG card blue with filament off and green with filament on.

## 0.26.4

- Tint the whole powered-on device card green in live, Practice and History.
  Plug state alone does not highlight the card.
- Enlarge equipment pictograms, arrange gauge controls beside the icons and
  give gauge power buttons a filled, fully clickable button area.
- Record ordinary Power clicks without a confirmation dialog, per owner.
  Practice remains available; recent-edit mode is deferred.

## 0.26.1

- Apply Vacuum's operator click rules to Power: read-only controls are disabled,
  confirmed presses record immediately, and Practice offers Undo, Discard,
  one-event Save and the configured fallback timer. Pending Practice survives
  tab navigation without a leaving-page prompt.
- Keep Power history separate from Vacuum history while reusing the calendar,
  grouped timeline, selected-moment replay and CSV export. Earlier power
  snapshots remain readable in Power history without rewriting their source.
- Move the water control below the target wire, above Baratrons/MFCs; remove
  the redundant Power heading.

## 0.25.6

- Give the water control clearance from the cathode-box label and upper
  electrical wire. Verified the rendered label gap after owner caught the
  collision missed in the previous visual review.

## 0.25.4

- Add manually recorded cathode cooling water to Power snapshots. The valve
  label and two pipe circles show blue for on, grey for off and unrecorded
  until an operator records the state.

## 0.25.3

- Add the owner-reviewed electrical diagram on a dark Power tab, with separate
  power, plug and gauge annotations. Rehearse locally, discard, or save one
  operator-attributed snapshot. Unknown states remain unrecorded.
- Store power snapshots separately from vacuum history; reject stale saves.
- Arrange setup equipment in two rows of three equal cards, including the
  membrane heater. Power on implies plugged; SingleGauge has no filament toggle.

## 0.24.5

- Read upstream ion-gauge channels and same-run Kikusui telemetry, preserving
  recorder-local time, recorded ranges and instrument-off gaps.
- Choose and arrange all numeric curves in the main view. Compare pressure,
  current, or pressure with MFC signal/setpoint using independent unit axes.
  Add log/linear scales, chart order, linked time zoom/pan and PNG export.
- Apply a manual Baratron zero offset per recording. Show signed values on
  linear axes and mark corrected curves; keep original samples unchanged.
- Keep exports in the right rail: original same-run CSVs as ZIP, ADC CSV,
  displayed-curve CSV with original/offset/corrected values, and chart PNG.
  Collapse data notes and remove repeated explanatory text.

## 0.23.6

- Reuse release-stamped equipment configuration and plumbing JSON between
  Vacuum and History visits; preload these and the SVG from the page head.
  Live state, warnings, rig settings and history remain uncached.
- Let History recognize a drawing that finished loading before its listener
  attached, so a fast cached load cannot leave the selected moment unpainted.

## 0.23.5

- Show the diagram only after its state and predicted colours are ready, removing
  the bare SVG and green-valve flashes when moving from History to Vacuum.
- Load initial resources together and return live state plus prediction in one
  read-only snapshot. History also waits for its selected moment's prediction.
- Show an explicit initial-load error instead of exposing an uncoloured drawing.

## 0.23.4

- Move History's predicted state and its single legend to the top of the right
  rail, beside the drawing. The phone drawer is named State & moment.
- Separate the export buttons with a 10px gap and consistent padding.

## 0.23.3

- Give rails more width as the window allows; History scrolls at the rail edge
  instead of inside the timeline card, with a local Find for longer days.
- Open History on the last selected moment, or the latest change on a first
  visit. Selecting a day shows its final recorded state, carrying the last
  known state across days without changes. Explicit moment links take priority.
- Distinguish empty history from a failed load and ignore outdated prediction
  responses when rapidly selecting different moments.

## 0.23.2

- Restore the oil reminder above the live drawing in amber, while retaining
  ordinary recording without automatic Practice or pulsing.

## 0.23.1

- Move MFC reminders to cutoff-opening confirmations; no idle banner or pulse.
- Show stopped-rotary oil risk as a muted reminder until vented. Normal stop
  then vent records without automatic Practice, timer hold or mistake audit.
- Preserve urgent ion-gauge and running-turbo exposure warnings.

## 0.23.0

- Group nearby same-operator history events into expandable sequences. A gap
  over one minute, a new day or operator, or a Practice save starts a new entry.
- Select the final state from the group header; expand to select original
  events. Inner-event links expand their group and reveal the selection.
- Keep recorded events, calendar counts and exports unchanged.

## 0.22.0

- Make oxygen and hydrogen mass-flow controllers ordinary on/off controls
  with valve painting and separate controller-to-cutoff volumes.
- Warn and pulse at closed cutoffs for possible trapped pressure, including
  with an off controller. Distinguish unknown pressure, remembered gas/air,
  possible supply leakage and an on controller feeding the section.
- Worsening warnings use Practice/Undo and the separate attempt audit.
  Preserve the authored SVG geometry and ids.

## 0.21.0

- Pulse affected equipment and show standing gas/air ion-gauge, turbo-air and
  stopped-oil-rotary advisories above the drawing. Keep historical warnings.
- Divert warned presses into Practice with Undo and automatic saving paused.
  Direct updates defer to Practice; warned sequences need explicit save review.
- Record operator, time, intended press, warnings and context separately in
  ignored warning_attempts.jsonl; offer its download in History.
- Teach diagram first, hardware second beside Practice.

## 0.20.9

- Warn of oil leaking into pipes when an oil rotary is stopped with
  predicted or remembered vacuum at its inlet. Exclude the dry scroll.
- Keep the advisory visible when the state card is collapsed; show it
  before a risky press, during Practice and in historical replay.
- Preserve inlet vacuum on the first stop from an older state file.

## 0.20.8

- Qualify pumping that can reach a vessel only through the long quarter-inch
  gas lines as a slow route. Name the limitation beside the affected pump,
  and keep it in the compact headline when all pumping routes are slow.
- Recognize alternative direct routes; preserve connectivity and colours.

## 0.20.7

- Derive the main high-vacuum colour from reachable turbo sides too:
  joined vessels pumped only by TMPD are solid green with GVU closed;
  TMPU alone gives solid blue. Both reaching produces the gradient.
- Test both mirrored gate configurations and stopped-turbo passages.

## 0.20.6

- Require both turbo pumping sides to reach a joined volume before showing
  a two-sided high-vacuum gradient. A turbo behind closed GVD no longer
  adds a false contribution. Genuine rough-pump and air/gas mixes remain.

## 0.20.5

- Colour all five gas bottle stems with their connected line prediction,
  including dark and sealed tones, on Vacuum, History and exported SVGs.
  Preserve the bottles' own operational colours.

## 0.20.4

- Paint the nitrogen source handle using the shared valve logic: open fill
  and edge follow the manifold prediction; closed uses the theme's closed
  valve inks. Bottle colours and gas connectivity remain unchanged.

## 0.20.3

- Adopt the updated drawing with thicker pipes, rounded corners, a curved
  crossover and the bypass absolute-gauge tee. Preserve the authored groups
  and drawing order.
- Colour the new tee and its connecting pipe with the bypass prediction on
  Vacuum, History and exported state SVGs.

## 0.20.2

- Add a remembered Dark diagram option on Vacuum and History, with a lifted
  slate ground, electric blue and bright green vacuum, quieter amber roughing,
  vivid vent red and distinct magenta gas. Sealed colours fade into the ground.
- Use pale valve rims and a visible empty membrane marker in dark mode.
- Place Dark diagram and Draw thick pipes at the top of More, before meanings.
- Historical SVG images follow the selected theme and thick-pipe setting.
- Preserve the authored SVG geometry, component identities and connectivity.

0.20.0 and 0.20.1 were local review previews. Earlier releases are recorded
in `.agents/log/`.
