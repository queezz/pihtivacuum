/* Plot: the left rail finds a recording by calendar day (a month grid, then
 * the day's few files), the plot is the content, the right rail states which
 * file and channels the plot shows. Thirteen hundred files never render as
 * one list: a rail card shows a day, not the archive. */
(function () {
    "use strict";

    const status = document.getElementById("plot-status");
    const frame = document.getElementById("plot-frame");
    const download = document.getElementById("downloadBtn");
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
            return storeMonth(key, []);
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
        document.getElementById("plot-generated").textContent = meta.generated_at || "—";
        document.getElementById("plot-linear").textContent = (meta.linear || []).join(", ") || "—";
        document.getElementById("plot-log").textContent = (meta.log || []).join(", ") || "—";
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
        const entries = selectedDate ? daysOf(monthKey)[selectedDate] || [] : [];
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
                selectFile(entry.name);
                fetchPlot(entry.name);
                window.pihtiRails?.closeDrawers();
            });
            return button;
        }));
    }

    function renderDownload() {
        if (!download) return;
        download.setAttribute("aria-disabled", String(!selectedFile));
        download.href = selectedFile ? `/download_controlunit_csv?file=${encodeURIComponent(selectedFile)}` : "#";
    }

    function writeAddress() {
        window.history.replaceState(null, "", selectedFile ? `/plasmaplots?file=${encodeURIComponent(selectedFile)}` : "/plasmaplots");
    }

    function redraw() {
        renderCalendar();
        renderDayList();
        renderDownload();
        writeAddress();
    }

    function selectDate(dateStr) {
        selectedDate = dateStr;
        if (dateStr !== "undated") currentMonth = calendar.monthOf(dateStr);
        if (selectedFile && dayOfFile(selectedFile) !== dateStr) selectedFile = null;
        redraw();
    }

    /* Selecting a file may be the first sight of a month the page never
     * carried — a deep link into last winter, say — so the month is fetched
     * before the day is shown. */
    async function selectFile(file) {
        const day = dayOfFile(file);
        const month = monthOfFile(file);
        if (month !== monthKey) {
            await loadMonth(month);
            monthKey = month;
        }
        selectedFile = file;
        selectedDate = day;
        if (day !== "undated") currentMonth = calendar.monthOf(day);
        redraw();
    }

    async function fetchPlot(file) {
        // The previous plot stays on screen while this one is drawn, so the
        // page never empties out under the reader.
        showStatus(`Plotting ${file}…`);
        try {
            const response = await fetch("/plot", {method: "POST", body: new URLSearchParams({file})});
            const payload = await readAnswer(response);
            if (!response.ok) throw new Error(payload.error || `Request failed (${response.status})`);
            showPlot(payload.generated);
            showStatus("");
            renderContext(payload);
        } catch (error) {
            console.error("The plot could not be generated", error);
            showEmpty(error.message || "This recording could not be plotted.");
        }
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
            showPlot(payload.generated);
            showStatus("");
            renderContext(payload);
            if (payload.file && dayOfFile(payload.file)) selectFile(payload.file);
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
        selectFile(latestFile);
        fetchPlot(latestFile);
    });
    download?.addEventListener("click", (event) => {
        if (!selectedFile) event.preventDefault();
    });

    // Read the address before the first render writes it back.
    const requested = new URLSearchParams(window.location.search).get("file");
    (async function start() {
        if (monthKey) {
            storeMonth(monthKey, archive.days);
            currentMonth = calendar.monthOf(`${monthKey}-01`);
            const newest = Object.keys(daysOf(monthKey)).sort().reverse()[0];
            if (newest) selectDate(newest);
        }
        updateMonthSteps();
        if (requested) {
            await selectFile(requested);
            fetchPlot(requested);
        } else {
            fetchLastPlot();
        }
    }());
}());
