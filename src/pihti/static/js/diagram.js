(function () {
    "use strict";

    const SVG_NS = "http://www.w3.org/2000/svg";
    let elementsConfig = [];
    let guideConfig = {guides: []};
    /* Facts about this rig that are not valve positions and cannot be read off
     * the drawing — today, only whether the flow-calibration pipe is plugged in.
     * They travel with the guides from the server, which reads them from the
     * machine-local settings file, so one guide file serves a rig with the pipe
     * connected and a rig without it. */
    let guideFacts = {};
    let vacuumState = {};
    let activeGuide = null;
    let isInteracting = false;
    let operatorIdentified = false;
    /* id -> the name a person uses at the rig, from elementsConfig. A page
     * shows the name; the key stays in the file and the log. */
    let nameById = {};
    /* The volume map (static/plumbing.json) and the last prediction the server
     * made from it. The colours live in the map, so the legend and the pipes
     * cannot disagree. */
    let plumbing = null;
    let predictionPending = false;
    /* The last prediction the server sent, so the band switch can repaint from
     * it without asking again. */
    let lastPrediction = null;
    /* The widening is off by default from 0.15.0: queezz drew the pipe widths
     * he wants, and an app that redraws them wider without being asked is
     * talking over his drawing. The More switch still offers it. */
    let bandOn = false;

    /* Practice (0.19.0). While it is on, `vacuumState` *is* the practised copy
     * and nothing reaches the state file or the history until Save; see the
     * practice section below for the whole of it. Declared up here with the
     * rest of this page's state because the press handler reads it. */
    let practiceOn = false;
    let practicePresses = [];
    let practiceRecorded = null;
    let practiceMemory = null;
    let practiceDeadline = 0;
    let practiceTick = null;
    /* The fallback interval, from the machine-local settings file. Three
     * minutes by default: long enough not to interrupt a procedure, short
     * enough that a person called away from the rig does not lose it. */
    let practiceAutosaveSeconds = 180;


    function normalizedStatus(value) {
        return value === "active" || value === true ? "active" : "inactive";
    }

    /* The readable name for a component, or "" when this release's diagram
     * does not carry it — a history entry can name a component that has since
     * been removed, and inventing a name for it would be worse than saying so.
     * History reads this through `window.pihtiElementName`. */
    function elementName(id) {
        return nameById[id] || "";
    }

    function displayName(id) {
        return elementName(id) || id;
    }

    function rgbToHex(rgb) {
        const match = rgb.match(/^rgb\((\d+),\s*(\d+),\s*(\d+)\)$/);
        if (!match) return rgb;
        return `#${match.slice(1).map((value) => parseInt(value, 10).toString(16).padStart(2, "0")).join("")}`;
    }

    function showTooltip(tooltip, event, text) {
        tooltip.style.display = "block";
        tooltip.style.left = `${event.pageX + 10}px`;
        tooltip.style.top = `${event.pageY + 10}px`;
        tooltip.textContent = text;
    }

    /* What a press would newly join to gas or vent air, asked of the server
     * just before the box appears. The walk lives in one place — the volume map
     * and the server's own reading of it — so a warning can never drift from
     * the colours beside it. `null` means the question could not be asked at
     * all, which the box then says: an unchecked press is not a safe one. */
    async function pressWarnings(id, status) {
        try {
            // While practising, the question is asked of the practised copy —
            // seeing the warning is the whole point of rehearsing the press
            // (queezz, 2026-09-08). The route reads and writes nothing either
            // way, and answers about the recorded state when none is sent.
            const response = practiceOn
                ? await fetch("/press-warnings", {
                    method: "POST",
                    headers: {"Content-Type": "application/json"},
                    body: JSON.stringify({id, status, state: vacuumState})
                })
                : await fetch(
                    `/press-warnings?id=${encodeURIComponent(id)}&status=${encodeURIComponent(status)}`
                );
            if (!response.ok) return null;
            const result = await response.json();
            return Array.isArray(result.warnings) ? result.warnings : null;
        } catch (error) {
            return null;
        }
    }

    /* The warning, in the words a person uses at the rig. queezz asked for both
     * on 2026-09-08: "create warning when putting gas/air on to IG" and "and
     * when vent goes on to TMP". One sentence per kind of thing the press would
     * newly expose, and the sentence says up front that it is read from the
     * valve positions — the confirm box is a modal of its own, and a reader
     * about to press something must know whether this is a measurement. It is
     * not, and it stops nothing: a warning here is still only a confirm box. */
    function warningText(warnings) {
        const sentences = [];
        const gauges = warnings.filter((item) => item.kind === "gauge");
        const turbos = warnings.filter((item) => item.kind === "turbo");
        if (gauges.length) {
            const states = new Set(gauges.map((item) => item.state));
            const what = states.has("air") && states.has("gas")
                ? "gas and vent air"
                : states.has("air") ? "vent air" : "gas";
            sentences.push(`Warning, predicted from the valve positions: this would let ${what} reach the ${joinWords(
                gauges.map((item) => inSentence(displayName(item.id)))
            )}, ${gauges.length > 1 ? "which are" : "which is"} switched on.`);
        }
        if (turbos.length) {
            sentences.push(`Warning, predicted from the valve positions: this would let vent air reach the ${joinWords(
                turbos.map((item) => inSentence(displayName(item.id)))
            )}, ${turbos.length > 1 ? "which are" : "which is"} marked running.`);
        }
        return sentences.join("\n\n");
    }

    async function toggleElementStatus(element, config) {
        if (isInteracting) return;
        // Read the press from the recorded state, never off the paint: a valve
        // wears the volume's colour now, so its fill no longer says whether it
        // is open (0.15.0).
        const newStatus = normalizedStatus(vacuumState[element.id]) === "active" ? "inactive" : "active";
        // Held from here rather than from after the box, so the five-second
        // refresh cannot repaint the drawing out from under an open question.
        isInteracting = true;
        try {
            const warnings = await pressWarnings(element.id, newStatus);
            const notice = warnings === null
                ? "This press could not be checked against the diagram just now."
                : warningText(warnings);
            const question = `Mark ${displayName(element.id)} ${newStatus}?`;
            // A warning is a confirm: an element with no confirm box of its own
            // still asks when there is something to say.
            if ((notice || config.confirmToggle)
                && !window.confirm(notice ? `${notice}\n\n${question}` : question)) return;
            // Practising: the press changes the local copy and nothing else.
            // No state file, no history, no round trip but the one that asks
            // the same predictor what the copy now looks like.
            if (practiceOn) {
                practicePresses.push({id: element.id, status: newStatus});
                vacuumState = {...vacuumState, [element.id]: newStatus};
                await refreshPractice();
                startPracticeTimer();
                renderPractice();
                return;
            }
            const response = await fetch("/update", {
                method: "POST",
                headers: {"Content-Type": "application/json"},
                body: JSON.stringify({id: element.id, status: newStatus})
            });
            const result = await response.json().catch(() => ({}));
            if (!response.ok) {
                applyState(vacuumState);
                if (response.status === 428) window.location.assign("/identify");
                else window.alert(result.error || "The diagram state could not be updated.");
                return;
            }
            vacuumState = result.state || {...vacuumState, [element.id]: newStatus};
            applyState(vacuumState, undefined, result.prediction);
        } catch (error) {
            applyState(vacuumState);
            console.error("Diagram state update failed", error);
        } finally {
            isInteracting = false;
        }
    }

    function attachElementListeners() {
        const container = document.getElementById("diagram-container");
        if (window.historyMode) {
            if (container) container.style.pointerEvents = "none";
            return;
        }
        const tooltip = document.getElementById("tooltip");
        if (!container || !tooltip) return;
        const configById = Object.fromEntries(elementsConfig.map((item) => [item.id, item]));
        elementsConfig.forEach(({id, followsLineMode}) => {
            const element = document.getElementById(id);
            if (!element) return;
            element.style.cursor = followsLineMode ? "default" : (operatorIdentified ? "pointer" : "not-allowed");
            element.addEventListener("mouseenter", (event) => showTooltip(tooltip, event, displayName(id)));
            element.addEventListener("mouseleave", () => { tooltip.style.display = "none"; });
        });
        container.addEventListener("click", (event) => {
            let target = event.target;
            while (target && target !== container && !configById[target.id]) target = target.parentElement;
            if (!target || target === container || !configById[target.id]) return;
            // Some elements have no press of their own: the Line configuration
            // card sets them instead (queezz, 2026-09-08, "the membrane 'valve'
            // should be linked").
            if (configById[target.id].followsLineMode) return;
            if (!operatorIdentified) {
                window.location.assign("/identify");
                return;
            }
            toggleElementStatus(target, configById[target.id]);
        });
    }

    /* A step names one element (`targetId`) or several (`targets`), and is
     * done in the diagram only when every one of them is in the wanted state. */
    function stepTargets(step) {
        if (Array.isArray(step.targets)) return step.targets;
        return step.targetId ? [{id: step.targetId, markerOffset: step.markerOffset}] : [];
    }

    /* Everything a step puts a beacon on. `marks` are parts the step wants the
     * eye sent to without claiming the diagram can tell whether they are right:
     * the turbo whose stopping is the operator's own choice, the two valves an
     * isolation step names while the prediction decides whether it is done. */
    function markerTargets(step) {
        return stepTargets(step).concat(Array.isArray(step.marks) ? step.marks : []);
    }

    /* The steps of the active guide that apply on this rig. A step may carry
     * `onlyWhen: {fact, is}`, and a fact the rig does not have takes the step
     * off the list entirely — markers and all — rather than leaving an
     * instruction nobody can follow standing on the page. */
    function guideSteps() {
        if (!activeGuide) return [];
        return (activeGuide.steps || []).filter((step) => {
            const rule = step.onlyWhen;
            if (!rule || !rule.fact) return true;
            return Boolean(guideFacts[rule.fact]) === (rule.is !== false);
        });
    }

    function guideStepSatisfied(step) {
        if (step.manual) return false;
        // A step may ask the *prediction* whether two volumes are still joined,
        // instead of naming the valves that would join them. The map knows which
        // valve separates which pair, and `predict()` already walks it — so an
        // isolation step cannot go stale when the plumbing map is corrected, and
        // one closed valve that really does isolate finishes the step even if
        // another route's valve is left open (queezz, 2026-09-08: "GVBU closed,
        // and we are isolated").
        if (Array.isArray(step.separates) && step.separates.length === 2) {
            const item = (lastPrediction?.connections || {})[step.separates[0]];
            if (!item) return false;
            return !(item.joined || []).includes(step.separates[1]);
        }
        const targets = stepTargets(step);
        return targets.length > 0
            && targets.every((target) => normalizedStatus(vacuumState[target.id]) === step.desiredStatus);
    }

    function spotlightStep(index, on) {
        document.querySelectorAll(`#operation-guide-overlay .operation-marker[data-step="${index}"]`)
            .forEach((marker) => marker.classList.toggle("spot", on));
    }

    /* Where a beacon stands: the element's top-right corner, stepped a little
     * further out, never its centre. queezz, 2026-09-08 (letter
     * 20260908-3688eabd-587dfe), with Vent Plasma running: "venting plasma
     * works. But numbered circles are obstructing the interactions." A disc
     * centred on a valve hides the very valve the step is asking you to press,
     * and a valve you cannot see is a valve you cannot aim at — so the disc
     * steps off the shape and points back at it. The beacons already take no
     * pointer events, and the CSS says so on the ring and the disc as well as
     * the group, so the press underneath always lands on the valve.
     *
     * A step's own `markerOffset` still applies on top of the corner, so the
     * few nudges the guides author by hand keep working. */
    const MARKER_STEP = 14;

    function rootPointForElement(svg, element, offset) {
        const rect = element.getBoundingClientRect();
        const inverse = svg.getScreenCTM().inverse();
        const middle = svg.createSVGPoint();
        middle.x = rect.left + rect.width / 2;
        middle.y = rect.top + rect.height / 2;
        const centre = middle.matrixTransform(inverse);
        const corner = svg.createSVGPoint();
        corner.x = rect.right;
        corner.y = rect.top;
        const point = corner.matrixTransform(inverse);
        // Step outward along the diagonal away from the shape's own middle, so
        // the disc clears the corner rather than sitting on it.
        const span = Math.hypot(point.x - centre.x, point.y - centre.y) || 1;
        point.x += ((point.x - centre.x) / span) * MARKER_STEP;
        point.y += ((point.y - centre.y) / span) * MARKER_STEP;
        point.x += (offset || [0, 0])[0];
        point.y += (offset || [0, 0])[1];
        return point;
    }

    function renderGuideMarkers(stepStates) {
        const svg = document.querySelector("#diagram-container svg");
        if (!svg) return;
        const existing = svg.querySelector("#operation-guide-overlay");
        // Rebuilding the overlay restarts the beacon's own animation, and the
        // five-second refresh rebuilt it whether anything had changed or not —
        // so the ring was cut off mid-breath twice a cycle. Same guide, same
        // step states, same markers: leave them alone and let the pulse run.
        const signature = `${activeGuide ? activeGuide.id : ""}|${stepStates.join(",")}`;
        if (existing && existing.dataset.signature === signature) return;
        existing?.remove();
        if (!activeGuide) return;
        const overlay = document.createElementNS(SVG_NS, "g");
        overlay.id = "operation-guide-overlay";
        overlay.dataset.signature = signature;
        overlay.setAttribute("aria-hidden", "true");
        guideSteps().forEach((step, index) => {
            markerTargets(step).forEach((stepTarget) => {
                const target = svg.querySelector(`#${CSS.escape(stepTarget.id)}`);
                if (!target) return;
                const point = rootPointForElement(svg, target, stepTarget.markerOffset);
                const marker = document.createElementNS(SVG_NS, "g");
                marker.setAttribute("class", `operation-marker ${stepStates[index]}`);
                marker.dataset.step = String(index);
                marker.setAttribute("transform", `translate(${point.x} ${point.y})`);
                // A halo ring behind the current step's markers, so the eye
                // finds "next" without reading the rail.
                const halo = document.createElementNS(SVG_NS, "circle");
                halo.setAttribute("class", "halo");
                halo.setAttribute("r", "18");
                const circle = document.createElementNS(SVG_NS, "circle");
                circle.setAttribute("r", "18");
                const text = document.createElementNS(SVG_NS, "text");
                text.setAttribute("text-anchor", "middle");
                text.setAttribute("dominant-baseline", "central");
                text.textContent = String(index + 1);
                marker.append(halo, circle, text);
                overlay.appendChild(marker);
            });
        });
        svg.appendChild(overlay);
    }

    function renderGuide() {
        const title = document.getElementById("guide-title");
        const summary = document.getElementById("guide-summary");
        const list = document.getElementById("guide-step-list");
        const alert = document.getElementById("guide-alert");
        const clear = document.getElementById("clear-guide");
        if (!title || !summary || !list || !alert || !clear) return;
        document.querySelectorAll(".operation-choice").forEach((button) => {
            button.setAttribute("aria-pressed", String(activeGuide?.id === button.dataset.guideId));
        });
        if (!activeGuide) {
            title.textContent = "No guide selected";
            summary.textContent = "Choose an operation on the left to place numbered steps on the diagram.";
            list.replaceChildren();
            alert.hidden = true;
            clear.hidden = true;
            renderGuideMarkers([]);
            renderGuideCompact([], -1);
            applyCardDefaults();
            scheduleFit();
            return;
        }
        title.textContent = activeGuide.label;
        summary.textContent = activeGuide.summary;
        clear.hidden = false;
        const steps = guideSteps();
        const satisfied = steps.map(guideStepSatisfied);
        const currentIndex = satisfied.findIndex((value) => !value);
        const stepStates = satisfied.map((done, index) => done ? "complete" : index === currentIndex ? "current" : "pending");
        list.replaceChildren(...steps.map((step, index) => {
            const item = document.createElement("li");
            item.className = stepStates[index];
            item.tabIndex = 0;
            const label = document.createElement("span");
            label.textContent = step.action;
            const state = document.createElement("small");
            const names = markerTargets(step).map((target) => displayName(target.id)).join(", ");
            const word = stepStates[index] === "complete" ? "Done in diagram" : stepStates[index] === "current" ? "Next" : "Later";
            state.textContent = names ? `${word} · ${names}` : word;
            item.append(label, state);
            // Pointing at a step swells its markers on the diagram.
            item.addEventListener("mouseenter", () => spotlightStep(index, true));
            item.addEventListener("mouseleave", () => spotlightStep(index, false));
            item.addEventListener("focus", () => spotlightStep(index, true));
            item.addEventListener("blur", () => spotlightStep(index, false));
            return item;
        }));
        const warning = (activeGuide.alerts || []).find((candidate) =>
            candidate.when.every((condition) => normalizedStatus(vacuumState[condition.id]) === condition.status)
        );
        alert.hidden = !warning;
        alert.textContent = warning ? warning.text : "";
        renderGuideMarkers(stepStates);
        renderGuideCompact(steps, currentIndex);
        applyCardDefaults();
        scheduleFit();
    }

    /* The legend teaches the five predicted states once, for the whole page:
     * the colour and its name at a glance, what each one means behind More.
     * Nothing else on the surface explains them again. */
    function renderVacuumLegend() {
        const list = document.getElementById("vacuum-legend");
        const detail = document.getElementById("vacuum-legend-detail");
        const more = document.getElementById("vacuum-more");
        if (!list || !plumbing) return;
        const states = plumbing.states || [];
        // Sealed off is not a colour of its own; it is any of the six above,
        // remembered and hatched. So it joins the legend as the seventh chip,
        // shown on one of them, and its meaning says what the hatch means rather
        // than naming a colour nothing can ever be (owner correction 2026-09-08,
        // letters 20260908-fe94c769-493d71 and 20260908-2c3d9837-37ab4a).
        const held = plumbing.sealed_state;
        const sample = held
            && (states.find((state) => state.id === held.sample) || states[0] || {}).color;
        // A full swatch, not a thin bar. queezz, 2026-09-08: "Make the legend
        // chips larger, a full swatch rather than a thin bar, so the colour can
        // be read there at all" — a five-pixel line of colour is not enough of
        // it to judge, and judging it in the legend is the legend's whole job.
        const chips = states.map((state) => [state.label, state.color, false]);
        if (held && sample) chips.push([held.label, sample, true]);
        list.replaceChildren(...chips.map(([text, colour, hatched]) => {
            const item = document.createElement("li");
            const swatch = document.createElement("span");
            swatch.className = hatched ? "vacuum-swatch vacuum-swatch--sealed" : "vacuum-swatch";
            // `backgroundColor`, never the `background` shorthand: the shorthand
            // resets `background-image`, which is where the sealed hatch lives.
            swatch.style.backgroundColor = colour;
            const label = document.createElement("span");
            label.textContent = text;
            item.append(swatch, label);
            return item;
        }));
        if (detail) {
            // The seven in a row at the top of More, big enough to compare one
            // against another rather than each against the drawing.
            const row = document.createElement("div");
            row.className = "vacuum-swatch-row";
            chips.forEach(([text, colour, hatched]) => {
                const cell = document.createElement("figure");
                const block = document.createElement("span");
                block.className = hatched
                    ? "vacuum-swatch-big vacuum-swatch--sealed"
                    : "vacuum-swatch-big";
                block.style.backgroundColor = colour;
                const caption = document.createElement("figcaption");
                caption.textContent = text;
                cell.append(block, caption);
                row.appendChild(cell);
            });
            const meanings = states.map((state) => [state.label, state.meaning]);
            if (held && sample) meanings.push([held.label, held.meaning]);
            const lines = [row, ...meanings.map(([text, meaning]) => {
                const line = document.createElement("p");
                line.className = "muted";
                line.textContent = `${text}: ${meaning}.`;
                return line;
            })];
            // Four sentences, each said once for the whole surface: what a
            // filled body means, what a two-tone one means, what a valve's own
            // two inks mean, and what a pump's colour says. Nothing else on the
            // page explains them again.
            [
                "The two vessels, the manifold tees and the cross are filled with the same colour.",
                "A two-tone body means two things reach it.",
                "An open valve wears the colour running through it, edge and all; a closed one is white with a black outline, and the colour stops on both sides of it.",
                "A running pump wears what it is doing, over the black rim it was drawn with; a stopped one is left as drawn, in grey, and its rim and inner lines recede to dark grey.",
                "A hatched colour means the space is shut and still holding that; the reading above says what, and for how long."
            ].forEach((sentence) => {
                const line = document.createElement("p");
                line.className = "muted";
                line.textContent = sentence;
                lines.push(line);
            });
            const band = document.createElement("p");
            band.className = "band-switch";
            const label = document.createElement("label");
            const box = document.createElement("input");
            box.type = "checkbox";
            box.id = "pipe-band";
            label.append(box, document.createTextNode(" Draw coloured pipes wider"));
            band.appendChild(label);
            lines.push(band);
            detail.replaceChildren(...lines);
        }
        if (more && !more.dataset.wired) {
            more.dataset.wired = "1";
            more.addEventListener("click", () => {
                const open = more.getAttribute("aria-expanded") === "true";
                more.setAttribute("aria-expanded", String(!open));
                more.textContent = open ? "More" : "Less";
                if (detail) detail.hidden = open;
            });
        }
    }

    /* The width queezz drew each line with, read once before anything of ours
     * has been written over it. The band is a multiple of it, so his own
     * hierarchy — thin gas tubing, thicker vacuum pipe — survives the widening,
     * and switching the band off restores exactly what he drew. */
    const authoredWidth = new Map();

    /* And the fill he drew each shape with, read the same way and for the same
     * reason. Clearing `element.style.fill` does **not** restore it: his fill
     * lives in that very `style` attribute, so clearing the property deletes it
     * and the shape falls through to the CSS default, black. Measured 2026-09-08
     * on the first attempt at leaving a stopped pump alone — every stopped pump
     * came back black. So the authored value is captured once, before anything
     * of ours has been written over it, and written back explicitly. */
    const authoredFill = new Map();

    function fillOf(element) {
        if (!authoredFill.has(element.id)) {
            authoredFill.set(element.id, window.getComputedStyle(element).fill || "");
        }
        return authoredFill.get(element.id);
    }

    function widthOf(element) {
        if (!authoredWidth.has(element.id)) {
            authoredWidth.set(
                element.id, parseFloat(window.getComputedStyle(element).strokeWidth) || 0
            );
        }
        return authoredWidth.get(element.id);
    }

    /* Paint each pipe with what its volume most likely holds. The prediction is
     * the server's, from the same volume map the legend reads, so one rule
     * decides both.
     *
     * A vessel is a volume you can see into, and a tee or a cross is a small
     * one, so those say their state by their body: the full state colour as a
     * fill, keeping the dark outline queezz drew (2026-09-08, "we can go very
     * loud, why not? Color it the color of the vacuum I say"). Every other
     * element is a line, and a coloured line is simply drawn wider — a solid
     * widening of his own stroke, never the translucent glow of 0.11.2, which
     * he read as a neon sign. An isolated line is not widened at all.
     *
     * The warning for air is the colour itself, named once in the key: a
     * sentence repeating it in the rail was a second telling of the same fact,
     * and it grew with the number of volumes until it took the guide's own
     * room (measured 2026-09-08). */
    /* One gradient per pair of colours that meet, kept in the drawing's own
     * defs so a body can point at it by name. An SVG gradient is painted across
     * a shape's bounding box rather than along a path, which is exactly why it
     * is used on the shapes and never on a bent pipe. */
    function mixGradient(svg, dominant, contributing) {
        const name = `pihti-mix-${dominant}-${contributing}`.replace(/#/g, "");
        const defs = paintDefs(svg);
        if (!defs.querySelector(`#${CSS.escape(name)}`)) {
            const gradient = document.createElementNS(SVG_NS, "linearGradient");
            gradient.id = name;
            gradient.setAttribute("x1", "0");
            gradient.setAttribute("y1", "0");
            gradient.setAttribute("x2", "1");
            gradient.setAttribute("y2", "0");
            [[0, dominant], [1, contributing]].forEach(([offset, colour]) => {
                const stop = document.createElementNS(SVG_NS, "stop");
                stop.setAttribute("offset", String(offset));
                stop.setAttribute("stop-color", colour);
                gradient.appendChild(stop);
            });
            defs.appendChild(gradient);
        }
        return `url(#${name})`;
    }

    /* The one defs block this page writes into, so a gradient and a hatch do
     * not each invent their own. */
    function paintDefs(svg) {
        let defs = svg.querySelector("#pihti-mix-defs");
        if (!defs) {
            defs = document.createElementNS(SVG_NS, "defs");
            defs.id = "pihti-mix-defs";
            svg.insertBefore(defs, svg.firstChild);
        }
        return defs;
    }

    /* The hatch a sealed volume wears over the colour of whatever it is still
     * holding. queezz, 2026-09-08 (letter 20260908-2c3d9837-37ab4a): "Sealed off
     * with good vacuum 3 days ago says something." The colour says what is in
     * there; the texture says nothing is reaching it. Stripes of the drawing's
     * own ground are cut through the state colour at 45 degrees, so every
     * coloured pixel keeps its full strength — a lighter tint would have dropped
     * two of the six below the palette's own 3:1 floor against that ground.
     *
     * The same pattern serves a filled body and a drawn line, and it is built
     * here exactly as `sealed_pattern_markup` builds it for `/state.svg`, from
     * the same three numbers in the map, so the screen and a saved render cannot
     * disagree. */
    function sealedPattern(svg, colour) {
        const name = `pihti-sealed-${colour}`.replace(/#/g, "");
        const defs = paintDefs(svg);
        if (!defs.querySelector(`#${CSS.escape(name)}`)) {
            const drawing = plumbing?.drawing || {};
            const ground = drawing.ground || "#e3dfd6";
            const period = Number(drawing.sealed_period) || 12;
            const stripe = Number(drawing.sealed_stripe) || 5;
            const pattern = document.createElementNS(SVG_NS, "pattern");
            pattern.id = name;
            pattern.setAttribute("width", String(period));
            pattern.setAttribute("height", String(period));
            pattern.setAttribute("patternUnits", "userSpaceOnUse");
            pattern.setAttribute("patternTransform", "rotate(45)");
            [[period, colour], [stripe, ground]].forEach(([width, paint]) => {
                const bar = document.createElementNS(SVG_NS, "rect");
                bar.setAttribute("width", String(width));
                bar.setAttribute("height", String(period));
                bar.setAttribute("fill", paint);
                pattern.appendChild(bar);
            });
            defs.appendChild(pattern);
        }
        return `url(#${name})`;
    }

    /* The paint an element wears: its own colour, or the sealed hatch of that
     * colour when nothing is reaching the volume any more. */
    function paintFor(svg, item, colour) {
        if (!item.sealed_paint || !svg || !colour) return colour;
        return sealedPattern(svg, colour);
    }

    /* A bottle symbol split into its letters and its trailing count: H2 -> H, 2.
     * queezz, 2026-09-08 (letter 20260908-e6ada507-7aa064): "Can we do H2, O2
     * with a subscript?" Ar and He carry no digit and come back whole. */
    function splitFormula(symbol) {
        const match = /^([A-Za-z]+)([0-9]*)$/.exec(symbol || "");
        return match ? [match[1], match[2]] : [symbol || "", ""];
    }

    /* The formula written into an SVG text node with a true subscript — a tspan
     * dropped by a fraction of the mark's own size and drawn smaller, the way
     * queezz's bottle symbols draw it on his own SVG, never a Unicode subscript
     * glyph a font may not carry. The same fractions the saved render uses. */
    function writeFormula(text, symbol, radius) {
        const [letters, digits] = splitFormula(symbol);
        text.textContent = letters;
        if (!digits) return;
        const sub = document.createElementNS(SVG_NS, "tspan");
        sub.setAttribute("dy", (radius * 0.22).toFixed(2));
        sub.setAttribute("font-size", (radius * 0.62).toFixed(2));
        sub.textContent = digits;
        text.appendChild(sub);
    }

    /* And the same formula in ordinary HTML, for the legend and the readout,
     * where a <sub> is the right element and the browser sizes it. */
    function formulaHtml(symbol) {
        const [letters, digits] = splitFormula(symbol);
        const span = document.createElement("span");
        span.append(letters);
        if (digits) {
            const sub = document.createElement("sub");
            sub.textContent = digits;
            span.appendChild(sub);
        }
        return span;
    }

    /* The bottle symbol, drawn large inside a vessel that is holding that gas.
     * queezz, 2026-09-08: "we can put a gas in a circle (same as the bottle
     * sign) inside the plasma vessel. Ar, O2, H2. So it's visible big at a
     * glance." Several gases draw several circles. It sits below the guide
     * overlay, so a beacon is never painted over. */
    function renderGasSymbols(svg, drawn) {
        svg.querySelector("#pihti-gas-symbols")?.remove();
        if (!drawn || !drawn.length) return;
        const group = document.createElementNS(SVG_NS, "g");
        group.id = "pihti-gas-symbols";
        group.setAttribute("aria-hidden", "true");
        drawn.forEach((item) => {
            // The box is the map's, in the drawing's own coordinates: the
            // plasma vessel is a cross, and the middle of its bounding box is
            // not the middle of anything a circle fits inside.
            const [left, top, right, bottom] = item.box || [];
            if (![left, top, right, bottom].every((value) => typeof value === "number")) return;
            const width = right - left;
            const height = bottom - top;
            const count = item.symbols.length;
            // The radius travels with the mark, worked out by the same rule that
            // sizes it in a saved render, so the two can never differ. queezz,
            // 2026-09-08 (letter 20260908-8eaaa7a9-334955): "The qms-vacuum gas
            // circle is bigger for some reason" — it was drawn at one absolute
            // size in both vessels, which is nearly the whole width of the
            // narrower QMS box. It is a fraction of the smaller side of the body
            // it sits in now, capped at the widest chamber's own mark.
            const radius = Number(item.radius) > 0
                ? Number(item.radius)
                : Math.max(6, Math.min(width / (2.2 * count), height / 2.6));
            const step = radius * 2.2;
            const middleY = top + height / 2;
            const start = left + width / 2 - step * (count - 1) / 2;
            item.symbols.forEach((symbol, index) => {
                const circle = document.createElementNS(SVG_NS, "circle");
                circle.setAttribute("class", "gas-symbol-body");
                circle.setAttribute("cx", String(start + step * index));
                circle.setAttribute("cy", String(middleY));
                circle.setAttribute("r", String(radius));
                const text = document.createElementNS(SVG_NS, "text");
                text.setAttribute("class", "gas-symbol-text");
                text.setAttribute("x", String(start + step * index));
                text.setAttribute("y", String(middleY));
                text.setAttribute("text-anchor", "middle");
                text.setAttribute("dominant-baseline", "central");
                text.setAttribute("font-size", String(radius * 0.9));
                writeFormula(text, symbol, radius);
                group.append(circle, text);
            });
        });
        const overlay = svg.querySelector("#operation-guide-overlay");
        if (overlay) svg.insertBefore(group, overlay);
        else svg.appendChild(group);
    }

    function paintPrediction(prediction) {
        lastPrediction = prediction;
        const svg = document.querySelector("#diagram-container svg");
        Object.entries(prediction.elements || {}).forEach(([id, item]) => {
            const element = document.getElementById(id);
            if (!element) return;
            if (item.part) {
                // The rim and the inner symbol lines of a pump, which are drawn
                // elements of their own with their own ids: a group's stroke
                // cannot reach a child that carries its own inline one. queezz,
                // 2026-09-08 (letter 20260908-e2498698-5c9c50): "we can also
                // gray out pump edges and lines. Dark gray. So it speaks more
                // loudly that that is closed." Only the stroke is touched — the
                // fill and the dashes he drew are his, and clearing either would
                // repaint his own drawing rather than say something about it.
                element.style.stroke = item.stroke;
                return;
            }
            if (item.valve || item.pump) {
                // A valve says its position with its body, at every size: an
                // open one wears the colour flowing through it, a shut one the
                // closed ink, so a colour never runs through a closed valve and
                // a small open one is readable from arm's length. Its edge goes
                // with its fill (queezz, 2026-09-08: "I think I like the valves
                // edge to be same color as the fill. When closed, black border
                // white fill is good. Stands out.") — so an open valve has no
                // black edge and reads as part of the pipe, and a closed one is
                // the single dark-rimmed shape on the drawing.
                //
                // A pump wears what it is doing beside it: a running turbo the
                // high-vacuum colour of the side it serves, a running rotary or
                // scroll the rough-vacuum colour. A **stopped** pump carries no
                // colour of ours at all — it is put back to the grey queezz drew
                // it in, because that grey already means off (2026-09-08: "Gray
                // for off was lost. Why? WHY???").
                //
                // An open valve inside a sealed space is part of that space and
                // wears the same hatch: a solid one would read as a route
                // something is coming through right now.
                const authoredPaint = fillOf(element);
                element.style.fill = item.fill ? paintFor(svg, item, item.fill) : authoredPaint;
                if (item.stroke) element.style.stroke = paintFor(svg, item, item.stroke);
                element.style.strokeDasharray = item.dash || "none";
                element.style.opacity = typeof item.opacity === "number" ? String(item.opacity) : "";
                return;
            }
            if (item.flange) {
                // The blank flange: not a vacuum claim at all, so it wears the
                // flange tone and never a state colour or the closed grey.
                element.style.stroke = item.stroke;
                element.style.strokeLinecap = "round";
                element.style.strokeLinejoin = "round";
                const drawn = widthOf(element);
                if (drawn) element.style.strokeWidth = String(drawn);
                return;
            }
            if (item.fill) {
                // One colour, body and edge alike. queezz, 2026-09-08: "I think
                // I'd like it without black shape borders. All one color. Why
                // not? Color speaks vacuum. Black border speaks... shapes?" So a
                // vessel, a tee and a cross drop the outline he drew and stand
                // in the state colour alone. Valves, pumps and gauges keep
                // theirs: they are equipment, not volumes.
                // Two things reaching one volume show on the shape and nowhere
                // else: a two-stop fill from the dominant colour to the
                // contributing one. queezz: "I think the shape gradient is a
                // good signal. 'You are pumping from two sides, take note'."
                // And a sealed body wears its remembered colour hatched: nothing
                // is reaching it, which is the whole point of it, so it never
                // carries a second tone either.
                element.style.fill = item.sealed
                    ? paintFor(svg, item, item.fill)
                    : item.mix && svg
                        ? mixGradient(svg, item.fill, item.mix)
                        : item.fill;
                if (item.stroke) element.style.stroke = paintFor(svg, item, item.stroke);
                element.style.strokeLinejoin = "round";
                return;
            }
            const authored = widthOf(element);
            element.style.stroke = paintFor(svg, item, item.stroke);
            // Round caps and joins close the notches a butt end leaves where a
            // gauge stem meets its pipe, without touching the drawing itself
            // (queezz, 2026-09-08: "I see small defect when line is enlarged").
            element.style.strokeLinecap = "round";
            element.style.strokeLinejoin = "round";
            if (!authored) return;
            element.style.strokeWidth = String(bandOn && item.band ? authored * item.band : authored);
        });
        if (svg) renderGasSymbols(svg, prediction.gas_symbols || []);
        // The drawn valve the Line configuration governs (the `Membrane`
        // element) is painted by the prediction itself now, in the loop above,
        // so `/state.svg` and this page cannot disagree about it. Present or
        // absent, not merely a different shade of the same blob: under
        // *Membrane installed* it is a solid plug across the line, and under
        // *Pipe open*, *Blank* and *Boron deposition* nothing of the app's is
        // mounted there, so it is an empty dashed outline and the line reads
        // straight through it. Under *Blank* the blank itself is said further
        // along, by the probe segment in the flange tone.
        renderConnections(prediction.connections || {});
        // A guide step may be satisfied by the prediction rather than by a valve
        // position, so the steps are read again now that this prediction has
        // landed — `applyState` renders them before it asks for one.
        renderGuide();
    }

    /* The band is a reading aid, not a claim, so it has a switch and the switch
     * lives with the key that explains the colours. The choice is this reader's
     * own, so it stays in this browser. */
    function setupBandToggle() {
        const toggle = document.getElementById("pipe-band");
        if (!toggle) return;
        let stored = null;
        try { stored = window.localStorage.getItem("pihti.pipeBand"); } catch (error) { stored = null; }
        bandOn = stored === "on";
        toggle.checked = bandOn;
        toggle.addEventListener("change", () => {
            bandOn = toggle.checked;
            if (lastPrediction) paintPrediction(lastPrediction);
            try {
                window.localStorage.setItem("pihti.pipeBand", bandOn ? "on" : "off");
            } catch (error) { /* a browser that refuses storage still draws */ }
        });
    }

    /* A label as it reads inside a sentence: "the plasma vessel", but "the QMS
     * vessel" — a designation the rig spells in capitals keeps them. */
    function inSentence(label) {
        if (!label) return label;
        return /^[A-Z]{2}/.test(label) ? label : label.charAt(0).toLowerCase() + label.slice(1);
    }

    function joinWords(words) {
        if (words.length < 2) return words.join("");
        return `${words.slice(0, -1).join(", ")} and ${words[words.length - 1]}`;
    }

    /* What the prediction finds each vessel joined to, as labelled rows rather
     * than as one running sentence. queezz asked the question in this order —
     * "if upstream and downstream are connected to a) each other b) gas c) vent
     * air" — and then, reading the answer written out as a long line per vessel
     * (letter 20260908-aa2558c2-f3d03e): "With proper groups, not a long-line
     * which is a list."
     *
     * So: Open to, Gas, Vent, Pumped by, Sealed since — his own order, with the
     * pumps last as before, and a row with nothing in it is not drawn at all.
     * It is the same prediction the colours come from, and the card says once,
     * at its top, that all of it is predicted rather than measured. */
    function connectionRows(item) {
        const rows = [];
        if ((item.joined || []).length) {
            rows.push(["Open to", joinWords(item.joined.map(
                (name) => inSentence(plumbing?.volumes?.[name]?.label || name)
            ))]);
        }
        if ((item.gas || []).length) {
            rows.push(["Gas", joinWords(item.gas.map((source) => source.gas))]);
        }
        if ((item.air || []).length) {
            rows.push(["Vent", joinWords(item.air.map(
                (valve) => inSentence(displayName(valve.id))
            ))]);
        }
        if ((item.pumps || []).length) {
            rows.push(["Pumped by", joinWords(item.pumps.map(
                (pump) => inSentence(displayName(pump.id))
            ))]);
        }
        return rows;
    }

    function rowList(rows) {
        const list = document.createElement("dl");
        list.className = "vacuum-group__rows";
        rows.forEach(([label, value]) => {
            const term = document.createElement("dt");
            term.textContent = label;
            const detail = document.createElement("dd");
            if (value instanceof Node) detail.append(value);
            else detail.textContent = value;
            list.append(term, detail);
        });
        return list;
    }

    /* What a sealed vessel is still holding, said the way queezz said it:
     * "sealed, was high vacuum, 1 day", "sealed, under nitrogen, 2 weeks",
     * "sealed, under air, 1 month" (letter 20260908-2c3d9837-37ab4a). The state
     * name is trimmed at its comma, because "was high vacuum, plasma side, 1
     * day" has one comma too many to read out loud — which side it was is said
     * by the colour on the drawing beside it. */
    function sealedPhrase(held) {
        if (held.was === "air") return [document.createTextNode("under air")];
        if (held.was === "gas") {
            const names = (held.symbols || []).map(
                (symbol) => (plumbing?.gas_sources || []).find(
                    (source) => source.symbol === symbol
                )?.gas
            ).filter(Boolean);
            if (names.length) return [document.createTextNode(`under ${joinWords(names)}`)];
            // No name recorded for it: say the formula, with its subscript.
            const symbols = (held.symbols || []).map(formulaHtml);
            if (!symbols.length) return [document.createTextNode("under gas")];
            const out = [document.createTextNode("under ")];
            symbols.forEach((span, index) => {
                if (index) out.push(document.createTextNode(index === symbols.length - 1 ? " and " : ", "));
                out.push(span);
            });
            return out;
        }
        const states = Object.fromEntries((plumbing?.states || []).map((state) => [state.id, state]));
        const label = (states[held.was]?.label || held.was).split(",")[0];
        return [document.createTextNode(`was ${label.toLowerCase()}`)];
    }

    /* The operator's next move, from his own three sentences: bake a chamber
     * that has stood under air or nitrogen too long; read the gauge before
     * pumping one that has held vacuum, and choose between opening the turbo
     * straight in and roughing through the bypass first. The gauge is named
     * because the diagram predicts and the gauge measures. */
    function sealedHint(hint) {
        const gauges = (hint.gauges || []).map((id) => inSentence(displayName(id)));
        // One sentence, naming this vessel's own gauges: two vessels sitting in
        // the same state print side by side, and the same three sentences twice
        // is a lecture rather than a readout.
        const read = gauges.length ? `Read the ${joinWords(gauges)}` : "Read a gauge on it";
        return `${hint.bake ? "Consider baking. " : ""}${read}; ${hint.advice || ""}.`;
    }

    /* The state name as it fits a 16rem rail: trimmed at its comma, because
     * "high vacuum, plasma side" spends the whole line saying what the colour
     * beside it already says. The legend under the groups carries the full
     * names, once. */
    function stateWord(id) {
        const states = Object.fromEntries((plumbing?.states || []).map((state) => [state.id, state]));
        return (states[id]?.label || id).split(",")[0].toLowerCase();
    }

    function stateColour(id) {
        const states = Object.fromEntries((plumbing?.states || []).map((state) => [state.id, state]));
        return states[id]?.color || "#000000";
    }

    function stateSwatch(item) {
        const held = item.sealed;
        const swatch = document.createElement("span");
        swatch.className = held ? "vacuum-swatch vacuum-swatch--sealed" : "vacuum-swatch";
        // The colour goes on the swatch itself, as it does in the legend. It
        // used to go on an `<i>` inside it, left from the thin-bar chip the
        // legend replaced in 0.16.0 — and that `<i>` has had no rule of its own
        // since, so every chip in this readout was drawing empty.
        swatch.style.backgroundColor = stateColour(held ? held.was : item.state);
        return swatch;
    }

    function emptyReadout() {
        // History carries no prediction until a moment is chosen, and an empty
        // list under a heading reads as "nothing is connected" rather than as
        // "nothing has been asked yet". Say which it is.
        const empty = document.createElement("li");
        empty.className = "muted";
        empty.textContent = window.historyMode
            ? "Choose a moment in the timeline to read what each vessel was joined to."
            : "Not read yet.";
        return empty;
    }

    function renderConnections(connections) {
        const list = document.getElementById("vacuum-connections");
        if (!list) return;
        if (!Object.keys(connections).length) {
            list.replaceChildren(emptyReadout());
            renderStateCompact(connections);
            scheduleFit();
            return;
        }
        list.replaceChildren(...Object.values(connections).map((item) => {
            const held = item.sealed;
            const group = document.createElement("li");
            const head = document.createElement("div");
            head.className = "vacuum-group__head";
            const name = document.createElement("b");
            name.textContent = item.label;
            const word = document.createElement("span");
            word.className = "vacuum-group__state";
            if (held) {
                // A shut vessel says what it is holding, not "isolated,
                // unknown" — that grey is for a volume with no memory at all.
                // Its own colour, hatched, is on the swatch beside it.
                word.append("sealed, ", ...sealedPhrase(held));
            } else {
                word.textContent = stateWord(item.state);
            }
            head.append(stateSwatch(item), name, word);
            group.append(head);
            const rows = connectionRows(item);
            if (held) rows.push(["Sealed since", held.duration]);
            if (rows.length) {
                group.append(rowList(rows));
            } else {
                const nothing = document.createElement("p");
                nothing.className = "vacuum-group__empty";
                nothing.textContent = "Nothing open to it.";
                group.append(nothing);
            }
            if (held?.hint) {
                const hint = document.createElement("p");
                hint.className = "vacuum-group__hint";
                hint.textContent = sealedHint(held.hint);
                group.append(hint);
            }
            return group;
        }));
        renderStateCompact(connections);
        scheduleFit();
    }

    /* -- the two right-rail cards, and how they give ground ---------------- */

    /* Collapsed, the state card is one line per vessel: the colour chip and the
     * state word, nothing else. queezz and the Commander, 2026-09-08 (letter
     * 20260908-50f93f77-8e8a28): "We should keep the predicted state somewhere,
     * and maybe not hide, but collapse." A collapsed card still says what it is
     * for; it never becomes an empty heading. */
    function renderStateCompact(connections) {
        const list = document.getElementById("vacuum-compact");
        if (!list) return;
        const items = Object.values(connections || {});
        if (!items.length) {
            list.replaceChildren(emptyReadout());
            return;
        }
        list.replaceChildren(...items.map((item) => {
            const row = document.createElement("li");
            const name = document.createElement("b");
            name.textContent = item.label;
            const word = document.createElement("span");
            word.className = "vacuum-group__state";
            word.textContent = item.sealed ? "sealed" : stateWord(item.state);
            row.append(stateSwatch(item), name, word);
            return row;
        }));
    }

    /* Collapsed, the guide card is its name and the current step with its
     * number — the one thing an operator mid-procedure needs to see while the
     * state card is open. */
    function renderGuideCompact(steps, currentIndex) {
        const line = document.getElementById("guide-compact");
        if (!line) return;
        line.replaceChildren();
        if (!activeGuide) {
            line.textContent = "No guide selected.";
            return;
        }
        const name = document.createElement("b");
        name.textContent = activeGuide.label;
        line.append(name);
        const step = document.createElement("span");
        step.className = "card-compact__step";
        step.textContent = currentIndex < 0
            ? "Every step is done in the diagram."
            : `Step ${currentIndex + 1} of ${steps.length}: ${steps[currentIndex].action}`;
        line.append(step);
    }

    /* Which cards are open. The reader's own press is remembered per browser and
     * always wins; until one is made, the default follows the situation — with a
     * guide running the guide is open and the state is compact, with no guide
     * the state is open (letter 20260908-50f93f77-8e8a28). */
    const CARD_KEYS = {state: "pihti.rail.stateCard", guide: "pihti.rail.guideCard"};
    const cardChoice = {state: null, guide: null};

    function readCardChoice(card) {
        try { return window.localStorage.getItem(CARD_KEYS[card]); } catch (error) { return null; }
    }

    function writeCardChoice(card, open) {
        try { window.localStorage.setItem(CARD_KEYS[card], open ? "open" : "collapsed"); }
        catch (error) { /* a browser that refuses storage still opens and closes */ }
    }

    function setCardOpen(card, open) {
        const toggle = document.getElementById(`${card}-card-toggle`);
        const body = document.getElementById(`${card}-card-body`);
        if (!toggle || !body) return;
        toggle.setAttribute("aria-expanded", String(open));
        body.hidden = !open;
        const compact = document.getElementById(card === "state" ? "vacuum-compact" : "guide-compact");
        if (compact) compact.hidden = open;
    }

    function applyCardDefaults() {
        const running = Boolean(activeGuide);
        [["state", !running], ["guide", true]].forEach(([card, fallback]) => {
            const stored = cardChoice[card];
            setCardOpen(card, stored === null ? fallback : stored === "open");
        });
    }

    function setupRailCards() {
        Object.keys(CARD_KEYS).forEach((card) => {
            cardChoice[card] = readCardChoice(card);
            const toggle = document.getElementById(`${card}-card-toggle`);
            if (!toggle || toggle.dataset.wired) return;
            toggle.dataset.wired = "1";
            toggle.addEventListener("click", () => {
                const open = toggle.getAttribute("aria-expanded") !== "true";
                cardChoice[card] = open ? "open" : "collapsed";
                writeCardChoice(card, open);
                setCardOpen(card, open);
                scheduleFit();
            });
        });
        applyCardDefaults();
    }

    /* Three stages before a scroll bar, in the order queezz asked for them
     * (letter 20260908-8853f919-4c54b6, on the six-step Vent Plasma card at
     * about 2000x1540: "the right procedure card gets a nasty scroll bar..
     * Would be nice if we can avoid that"):
     *
     *   1. the card grows to the rail's own height;
     *   2. still longer, the steps already done fold to one line each and the
     *      current step and the next stay in full;
     *   3. only then a bar inside the list, thin and quiet.
     *
     * Everything is measured in the rendered DOM rather than counted in rows: a
     * row count picked from one author's screen caps a list that had room and
     * leaves one that has none uncapped (Fleet WEBUI-COOKBOOK.md). The page
     * itself never scrolls for the rail — the rail scrolls inside its own box,
     * which is the escape valve when both cards are open and long. */
    const STEP_LIST_FLOOR = 90;
    let fitPending = false;

    /* Measure after the browser has settled, never in the middle of the change
     * that provoked it. Measured 2026-09-09: called straight out of a `resize`
     * or a re-render, the fit read a card height from a layout that was still
     * moving, stopped folding one step in, and left the rail overflowing — the
     * same reading a moment later folded four and fitted exactly. One short
     * timer, one pending flag, and every caller goes through here — a timer
     * rather than an animation frame, because a browser stops handing out
     * frames to a tab nobody is looking at, and a rail that only fits itself
     * while it is on screen is a rail that is wrong the moment you come back
     * to it. */
    const FIT_DELAY = 50;

    function scheduleFit() {
        if (fitPending) return;
        fitPending = true;
        window.setTimeout(() => {
            fitPending = false;
            fitRail();
        }, FIT_DELAY);
    }

    function fitRail() {
        const rail = document.getElementById("guide-steps");
        const card = document.getElementById("guide-card");
        const list = document.getElementById("guide-step-list");
        if (!rail || !card || !list || !list.children.length) return;
        list.classList.remove("guide-steps--scrolls");
        list.style.maxHeight = "";
        Array.from(list.children).forEach((item) => item.classList.remove("folded"));
        // A drawer is a full-height panel of its own and the rail's height rule
        // does not apply there; below the breakpoint the drawer simply scrolls.
        if (!rail.clientHeight || window.matchMedia("(max-width: 1199px)").matches) return;
        // A `display: none` child is not a flex item and takes no gap with it,
        // so both the heights and the gaps are counted from what is really laid
        // out — the drawer's own Close button is hidden at these widths.
        const laidOut = Array.from(rail.children).filter((child) => child.getClientRects().length);
        const others = laidOut
            .filter((child) => child !== card)
            .reduce((total, child) => total + child.getBoundingClientRect().height, 0);
        const gaps = 14 * Math.max(0, laidOut.length - 1);
        const room = rail.clientHeight - others - gaps;
        if (card.getBoundingClientRect().height <= room) return;
        // 2. Fold everything but the current step and the one after it: the
        // steps already done first, oldest first, then the later ones from the
        // end backwards. "The current step plus the next stay in full" is his
        // own wording, and those two are the only ones an operator is about to
        // act on.
        const rows = Array.from(list.children);
        const current = rows.findIndex((item) => item.classList.contains("current"));
        const keep = new Set(current < 0 ? [] : [current, current + 1]);
        const foldable = rows
            .map((item, index) => index)
            .filter((index) => !keep.has(index))
            .sort((left, right) => {
                const done = (index) => rows[index].classList.contains("complete");
                if (done(left) !== done(right)) return done(left) ? -1 : 1;
                return done(left) ? left - right : right - left;
            });
        foldable.forEach((index) => {
            if (card.getBoundingClientRect().height <= room) return;
            const item = rows[index];
            // A folded step is one line, so its own wording moves to its title
            // — nothing a reader could need is thrown away.
            if (!item.title) item.title = item.firstChild?.textContent || "";
            item.classList.add("folded");
        });
        if (card.getBoundingClientRect().height <= room) return;
        // 3. A thin quiet bar inside the list, and never a crushed card: below
        // the floor the rail takes the overflow instead.
        const overflow = card.getBoundingClientRect().height - room;
        const capped = list.getBoundingClientRect().height - overflow;
        if (capped < STEP_LIST_FLOOR) return;
        list.style.maxHeight = `${Math.floor(capped)}px`;
        list.classList.add("guide-steps--scrolls");
    }

    async function refreshPrediction(moment) {
        if (!plumbing || predictionPending) return;
        if (window.historyMode && !moment) return;
        predictionPending = true;
        try {
            const query = moment ? `?at=${encodeURIComponent(moment)}` : "";
            const response = await fetch(`/predicted-vacuum${query}`);
            if (response.ok) paintPrediction(await response.json());
        } catch (error) {
            console.error("Predicted vacuum state could not be read", error);
        } finally {
            predictionPending = false;
        }
    }

    function applyState(state, moment, prediction) {
        if (!elementsConfig.length) return;
        // Everything the prediction fills — every valve, and the five bodies —
        // is the prediction's to paint (0.15.0). Painting the operator palette
        // over it first and correcting it a moment later is what a flicker is.
        const predicted = lastPrediction?.elements || {};
        elementsConfig.forEach((element) => {
            // The Line configuration sets this element's fill in
            // paintPrediction, from the same annotation it has no press of its
            // own to disagree with — a raw press-state fill here would only be
            // overwritten, and could flash first.
            if (element.followsLineMode) return;
            if (predicted[element.id]?.fill) return;
            const diagramElement = document.getElementById(element.id);
            if (!diagramElement) return;
            // An element may declare no operator palette at all — the pumps do
            // not, since 0.16.1 — and then nothing here paints it.
            if (!element.colors) return;
            const status = normalizedStatus(state[element.id]);
            diagramElement.style.fill = element.colors[status];
        });
        // A prediction that came back with the change itself needs no second
        // request: one small round trip, one redraw in place.
        if (prediction) {
            paintPrediction(prediction);
            return;
        }
        renderGuide();
        refreshPrediction(moment);
    }

    /* -- practice: rehearse the presses, record the procedure once ---------
     *
     * queezz, 2026-09-08 (letters 20260908-9d38bf34-8415c7 and
     * 20260908-e460b66f-616b53): "I want now a 'practice' before recording
     * history mode somehow. You open the valve, and see where color
     * (vacuum/air) goes. Then you can undo. Also maybe using that we can do a
     * procedure, then save state. That way one state jump, less history
     * spamming. And better operational safety."
     *
     * While it is on, `vacuumState` *is* the practised copy, so every other
     * thing on this page — the colours, the marks, the sealed readout, the
     * 0.13.0 warnings, the guides' own beacons — runs over it without knowing
     * anything about practice. The recorded state is kept aside to go back to.
     * Nothing reaches the state file or the history until Save. */
    function practiceUnsaved() {
        return practiceOn && practicePresses.length > 0;
    }

    /* The prediction for the practised copy, and the memory it leaves behind.
     * Both travel to the server and back: the predictor has been state in,
     * prediction out since 0.17.0 exactly so this could run over a copy, and
     * the recorded memory never moves while a rehearsal is going on. */
    async function refreshPractice() {
        try {
            const response = await fetch("/practice/prediction", {
                method: "POST",
                headers: {"Content-Type": "application/json"},
                body: JSON.stringify({state: vacuumState, memory: practiceMemory})
            });
            if (!response.ok) return;
            const result = await response.json();
            practiceMemory = result.memory || practiceMemory;
            applyState(vacuumState, undefined, result.prediction);
        } catch (error) {
            console.error("The practised state could not be predicted", error);
        }
    }

    function renderPractice() {
        const note = document.getElementById("practice-note");
        const actions = document.getElementById("practice-actions");
        const save = document.getElementById("practice-save");
        const undo = document.getElementById("practice-undo");
        const banner = document.getElementById("practice-banner");
        const toggle = document.getElementById("practice-toggle");
        if (!note || !actions || !save || !undo || !banner || !toggle) return;
        toggle.checked = practiceOn;
        actions.hidden = !practiceOn;
        banner.hidden = !practiceOn;
        // One line, and it says which mode this is rather than lecturing about
        // both: while practising it is the standing reminder that nothing is
        // recorded until Save, which is the sentence queezz asked to be taught.
        note.textContent = practiceOn
            ? "Nothing is recorded until you press Save."
            : "Presses are recorded in history as you make them.";
        const count = practicePresses.length;
        // The count rides on the button, so the thing you must press is also
        // the thing that says how much is waiting.
        save.textContent = count
            ? `Save ${count} press${count === 1 ? "" : "es"} to history`
            : "Save to history";
        save.disabled = !count;
        undo.disabled = !count;
        renderPracticeCountdown();
    }

    function renderPracticeCountdown() {
        const line = document.getElementById("practice-timer");
        if (!line) return;
        if (!practiceUnsaved() || !practiceDeadline) {
            line.textContent = "";
            return;
        }
        const left = Math.max(0, Math.round((practiceDeadline - Date.now()) / 1000));
        const minutes = Math.floor(left / 60);
        const seconds = String(left % 60).padStart(2, "0");
        line.textContent = `Saves itself in ${minutes}:${seconds}.`;
    }

    function stopPracticeTimer() {
        practiceDeadline = 0;
        if (practiceTick !== null) {
            window.clearInterval(practiceTick);
            practiceTick = null;
        }
        renderPracticeCountdown();
    }

    /* The fallback, counting down from the last press. It never fires while a
     * confirm box is open — `isInteracting` is held from before the box
     * appears until after the press lands — so the timer waits its turn rather
     * than saving a sequence somebody is still deciding about. */
    function startPracticeTimer() {
        practiceDeadline = Date.now() + practiceAutosaveSeconds * 1000;
        if (practiceTick === null) {
            practiceTick = window.setInterval(() => {
                renderPracticeCountdown();
                if (!practiceUnsaved() || isInteracting) return;
                if (Date.now() >= practiceDeadline) savePractice(true);
            }, 1000);
        }
        renderPracticeCountdown();
    }

    async function savePractice(auto) {
        if (!practicePresses.length || isInteracting) return;
        const presses = practicePresses.slice();
        isInteracting = true;
        try {
            const response = await fetch("/practice/save", {
                method: "POST",
                headers: {"Content-Type": "application/json"},
                body: JSON.stringify({presses, auto: Boolean(auto)})
            });
            const result = await response.json().catch(() => ({}));
            if (!response.ok) {
                if (response.status === 428) window.location.assign("/identify");
                else window.alert(result.error || "The practised sequence could not be recorded.");
                return;
            }
            // Recorded: the copy and the record are the same thing again, and
            // practice stays on with nothing waiting.
            practicePresses = [];
            practiceMemory = null;
            practiceRecorded = result.state || vacuumState;
            vacuumState = {...practiceRecorded};
            stopPracticeTimer();
            applyState(vacuumState, undefined, result.prediction);
            renderPractice();
        } catch (error) {
            console.error("The practised sequence could not be recorded", error);
        } finally {
            isInteracting = false;
        }
    }

    async function undoPractice() {
        if (!practicePresses.length) return;
        practicePresses.pop();
        vacuumState = {...practiceRecorded};
        practicePresses.forEach((press) => { vacuumState[press.id] = press.status; });
        practiceMemory = null;
        await refreshPractice();
        if (practicePresses.length) startPracticeTimer();
        else stopPracticeTimer();
        renderPractice();
    }

    /* Discard puts the recorded state back and cancels the timer with it: a
     * sequence somebody threw away must not come back a minute later. */
    async function discardPractice() {
        practicePresses = [];
        practiceMemory = null;
        vacuumState = {...practiceRecorded};
        stopPracticeTimer();
        await refreshPractice();
        renderPractice();
    }

    async function setPractice(on) {
        if (!on && practiceUnsaved()) {
            const count = practicePresses.length;
            const question = `${count} practised press${count === 1 ? " is" : "es are"} not recorded yet.`
                + " Leave practice and discard them?";
            if (!window.confirm(question)) {
                renderPractice();
                return;
            }
        }
        practiceOn = on;
        practicePresses = [];
        practiceMemory = null;
        stopPracticeTimer();
        if (on) {
            practiceRecorded = {...vacuumState};
            renderPractice();
            await refreshPractice();
        } else {
            vacuumState = {...(practiceRecorded || vacuumState)};
            practiceRecorded = null;
            renderPractice();
            await fetchAndUpdateStates();
        }
    }

    async function setupPractice() {
        const toggle = document.getElementById("practice-toggle");
        if (!toggle) return;
        try {
            const response = await fetch("/practice/settings");
            if (response.ok) {
                const settings = await response.json();
                if (Number(settings.autosave_seconds) > 0) {
                    practiceAutosaveSeconds = Number(settings.autosave_seconds);
                }
            }
        } catch (error) { /* the default interval still counts down */ }
        toggle.addEventListener("change", () => setPractice(toggle.checked));
        document.getElementById("practice-save")?.addEventListener("click", () => savePractice(false));
        document.getElementById("practice-undo")?.addEventListener("click", undoPractice);
        document.getElementById("practice-discard")?.addEventListener("click", discardPractice);
        // Leaving with unsaved practice asks first, in the browser's own words.
        window.addEventListener("beforeunload", (event) => {
            if (!practiceUnsaved()) return;
            event.preventDefault();
            event.returnValue = "";
        });
        renderPractice();
    }

    async function fetchAndUpdateStates() {
        // A practised copy is not refreshed from the record: the five-second
        // poll would paint the recorded state over the rehearsal mid-press.
        if (practiceOn) return;
        if (isInteracting) return;
        try {
            const response = await fetch("/elements-state");
            vacuumState = await response.json();
            applyState(vacuumState);
        } catch (error) {
            console.error("Diagram state refresh failed", error);
        }
    }

    function setupGuideControls() {
        const choices = document.getElementById("operation-choices");
        if (!choices) return;
        choices.replaceChildren(...guideConfig.guides.map((guide) => {
            const button = document.createElement("button");
            button.type = "button";
            button.className = "operation-choice";
            button.dataset.guideId = guide.id;
            button.setAttribute("aria-pressed", "false");
            button.textContent = guide.label;
            button.addEventListener("click", () => {
                activeGuide = guide;
                renderGuide();
                window.pihtiRails?.openDrawer("guide-steps");
            });
            return button;
        }));
        document.getElementById("clear-guide")?.addEventListener("click", () => {
            activeGuide = null;
            renderGuide();
        });
    }

    /* The configurations the card offers, in the order queezz named them, read
     * from the map rather than typed here twice: "1. membrane installed. 2. pipe
     * open... 3. blank, bellows not connected. 4. boron deposition sample holder
     * installed" (owner decision 2026-09-08). The one-line meaning beside each
     * lives in the map too, and the card's More prints them. */
    function lineModeConfig() {
        return (plumbing && plumbing.line_configuration) || {};
    }

    function lineModeLabel(mode) {
        const modes = lineModeConfig().modes || {};
        return (modes[mode] || modes.unknown || {}).label || "Unknown";
    }

    function buildLineModeChoices() {
        const holder = document.getElementById("line-mode-choices");
        const detail = document.getElementById("line-mode-detail");
        const more = document.getElementById("line-mode-more");
        const config = lineModeConfig();
        const order = config.order || [];
        const modes = config.modes || {};
        if (holder) {
            holder.replaceChildren(...order.map((mode) => {
                const button = document.createElement("button");
                button.type = "button";
                button.dataset.lineMode = mode;
                button.textContent = (modes[mode] || {}).label || mode;
                return button;
            }));
        }
        if (detail) {
            detail.replaceChildren(...order.map((mode) => {
                const line = document.createElement("p");
                line.className = "muted";
                line.textContent = `${(modes[mode] || {}).label || mode}: ${(modes[mode] || {}).meaning || ""}.`;
                return line;
            }));
        }
        if (more && !more.dataset.wired) {
            more.dataset.wired = "1";
            more.addEventListener("click", () => {
                const open = more.getAttribute("aria-expanded") === "true";
                more.setAttribute("aria-expanded", String(!open));
                more.textContent = open ? "More" : "Less";
                if (detail) detail.hidden = open;
            });
        }
    }

    function renderLineMode(context) {
        const status = document.getElementById("line-mode-status");
        const note = document.getElementById("line-mode-note");
        if (status) status.textContent = lineModeLabel(context.line_mode);
        document.querySelectorAll("[data-line-mode]").forEach((button) => {
            const selected = button.dataset.lineMode === context.line_mode;
            button.setAttribute("aria-pressed", String(selected));
            button.disabled = !operatorIdentified;
        });
        if (note) {
            note.textContent = operatorIdentified
                ? context.updated_by ? `Last marked by ${context.updated_by}.` : "Choose the current physical configuration."
                : "Choose an operator to change this annotation.";
        }
    }

    function setupLineModes(initialContext) {
        let context = initialContext;
        buildLineModeChoices();
        renderLineMode(context);
        document.querySelectorAll("[data-line-mode]").forEach((button) => {
            button.addEventListener("click", async () => {
                const response = await fetch("/operation-context", {
                    method: "POST",
                    headers: {"Content-Type": "application/json"},
                    body: JSON.stringify({line_mode: button.dataset.lineMode})
                });
                if (response.status === 428) {
                    window.location.assign("/identify");
                    return;
                }
                const result = await response.json().catch(() => ({}));
                if (!response.ok) {
                    const note = document.getElementById("line-mode-note");
                    if (note) note.textContent = result.error || "The annotation could not be changed.";
                    return;
                }
                context = result;
                renderLineMode(context);
                // The drawing changes with the configuration, now rather than
                // whenever the five-second refresh next comes round. queezz,
                // 2026-09-08: "pipe open doesn't change its state" — measured
                // on 0.13.0, the membrane symbol was still drawn open six
                // seconds after the press, and longer in a background tab where
                // the browser throttles the timer. Since 0.15.0 the answer to
                // the press carries the new prediction with it, so this costs
                // one round trip rather than three: "VERY slow. And no reason
                // for it to be slow."
                if (result.prediction) {
                    if (result.state) vacuumState = result.state;
                    applyState(vacuumState, undefined, result.prediction);
                } else {
                    await fetchAndUpdateStates();
                }
            });
        });
    }

    async function loadDiagram() {
        const container = document.getElementById("diagram-container");
        if (!container) return;
        // Stamped with the release so the browser may keep it: the drawing is
        // 185 kB and every tab that shows it used to re-fetch it.
        const stamp = document.body.dataset.assetVersion || "";
        const svgResponse = await fetch(`/static/diagram.svg?v=${encodeURIComponent(stamp)}`);
        container.innerHTML = await svgResponse.text();
        document.querySelectorAll(".non-clickable").forEach((element) => { element.style.pointerEvents = "none"; });
        const configResponse = await fetch("/elements-config");
        elementsConfig = await configResponse.json();
        nameById = Object.fromEntries(
            elementsConfig.filter((item) => item.label).map((item) => [item.id, item.label])
        );
        plumbing = await fetch("/plumbing").then((response) => response.ok ? response.json() : null).catch(() => null);
        renderVacuumLegend();
        setupBandToggle();
        setupRailCards();
        // A rail that is measured once at load is measured for one window size.
        // The reader's window is the one that matters, so the fit is re-run
        // whenever it changes shape.
        window.addEventListener("resize", scheduleFit);
        if (window.historyMode) {
            container.style.pointerEvents = "none";
            renderConnections({});
            await fetchAndUpdateStates();
            attachElementListeners();
            document.dispatchEvent(new CustomEvent("pihti:diagram-ready"));
            return;
        }
        const [guidesResponse, userResponse, contextResponse] = await Promise.all([
            fetch("/operation-guides"), fetch("/get_current_user"), fetch("/operation-context")
        ]);
        guideConfig = await guidesResponse.json();
        guideFacts = guideConfig.facts || {};
        const user = await userResponse.json();
        operatorIdentified = user.is_identified;
        const context = await contextResponse.json();
        setupGuideControls();
        setupLineModes(context);
        await setupPractice();
        await fetchAndUpdateStates();
        attachElementListeners();
        document.dispatchEvent(new CustomEvent("pihti:diagram-ready"));
        window.setInterval(fetchAndUpdateStates, 5000);
    }

    window.applyState = applyState;
    window.pihtiElementName = elementName;
    loadDiagram().catch((error) => console.error("Diagram could not be loaded", error));
}());
