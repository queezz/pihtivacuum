# Reuse the drawing's reference data — 2026-09-10

queezz asked to improve tab switching, clarifying that he meant the SVG appearing.
Measured the Pi's local HTTP response: Vacuum and History about 6ms. On this PC,
resolving pihti cost 1.0-2.7 seconds for a new curl process; direct IP was about
11ms and curl's reused hostname lookup about 10ms. No DNS settings were changed.
This was separate from the application's redundant diagram-resource requests.

0.23.6 adds release-keyed immutable caching for /elements-config and /plumbing,
with the enriched map intact. The same URLs and diagram.svg preload in the head
and are reused by fetch, with no duplicate transfer. Everything representing
current state or machine-local settings stays no-store. Warm loading also needs
a ready flag: History cannot depend solely on catching an event that may have
fired before its DOMContentLoaded listener attaches.

## Verification

Synthetic Lab harness, loopback only, all writes outside Dropbox. Injected
250ms endpoint delays and requestAnimationFrame/computed-style observations.
Before: warm Vacuum's first fully coloured SVG frame 552ms, config 9237 bytes
and plumbing 33085 bytes transferred on every visit; settings waited in the
connection queue and finished at 514ms after its request began. After warming
0.23.6: first complete frame 309ms, configuration/map/SVG transferSize all zero,
only five fresh setup requests. History first completed frame 584ms before and
544ms after; its event-list and selected-prediction work still costs time. Cold
release load is still cold (1226ms observed); these are delayed scratch results,
not claims about every Pi load or a cold browser. No bare/green intermediate SVG
became visible. Tests prove version rollover and that dynamic data never cache.

Perimeter Walk on the same synthetic service: own tab and all four tabs,
Back/Forward, selected History deep-link reload, More, theme/thickness controls,
Practice valve change, Undo/Discard, phone drawers. At 1280x700 and 1280x1000
rails stayed y=76 across scrolling; page scroll stayed zero. No fragment anchors
are defined by these surfaces. There is no new user-facing control or teaching.
Gates: 157 pytest cases and 12 Node cases passed, JS syntax and diff whitespace
checks passed. Core Ruff retains only the same two pre-existing F841 findings
in tests/test_server.py; the change adds none. No production data were copied.

Scratch stopped through Lab; tracked PID 67664 exited and port 48937 verified free. The external harness is retained for timing reproduction.
