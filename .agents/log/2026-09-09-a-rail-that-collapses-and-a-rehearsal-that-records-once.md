# A rail that collapses, and a rehearsal that records once (0.17.1 – 0.19.1)

Commander-dispatched ship in the coordinated PIHTI trio run, on the work
Windows PC, with queezz awake and watching his own service the whole time —
three more letters arrived mid-session and one of them corrected a card while
it was still being built.

Four releases, four commits, each landing as soon as its own gates were green.

## 0.17.1 — a stopped turbo is a passage, not a wall

His ruling, watching the 0.17.0 tree with TMPD stopped and the QMS rotary
running on its backing line: *"The rough pump pumps, it can really do that."*

Gas goes through a stationary rotor, so a turbo now has two states in the map
rather than one behaviour in code:

```json
{"id": "TMPD", "kind": "turbo", "volume": "qms-turbo-line",
 "backed_by": "qms-foreline", "stopped": "passage", "serves": "qms-vessel"}
```

`plumbing.passage_edges` joins a turbo's inlet line to its backing line whenever
it is **not** running, exactly as an open valve would. Running, it is the pump
and the wall again. Only a closed valve blocks, and a rough pump carries neither
field because it exhausts to the room, so a stopped one joins nothing.

Measured on the scratch service, which is his own frame: GVD open, TMPD stopped,
the QMS scroll running — the QMS vessel, its turbo line and its backing line all
read rough vacuum, and the readout says *Pumped by · roughing line, downstream
(RoughD)*. With TMPD spinning the vessel is high vacuum again and the scroll is
its backing.

**The knock-on he predicted shipped with it.** Venting a backing line under a
stopped turbo now has a path up to the vessel above it, so the 0.13.0 press
warning has something to warn about: the ionization gauge standing in that
vessel would newly see air. Under a *running* turbo the same press is still
quiet, because the press changes nothing for it.

One existing assertion moved rather than being deleted: "air does not reach the
plasma vessel through a turbo" now reads "through a **running** turbo", with the
stopped case asserted beside it.

## 0.18.0 — the predicted state moves into the right rail

*"I think the bottom card deserves a proper place in the rail, no? And not
hiding in small sizes, shying away. Proper. With proper groups, not a long-line
which is a list."*

The whole thing — the vessel readout, the legend swatches and More — is a
right-rail card above the Current guide now, present at every width the rail
exists and inside the drawer where it does not. One DOM; no breakpoint can drop
it. **History keeps its key under the drawing**, because that page's right rail
already carries its own cargo (the selected moment and the export), and a rail
answers for its own tab.

Each vessel is a group rather than a sentence: the colour chip and the state
word, then labelled rows — Open to, Gas, Vent, Pumped by, Sealed since — and a
row with nothing in it is simply not drawn.

**What made room for it is the collapse, not a taller rail.** Two earlier
attempts at a third card were measured out in 0.11.0 because every card
insisted on its full height at once. Both right-rail cards now fold to a
headline and neither ever vanishes: the state card collapsed is one line per
vessel, the guide card collapsed is its name and the current step with its
number. Default: with a guide running the guide opens and the state goes
compact; with no guide the state opens. The reader's own press is remembered
per browser and always wins.

### The guide card's overflow, in his order

*"the right procedure card gets a nasty scroll bar.. Would be nice if we can
avoid that."*

1. The card grows to the rail's own room.
2. Still longer: every step but the current one and the one after it folds to a
   single line — the done ones first, oldest first, then the later ones from
   the end backwards — and a folded step's full wording moves to that row's own
   title, so nothing a reader could need is thrown away.
3. Only then, a thin quiet bar inside the list.
4. Below a floor the card is never crushed: the **rail** takes the overflow and
   scrolls inside its own box, which is Fleet `WEBUI.md`'s 2026-09-08
   amendment. The page never scrolls for the rail.

**One defect found and fixed on the way, worth writing down.** Called straight
out of a `resize` or a re-render, the fit read a card height from a layout that
was still moving: it folded one step, decided the card fitted, and left the rail
overflowing by 500 px. The same measurement a moment later folded four and
fitted exactly. So every caller goes through one short timer and one pending
flag — a timer rather than an animation frame, because a browser stops handing
frames to a tab nobody is looking at, and a rail that only fits itself while it
is on screen is wrong the moment you come back to it.

## 0.19.0 — practice

*"I want now a 'practice' before recording history mode somehow. You open the
valve, and see where color (vacuum/air) goes. Then you can undo. Also maybe
using that we can do a procedure, then save state. That way one state jump, less
history spamming. And better operational safety."*

While the switch is on, the page's own `vacuumState` **is** the practised copy,
so everything else runs over it without knowing anything about practice: the
colours, the gas marks, the sealed readout, the 0.13.0 press warnings and the
guides' own beacons. That is what 0.17.0's promise bought — the predictor has
been state in, prediction out, with the memory as an argument, precisely so this
could exist.

- `POST /practice/prediction` answers about the copy and carries the volume
  memory **out and back**, so a vessel shut in rehearsal reads as *sealed since
  now* while the recorded memory does not move.
- `POST /press-warnings` takes the same copy, because seeing the warning is the
  point of rehearsing the press.
- Neither route writes a byte. The five-second poll is skipped while
  practising, or it would paint the record over the rehearsal.

Undo steps back one press. Discard restores the recorded state **and cancels the
timer with it** — a sequence somebody threw away must not come back a minute
later. Save records the whole thing as one signed event.

### One event, and what it cost

A practice save is **one row** in `logs.csv`, one entry on the timeline, one jump
on replay. That needed two new columns — `changes`, holding every press in order
as JSON, and `note` — so:

- An older four-column log is widened once, atomically, keeping every row
  (`widen_log_header`: rewrite to a temp file beside it, one `os.replace`; an
  interrupted run leaves the original untouched, and a log whose header is
  neither shape is left completely alone).
- An ordinary press leaves both columns empty and reads exactly as it always
  did.
- The server's `state_at_index` and `memory_timeline`, and History's own copy of
  that reconstruction, all walk an event's list of changes instead of assuming
  one — forwards to remember what each element was, backwards to put it back.

Measured on the real 802-event scratch log: the header widened in place, every
row preserved, and the sequence landed as one line.

### Teaching saving

*"In the new 'practice' mode we really need to teach to save the state. And
maybe have a timer fallback, which saves automatically."*

- One standing line beside the button: **"Nothing is recorded until you press
  Save."** When practice is off the same line says the opposite fact rather than
  explaining both, so the card states rather than lectures.
- Save is the loud one, never hidden, and carries the count: *Save 3 presses to
  history*.
- Under it a visible countdown: *Saves itself in 0:29.*
- An amber strip above the drawing itself: **Practising. This drawing is a copy,
  not the record.**
- Leaving the page with unsaved practice asks first.

**The interval is three minutes, and here is why.** The longest guide here is
six steps and a slow one is a minute or two, so the timer must not interrupt a
procedure; and a person called away from the rig should not lose what they
practised. It is `PRACTICE_AUTOSAVE_SECONDS` in the machine-local settings file,
held between 30 and 1800 seconds so a typo can neither turn the fallback off nor
make it fire mid-press. A directions item asks queezz whether three minutes is
right — it is one number.

**A record nobody pressed Save on says so.** The auto-saved event's note ends
*"saved by the timer"*, and it never fires while a confirm box is open —
`isInteracting` is held from before the box appears until after the press lands.

## 0.19.1 — one legend, and a switch you can find

Written while the state card was still going up, from his own screen: *"Why do
we need two legends? pic 2, the thick pipes is too far hidden. Do we need that
much text in a rail card??"*

He was right three times. The chips in the card were already swatches, and More
opened a second board of bigger ones on a stone panel — the same information
twice on one card — followed by thirteen sentences, with the thick-pipes tick at
the very bottom of them.

- The chips **are** the swatches, laid two to a row so all seven fit a 16 rem
  rail. The second board is gone.
- More holds one short line per chip, read from the map's own `meaning` —
  shortened *there* rather than in the page, so the one source stays the one
  source — plus three lines for the rules the drawing follows.
- **Draw thick pipes** sits directly under the chips and above More, visible
  whenever the card is open, on the Vacuum page and on History alike.

**One thing for his eye.** Two columns at this rail width makes the long labels
("High vacuum, plasma side") wrap to three lines, so the seven chips take four
rows and about 210 px — a single wrapping column would take about 180. Two
columns is what his letter asked for and it is what shipped; if the packing
reads worse than the wall did, it is one CSS line.

## Verify: the Perimeter Walk on a scratch service

`lab start pihti-diagram --port 48995 --host 127.0.0.1` under scratch
`LAB_CONFIG` / `LAB_RUNTIME_ROOT` / `LAB_LOG_ROOT`, every `PIHTI_*` write path
inside a marked `fleet-scratch-2024-interactive-diagram-round8` root in this
machine's own temp — outside Dropbox — with a copy of the real state, log,
context, roster and settings. The listener was confirmed as a child of Lab's
tracked PID each time it was started.

**Rails.** Both rails at **76 px** at 0/25/50/75/100 % of the scroll range at
1280×700, 1280×1000, 1440×900, 2000×1540 and on History, every reading
identical. Document width 1265 at 1280 and 1425 at 1440: no page-width overflow.
At 390×844 the document is exactly 390 with no horizontal scroll, both drawers
open, and a card header is a 41 px target under a thumb.

**The page never scrolls for the rail.** With the legend out of the main column
the Vacuum page's own scroll range is 0 at every desktop size; the practising
banner adds 29 px, and the rails hold 76 through all of it.

**The guide card's three stages, measured.** At 1440×900 with the six-step *Vent
Plasma* running: the card grew to 1220 px against 676 of room, folded four
steps, capped the list at 252 px with the thin bar — and the rail's own
`scrollHeight` came back **equal** to its `clientHeight`, so it does not scroll
at all. At 1280×700 the same guide folds to 791 px against 476 of room and the
rail takes the rest rather than crushing the card, which is the honest answer at
that height.

**Practice, on the scratch data.** `logs.csv` and `elements_state.json` were
**byte-identical** through a three-press rehearsal (md5 unchanged, 802 events
before and after). Undo stepped back exactly one press and the drawing followed;
Discard restored the recorded state exactly and cleared the countdown. Save
wrote **one** row; the timer fired by itself 30 seconds after the last press and
wrote one row whose note ends *saved by the timer*. History shows both as single
entries — *3 presses · saved* — and the Selected moment names all three
components in the order they were pressed, signed KAA.

**Beacons under reduced motion.** This machine still answers *true* to
`prefers-reduced-motion: reduce`. With a guide running the current step's ring
measured `getAnimations().length` 1, `animation-name` `marker-halo-quiet`,
duration 2.4 s, `r: 26px`, and four samples across the period differing: 0.789 →
0.717 → 0.130 → 0.513.

*A note for the next session that measures this:* the animation clock **freezes**
while the browser pane is hidden, and `getComputedStyle` then returns one value
forever. Front the pane before sampling, or you will report a dead beacon that
is running perfectly.

**A beaconed valve pressed and pressed back.** `elementFromPoint` at GVU's own
centre returns the drawing underneath; all 44 marker parts compute
`pointer-events: none`; a real click at GVU's centre closed it (white on black)
and a second opened it (blue, fill and edge).

**The rest of the walk.** Every top tab pressed from inside the Vacuum page —
History, Plot, Services and back — each landing at its own top with both rails at
76. Browser Back landed on Plot and Forward returned to Services. Console clean
on a fresh tab: no messages at all. The teaching count on the loaded page: the
honesty sentence renders exactly once, "measure pressure" appears nowhere, and no
raw component key reaches the page.

**Screenshots taken for him to compare** — the rail with both cards and a
six-step guide at 1280×700; both cards collapsed; the stopped-turbo rough case
with the QMS side amber and the readout naming the scroll pump; practice on with
three presses and the countdown; the drawer at 390 with the practising banner;
and the one legend with the thick-pipes switch under it.

**Two things to say plainly about his own services.** The Pi's 5000 was never
addressed. His 4186 was listening before and after, on the same PID 47288
throughout, and was never started, stopped, or contacted.

## Gates

`pytest -q` **87 passed**, exit code captured explicitly, before every commit.
`node --check` clean on `diagram.js` and `history.js`. There is no ruff
configuration in this repository and no `CHANGELOG.md`: shipped work is recorded
in `.agents/log/`, so this entry is the release note for all four versions.

Sixteen tests are new — the turbo's two states and the passage's own boundary,
the warning knock-on, the rail card's placement and collapse, the fold-then-
scroll order, the grouped readout, practice writing nothing, one event carrying
the presses in order, the one-jump replay, the timer's mark, the interval's
bounds, practice's refusals, the log-header widening, the page's teaching, and
one legend rather than two. Three existing ones moved to the new law.

## Mail

Eight letters collected: `20260908-948b8dbc-b1eb0d` (the stopped turbo),
`20260908-6f3f0308-5906a1` (the ControlUnit idea, recorded not built),
`20260908-aa2558c2-f3d03e`, `20260908-50f93f77-8e8a28` and
`20260908-8853f919-4c54b6` (the rail card and its collapse),
`20260908-9d38bf34-8415c7` and `20260908-e460b66f-616b53` (practice), and
`20260908-c03c1788-9def42` (one legend).

Three more arrived mid-session and are collected with their substance recorded
in `directions.md` in his own words: the guides' thorough review
(`20260908-363c0087-774c89`, standing work, no build ordered), the Boron
deposition probe-pipe correction (`20260908-5d638879-1b617e`, the next ship's
build), and the legend one above, which was built here because it corrected a
card this session had just put up.

## Not pushed, not deployed

Told not to push and not to touch the Pi, which crosses this repository's own
`.agents/README.md` (owner decision 2026-09-04). Nineteen commits now sit on
local `master` ahead of `origin`. To get it live, in an ordinary terminal:

```powershell
git -C "$env:USERPROFILE\Dropbox\20-Code\2024-interactive-diagram" push
```

then on the Pi: `git pull --ff-only` in `/home/pi/pihtivacuum`, `sudo systemctl
restart pihti`, and confirm `/version` says 0.19.1.

## Usage receipt

Provider Anthropic, model Claude Opus 5. Task: commander run round 8: pihti trio
/ Diagram rail cards and practice. Child agents: 0. Provider usage: unavailable
— no meter was shown to this session.
