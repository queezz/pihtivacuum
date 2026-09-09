# Expandable history time groups — 0.23.0

Owner asked to group close events into logical states while retaining expansion
and individual selection. Chosen default: adjacent gaps <=60s, same operator/day;
saved Practice sequences stay standalone. Pure presentation over original indices,
no source data or API changes. Header shows time range/count/operator and selects
final state; separate 44px expansion target preserves selection. Inner timestamp
links expand group, and timeline scroll reveals the chosen event.

Validation: 154 pytest pass; three Node native tests cover inclusive gap boundary,
empty input, operator/day/unknown/invalid boundaries and standalone Practice saves.
Browser scratch lab with four synthetic events: three group together and later
one stands alone. Group selects 00:01:35; inner row selects 00:01:15 and reload
retains selection/expansion. Fresh origin 4288 used for final cached assets after
initial 4287 verification. Both desktop rail tops 76 at 1280x1000 and 1280x700;
selected child bottom 617.7 inside timeline bottom 667.3. 390x844 phone drawer
expands/collapses and selects children with no horizontal overflow, 44px toggle.
Perimeter Walk: Vacuum/Plot/Services/History; moment permalink, SVG export,
Back/Forward, reload and CSV download. No real operator data used or altered.
Scratch process ownership and stop verified in tool evidence. Release push and
Pi deployment result also recorded in task tool evidence.
