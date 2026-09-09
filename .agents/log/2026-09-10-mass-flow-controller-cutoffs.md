# Mass-flow controllers and cutoff pressure — 0.22.0

Owner requested on/off MFCs, possible leakage while off, and pressure warning
for the small volume between MFC and closed cutoff. Existing rectangles used
without renaming; existing to-cutoff path ownership split in map, no SVG edits.
MFCs reuse normal valve connectivity, paint, toggles, Practice and history.
Standing advisory is present at closed cutoffs, escalating for supply gas/air
and MFC on. Question about warning scope was optional, unanswered; proceeded
with stated conservative default, not an assertion that pressure is measured.

154 pytest tests pass. New coverage exercises both gases, all on/off and cutoff
combinations, separate outlet paint, both themes, and unknown/trapped/fed warning
severity. Older gas-flow fixtures now explicitly turn on their controller;
oil-specific assertions filter oil warnings rather than all equipment warnings.

Scratch lab service 4287 with synthetic Diagram QA and redirected data. Browser
proved hydrogen MFC on feeds outlet but vessel stays HV behind closed cutoff,
warning escalates and enters Practice with paused timer, and Undo restores pale
closed MFC. Oxygen independently toggled and saved to history. Pulse animation
name measured; both MFC and cutoff highlighted. Perimeter Walk: Vacuum, Plot,
Services, History; 1280x1000/700 rail tops remain 76 after scroll; history latest,
reload, permalink, themed SVG, Back/Forward, CSV and warning-audit downloads.
390x844 settled layout has no horizontal overflow and warning remains above SVG.
Owner service untouched; scratch stopped at finish. Pi hostname deployment
check and push results are in task tool evidence.
