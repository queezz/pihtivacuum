# Open directions

- Read the vent guides from the predicted state instead of from a fixed element list — build work, deliberately not built in 0.12.0, and the second half of the colour direction that 0.11.0 opened. `Vent Plasma` and `Vent QMS` in `src/pihti/static/operationGuides.json` name their routes as a hand-written list of ids; `plumbing.json` now knows which valve separates which two volumes, and `predict()` already answers, per vessel, what it is joined to and how. A guide step could therefore say "close every route between the two vessels" and let the prediction name them, so a guide cannot go stale when the plumbing map is corrected. queezz asked for it on 2026-09-08 (letter `20260907-d5386824-f57dfd`, "based on vacuum color update the vent procedures") and the same letter said to record it rather than build it.
  Blocked on: the vent-guide route confirmation below, where 0.13.0 has now written out what the map itself says the four routes, the two ionization gauges and the two nitrogen paths are — so it needs a yes or a correction from queezz rather than an answer from nothing. The guides cannot read the prediction until those are the ones he actually uses.
  Done when: the two guides carry no hand-written route list, the steps still read the same to an operator, and `pytest` still passes.

- Read the 41 component names the diagram now shows a person — in the guide steps, the hover tooltip, the confirm box and the History timeline — and correct any that is not what you call that piece of equipment at the rig — owner work pending. They live as a `label` line beside each `id` in `src/pihti/static/elementsConfig.json`; nothing else needs touching. They were written for 0.10.0 by spelling the key out in words, and by borrowing the vent guides' own wording where it already named a part ("the plasma gate valve" for `GVU`, "the QMS ionization gauge" for `downstream-ionization-gauge`), with the rig designation kept in brackets where the key *is* the designation — "Plasma turbo pump (TMPU)". Nothing about the hardware was guessed beyond that. The ones most likely to be wrong, because only the upstream/downstream convention supports them: `GVBU`/`GVBD` ("Bypass gate valve, upstream/downstream"), `RoughU`/`RoughD` ("Roughing line, upstream/downstream"), `Rough-Bypass` ("Roughing bypass"), `valve_qms` ("QMS valve"), `bypass-l1`/`bypass-l2` ("Bypass line valve 1/2"), `bypass-vcr-u`/`bypass-vcr-d` ("Bypass VCR valve, upstream/downstream") and `upstream-single-gauge` ("Upstream single gauge" — kept because it reads like a Pfeiffer SingleGauge, not because anything here knows that). Three more joined in 0.11.0, the vent valves that were drawn but had no state until then: "Plasma backing line vent valve", "QMS backing line vent valve" and "Bypass pumping line vent valve".
  Done when: every label reads the way you would say it out loud at the rig, and `pytest` still passes.

- **Closed (owner decision 2026-09-08, letter `20260907-b9fddf7b-4768ce`).** queezz: "Right, you may and should correct spelling. And oddities. QMS is the QMS itself, an image. qms-vacuum is its pipe to the L valve." Applied in 0.11.1, in `diagram.svg`, `elementsConfig.json`, `plumbing.json`, and tests, with the render proved byte-identical before and after (same Inkscape PNG hashes as the 0.11.0 ship). `QMS` and `qms-vacuum` were kept exactly as they were, per the owner's own words above — not renamed to `qms-head` as an earlier draft of this item had guessed. History and the state file may still carry an old id from before this rename; `src/pihti/server.py`'s `ID_ALIASES` resolves it on read without rewriting stored history, proved by `tests/test_server.py::test_an_old_permalink_still_selects_the_renamed_element`. The rename table:

  | old | new |
  | --- | --- |
  | `bypas-manifold-downstream-line` | `bypass-manifold-downstream-line` |
  | `bypas-manifold-main` | `bypass-manifold-main` |
  | `bypas-manifold-t-downstream-t` | `bypass-manifold-t-downstream-t` |
  | `bypas-manifold-t-upsteram` | `bypass-manifold-t-upstream` |
  | `bypas-manifold-upstream-gv` | `bypass-manifold-upstream-gv` |
  | `bypas-manifold-upstream-t-to-pipe` | `bypass-manifold-upstream-t-to-pipe` |
  | `bypas-pumpline` | `bypass-pumpline` |
  | `bypas-pumpline-vent` | `bypass-pumpline-vent` |
  | `bypas-pumpline-vent-air-side` | `bypass-pumpline-vent-air-side` |
  | `plasma-vacuum-pump-portt` | `plasma-vacuum-pump-port` |
  | `gasapanel-manifold-argon` | `gaspanel-manifold-argon` |
  | `GVU-6` | `upstream-pumpline-vent-valve` |
  | `GVU-6-9` | `downstream-pumpline-vent-valve` |
  | `Rough-bypass-vent` | `bypass-pumpline-vent-valve` |
  | `nitrogen-line` | `nitrogen-bottle` |
  | `path1464-3-2-6` | `gasline-argon-1` (also moved into the `pipes-gasline-argon` group) |

  `Rough-Bypass` (the pump) kept its id, as asked. The letter also named an element whose id was reportedly `false`, to be renamed or dropped if stray; no such id exists in `diagram.svg` — the only `false` in the file is `showgrid="false"` in the Inkscape namedview, a false positive from an earlier session's own search. Nothing was done there, and nothing needs to be.

- **Closed (owner decision 2026-09-08, letter `20260907-dc825e44-e6d89e`).** queezz: "pipe open or membrane mode without a membrane are the same. Boron uses same pipe. But other end not connected to downstream. Could be pumped from plasma side via bypass. Membrane installed and the membrane 'valve' should be linked." Applied in 0.12.1: `line_configuration.modes.boron` in `plumbing.json` now names `dead_end_valve: bypass-vcr-d`, so under Boron deposition the downstream valve on the narrow pipe never reaches it, whatever position it is in — the pipe simply takes the plasma-vessel side's own predicted state, or isolated when that side is shut too, and it can still be pumped from the plasma side through the bypass manifold since that reach never depended on the pipe's far end. The drawn `Membrane` ellipse on the probe line is answered the same letter: `line_configuration.linked_valve` names it, `plumbing.predict()` reads it through the Line configuration on every state read rather than from a press, and `elementsConfig.json` marks it `followsLineMode` so it has no click of its own — closed only under *Membrane installed*, open under *Pipe open* and *Boron deposition* alike. `/update` refuses a direct write to it. Proved in `tests/test_server.py`: one test per configuration for the narrow pipe and the two vessels, one for the `Membrane` element following the configuration on every mode, and one that the readout never claims the QMS vessel for the plasma vessel under Boron deposition.

- Confirm two remaining plumbing guesses in `src/pihti/static/plumbing.json`, where the drawing alone could not settle it — the owner's call. The **helium bottle** is recorded as feeding the argon line, because that is where its stem is drawn; nothing here knows whether helium and argon really share that run. The **gas panel manifold** is one drawn line that runs straight through the nitrogen valve, so it takes a single colour along its whole length; if the nitrogen side should colour on its own, that line needs splitting in Inkscape at the valve.
  Stakes: each wrong guess paints a volume the wrong colour in one particular valve position, and the colour exists as a sanity check, so a wrong one is worse than none.
  Recommendation: the helium one is a yes-or-no; the gas panel one needs a few minutes in Inkscape.
  Safe default: both stay as recorded, and the key keeps saying the whole thing is a prediction.

- Say whether the **wider coloured pipes** stay, and whether the new **field colour** is the one you want — owner work pending, and yours because the pipe widths in `diagram.svg` are yours and the field is a matter of taste. 0.12.0 draws a coloured pipe at 1.6 times the width you drew it, solid, with no widening at all on an isolated line; the switch is in the key under the drawing (More → *Draw coloured pipes wider*) and the choice stays in that browser. The field went from coral to a quiet warm stone `#e3dfd6`, which is what let the five colours separate by weight as well as by hue — the whole table is in `.agents/log/2026-09-08-a-quieter-field-and-a-readout.md`. If widening the pipes yourself makes the band redundant, say so and it goes; if the stone is too pale or too warm, name a direction and the palette is rechosen against it.
  Done when: queezz has judged the drawing with the band off, and said keep or drop for the band and yes or a direction for the field.

- Say yes, or correct me, on the routes and gauges the vent guides should name — the plumbing map has now been asked, and everything below is what *it* says, so this is a yes-or-a-correction rather than a blank page — the owner's call. The `Vent Plasma` and `Vent QMS` guides in `static/operationGuides.json` still carry a hand-written list of parts from 0.5.0, and three of the four things on it disagree with the map you drew. Read each line and say *yes* or name the right part.

  **The ways gas can get from one vessel to the other.** Ignoring anything that runs out into the room, the map finds exactly four, and a vent guide should have you shut all four:

  1. The narrow pipe between the vessels — the **upstream and downstream bypass VCR valves** (both of them), and only while the Line configuration says *Pipe open*.
  2. Round through the bypass manifold — the **upstream bypass gate valve**, then **bypass line valve 1**, then the **downstream bypass gate valve**.
  3. The same two gate valves, but through the drawn **Membrane** on the probe line instead of bypass line valve 1. It is a second parallel link between the bypass manifold and the probe line, and since 0.12.1 it opens and shuts with the Line configuration rather than by a press.
  4. The long way round through the gas panel — the **main gas line**, the **argon gas line**, the **flow calibration valve**, then the **downstream bypass gate valve**.

  The 0.5.0 guess named the *QMS valve* and the *roughing bypass* among the four. Per the map neither is one: the QMS valve opens the QMS vessel onto its own sensor branch, which is a dead end, and the roughing bypass is a pump, and every pump in this map is a wall rather than a route.

  **Which ionization gauge sees which vessel.** There are two, and only one of them is on a vessel: the **QMS ionization gauge (downstream)** sits on the QMS vessel itself, and the **bypass ionization gauge** sits on the bypass manifold, one gate valve away from the plasma vessel rather than on it. The plasma vessel's own two gauges in the map are the **upstream single gauge** and the **upstream Baratron**, and neither is an ionization gauge, so by the map there is nothing on the plasma vessel for *Vent Plasma* to switch off — it would switch off the bypass one, and only while the upstream bypass gate valve is open. Is that right, or does the plasma vessel carry an ion gauge the drawing does not show?

  **How nitrogen reaches each vessel.** It enters at the **gas panel nitrogen valve**, on the gas panel manifold. To the **plasma vessel** the map's shortest path is the nitrogen valve, then the **gas panel argon valve**, then the **argon gas line**, then the **main gas line** — four valves, not the two the guide names; the oxygen and hydrogen sides reach the same place if you would rather go that way. To the **QMS vessel**: the nitrogen valve, the **gas panel argon valve**, the **flow calibration valve**, then the **downstream bypass gate valve** — or simply nitrogen into the plasma vessel and across through the two VCR valves.

  Stakes: the guides tell an operator which valves to touch while letting air into the rig. A route the guide does not name is a route nobody closes, and a part named wrongly sends you to the wrong handle.
  Recommendation: read the four routes and the nitrogen paths above and say "yes" if they match what you do at the rig; correct only the lines that are wrong.
  Safe default: nothing changes, the guides keep their 0.5.0 list, and they keep their prototype flag saying so.
  Done when: queezz has answered yes or corrected the lines, the JSON matches his answer, and the guide loses its prototype flag.

- Say whether a **stopped pump should still be a wall** in the prediction — the owner's call, found while building the 0.13.0 warnings. Every pump in `plumbing.json` is a boundary: nothing ever passes through one, running or stopped. That is why venting the plasma backing line leaves the vessel above it blue, and it is also why pressing a backing-line vent valve raises no warning even with that turbo spinning — the map has no path from a foreline to the vessel above its pump, so the warning has nothing to warn about.
  Stakes: on the drawing, whether a vented backing line ever colours the vessel above it; in the new warnings, whether venting a backing line under a spinning turbo says anything at all. If a stopped turbo really does let air through to the vessel, the diagram is quietly optimistic today.
  Recommendation: leave a *running* turbo a wall — that is right, and it is what the colours were built on. The open question is only the stopped one, and a spinning turbo vented from its exhaust side, which is a real way to break a pump and which this map cannot currently see.
  Safe default: pumps stay walls in both states, and the backing-line vents stay quiet.

- PIHTI Log asks whether this page's maximum width should match theirs: theirs stops at 1920 pixels, this one at 1600, so on a wide screen their board spreads and this one does not — the owner's call. Their cap is your own decision of 2026-09-04, so they are not changing it on their own, and neither is this side.
  Stakes: only on a screen wider than 1600 pixels, and only for how much empty margin sits beside the content.
  Recommendation: match at 1920 if you read this on the wide monitor; otherwise leave it.
  Safe default: nothing changes; the two differ above 1600 pixels.

- Name the folder on the lab NAS that this diagram's runtime data (`logs.csv`, `elements_state.json`, `operators.json`, the operation-context files) is copied into, so the Pi can copy there on a daily timer — owner work pending. Automatic from the Pi is settled (owner decision 2026-09-07: "Sure. NAS it is. I'll point you there when I'm in the lab"), so only the address is missing; the Pi also needs the share reachable from it.
  Done when: queezz gives the NAS path and confirms the Pi can write to it, and a dated daily copy lands there without anyone pressing anything.
