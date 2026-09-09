# Slow gas-line roughing hint (0.20.8)

Owner distinguished real rough connectivity from useful pumping speed:
metres of quarter-inch gas tubing make this route very slow. Added authored
slow_pumping entry boundaries (gasline-main, flow-calibration-valve). The
readout computes reach without these edges, separately from real connectivity
and with atmospheric edges excluded as before. A running pump connected only
through the restricted edges receives the authored route_hint. An alternative
unrestricted path suppresses that pump's hint. If every reachable pump is
limited, the vessel headline says rough vacuum · slow route (or the current
state word); the compact headline retains it. Pump details say slow through
long quarter-inch gas lines. No pressure or duration estimate, no colour,
geometry, guide or connectivity changes. AGENTS.md records the scope.

134 tests pass. Five new cases cover both gas-line entries, propagated vessel
connections, direct bypass supplementation, a closed pump route and a pump
with an alternative direct path. Predictions with/without route metadata have
identical volumes, elements, mixes, gases and gas symbols. diff --check clean.

Scratch lab 4287 used a fresh slow-route-data directory with synthetic state
and Diagram QA. Listener 11148 child of tracked 23900. Owner 4186 PID 25628.
Browser readout showed gas-panel-only roughing as slow; opening bypass-l2
admitted the running bypass pump and removed the slow-only headline while
retaining the gas-panel pump's qualifier. Closing it restored the hint.
Compact card, dark mode and phone drawer retained readable wording. Inspected
screenshot; text wraps within its rail. Rails held at 76px at both 1280x1000
and 1280x700. All top tabs, History latest/reload/permalink, SVG and CSV exports,
Back/Forward exercised. History retained the route explanation. No new anchors;
the headline states the limitation and pump detail names its reason.

Tab closed, viewport reset. Lab scratch tree stopped, PIDs gone and 4287 free;
owner listener unchanged. Pi deployment remains unperformed because its
hostname was unavailable in the preceding ships in this session.
