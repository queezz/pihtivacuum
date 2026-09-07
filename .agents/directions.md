# Open directions

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

- Confirm three plumbing guesses in `src/pihti/static/plumbing.json`, where the drawing alone could not settle it — the owner's call. First, the **membrane**: it is recorded as a barrier that lets gas past only when it is marked *off*, so "membrane installed" separates the probe line from the bypass manifold. That matches the Line configuration control's own wording, but it is a guess about what the hardware does. Second, the **helium bottle** is recorded as feeding the argon line, because that is where its stem is drawn; nothing here knows whether helium and argon really share that run. Third, the **gas panel manifold** is one drawn line that runs straight through the nitrogen valve, so it takes a single colour along its whole length; if the nitrogen side should colour on its own, that line needs splitting in Inkscape at the valve.
  Stakes: each wrong guess paints a volume the wrong colour in one particular valve position, and the colour exists as a sanity check, so a wrong one is worse than none.
  Recommendation: settle the membrane's real sense first — it is the one that changes the picture most often.
  Safe default: the three stay as recorded, and the legend keeps saying the whole thing is a prediction.

- Confirm or correct the reshaped `Vent Plasma` and `Vent QMS` guides in `static/operationGuides.json` (0.5.0, shape from queezz 2026-09-04: gauges together, then gate valve with its turbo, then every route between the two vessels, then the gas line). Settled by queezz the same day: venting means letting nitrogen in through the gas line, and only ionization gauges go off (Baratron, Pirani, the Pfeiffer single gauge and the Ulvac membrane gauge work at one atmosphere). The session guessed the four vessel-to-vessel routes as `valve_qms`, `GVBU`, `GVBD` and `Rough-Bypass`, the plasma-side ionization gauge as `bypass-ionization-gauge`, the nitrogen path as `gaspanel-valve-n` then `gasline-main`, and left the QMS vessel's own nitrogen route unnamed — owner guidance pending: which elements are really the four routes, which ionization gauge sees which vessel, and how nitrogen reaches the QMS vessel. The volume map added in 0.11.0 now knows which pipes each valve separates, so once these are named the guides can read the prediction instead of carrying a fixed element list.
  Done when: queezz names the routes, gauges and nitrogen paths, the JSON matches, and the guide loses its prototype flag.

- PIHTI Log asks whether this page's maximum width should match theirs: theirs stops at 1920 pixels, this one at 1600, so on a wide screen their board spreads and this one does not — the owner's call. Their cap is your own decision of 2026-09-04, so they are not changing it on their own, and neither is this side.
  Stakes: only on a screen wider than 1600 pixels, and only for how much empty margin sits beside the content.
  Recommendation: match at 1920 if you read this on the wide monitor; otherwise leave it.
  Safe default: nothing changes; the two differ above 1600 pixels.

- Name the folder on the lab NAS that this diagram's runtime data (`logs.csv`, `elements_state.json`, `operators.json`, the operation-context files) is copied into, so the Pi can copy there on a daily timer — owner work pending. Automatic from the Pi is settled (owner decision 2026-09-07: "Sure. NAS it is. I'll point you there when I'm in the lab"), so only the address is missing; the Pi also needs the share reachable from it.
  Done when: queezz gives the NAS path and confirms the Pi can write to it, and a dated daily copy lands there without anyone pressing anything.
