(function () {
    "use strict";

    const SVG_NS = "http://www.w3.org/2000/svg";
    let elementsConfig = [];
    let guideConfig = {guides: []};
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
    let bandOn = true;

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

    async function toggleElementStatus(element, config) {
        if (isInteracting) return;
        const currentFill = rgbToHex(element.style.fill || window.getComputedStyle(element).fill);
        const newStatus = currentFill === config.colors.active ? "inactive" : "active";
        if (config.confirmToggle && !window.confirm(`Mark ${displayName(element.id)} ${newStatus}?`)) return;
        isInteracting = true;
        element.style.fill = newStatus === "active" ? config.colors.active : config.colors.inactive;
        try {
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
            applyState(vacuumState);
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
        elementsConfig.forEach(({id}) => {
            const element = document.getElementById(id);
            if (!element) return;
            element.style.cursor = operatorIdentified ? "pointer" : "not-allowed";
            element.addEventListener("mouseenter", (event) => showTooltip(tooltip, event, displayName(id)));
            element.addEventListener("mouseleave", () => { tooltip.style.display = "none"; });
        });
        container.addEventListener("click", (event) => {
            let target = event.target;
            while (target && target !== container && !configById[target.id]) target = target.parentElement;
            if (!target || target === container || !configById[target.id]) return;
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

    function guideStepSatisfied(step) {
        const targets = stepTargets(step);
        return !step.manual && targets.length > 0
            && targets.every((target) => normalizedStatus(vacuumState[target.id]) === step.desiredStatus);
    }

    function spotlightStep(index, on) {
        document.querySelectorAll(`#operation-guide-overlay .operation-marker[data-step="${index}"]`)
            .forEach((marker) => marker.classList.toggle("spot", on));
    }

    function rootPointForElement(svg, element, offset) {
        const rect = element.getBoundingClientRect();
        const point = svg.createSVGPoint();
        point.x = rect.left + rect.width / 2;
        point.y = rect.top + rect.height / 2;
        const rootPoint = point.matrixTransform(svg.getScreenCTM().inverse());
        rootPoint.x += (offset || [0, 0])[0];
        rootPoint.y += (offset || [0, 0])[1];
        return rootPoint;
    }

    function renderGuideMarkers(stepStates) {
        const svg = document.querySelector("#diagram-container svg");
        if (!svg) return;
        svg.querySelector("#operation-guide-overlay")?.remove();
        if (!activeGuide) return;
        const overlay = document.createElementNS(SVG_NS, "g");
        overlay.id = "operation-guide-overlay";
        overlay.setAttribute("aria-hidden", "true");
        activeGuide.steps.forEach((step, index) => {
            stepTargets(step).forEach((stepTarget) => {
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
            return;
        }
        title.textContent = activeGuide.label;
        summary.textContent = activeGuide.summary;
        clear.hidden = false;
        const satisfied = activeGuide.steps.map(guideStepSatisfied);
        const currentIndex = satisfied.findIndex((value) => !value);
        const stepStates = satisfied.map((done, index) => done ? "complete" : index === currentIndex ? "current" : "pending");
        list.replaceChildren(...activeGuide.steps.map((step, index) => {
            const item = document.createElement("li");
            item.className = stepStates[index];
            item.tabIndex = 0;
            const label = document.createElement("span");
            label.textContent = step.action;
            const state = document.createElement("small");
            const names = stepTargets(step).map((target) => displayName(target.id)).join(", ");
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
        list.replaceChildren(...states.map((state) => {
            const item = document.createElement("li");
            const swatch = document.createElement("span");
            swatch.className = "vacuum-swatch";
            const line = document.createElement("i");
            line.style.background = state.color;
            swatch.appendChild(line);
            const label = document.createElement("span");
            label.textContent = state.label;
            item.append(swatch, label);
            return item;
        }));
        if (detail) {
            const lines = states.map((state) => {
                const line = document.createElement("p");
                line.className = "muted";
                line.textContent = `${state.label}: ${state.meaning}.`;
                return line;
            });
            const vessels = document.createElement("p");
            vessels.className = "muted";
            vessels.textContent =
                "The two vessels, and the manifold tees and cross, are filled with the same colour.";
            lines.push(vessels);
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
    function paintPrediction(prediction) {
        lastPrediction = prediction;
        Object.entries(prediction.elements || {}).forEach(([id, item]) => {
            const element = document.getElementById(id);
            if (!element) return;
            if (item.fill) {
                element.style.fill = item.fill;
                return;
            }
            const authored = widthOf(element);
            element.style.stroke = item.stroke;
            if (!authored) return;
            element.style.strokeWidth = String(bandOn && item.band ? authored * item.band : authored);
        });
        renderConnections(prediction.connections || {});
    }

    /* The band is a reading aid, not a claim, so it has a switch and the switch
     * lives with the key that explains the colours. The choice is this reader's
     * own, so it stays in this browser. */
    function setupBandToggle() {
        const toggle = document.getElementById("pipe-band");
        if (!toggle) return;
        let stored = null;
        try { stored = window.localStorage.getItem("pihti.pipeBand"); } catch (error) { stored = null; }
        bandOn = stored !== "off";
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

    /* What the prediction finds each vessel joined to, in words. queezz asked
     * the question in this order — "if upstream and downstream are connected to
     * a) each other b) gas c) vent air" — so the sentence answers it in that
     * order, then names the pumps. It is the same prediction the colours come
     * from, and the card says once that all of it is predicted, not measured. */
    function connectionSentence(item) {
        const clauses = [];
        if ((item.joined || []).length) {
            clauses.push(`Open to the ${joinWords(item.joined.map(
                (name) => inSentence(plumbing?.volumes?.[name]?.label || name)
            ))}.`);
        }
        if ((item.gas || []).length) {
            const gases = joinWords(item.gas.map((source) => source.gas));
            clauses.push(`${gases.charAt(0).toUpperCase()}${gases.slice(1)} ${item.gas.length > 1 ? "are" : "is"} open into it.`);
        }
        if ((item.air || []).length) {
            clauses.push(`Vent air through the ${joinWords(item.air.map(
                (valve) => inSentence(displayName(valve.id))
            ))}.`);
        }
        if ((item.pumps || []).length) {
            clauses.push(`Pumped by the ${joinWords(item.pumps.map(
                (pump) => inSentence(displayName(pump.id))
            ))}.`);
        }
        if (!clauses.length) clauses.push("Nothing open to it.");
        return clauses.join(" ");
    }

    function renderConnections(connections) {
        const list = document.getElementById("vacuum-connections");
        if (!list) return;
        // History carries no prediction until a moment is chosen, and an empty
        // list under a heading reads as "nothing is connected" rather than as
        // "nothing has been asked yet". Say which it is.
        if (!Object.keys(connections).length) {
            const empty = document.createElement("li");
            empty.className = "muted";
            empty.textContent = window.historyMode
                ? "Choose a moment in the timeline to read what each vessel was joined to."
                : "Not read yet.";
            list.replaceChildren(empty);
            return;
        }
        const states = Object.fromEntries((plumbing?.states || []).map((state) => [state.id, state]));
        list.replaceChildren(...Object.values(connections).map((item) => {
            const row = document.createElement("li");
            const swatch = document.createElement("span");
            swatch.className = "vacuum-swatch";
            const line = document.createElement("i");
            line.style.background = states[item.state]?.color || "#000000";
            swatch.appendChild(line);
            const text = document.createElement("span");
            const name = document.createElement("b");
            name.textContent = `${item.label} — ${(states[item.state]?.label || item.state).toLowerCase()}.`;
            text.append(name, document.createTextNode(` ${connectionSentence(item)}`));
            row.append(swatch, text);
            return row;
        }));
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

    function applyState(state, moment) {
        if (!elementsConfig.length) return;
        elementsConfig.forEach((element) => {
            const diagramElement = document.getElementById(element.id);
            if (!diagramElement) return;
            const status = normalizedStatus(state[element.id]);
            diagramElement.style.fill = element.colors[status];
        });
        renderGuide();
        refreshPrediction(moment);
    }

    async function fetchAndUpdateStates() {
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

    function renderLineMode(context) {
        const labels = {unknown: "Unknown", membrane: "Membrane installed", open: "Pipe open", boron: "Boron deposition"};
        const status = document.getElementById("line-mode-status");
        const note = document.getElementById("line-mode-note");
        if (status) status.textContent = labels[context.line_mode] || labels.unknown;
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
        const user = await userResponse.json();
        operatorIdentified = user.is_identified;
        const context = await contextResponse.json();
        setupGuideControls();
        setupLineModes(context);
        await fetchAndUpdateStates();
        attachElementListeners();
        document.dispatchEvent(new CustomEvent("pihti:diagram-ready"));
        window.setInterval(fetchAndUpdateStates, 5000);
    }

    window.applyState = applyState;
    window.pihtiElementName = elementName;
    loadDiagram().catch((error) => console.error("Diagram could not be loaded", error));
}());
