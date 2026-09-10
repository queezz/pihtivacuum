# One complete diagram paint — 2026-09-10

queezz reported bare SVG, then green valves, then vacuum colours on every
History-to-Vacuum navigation. The drawing was inserted before a chain of awaited
requests; operator colours painted before the prediction response arrived.

0.23.5 fetches independent resources concurrently and uses `/diagram-state` for
paired live state/prediction. Initial SVG remains hidden until a complete paint.
History no longer fetches live state before reconstructing its selected event;
its operator and prediction paint happen together, with older replies ignored.
Failure is explicit, including a failed selection after a successful History
paint. SVG geometry, ids, plumbing and palette were not changed.

## Evidence

A Lab-managed loopback scratch service used only synthetic state/history/roster,
with all application writes outside Dropbox. A harness added 250ms to relevant
JSON responses and sampled computed SVG styles on animation frames. Baseline
showed visible grey at 655ms, green valves at 1953ms, final blue at 2228ms. After
fix, only final blue was visible (874ms light; 553ms dark on another navigation).
These are delayed local test observations, not Raspberry Pi speed estimates.
Dark's first visible ground was #293440, valve and running turbo #42c5ff.
History's raw frame was hidden; its first visible frame was fully painted.
Synthetic 503 on the initial snapshot showed the error and no visible SVG.
Removing the failure and reloading recovered normally.

Rendered Perimeter Walk: Vacuum/History/Plot/Services and own-tab navigation,
Back/Forward, selected-moment deep-link reload, and mobile drawers worked.
There are no fragment anchors on these diagram surfaces. At 1280x700 and
1280x1000 both rails remained at y=76; expanding More and scrolling the rail
moved its content (166px observed) while its top stayed 76 and page scroll 0.
390px layout had no horizontal overflow; the diagram fit at 353px width.
Theme and thickness controls remained inside More, one legend in the drawer.
Used the diagram across the checks, including a synthetic valve press, explicit
Practice, Undo and Discard. No intermediate operator palette reappeared.
The initial status adds one short loading/error message, no duplicate teaching.

Gates: 156 pytest tests passed; 11 Node tests passed (first paint and History
grouping/selection); JS syntax and git diff whitespace checks passed. Core Ruff
reported two pre-existing F841 unused variables in tests/test_server.py (colours
and mapping); neither is introduced here. No production data or credentials
were copied into scratch or recorded in this evidence.

Scratch service stopped through Lab; tracked PID 74504 exited and port 48937 is free. Scratch retained for reproducible delayed-response evidence.
