/* History: the calendar picks a day, the timeline picks a moment, the diagram
 * in the main column replays the operator-entered state at that moment.
 * The address bar carries the selection (?day=… or ?at=…) so a moment can be
 * linked to and survives reload. */
/* Presentation only: keep the original event indices and recorded states. */
function pihtiGroupHistoryEvents(rows, gapSeconds = 60) {
    const groups = [];
    const isSequence = (event) => (event.changes || []).length > 1 || (event.note || "").startsWith("practice sequence");
    for (const row of rows) {
        const group = groups[groups.length - 1];
        const previous = group?.[group.length - 1];
        const gap = previous ? (Date.parse(row.event.ts.replace(" ", "T")) - Date.parse(previous.event.ts.replace(" ", "T"))) / 1000 : NaN;
        if (previous && row.event.user && row.event.user === previous.event.user
            && row.event.ts.slice(0, 10) === previous.event.ts.slice(0, 10)
            && gap >= 0 && gap <= gapSeconds
            && !isSequence(row.event) && !isSequence(previous.event)) group.push(row);
        else groups.push([row]);
    }
    return groups;
}

(function () {
    "use strict";

    let events = [];
    const expandedGroups = new Set();
    let currentState = {};
    let dailyCounts = {};
    let selectedIdx = null;
    let selectedDate = null;
    let unavailableMoment = null;
    let currentMonth = null;
    let pendingState = null;
    let diagramReady = false;
    let loadFailed = false;
    const SELECTION_KEY = "pihti-history-moment";
    /* Component names arrive with the diagram's own element configuration,
     * which diagram.js fetches. Until it reports ready, nothing here can tell
     * a named component from one the diagram no longer carries, so the rows
     * print the recorded name plainly and are drawn again when it does. */
    let namesReady = false;

    const RETIRED_NOTE = "This component is not on the current diagram; its recorded name is shown.";

    const pad = (value) => String(value).padStart(2, "0");
    const dateOf = (ts) => (ts || "").split(" ")[0];
    const timeOf = (ts) => (ts || "").split(" ")[1] || "";
    const isoDate = (date) => `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`;
    const todayStr = () => isoDate(new Date());

    function escapeHtml(value) {
        const div = document.createElement("div");
        div.textContent = value ?? "";
        return div.innerHTML;
    }

    /* What a reader is shown for one recorded component: its readable name
     * where the diagram has one, otherwise the recorded name, marked as
     * retired rather than quietly passed off as the equipment's own word. */
    function componentLabel(id) {
        const name = window.pihtiElementName?.(id) || "";
        return {text: name || id, retired: namesReady && !name};
    }

    function monthOf(dateStr) {
        const [year, month] = dateStr.split("-").map(Number);
        return new Date(year, month - 1, 1);
    }

    /* The log holds only changes, so a moment's state is the current state
     * walked backwards: every change after the moment is undone to the value
     * that element had before it. Same reconstruction as the server's
     * /history/state-at, done here so a click costs no round trip. */
    /* An event carries one press ordinarily and a whole practised sequence when
     * it is a practice save (0.19.0), so each one is walked through its own
     * list of changes — forwards to remember what each element was before, and
     * backwards to put it back. An older release's events carry no `changes`
     * at all, and their own id and state stand as the one change they are. */
    function changesOf(event) {
        return Array.isArray(event.changes) && event.changes.length
            ? event.changes
            : [{id: event.id, state: event.state}];
    }

    function stateAtIndex(idx) {
        const state = {};
        for (const [id, value] of Object.entries(currentState)) state[id] = value === "active";
        const lastById = {};
        const previous = events.map((event) => changesOf(event).map((change) => {
            const before = lastById[change.id];
            lastById[change.id] = change.state;
            return before;
        }));
        for (let eventIdx = events.length - 1; eventIdx > idx; eventIdx -= 1) {
            const changes = changesOf(events[eventIdx]);
            for (let changeIdx = changes.length - 1; changeIdx >= 0; changeIdx -= 1) {
                const before = previous[eventIdx][changeIdx];
                state[changes[changeIdx].id] = before === undefined ? false : before;
            }
        }
        return state;
    }

    function indexAtOrBefore(moment) {
        let idx = null;
        events.forEach((event, eventIdx) => {
            if (event.ts <= moment) idx = eventIdx;
        });
        return idx;
    }

    function readAddress() {
        const params = new URLSearchParams(window.location.search);
        const at = (params.get("at") || "").replace("T", " ").trim();
        const day = (params.get("day") || "").trim();
        if (at) {
            const idx = indexAtOrBefore(at);
            if (idx !== null) return {idx, date: /^\d{4}-\d{2}-\d{2}$/.test(day) ? day : dateOf(events[idx].ts)};
            if (/^\d{4}-\d{2}-\d{2}/.test(at)) return {idx: null, date: at.slice(0, 10), cutoff: at};
        }
        if (/^\d{4}-\d{2}-\d{2}$/.test(day)) return {idx: null, date: day};
        return null;
    }

    function writeAddress() {
        const params = new URLSearchParams();
        if (selectedIdx !== null) {
            params.set("at", events[selectedIdx].ts);
            if (selectedDate !== dateOf(events[selectedIdx].ts)) params.set("day", selectedDate);
            try { localStorage.setItem(SELECTION_KEY, events[selectedIdx].ts); } catch (_) { /* Storage is optional. */ }
        }
        else if (unavailableMoment) params.set("at", unavailableMoment);
        else if (selectedDate) params.set("day", selectedDate);
        const query = params.toString();
        window.history.replaceState(null, "", query ? `/history?${query}` : "/history");
    }

    function renderCalendar() {
        window.pihtiCalendar?.render({
            grid: document.getElementById("calendar-grid"),
            label: document.getElementById("calendar-month-label"),
            month: currentMonth,
            counts: dailyCounts,
            selected: selectedDate,
            noun: "change",
            onSelect: selectDate,
        });
    }

    function renderTimeline() {
        const list = document.getElementById("history-events");
        const empty = document.getElementById("history-no-events");
        const label = document.getElementById("timeline-label");
        if (!list || !empty) return;
        const rows = events
            .map((event, idx) => ({event, idx}))
            .filter(({event}) => dateOf(event.ts) === selectedDate);
        if (label) label.textContent = selectedDate ? `Timeline · ${selectedDate}` : "Timeline";
        empty.hidden = rows.length > 0;
        function eventRow({event, idx}) {
            const row = document.createElement("button");
            row.type = "button";
            row.className = "tl-row";
            row.dataset.idx = String(idx);
            row.setAttribute("aria-pressed", String(idx === selectedIdx));
            const changes = changesOf(event);
            // A practised procedure is one entry, not one per valve: it is
            // named by how many presses it carries and by every component it
            // touched, in the order they were pressed (queezz, 2026-09-08:
            // "one state jump, less history spamming").
            const grouped = changes.length > 1;
            const component = componentLabel(event.id);
            const names = changes.map((change) => componentLabel(change.id).text).join(", ");
            const what = grouped ? `${changes.length} presses` : component.text;
            row.title = `${event.ts} · ${grouped ? `${event.note || "sequence"}: ${names}` : `${component.text}${component.retired ? ` (${RETIRED_NOTE})` : ""} · ${event.state ? "active" : "inactive"}`} · ${event.user || "unknown operator"}`;
            row.innerHTML = `
                <span class="tl-time">${escapeHtml(timeOf(event.ts))}</span>
                <span class="tl-id${!grouped && component.retired ? " tl-id--retired" : ""}">${escapeHtml(what)}</span>
                <span class="pill tl-pill ${grouped ? "" : (event.state ? "active" : "")}">${grouped ? "saved" : (event.state ? "on" : "off")}</span>`;
            row.addEventListener("click", () => selectEvent(idx));
            return row;
        }
        list.replaceChildren(...pihtiGroupHistoryEvents(rows).reverse().map((group) => {
            if (group.length === 1) return eventRow(group[0]);
            const first = group[0], last = group[group.length - 1];
            const key = String(first.idx);
            const container = document.createElement("div");
            container.className = "tl-group";
            container.dataset.selected = String(group.some(({idx}) => idx === selectedIdx));
            const header = document.createElement("div");
            header.className = "tl-group-header";
            const select = document.createElement("button");
            select.type = "button";
            select.className = "tl-group-select";
            select.setAttribute("aria-pressed", String(last.idx === selectedIdx));
            const range = `${timeOf(first.event.ts)}–${timeOf(last.event.ts)}`;
            select.title = `${group.length} changes by ${last.event.user}. Show the final state at ${last.event.ts}.`;
            select.innerHTML = `<span class="tl-time">${escapeHtml(range)}</span><span class="tl-id">${group.length} changes · ${escapeHtml(last.event.user)}</span><span class="muted">Show final state</span>`;
            select.addEventListener("click", () => selectEvent(last.idx));
            const toggle = document.createElement("button");
            toggle.type = "button";
            toggle.className = "tl-group-toggle";
            const children = document.createElement("div");
            children.id = `history-group-${first.idx}`;
            children.className = "tl-group-events";
            children.hidden = !expandedGroups.has(key);
            children.replaceChildren(...group.slice().reverse().map(eventRow));
            toggle.setAttribute("aria-controls", children.id);
            function reflectExpansion() {
                toggle.setAttribute("aria-expanded", String(!children.hidden));
                toggle.setAttribute("aria-label", `${children.hidden ? "Expand" : "Collapse"} ${group.length} changes at ${range}`);
                toggle.textContent = children.hidden ? "+" : "−";
            }
            reflectExpansion();
            toggle.addEventListener("click", () => {
                children.hidden = !children.hidden;
                if (children.hidden) expandedGroups.delete(key);
                else expandedGroups.add(key);
                reflectExpansion();
            });
            header.append(select, toggle);
            container.append(header, children);
            return container;
        }));
        filterTimeline();
        // Reveal the selection inside the timeline, without scrolling the page.
        const chosen = list.querySelector('.tl-group-select[aria-pressed="true"]')
            || list.querySelector('.tl-row[aria-pressed="true"]');
        const scroller = list.closest(".rail");
        if (chosen && scroller) {
            const target = chosen.getBoundingClientRect(), bounds = scroller.getBoundingClientRect();
            if (target.bottom > bounds.bottom) scroller.scrollTop += target.bottom - bounds.bottom;
            else if (target.top < bounds.top) scroller.scrollTop += target.top - bounds.top;
        }
    }

    function filterTimeline() {
        const query = (document.getElementById("history-find")?.value || "").trim().toLowerCase();
        const list = document.getElementById("history-events");
        if (!list) return;
        const rows = [...list.children];
        rows.forEach((row) => {
            const words = [row.textContent, row.title, ...[...row.querySelectorAll("[title]")].map((item) => item.title)].join(" ");
            row.hidden = Boolean(query) && !words.toLowerCase().includes(query);
        });
        const empty = document.getElementById("history-no-events");
        empty.hidden = rows.some((row) => !row.hidden);
        empty.textContent = loadFailed ? "History could not be loaded."
            : rows.length ? "No matching changes." : "No diagram changes on this day.";
    }

    function renderMoment() {
        const emptyNote = document.getElementById("moment-empty");
        const facts = document.getElementById("moment-facts");
        const image = document.getElementById("moment-image");
        if (!emptyNote || !facts || !image) return;
        const event = selectedIdx === null ? null : events[selectedIdx];
        emptyNote.hidden = Boolean(event);
        facts.hidden = !event;
        image.hidden = !event;
        const status = document.getElementById("history-status");
        const message = loadFailed ? "History could not be loaded. Reload to try again."
            : events.length ? "No recorded state at or before this moment." : "No recorded changes yet.";
        emptyNote.textContent = message;
        if (status) { status.hidden = Boolean(event); status.textContent = message; }
        document.getElementById("diagram-container").hidden = !event;
        document.getElementById("history-state-card").hidden = !event;
        if (!event) return;
        const link = document.getElementById("moment-link");
        link.textContent = event.ts;
        link.href = `/history?at=${encodeURIComponent(event.ts)}`;
        const changes = changesOf(event);
        const grouped = changes.length > 1;
        const component = componentLabel(event.id);
        const element = document.getElementById("moment-element");
        // A practised sequence names every component it touched, in order.
        element.textContent = grouped
            ? changes.map((change) => componentLabel(change.id).text).join(", ")
            : component.text;
        element.classList.toggle("tl-id--retired", !grouped && component.retired);
        if (!grouped && component.retired) element.title = RETIRED_NOTE;
        else element.removeAttribute("title");
        document.getElementById("moment-state").textContent = grouped
            ? (event.note || `${changes.length} presses`)
            : (event.state ? "active" : "inactive");
        document.getElementById("moment-user").textContent = event.user || "—";
        document.getElementById("moment-image-link").href = `/state.svg?at=${encodeURIComponent(event.ts)}`;
        window.pihtiUpdateImageLink?.();
    }

    function applyPendingState() {
        if (!diagramReady || !pendingState || typeof window.applyState !== "function") return;
        const stateForApply = {};
        for (const [id, value] of Object.entries(pendingState)) stateForApply[id] = value ? "active" : "inactive";
        window.applyState(stateForApply, selectedIdx === null ? null : events[selectedIdx].ts);
    }

    function selectDate(dateStr, cutoff = `${dateStr} 23:59:59`) {
        const idx = indexAtOrBefore(cutoff);
        if (idx !== null) { selectEvent(idx, dateStr); return; }
        unavailableMoment = cutoff === `${dateStr} 23:59:59` ? null : cutoff;
        selectedDate = dateStr;
        const find = document.getElementById("history-find");
        if (find) find.value = "";
        currentMonth = monthOf(dateStr);
        selectedIdx = null;
        pendingState = null;
        renderCalendar();
        renderTimeline();
        renderMoment();
        writeAddress();
    }

    function selectEvent(idx, dateStr = dateOf(events[idx]?.ts)) {
        if (idx < 0 || idx >= events.length) return;
        selectedIdx = idx;
        unavailableMoment = null;
        const find = document.getElementById("history-find");
        if (find) find.value = "";
        const group = pihtiGroupHistoryEvents(events.map((event, eventIdx) => ({event, idx: eventIdx})))
            .find((items) => items.some((item) => item.idx === idx));
        if (group && group[group.length - 1].idx !== idx) expandedGroups.add(String(group[0].idx));
        selectedDate = dateStr;
        currentMonth = monthOf(selectedDate);
        renderCalendar();
        renderTimeline();
        renderMoment();
        writeAddress();
        pendingState = stateAtIndex(idx);
        applyPendingState();
    }

    function shiftMonth(delta) {
        currentMonth = new Date(currentMonth.getFullYear(), currentMonth.getMonth() + delta, 1);
        renderCalendar();
    }

    function attachListeners() {
        // Cached drawing resources may finish before History starts listening.
        diagramReady = Boolean(window.pihtiDiagramReady);
        namesReady = diagramReady;
        document.getElementById("history-find")?.addEventListener("input", filterTimeline);
        document.getElementById("calendar-prev")?.addEventListener("click", () => shiftMonth(-1));
        document.getElementById("calendar-next")?.addEventListener("click", () => shiftMonth(1));
        document.getElementById("calendar-latest")?.addEventListener("click", () => {
            if (events.length) selectEvent(events.length - 1);
            else selectDate(todayStr());
        });
        document.addEventListener("pihti:diagram-ready", () => {
            diagramReady = true;
            namesReady = true;
            applyPendingState();
            // The rows were drawn before the names existed; draw them again.
            renderTimeline();
            renderMoment();
        });
    }

    async function load() {
        attachListeners();
        try {
            const [eventsResponse, stateResponse] = await Promise.all([
                fetch("/history/events"), fetch("/elements-state"),
            ]);
            if (!eventsResponse.ok || !stateResponse.ok) throw new Error("History request failed");
            events = await eventsResponse.json();
            currentState = await stateResponse.json();
            if (!Array.isArray(events)) throw new Error("Invalid history response");
        } catch (error) {
            console.error("History events could not be loaded", error);
            events = [];
            currentState = {};
            loadFailed = true;
        }
        dailyCounts = {};
        events.forEach((event) => {
            const date = dateOf(event.ts);
            if (date) dailyCounts[date] = (dailyCounts[date] || 0) + 1;
        });
        const requested = readAddress();
        if (requested?.idx !== null && requested?.idx !== undefined) {
            selectEvent(requested.idx, requested.date);
        } else if (requested?.date) {
            selectDate(requested.date, requested.cutoff);
        } else {
            let remembered;
            try { remembered = localStorage.getItem(SELECTION_KEY); } catch (_) { /* Storage is optional. */ }
            const idx = events.findIndex((event) => event.ts === remembered);
            if (events.length) selectEvent(idx >= 0 ? idx : events.length - 1);
            else selectDate(todayStr());
        }
    }

    if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", load);
    else load();
}());
