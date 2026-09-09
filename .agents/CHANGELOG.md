# Changelog

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
