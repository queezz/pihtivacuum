/* Plot: the left rail finds a recording by calendar day (a month grid, then
 * the day's few files), the plot is the content, the right rail states which
 * file and channels the plot shows. Thirteen hundred files never render as
 * one list: a rail card shows a day, not the archive. */
(function () {
    "use strict";

    const status = document.getElementById("plot-status");
    const frame = document.getElementById("plot-frame");
    const download = document.getElementById("downloadBtn");
    const adcDownload = document.getElementById("download-adc");
    let workspace = null;
    let workspaceSignature = "";
    const comparison = new Set();
    let plotScroll = 0;
    let comparing = false;
    let selectionTicket = 0;
    const calendar = window.pihtiCalendar;

    /* The archive is read one month at a time. Thirteen hundred recordings
     * used to travel in the page — a hundred kilobytes on every visit, and
     * uncacheable, because the newest day changes. The page now carries only
     * the newest month; going back asks the server, and a month that has
     * passed answers 304 from then on, because history does not change
     * (queezz, 2026-09-07). */
    const archive = readArchive();
    const months = archive.months || [];          // newest first, may end in "undated"
    const loaded = new Map();                     // month -> {"YYYY-MM-DD": [{name, time}]}
    const latestFile = archive.latest || "";
    let monthKey = archive.month || "";
    let selectedDate = null;
    let selectedFile = null;
    let currentMonth = null;                      // Date, first of the drawn month

    function readArchive() {
        const raw = document.getElementById("archive-data");
        if (!raw) return {};
        try {
            return JSON.parse(raw.textContent);
        } catch (error) {
            console.error("The recording index could not be read", error);
            return {};
        }
    }

    function storeMonth(key, groups) {
        const byDate = {};
        for (const group of groups || []) byDate[group.date] = group.files;
        loaded.set(key, byDate);
        return byDate;
    }

    function daysOf(key) {
        return loaded.get(key) || {};
    }

    /* A refusal is not always JSON: a missing recording answers with Flask's
     * own 404 page, and reading that as JSON used to put a parser error in
     * front of the reader instead of a sentence. */
    async function readAnswer(response) {
        try {
            return await response.json();
        } catch (error) {
            return {error: response.status === 404
                ? "That recording is not on this machine."
                : `The server answered ${response.status}.`};
        }
    }

    async function loadMonth(key) {
        if (!key || loaded.has(key)) return daysOf(key);
        const note = document.getElementById("calendar-loading");
        if (note) note.hidden = false;
        try {
            const response = await fetch(`/plot/recordings?month=${encodeURIComponent(key)}`);
            const payload = await readAnswer(response);
            if (!response.ok) throw new Error(payload.error || `Request failed (${response.status})`);
            return storeMonth(key, payload.days);
        } catch (error) {
            console.error("That month could not be read", error);
            showStatus("That month could not be read. Try selecting it again.");
            throw error;
        } finally {
            if (note) note.hidden = true;
        }
    }

    /* A recording says its own day in its name, so nothing has to be looked up
     * in an index the page no longer holds. */
    function dayOfFile(file) {
        const match = /^cu_(\d{4})(\d{2})(\d{2})_/.exec(file || "");
        return match ? `${match[1]}-${match[2]}-${match[3]}` : "undated";
    }

    function monthOfFile(file) {
        const day = dayOfFile(file);
        return day === "undated" ? "undated" : day.slice(0, 7);
    }

    /* Status is a line above the plot, never a veil over the page. A modal
     * overlay used to cover the tab bar and both rails while the last plot
     * loaded, which is what made arriving here feel like waiting for a door to
     * open (queezz, 2026-09-07: "Plot tab blocks UI until it loads. Bad."). */
    function showStatus(text) {
        if (!status) return;
        status.textContent = text || "";
        status.hidden = !text;
    }

    function recordedFromName(name) {
        const match = /^cu_(\d{4})(\d{2})(\d{2})_(\d{2})(\d{2})(\d{2})/.exec(name || "");
        return match ? `${match[1]}-${match[2]}-${match[3]} ${match[4]}:${match[5]}:${match[6]}` : "—";
    }

    /* The plot is a document of its own, framed. Plotly's bundle is megabytes;
     * parsed inside this page it froze every control on it, and framed it
     * parses in its own document while the tabs, the calendar and the rails
     * stay live. The stamp only makes the frame reload when the plot changed. */
    function showPlot(stamp) {
        if (!frame) return;
        frame.src = `/plot/last.html?t=${encodeURIComponent(stamp || Date.now())}`;
        frame.hidden = false;
    }

    function showEmpty(text) {
        if (frame) { frame.hidden = true; frame.removeAttribute("src"); }
        showStatus(text);
    }

    function renderContext(meta) {
        const note = document.getElementById("plot-empty-note");
        const facts = document.getElementById("plot-facts");
        if (!note || !facts) return;
        const known = Boolean(meta && meta.file);
        note.hidden = known;
        facts.hidden = !known;
        if (!known) {
            note.textContent = meta ? "The last plot was made before its file was recorded." : "No plot yet. Choose a day and a recording on the left.";
            return;
        }
        document.getElementById("plot-file").textContent = meta.file;
        document.getElementById("plot-recorded").textContent = recordedFromName(meta.file);
        document.getElementById("plot-time-basis").textContent = meta.time_label || "Recorder local time";
        const sources = document.getElementById("plot-source-list");
        sources.replaceChildren(...(meta.sources || []).map((source) => {
            const group = document.createElement("details");
            const title = document.createElement("summary");
            title.textContent = `${source.name} · ${source.rows} rows · ${source.columns.length} columns`;
            const columns = document.createElement("p");
            columns.className = "muted";
            columns.textContent = source.columns.join(", ");
            group.append(title, columns);
            return group;
        }));
        const notes = document.getElementById("plot-notes");
        document.getElementById("plot-ranges").replaceChildren(...(meta.series || []).filter(s => s.summary).map(s => {
            const p = document.createElement("p"); p.textContent = `${s.label}: ${s.summary}`; return p;
        }));
        notes.replaceChildren(...(meta.notes || []).map((text) => {
            const p = document.createElement("p"); p.textContent = text; return p;
        }));
        renderCompareState();
    }

    function renderCalendar() {
        const grid = document.getElementById("plot-calendar");
        if (!calendar || !currentMonth || !grid) return;
        // Only the month on screen is counted, because only it is loaded.
        const byDate = daysOf(monthKey);
        const counts = Object.fromEntries(
            Object.keys(byDate).filter((date) => date !== "undated").map((date) => [date, byDate[date].length])
        );
        grid.hidden = monthKey === "undated";
        calendar.render({
            grid,
            label: document.getElementById("calendar-month-label"),
            month: currentMonth,
            counts,
            selected: selectedDate,
            noun: "recording",
            onSelect: selectDate,
        });
    }

    function renderDayList() {
        const list = document.getElementById("file-list");
        const empty = document.getElementById("day-files-empty");
        const label = document.getElementById("day-files-label");
        if (!list || !empty) return;
        const query = document.getElementById("plot-file-find")?.value.toLowerCase() || "";
        const entries = (selectedDate ? daysOf(monthKey)[selectedDate] || [] : [])
            .filter((entry) => `${entry.name} ${entry.time}`.toLowerCase().includes(query));
        if (label) label.textContent = selectedDate ? `Files · ${selectedDate}` : "Files";
        empty.hidden = entries.length > 0;
        list.replaceChildren(...entries.map((entry) => {
            const button = document.createElement("button");
            button.type = "button";
            button.dataset.file = entry.name;
            button.title = entry.name;
            button.textContent = entry.time;
            button.setAttribute("aria-pressed", String(entry.name === selectedFile));
            button.addEventListener("click", () => {
                openRecording(entry.name);
                window.pihtiRails?.closeDrawers();
            });
            return button;
        }));
    }

    function renderDownload() {
        if (!download) return;
        download.setAttribute("aria-disabled", String(!selectedFile));
        download.href = selectedFile ? `/plot/export?file=${encodeURIComponent(selectedFile)}` : "#";
        adcDownload.setAttribute("aria-disabled", String(!selectedFile));
        adcDownload.href = selectedFile ? `/download_controlunit_csv?file=${encodeURIComponent(selectedFile)}` : "#";
    }

    function writeAddress() {
        window.history.replaceState(null, "", selectedFile ? `/plasmaplots?file=${encodeURIComponent(selectedFile)}` : "/plasmaplots");
    }

    function redraw() {
        renderCalendar();
        renderDayList();
        renderDownload();

    }

    function selectDate(dateStr) {
        selectedDate = dateStr;
        if (dateStr !== "undated") currentMonth = calendar.monthOf(dateStr);
        redraw();
        updateMonthSteps();
        return true;
    }

    async function openRecording(file) {
        try {
            if (await selectFile(file)) {
                const address = `/plasmaplots?file=${encodeURIComponent(file)}`;
                if (location.pathname + location.search !== address) history.pushState(null, "", address);
                fetchPlot(file);
            }
        } catch (_) { /* loadMonth already explains the failure. */ }
    }

    /* Selecting a file may be the first sight of a month the page never
     * carried — a deep link into last winter, say — so the month is fetched
     * before the day is shown. */
    async function selectFile(file) {
        const ticket = ++selectionTicket;
        const day = dayOfFile(file);
        const month = monthOfFile(file);
        if (month !== monthKey) {
            await loadMonth(month);
            if (ticket !== selectionTicket) return false;
            monthKey = month;
        }
        selectedFile = file;
        selectedDate = day;
        if (day !== "undated") currentMonth = calendar.monthOf(day);
        redraw();
        updateMonthSteps();
        return true;
    }

    async function fetchPlot(file) {
        closeEditor();
        showStatus(`Plotting ${file}…`);
        workspace = null;
        comparison.clear();
        workspaceSignature = "";
        renderPanelControls();
        renderContext({file});
        frame.hidden = false;
        frame.src = `/plot/view?file=${encodeURIComponent(file)}`;
        try { localStorage.setItem("pihti.plot.last-file", file); } catch (_) { /* Optional memory. */ }
    }

    /* Only the few hundred bytes of "what is the last plot" are read here. The
     * plot's own megabytes arrive in the frame, after this page is already
     * usable. */
    async function fetchLastPlot() {
        try {
            const response = await fetch("/plot/meta");
            const payload = await readAnswer(response);
            if (!response.ok) throw new Error(payload.error || `Request failed (${response.status})`);
            if (!payload.has_plot) {
                showEmpty(latestFile ? "No plot yet. Choose a day and a recording on the left." : "No plot available.");
                renderContext(null);
                return;
            }
            if (payload.file) openRecording(payload.file);
            else { showPlot(payload.generated); showStatus(""); renderContext(payload); }
        } catch (error) {
            console.error("The last plot could not be loaded", error);
            showEmpty("The last plot could not be loaded.");
        }
    }

    /* Prev and next step to the next month that actually holds recordings, so
     * going back a year is a few presses rather than twelve through empty
     * grids. Months with nothing in them are not stops on the way. */
    const datedMonths = months.filter((month) => month !== "undated");

    async function stepMonth(delta) {
        const here = datedMonths.indexOf(monthKey);
        // `months` is newest first, so a step back in time is a step forward
        // through the list.
        const next = datedMonths[here === -1 ? 0 : here - delta];
        if (!next) return;
        await loadMonth(next);
        monthKey = next;
        currentMonth = calendar.monthOf(`${next}-01`);
        selectedDate = null;
        renderCalendar();
        renderDayList();
        updateMonthSteps();
    }

    function updateMonthSteps() {
        const here = datedMonths.indexOf(monthKey);
        const prev = document.getElementById("calendar-prev");
        const next = document.getElementById("calendar-next");
        if (prev) prev.disabled = here === -1 || here >= datedMonths.length - 1;
        if (next) next.disabled = here <= 0;
    }

    document.getElementById("calendar-prev")?.addEventListener("click", () => stepMonth(-1));
    document.getElementById("calendar-next")?.addEventListener("click", () => stepMonth(1));
    const undatedButton = document.getElementById("calendar-undated");
    if (undatedButton && months.includes("undated")) {
        undatedButton.hidden = false;
        undatedButton.addEventListener("click", async () => {
            await loadMonth("undated");
            monthKey = "undated";
            selectDate("undated");
        });
    }
    document.getElementById("calendar-latest")?.addEventListener("click", () => {
        if (!latestFile) return;
        openRecording(latestFile);
    });
    download?.addEventListener("click", (event) => {
        if (!selectedFile) event.preventDefault();
    });
    adcDownload?.addEventListener("click", (event) => {
        if (!selectedFile) event.preventDefault();
    });

    function command(action, values = {}) {
        if (workspace) frame.contentWindow.postMessage({type: "pihti-plot-command", action, ...values}, location.origin);
    }

    function renderPanelControls() {
        for (const id of ["plot-reset", "plot-defaults", "plot-image", "plot-curves-export", "plot-drag", "plot-arrange-toggle"]) {
            document.getElementById(id).disabled = !workspace;
        }
        const container = document.getElementById("plot-panels");
        container.replaceChildren(...(workspace?.panels || []).filter((p) => p.active).map((panel) => {
            const row = document.createElement("div"); row.className = "plot-panel-control";
            const label = document.createElement("label"); label.className = "plot-field";
            label.append(document.createTextNode(`${panel.label}${panel.secondaryUnit ? ` · left ${panel.unit}` : ""}`));
            const scale = document.createElement("select");
            scale.setAttribute("aria-label", `${panel.label} scale`);
            for (const [value, name] of [["linear", "Linear"], ["log", "Log"]]) {
                scale.add(new Option(name, value));
            }
            scale.value = panel.scale;
            scale.addEventListener("change", () => command("scale", {panel: panel.id, value: scale.value}));
            label.append(scale); row.append(label);
            if (panel.secondaryUnit) {
                const right = document.createElement("label"); right.className = "plot-field";
                right.append(document.createTextNode(`Right axis · ${panel.secondaryUnit}`));
                const rightScale = document.createElement("select");
                rightScale.setAttribute("aria-label", `${panel.label} right scale`);
                rightScale.add(new Option("Linear", "linear")); rightScale.add(new Option("Log", "log"));
                rightScale.value = panel.secondaryScale || "linear";
                rightScale.addEventListener("change", () => command("scale", {panel: panel.id, axis: "right", value: rightScale.value}));
                right.append(rightScale); row.append(right);
            }
            const order = document.createElement("div"); order.className = "plot-order";
            for (const [direction, name] of [[-1, "Move up"], [1, "Move down"]]) {
                const button = document.createElement("button"); button.type = "button";
                button.textContent = name; button.setAttribute("aria-label", `${panel.label}: ${name}`);
                button.addEventListener("click", () => command("reorder", {panel: panel.id, direction}));
                order.append(button);
            }
            row.append(order); return row;
        }));
        renderCurveControls();
    }

    function renderCurveControls() {
        const query = document.getElementById("plot-curve-find").value.toLowerCase();
        const list = document.getElementById("plot-curve-list");
        list.replaceChildren(...(workspace?.series || []).filter((s) =>
            `${s.label} ${s.unit} ${s.source}`.toLowerCase().includes(query)).map((series) => {
            const row = document.createElement("div"); row.className = "plot-field plot-curve-row";
            const choose = document.createElement("label"); choose.className = "plot-compare-choice";
            const checkbox = document.createElement("input"); checkbox.type = "checkbox";
            checkbox.checked = comparison.has(series.id);
            checkbox.setAttribute("aria-label", `Compare ${series.label}`);
            checkbox.addEventListener("change", () => {
                if (checkbox.checked) comparison.add(series.id); else comparison.delete(series.id);
                renderCompareState();
            });
            choose.append(checkbox, document.createTextNode(`${series.label} · ${series.unit}`));
            row.append(choose);
            if (series.meaning) row.title = series.meaning;
            const select = document.createElement("select");
            select.setAttribute("aria-label", `${series.label} chart`);
            select.add(new Option("Hidden", "hidden"));
            for (const panel of workspace.panels.filter((p) => p.unit === series.unit || p.secondaryUnit === series.unit)) {
                select.add(new Option(panel.label, panel.id));
            }
            select.add(new Option("Separate chart", "new"));
            select.value = series.visible ? series.panel : "hidden";
            select.addEventListener("change", () => {
                if (select.value === "hidden") command("visibility", {series: series.id, visible: false});
                else command("move", {series: series.id, panel: select.value});
            });
            row.append(select);
            if (["Bu_c", "Bd_c"].includes(series.column)) {
                const zero = document.createElement("details");
                const title = document.createElement("summary");
                title.textContent = series.zero_applied ? `Zero offset · ${series.zero_offset.toExponential()} ${series.unit}` : "Zero offset";
                const label = document.createElement("label"); label.className = "plot-field";
                label.append(document.createTextNode(`Subtract offset · ${series.unit}`));
                const input = document.createElement("input"); input.type = "text"; input.inputMode = "text";
                input.value = String(series.zero_offset || 0);
                input.setAttribute("aria-label", `${series.label} zero offset`);
                label.append(input);
                const actions = document.createElement("div"); actions.className = "plot-order";
                const apply = document.createElement("button"); apply.type = "button"; apply.textContent = "Apply";
                apply.addEventListener("click", () => {
                    const value = Number(input.value.trim());
                    input.setCustomValidity(input.value.trim() && Number.isFinite(value) ? "" : "Enter a finite number, such as -1e-6.");
                    if (input.reportValidity()) command("zero", {series: series.id, offset: value});
                });
                const reset = document.createElement("button"); reset.type = "button"; reset.textContent = "Reset zero";
                reset.disabled = !series.zero_applied;
                reset.addEventListener("click", () => command("reset-zero", {series: series.id}));
                actions.append(apply, reset);
                const hint = document.createElement("small"); hint.textContent = "Displayed = recorded − offset. Use Linear to see negative values.";
                zero.append(title, label, actions, hint); row.append(zero);
            }
            return row;
        }));
        renderCompareState();
    }

    function renderCompareState() {
        const chosen = (workspace?.series || []).filter((s) => comparison.has(s.id));
        const units = new Set(chosen.map((s) => s.unit));
        document.getElementById("plot-compare").disabled = chosen.length < 2 || units.size > 2;
        document.getElementById("plot-compare-note").textContent = units.size > 2
            ? "Use up to two units per comparison; each gets its own axis."
            : chosen.length ? `${chosen.length} curves · ${[...units].join(" + ")}${units.size === 2 ? " · two axes" : ""}` : "Select curves to compare.";
    }

    window.addEventListener("message", (event) => {
        if (event.origin !== location.origin || event.source !== frame.contentWindow) return;
        const payload = event.data;
        if (!payload || (payload.file && payload.file !== selectedFile)) return;
        if (payload.type === "pihti-plot-error") {
            comparing = false;
            document.getElementById("plot-compare-note").textContent = payload.error;
            showStatus(payload.error || "This recording could not be plotted.");
        } else if (payload.type === "pihti-plot-ready") {
            workspace = payload;
            showStatus("");
            const signature = JSON.stringify([payload.file, payload.panels, payload.series, payload.drag]);
            if (signature !== workspaceSignature) {
                workspaceSignature = signature;
                renderContext(payload);
                renderPanelControls();
                document.getElementById("plot-drag").value = payload.drag || "zoom";
            }
            if (comparing) {
                comparing = false;
                comparison.clear();
                closeEditor(true);
            }
            if (Number.isFinite(payload.height)) frame.style.height = `${Math.max(380, payload.height)}px`;
        }
    });
    frame.addEventListener("load", () => {
        if (frame.src.includes("/plot/view") && !frame.contentDocument?.getElementById("recording-data")) {
            showStatus("That recording is unavailable. Choose another file.");
        }
    });
    window.addEventListener("popstate", () => {
        const file = new URLSearchParams(location.search).get("file");
        if (file) openRecording(file);
        else { selectedFile = null; renderDownload(); showEmpty("Choose a recording."); }
    });
    document.getElementById("plot-drag").addEventListener("change", (event) => command("drag", {value: event.target.value}));
    document.getElementById("plot-reset").addEventListener("click", () => command("reset"));
    document.getElementById("plot-defaults").addEventListener("click", () => command("defaults"));
    document.getElementById("plot-curves-export").addEventListener("click", () => command("export-curves"));
    document.getElementById("plot-image").addEventListener("click", () => command("image"));
    document.getElementById("plot-compare").addEventListener("click", () => {
        comparing = true;
        closeEditor(true);
        showStatus("Arranging curves…");
        command("compare", {series: [...comparison]});
    });
    document.getElementById("plot-file-find")?.addEventListener("input", renderDayList);
    document.getElementById("plot-curve-find").addEventListener("input", renderCurveControls);
    document.getElementById("plot-arrange-toggle").addEventListener("click", (event) => {
        const panel = document.getElementById("plot-arrange");
        if (!panel.hidden) { closeEditor(); return; }
        plotScroll = window.scrollY;
        panel.hidden = false;
        document.getElementById("plotArea").inert = true;
        document.querySelector(".page-main").classList.add("plot-editing");
        event.target.setAttribute("aria-expanded", "true");
        window.pihtiRails?.closeDrawers();
        window.scrollTo(0, 0);
        document.getElementById("plot-curve-find").focus({preventScroll: true});
    });
    function closeEditor(toTop = false) {
        const panel = document.getElementById("plot-arrange");
        if (panel.hidden) return;
        panel.hidden = true;
        document.getElementById("plotArea").inert = false;
        document.querySelector(".page-main").classList.remove("plot-editing");
        document.getElementById("plot-arrange-toggle").setAttribute("aria-expanded", "false");
        window.scrollTo(0, toTop ? 0 : plotScroll);
    }
    document.getElementById("plot-arrange-close").addEventListener("click", () => closeEditor());
    document.addEventListener("keydown", (event) => { if (event.key === "Escape") closeEditor(); });
    document.getElementById("plot-axes-toggle").addEventListener("click", (event) => {
        const panel = document.getElementById("plot-panels"); panel.hidden = !panel.hidden;
        event.target.setAttribute("aria-expanded", String(!panel.hidden));
    });

    // Read the address before the first render writes it back.
    let remembered = "";
    try { remembered = localStorage.getItem("pihti.plot.last-file") || ""; } catch (_) { /* Optional memory. */ }
    const requested = new URLSearchParams(window.location.search).get("file") || remembered;
    (async function start() {
        renderPanelControls();
        if (monthKey) {
            storeMonth(monthKey, archive.days);
            currentMonth = calendar.monthOf(`${monthKey}-01`);
            const newest = Object.keys(daysOf(monthKey)).sort().reverse()[0];
            if (newest) selectDate(newest);
        }
        updateMonthSteps();
        if (requested) {
            openRecording(requested);
        } else {
            fetchLastPlot();
        }
    }());
}());
