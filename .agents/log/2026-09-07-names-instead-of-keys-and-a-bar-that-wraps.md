# Names instead of keys, and a top bar that wraps (0.10.0)

Commander-dispatched session in a coordinated run of the three PIHTI services
(this diagram, PIHTI Log, ControlUnit), on the work Windows PC. This project
was the *reference* for the run: the other two are copying this Services board,
so nothing about the board's desktop layout, wording, card order or legend was
touched. The two things fixed are elsewhere.

## The stale index, first

`git status` opened showing staged modifications and staged *deletions* of
files that were sitting right there on disk — Dropbox had synced a `.git` from
another machine after the commit was made. `git reset -q` rebuilt the index
from HEAD and the worktree came back completely clean at `3523a8b`, matching
`origin/master`. No real uncommitted work was hiding under it.

## What the Mac audit found (letter `20260907-8cbfd520-ca289d`)

Two P2 defects, both reproduced here before a line was changed.

**The operator selector fell off the right edge of a phone.** At 390 px the
document was 454 px wide against a 390 px viewport, on all five pages, and the
`.tab-meta` block holding the selector started at x 259 and ran to 454 — most
of "Read only" was simply off-screen. The bar is one `flex` row of five tabs
plus the selector and it had no `flex-wrap`, so there was nowhere for the
overflow to go.

**The guide and the History timeline printed machine keys.** "Next ·
bypass-ionization-gauge", "Later · gaspanel-valve-n, gasline-main", and
History's Element field and every timeline row writing `event.id` straight
out. Fleet `WEBUI.md`: what a viewer sees is for the viewer, and a key is a
string meant for the machine.

## Fixed

**The bar wraps rather than overflows.** `flex-wrap: wrap` on `.tabbar` and on
`.tab-group`, `margin-left: auto` on `.tab-meta` so the selector holds the same
right-hand corner whether it shares the tab row or has one of its own. No
breakpoint decides this and no phone-only control was added: at any width with
room for one row nothing moves at all, and below that the selector drops a row.
The tabs wrap too, so navigation can never be pushed off the screen at a width
nobody thought to test.

The one thing to know about the taller bar: `--bar` feeds the sticky rail
offset, and a wrapped bar is 96 px rather than 56 px. It does not matter,
because wrapping only happens well below the 1199 px breakpoint where the rails
stop being sticky and become fixed drawers at `top: 0`. Measured both ways.

**Every component has a name, and it lives in one place.** A `label` line
beside each `id` in `static/elementsConfig.json` — 38 of them — read through a
single `window.pihtiElementName(id)` that `diagram.js` exposes and `history.js`
borrows, the same way `window.applyState` already crosses between them. The
guide steps, the hover tooltip and the confirm box all use it; History
re-renders its timeline and its Selected-moment card when `pihti:diagram-ready`
fires, because the names arrive with the diagram's own configuration and the
timeline is drawn before that.

The names were written by spelling the key out in words, and by borrowing the
vent guides' own wording where they already named a part — the guides say "the
plasma gate valve" for `GVU` and "the QMS ionization gauge" for
`downstream-ionization-gauge` — with the rig designation kept in brackets where
the key *is* the designation: "Plasma turbo pump (TMPU)". Nothing about the
hardware was inferred past that, deliberately: a wrong name on an operator aid
is worse than a key. `directions.md` now carries an owner-work item listing the
seven or eight that rest on the upstream/downstream convention alone and asks
queezz to correct anything that is not what he says at the rig.

**A component the diagram no longer carries says so.** `elementName` returns
empty for an unknown id, and History renders the recorded key in the muted
mono face with "This component is not on the current diagram; its recorded name
is shown." on the row, rather than passing a key off as an equipment name.
Proven with a hand-planted `legacy-pirani-gauge` row in a scratch log.

**And then the names did not fit.** The first pass left `.tl-id`'s
`text-overflow: ellipsis` alone, and the 256 px timeline rail promptly turned
"Plasma gate valve (GVU)" into "Plasma gate valv…" — half a name, which is the
exact reading the names existed to end. The rows now wrap (`overflow-wrap:
anywhere`, time and pill pinned to the row's top) and grow from 31 px to 44 px;
the card they sit in already owns its own scroll, so the rail neither grows nor
becomes a second page scrollbar. Measured with 35 rows at both window heights.

## Two owner health decisions, checked and recorded, no code

Both arrived from `code/pihti-log` and both land on the producers: an idle
ControlUnit reports `ok` with an idle detail (`20260907-086b78af-5a8d73`), and
a pending journal draft stops degrading the shared board
(`20260907-817e5f67-f68a07`, superseding `20260907-ba2d4f0a-afb66f`). Read
`neighbours.py` to confirm this side does not second-guess a producer:
`read_health` passes a reported `ok`/`degraded`/`down` through with the
producer's own detail and only classifies what this machine alone can see — a
refusal, an HTTP error, silence, a malformed body, a missing address. Recorded
in `.agents/ensemble-health.md` with a test that pins it.

## The roster, and why the trio's duplicate-label rule does not apply here

The trio rule is "when two display names collide, render Display Name
(username)". This project has nothing to disambiguate: its roster is this
machine's own flat JSON list of account names, with no username beside a
display name and no shared trio roster file, and `roster.normalize_names`
already folds case and whitespace so two spellings of one name collapse to one
option. A test now plants a synthetic duplicate roster and proves the page
offers exactly one option. Reported and skipped rather than invented.

## Perimeter Walk

Scratch `lab start pihti-diagram --port 48940 --host 127.0.0.1` under scratch
`LAB_CONFIG`/`LAB_RUNTIME_ROOT`/`LAB_LOG_ROOT`, with `PIHTI_DATA_ROOT`,
`PIHTI_SETTINGS_FILE`, `PIHTI_CUDATA_DIRECTORY`, `PIHTI_OPERATORS_FILE`,
`PIHTI_SESSION_KEY_FILE`, `PIHTI_USERS_FILE` and `PIHTI_USERS_KEY_FILE` all in
the session scratchpad; nothing written inside Dropbox. The listener was
confirmed by `OwningProcess` as the child of Lab's tracked PID. The owner's
4186 was empty before and after and was never queried while live; the Pi's 5000
was never touched.

- **The measurement that answers the audit:** at 390 px the document is now
  390 px wide on `/`, `/history`, `/plasmaplots`, `/services` and `/identify`,
  where it was 454 px on every one of them. All five tabs stay visible, the
  selector's right edge sits at 380 inside a 390 px screen, and changing it to
  an operator really does identify — `/get_current_user` came back
  `is_identified: true`. At 320 px the tabs take a second row and there is
  still no overflow, selector right edge 310.
- **The desktop board did not move.** At 1280 the rails are at y 76, 256 px
  wide, 904 px (1000-tall window) and 604 px (700-tall), left at x 20 and right
  at x 989; the three cards keep their order and their x positions 296 / 640 /
  296 with a `329.5px 329.5px` grid and a 14 px gap. The tab bar is 56 px, as
  before. Identical to the readings taken before a line was changed.
- Rail offset identical at 0/25/50/75/100 % of the scroll range at both window
  heights (76 px every sample). No page here has a scroll range with this data,
  because each rail caps itself and its lists scroll inside their own cards.
- Guide: markers per step 1/2/4/2/1, exactly the target counts; hovering step 2
  spotlit its two markers and only those, and cleared on leave; the tooltip on
  the SVG now reads "Plasma gate valve (GVU)".
- History: deep link `?at=2026-09-06 08:15:00` restores the retired-component
  moment with its marker and its explanation; `?at=2026-09-07 22:54:05`
  restores a named one; both survive a real reload at scroll 0.
- Every top tab pressed from inside Services, including Services itself, which
  returns home; Back landed on Plot, Forward restored Services at scroll 0 with
  the card order intact. The About drawer opens and Escape closes it, with no
  horizontal overflow either way.
- Console clean.
- `lab stop` killed the tree; tracked PID gone, 48940 free, scratch root marked
  `superseded`.

**The hazard, met in the walk exactly as `AGENTS.md` warns.** Editing
`styles.css` a second time *within* 0.10.0 served the browser the copy it had
already cached under `?v=0.10.0`, and the wrap fix silently did not apply — the
computed style still read `white-space: nowrap` while the file on disk said
otherwise. Diagnosed by comparing the computed style against a freshly fetched
copy of the same file, then re-verified against the real stamped URL after
`fetch(..., {cache: 'reload'})`. It is a walk artefact, not a shipping defect: a
release carries one `styles.css` under one version, and no browser will ever
have seen a different 0.10.0. It is worth knowing that a walk that edits twice
under one version number will lie to you the second time.

**Two honest limits of the instrument.** The browser pane reported
`document.hidden` for most of the walk, which throttles CSS transitions, so the
drawer's 180 ms slide could not be timed; its open/closed state, its geometry
and Escape were read from the DOM instead. Real pointer clicks timed out while
the pane was hidden, so tab navigation was driven by `element.click()` on the
same anchors and by `history.back()`/`forward()` — the same browser operations,
not a simulation of them.

## Gates

`pytest` 31 passed (exit 0), `node --check` on `diagram.js` and `history.js`,
`git diff --check` clean. There is no ruff configuration in this repository.
Four new tests: every component has a unique readable name and no page prints a
raw key (asserted against the JS source as well as the served config), the bar
wraps instead of clipping, a neighbour's own status is taken at its word, and
two spellings of one operator never become two identical options.

## Version

0.10.0 in `pyproject.toml`, `src/pihti/__init__.py` and the three assertions in
`tests/test_server.py`. `README.md` said "Current release: **0.4.0**", five
releases stale — a version copy the repository carries and Fleet `RULES.md` §2
says to keep synchronized, so it is corrected here.

## Not pushed, not deployed

This run was told not to push and not to touch the Pi, which crosses this
repository's own `.agents/README.md` (owner decision 2026-09-04: pushing
`master` is part of shipping here, because the Pi deploys by pulling). So the
commit is sitting on local `master`. To get it live queezz runs, in an ordinary
terminal:

```powershell
git -C "$env:USERPROFILE\Dropbox\20-Code\2024-interactive-diagram" push
```

then on the Pi: `git pull --ff-only` in `/home/pi/pihtivacuum`, `sudo systemctl
restart pihti`, and confirm `/version` says 0.10.0.

## Mail

Collected: `20260907-8cbfd520-ca289d` (the Mac audit), `20260907-09cac2c8-d703f1`
(Diagram is the trio's reference), `20260907-817e5f67-f68a07` (journal recovery
off the link board), `20260907-086b78af-5a8d73` (an idle ControlUnit is ok),
`20260907-ba2d4f0a-afb66f` (superseded by the one above, recorded as such) and
`20260907-badc369e-291e47` (ControlUnit 4.2.1 carries the 0.8.0 shape). Note
`20260907-78f344ce-e15344` logged — PIHTI Log 0.37.1 has the legend; nothing
was owed and nothing was changed on account of it. One note posted back to
`code/pihti-log` saying what shipped.

## Usage receipt

Provider Anthropic, model Claude Opus 5. Task: commander run, PIHTI trio /
Diagram. Child agents: 0. Provider usage: unavailable — no meter was shown to
this session.
