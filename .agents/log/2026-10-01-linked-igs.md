# Linked IG annotations

Owner requested linking the IG filament toggles and plug dependencies with
Vacuum's IGs, plus a distinct blue card for a powered controller without its
filament on. Linked Plasma IG to bypass-ionization-gauge and QMS IG to
downstream-ionization-gauge. Only these shared gauge changes cross the two
separate logs. Vacuum activation records the corresponding controller power
and plug; unplug/power-off clears filament and Vacuum IG. Filament-off retains
controller power. Both Practice save routes propagate only after recording.

Power IG activation checks the existing Vacuum predictor exposure warnings.
A warned direct press stays unrecorded and enters Power Practice. An automatic
save cannot bypass the review. Explicit reviewed saves carry that note in both
histories. Current Vacuum gauge state is authoritative for Power filament paint.

Validation: 176 pytest tests and 11 Node tests pass. Added cross-tab linkage,
both Practice saves, per-diagram history IDs and exposure-gate regression tests.
Scratch browser verified Power filament-on paints the Vacuum upstream IG,
Vacuum-off paints Power's filament off and blue standby card. Power-on with
filament-on paints green. Preview saved as local/power-linked-igs.png.
