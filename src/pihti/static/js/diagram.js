(function () {
    "use strict";

    const SVG_NS = "http://www.w3.org/2000/svg";
    let elementsConfig = [];
    let guideConfig = {guides: []};
    let vacuumState = {};
    let activeGuide = null;
    let isInteracting = false;
    let operatorIdentified = false;

    function normalizedStatus(value) {
        return value === "active" || value === true ? "active" : "inactive";
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
        if (config.confirmToggle && !window.confirm(`Mark ${element.id} ${newStatus}?`)) return;
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
            element.addEventListener("mouseenter", (event) => showTooltip(tooltip, event, id));
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

    function guideStepSatisfied(step) {
        return !step.manual && normalizedStatus(vacuumState[step.targetId]) === step.desiredStatus;
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
            const target = svg.querySelector(`#${CSS.escape(step.targetId)}`);
            if (!target) return;
            const point = rootPointForElement(svg, target, step.markerOffset);
            const marker = document.createElementNS(SVG_NS, "g");
            marker.setAttribute("class", `operation-marker ${stepStates[index]}`);
            marker.setAttribute("transform", `translate(${point.x} ${point.y})`);
            const circle = document.createElementNS(SVG_NS, "circle");
            circle.setAttribute("r", "15");
            const text = document.createElementNS(SVG_NS, "text");
            text.setAttribute("text-anchor", "middle");
            text.setAttribute("dominant-baseline", "central");
            text.textContent = String(index + 1);
            marker.append(circle, text);
            overlay.appendChild(marker);
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
            const label = document.createElement("span");
            label.textContent = step.action;
            const state = document.createElement("small");
            state.textContent = stepStates[index] === "complete" ? "Done in diagram" : stepStates[index] === "current" ? "Next" : "Later";
            item.append(label, state);
            return item;
        }));
        const warning = (activeGuide.alerts || []).find((candidate) =>
            candidate.when.every((condition) => normalizedStatus(vacuumState[condition.id]) === condition.status)
        );
        alert.hidden = !warning;
        alert.textContent = warning ? warning.text : "";
        renderGuideMarkers(stepStates);
    }

    function applyState(state) {
        if (!elementsConfig.length) return;
        elementsConfig.forEach((element) => {
            const diagramElement = document.getElementById(element.id);
            if (!diagramElement) return;
            const status = normalizedStatus(state[element.id]);
            diagramElement.style.fill = element.colors[status];
        });
        renderGuide();
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
        const svgResponse = await fetch("/static/diagram.svg");
        container.innerHTML = await svgResponse.text();
        document.querySelectorAll(".non-clickable").forEach((element) => { element.style.pointerEvents = "none"; });
        const configResponse = await fetch("/elements-config");
        elementsConfig = await configResponse.json();
        if (window.historyMode) {
            container.style.pointerEvents = "none";
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
    loadDiagram().catch((error) => console.error("Diagram could not be loaded", error));
}());
