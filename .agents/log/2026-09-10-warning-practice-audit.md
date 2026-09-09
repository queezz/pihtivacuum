# Warning Practice and audit — 0.21.0

Owner asked for on ion-gauge gas/air warnings, affected-item pulsing, diagram
before hardware, automatic Practice/Undo, and who/what/when attempt attribution.
Implemented standing equipment warnings shared with preflight; sealed gas/air
also warns. Warned browser presses audit separately and enter Practice. Timer
holds until explicit save or leaving Practice. Server refuses direct warned
updates and automatic warned sequence saves; explicit reviewed save remains
possible because this is an operator aid, not an interlock.

Validation: 145 pytest tests pass, including both gauges with gas/air, read-only
preflight, separate attributed audit with timezone, unchanged state/history,
stopped-rotary deferral and manual-only warned sequence saves. diff --check clean.
Scratch lab service on 4287, synthetic Diagram QA and redirected data. Browser
proved automatic Practice, visible warning, Cancel save, Undo clearing pulse,
explicit reviewed save and separate audit download. Rendered animation-name
was equipment-warning-pulse; opacity samples .757171, 1 and .959991 differed.
CUA does not expose SVG getAnimations (method unavailable), so actual opacity
and screenshots establish animation; reduced-motion rule uses the same opacity
animation at 3 seconds. No geometry or pointer behavior changes.

Perimeter: Vacuum/Plot/Services/History; both rail tops 76 at 1280x1000 and
1280x700 after scroll; 390x844 settled layout has no horizontal overflow and
warning above drawing. History latest/reload/permalink, standalone themed SVG,
Back/Forward, CSV and attempt downloads exercised. Warning on historical replay
visible. No production/operator service touched. Pi hostname previously failed
to resolve; deployment remains pending reachability. Scratch cleanup and commit
recorded in task tool evidence.
