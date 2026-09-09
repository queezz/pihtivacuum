# Changelog

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
