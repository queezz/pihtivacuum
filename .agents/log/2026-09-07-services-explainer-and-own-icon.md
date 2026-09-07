# The Services explainer at a glance, an honest start line, and our own icon

Session on the work Windows PC, queezz live in chat. Cold start was
orientation-only; he overrode it in the same conversation ("Can we improve the
explainer tab?"), so this session left orientation and shipped 0.8.0.

## What he asked

- The right-rail explainer on Services is "too long and too quite. And we need
  to address me, I love to see it all at a glance. With possible expansions if
  more is really needed. I think Japanese strong English not so Japanese
  student's would also appreciate that."
- "And the ControlUnit, we should teach that the rig's GUI starts the
  webserver."
- Later: the favicon is still KAA's stylised circle, inherited; something like
  `Vc` or `Vac`, "letters, but like a chem element", so this tab is not
  confused with his CV site.

## Built (0.8.0)

- **The explainer teaches at a glance.** One lead line addressed to him, then
  the same five chips the cards render, each with its meaning in three or four
  words, then `More` for the rest (independence, where addresses live, that
  each card says how to start its service). Three muted paragraphs became one
  legible legend: the lead and the legend sit at `--fg`, not `--muted`. Fleet
  `WEBUI.md` Teaching is the rule — cards state, the rail teaches once — and
  the short parallel lines are also for the readers whose English is a second
  language.
- **Start rows lead with meaning, command behind a toggle** (`WEBUI.md`, Text).
  `ControlUnit` carries no command at all: there is no `lab controlunit` alias
  anywhere in this lab, and the card had been printing one. It now says the
  rig's GUI on the Raspberry Pi opens the web server itself. `START_HINTS` in
  `src/pihti/neighbours.py` holds the sentences; a machine whose layout differs
  overrides the sentence in its own settings (`{"controlunit": {"url": ...,
  "start": "..."}}`), never the command.
- **Our own icon.** `static/favicon.svg`: a periodic-table tile in the page's
  panel and accent colours with `Vc` drawn as strokes, not set in a typeface,
  so no font need be installed. The inherited 320 KB `favicon.ico` is removed
  and `base.html` links the SVG; a test pins that the pages carry it and that
  `favicon.ico` is gone.

## Found in the walk, and fixed

The board re-renders every thirty seconds. An expanded command collapsed under
the reader on the next refresh — a disclosure the surface took back. The set of
opened aliases now outlives the cards it dresses, proven by pressing `show
command`, pressing `Ask again now`, and re-reading the DOM: the pressed one
stayed open, the other stayed closed.

## Found in the gates, and fixed

`tests/test_server.py`'s `make_app` never set `SETTINGS_FILE`, so every test
app fell back to the default — the repository root, whose gitignored
`settings.json` carries this machine's real neighbour addresses. The
"not configured" case passed only on a machine that had none. The helper now
points at the sandbox; the suite no longer reads the operator's own file.

## Perimeter Walk

Scratch `lab start pihti-diagram --port 48934 --host 127.0.0.1` under scratch
`LAB_CONFIG`/`LAB_RUNTIME_ROOT`/`LAB_LOG_ROOT`, with `PIHTI_DATA_ROOT`,
`PIHTI_SETTINGS_FILE`, `PIHTI_CUDATA_DIRECTORY`, `PIHTI_OPERATORS_FILE`,
`PIHTI_SESSION_KEY_FILE`, `PIHTI_USERS_FILE` and `PIHTI_USERS_KEY_FILE` all in
the session scratchpad; runtime data copied there, nothing written in Dropbox.
Listener confirmed by `OwningProcess` as the child of Lab's tracked PID. The
owner's 4186 was empty before and after and was never queried while live; the
Pi's 5000 was never touched.

- Every top tab pressed from inside Services, including Services itself, which
  returns home; Back landed on Plot, Forward restored Services at scroll 0.
  Reload on `/services` restored the board.
- Rails at 76 px on Services, Vacuum, History and Plot, at 1280x1000 and
  1280x700, at every sampled scroll position; no page had a scroll range with
  this data, because each rail caps itself and its lists scroll inside their
  own cards. No horizontal overflow anywhere.
- At 700 px with `More` open and both commands shown, the rail card is 537 px
  inside a 604 px rail: nothing clipped, the rail never scrolls. At 480 px the
  About drawer opens with the legend readable, `More` still fits, and Escape
  closes it.
- Five states forced through a patched `fetch` (removed by a reload before
  anything was called verified): five visually distinct chips — green, amber,
  brick, dashed white, dim — and `ControlUnit` offered no command in any of
  them, including `not configured`, whose card still says how to start it.
- Teaching checks: each concept explained once, in the rail; from structure
  alone the surface answers "what do I do first" (read the chips) and "how do I
  start the next round" (Ask again now, in the Check card).
- Console clean apart from four `ERR_CONNECTION_REFUSED` entries logged while
  the scratch server was deliberately stopped — the board's own error path,
  behaving.
- `lab stop` killed the tree; tracked PID gone, 48934 free, scratch root marked
  `superseded`.

## Gates

`pytest` 25 passed (exit 0), `node --check` on `services.js`, the favicon SVG
parses, `git diff --check` clean.

## Mail and orders

- Letter `20260907-f4233fa8-a494c0` from `code/pihti-log` asked this project to
  carry the approved board to all three siblings and named the refusal/timeout
  drift. Recorded in `.agents/ensemble-health.md`, collected; the reference and
  the state meanings went out as letters to `code/ControlUnit` and
  `code/pihti-log`.
- Order `20260904-3a19cc77-fe6464` (NAS backup) answered: "Sure. NAS it is.
  I'll point you there when I'm in the lab." Recorded as an owner decision in
  `.agents/directions.md`, which now waits only on the location; collected.

## 0.8.1: the rig's launcher, named exactly

Second letter from `code/pihti-log` the same afternoon
(`20260907-c39f87ab-3afa0a`), carrying queezz's correction "ControlUnit starts
with their GUI. See in the repo." It confirms 0.8.0's card rather than
contradicting it, and adds the concrete step. Verified in the ControlUnit
checkout rather than taken on the letter's word: `AGENTS.md` "Running on the
rig" and `scripts/run_controlunit.sh` agree that the Pi's `~/Desktop/aktest.sh`
calls that script, which runs `python -m controlunit.main --web`.

The card now reads "Start it from the desktop launcher on the rig's Raspberry
Pi; it serves its own web view" — the launcher is what a person at the rig
presses. Content only, no UI code touched, so the 0.8.0 walk stands; the new
sentence was still rendered on scratch 48934 to confirm it costs one wrapped
line (ControlUnit's card 237 px against the others' 219 px), no horizontal
overflow, rails at 76 px, both rails free of overflow. pytest 25 passed.
Letter recorded here and collected.

## Deployed to the Pi

queezz: "Wen done, update Pi and start new version." Keys-only over the Windows
agent service (`& "$env:WINDIR\System32\OpenSSH\ssh.exe" pi@pihti` — the
socket form `.agents/README.md` records is the work PC's, not this box's).
`git pull --ff-only` on `/home/pi/pihtivacuum` took it 402ee13 -> 99b0452,
`systemctl restart pihti`, service active. The Pi answers `/version` 0.8.1,
serves `favicon.svg` as `image/svg+xml`, and `/services` renders the five-row
legend. Its board on arrival: diagram ok 0.8.1, PIHTI Log ok 0.37.0,
ControlUnit **down** — the rig's control unit is not running, and the card that
used to say `lab controlunit` now tells whoever reads it to start it from the
rig's desktop launcher. The new wording earned its keep on its first day.

## Still open

- The vent guides, the `zone-*` split and colour-by-vacuum stand unchanged.
