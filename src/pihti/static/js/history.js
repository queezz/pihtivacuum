/* History: the calendar picks a day, the timeline picks a moment, the diagram
 * in the main column replays the operator-entered state at that moment.
 * The address bar carries the selection (?day=… or ?at=…) so a moment can be
 * linked to and survives reload. */
(function () {
    "use strict";

    let events = [];
    let currentState = {};
    let dailyCounts = {};
    let selectedIdx = null;
    let selectedDate = null;
    let currentMonth = null;
    let pendingState = null;
    let diagramReady = false;

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

    function monthOf(dateStr) {
        const [year, month] = dateStr.split("-").map(Number);
        return new Date(year, month - 1, 1);
    }

    /* The log holds only changes, so a moment's state is the current state
     * walked backwards: every change after the moment is undone to the value
     * that element had before it. Same reconstruction as the server's
     * /history/state-at, done here so a click costs no round trip. */
    function stateAtIndex(idx) {
        const state = {};
        for (const [id, value] of Object.entries(currentState)) state[id] = value === "active";
        const lastById = {};
        const previous = events.map((event) => {
            const before = lastById[event.id];
            lastById[event.id] = event.state;
            return before;
        });
        for (let eventIdx = events.length - 1; eventIdx > idx; eventIdx -= 1) {
            const event = events[eventIdx];
            state[event.id] = previous[eventIdx] === undefined ? false : previous[eventIdx];
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
            if (idx !== null) return {idx, date: dateOf(events[idx].ts)};
            if (/^\d{4}-\d{2}-\d{2}/.test(at)) return {idx: null, date: at.slice(0, 10)};
        }
        if (/^\d{4}-\d{2}-\d{2}$/.test(day)) return {idx: null, date: day};
        return null;
    }

    function writeAddress() {
        const params = new URLSearchParams();
        if (selectedIdx !== null) params.set("at", events[selectedIdx].ts);
        else if (selectedDate) params.set("day", selectedDate);
        const query = params.toString();
        window.history.replaceState(null, "", query ? `/history?${query}` : "/history");
    }

    function renderCalendar() {
        const grid = document.getElementById("calendar-grid");
        const label = document.getElementById("calendar-month-label");
        if (!grid || !label) return;
        const year = currentMonth.getFullYear();
        const month = currentMonth.getMonth();
        label.textContent = currentMonth.toLocaleDateString(undefined, {month: "long", year: "numeric"});
        const maxCount = Math.max(1, ...Object.values(dailyCounts));
        const daysInMonth = new Date(year, month + 1, 0).getDate();
        const today = todayStr();
        const cells = ["Su", "Mo", "Tu", "We", "Th", "Fr", "Sa"].map((name) => {
            const head = document.createElement("div");
            head.className = "cal-head";
            head.textContent = name;
            return head;
        });
        for (let i = 0; i < new Date(year, month, 1).getDay(); i += 1) {
            const empty = document.createElement("div");
            empty.className = "cal-empty";
            cells.push(empty);
        }
        for (let day = 1; day <= daysInMonth; day += 1) {
            const dateStr = `${year}-${pad(month + 1)}-${pad(day)}`;
            const count = dailyCounts[dateStr] || 0;
            const cell = document.createElement("button");
            cell.type = "button";
            cell.className = "cal-day" + (count ? " has-events" : "") + (dateStr === today ? " today" : "");
            cell.dataset.date = dateStr;
            cell.textContent = String(day);
            cell.setAttribute("aria-pressed", String(dateStr === selectedDate));
            cell.setAttribute("aria-label", `${dateStr}, ${count} change${count === 1 ? "" : "s"}`);
            if (count) {
                const intensity = 0.18 + 0.55 * Math.min(1, count / maxCount);
                cell.style.backgroundColor = `rgba(126, 184, 247, ${intensity.toFixed(2)})`;
            }
            cell.addEventListener("click", () => selectDate(dateStr));
            cells.push(cell);
        }
        grid.replaceChildren(...cells);
    }

    function renderTimeline() {
        const list = document.getElementById("history-events");
        const empty = document.getElementById("history-no-events");
        const label = document.getElementById("timeline-label");
        if (!list || !empty) return;
        const rows = events
            .map((event, idx) => ({event, idx}))
            .filter(({event}) => dateOf(event.ts) === selectedDate)
            .reverse();
        if (label) label.textContent = selectedDate ? `Timeline · ${selectedDate}` : "Timeline";
        empty.hidden = rows.length > 0;
        list.replaceChildren(...rows.map(({event, idx}) => {
            const row = document.createElement("button");
            row.type = "button";
            row.className = "tl-row";
            row.dataset.idx = String(idx);
            row.setAttribute("aria-pressed", String(idx === selectedIdx));
            row.title = `${event.ts} · ${event.id} · ${event.state ? "active" : "inactive"} · ${event.user || "unknown operator"}`;
            row.innerHTML = `
                <span class="tl-time">${escapeHtml(timeOf(event.ts))}</span>
                <span class="tl-id">${escapeHtml(event.id)}</span>
                <span class="pill tl-pill ${event.state ? "active" : ""}">${event.state ? "on" : "off"}</span>`;
            row.addEventListener("click", () => selectEvent(idx));
            return row;
        }));
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
        if (!event) return;
        const link = document.getElementById("moment-link");
        link.textContent = event.ts;
        link.href = `/history?at=${encodeURIComponent(event.ts)}`;
        document.getElementById("moment-element").textContent = event.id;
        document.getElementById("moment-state").textContent = event.state ? "active" : "inactive";
        document.getElementById("moment-user").textContent = event.user || "—";
        document.getElementById("moment-image-link").href = `/state.svg?at=${encodeURIComponent(event.ts)}`;
    }

    function applyPendingState() {
        if (!diagramReady || !pendingState || typeof window.applyState !== "function") return;
        const stateForApply = {};
        for (const [id, value] of Object.entries(pendingState)) stateForApply[id] = value ? "active" : "inactive";
        window.applyState(stateForApply);
    }

    function selectDate(dateStr) {
        selectedDate = dateStr;
        currentMonth = monthOf(dateStr);
        if (selectedIdx !== null && dateOf(events[selectedIdx].ts) !== dateStr) selectedIdx = null;
        renderCalendar();
        renderTimeline();
        renderMoment();
        writeAddress();
    }

    function selectEvent(idx) {
        if (idx < 0 || idx >= events.length) return;
        selectedIdx = idx;
        selectedDate = dateOf(events[idx].ts);
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
        document.getElementById("calendar-prev")?.addEventListener("click", () => shiftMonth(-1));
        document.getElementById("calendar-next")?.addEventListener("click", () => shiftMonth(1));
        document.getElementById("calendar-latest")?.addEventListener("click", () => {
            if (events.length) selectEvent(events.length - 1);
            else selectDate(todayStr());
        });
        document.addEventListener("pihti:diagram-ready", () => {
            diagramReady = true;
            applyPendingState();
        });
    }

    async function load() {
        attachListeners();
        try {
            const [eventsResponse, stateResponse] = await Promise.all([
                fetch("/history/events"), fetch("/elements-state"),
            ]);
            events = await eventsResponse.json();
            currentState = await stateResponse.json();
        } catch (error) {
            console.error("History events could not be loaded", error);
            events = [];
            currentState = {};
        }
        dailyCounts = {};
        events.forEach((event) => {
            const date = dateOf(event.ts);
            if (date) dailyCounts[date] = (dailyCounts[date] || 0) + 1;
        });
        const requested = readAddress();
        if (requested?.idx !== null && requested?.idx !== undefined) {
            selectEvent(requested.idx);
        } else if (requested?.date) {
            selectDate(requested.date);
        } else {
            selectedDate = events.length ? dateOf(events[events.length - 1].ts) : todayStr();
            currentMonth = monthOf(selectedDate);
            renderCalendar();
            renderTimeline();
            renderMoment();
        }
    }

    if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", load);
    else load();
}());
