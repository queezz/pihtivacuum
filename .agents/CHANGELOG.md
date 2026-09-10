# Changelog

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
