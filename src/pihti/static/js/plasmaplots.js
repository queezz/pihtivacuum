/* Plot: the left rail finds a recording by calendar day (a month grid, then
 * the day's few files), the plot is the content, the right rail states which
 * file and channels the plot shows. Thirteen hundred files never render as
 * one list: a rail card shows a day, not the archive. */
(function () {
    "use strict";

    const plotArea = document.getElementById("plotArea");
    const overlay = document.getElementById("loading-overlay");
    const download = document.getElementById("downloadBtn");
    const calendar = window.pihtiCalendar;

    // {"YYYY-MM-DD": [{name, time}, ...]} newest day first, from the server.
    const days = readDays();
    const dayKeys = Object.keys(days);
    const counts = Object.fromEntries(dayKeys.map((day) => [day, days[day].length]));
    let selectedDate = null;
    let selectedFile = null;
    let currentMonth = null;

    function readDays() {
        const raw = document.getElementById("file-days-data");
        if (!raw) return {};
        try {
            const result = {};
            for (const group of JSON.parse(raw.textContent)) {
                if (/^\d{4}-\d{2}-\d{2}$/.test(group.date)) result[group.date] = group.files;
            }
            return result;
        } catch (error) {
            console.error("The recording list could not be read", error);
            return {};
        }
    }

    function dayOfFile(file) {
        return dayKeys.find((day) => days[day].some((entry) => entry.name === file)) || null;
    }

    function setLoading(isLoading) {
        if (overlay) overlay.hidden = !isLoading;
    }

    function recordedFromName(name) {
        const match = /^cu_(\d{4})(\d{2})(\d{2})_(\d{2})(\d{2})(\d{2})/.exec(name || "");
        return match ? `${match[1]}-${match[2]}-${match[3]} ${match[4]}:${match[5]}:${match[6]}` : "—";
    }

    function installPlotHtml(html) {
        if (!plotArea) return;
        plotArea.innerHTML = html;
        plotArea.querySelectorAll("script").forEach((oldScript) => {
            const script = document.createElement("script");
            for (const attribute of oldScript.attributes) script.setAttribute(attribute.name, attribute.value);
            script.textContent = oldScript.textContent;
            oldScript.replaceWith(script);
        });
    }

    function showEmpty(text) {
        if (plotArea) plotArea.innerHTML = `<p class="plot-empty">${text}</p>`;
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
        if (!calendar || !currentMonth) return;
        calendar.render({
            grid: document.getElementById("plot-calendar"),
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
        const entries = selectedDate ? days[selectedDate] || [] : [];
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

    function selectDate(dateStr) {
        selectedDate = dateStr;
        currentMonth = calendar.monthOf(dateStr);
        if (selectedFile && dayOfFile(selectedFile) !== dateStr) selectedFile = null;
        renderCalendar();
        renderDayList();
        renderDownload();
        writeAddress();
    }

    function selectFile(file) {
        const day = dayOfFile(file);
        selectedFile = day ? file : null;
        if (day) {
            selectedDate = day;
            currentMonth = calendar.monthOf(day);
        }
        renderCalendar();
        renderDayList();
        renderDownload();
        writeAddress();
    }

    async function fetchPlot(file) {
        setLoading(true);
        try {
            const response = await fetch("/plot", {method: "POST", body: new URLSearchParams({file})});
            const payload = await response.json();
            if (!response.ok) throw new Error(payload.error || `Request failed (${response.status})`);
            installPlotHtml(payload.plot);
            renderContext(payload);
        } catch (error) {
            console.error("The plot could not be generated", error);
            showEmpty(`This file could not be plotted. ${error.message || ""}`.trim());
        } finally {
            setLoading(false);
        }
    }

    async function fetchLastPlot() {
        setLoading(true);
        try {
            const response = await fetch("/get_last_plot");
            const payload = await response.json();
            if (!response.ok) throw new Error(payload.error || `Request failed (${response.status})`);
            if (!payload.plot) {
                showEmpty(dayKeys.length ? "No plot yet. Choose a day and a recording on the left." : "No plot available.");
                renderContext(null);
                return;
            }
            installPlotHtml(payload.plot);
            renderContext(payload);
            if (payload.file && dayOfFile(payload.file)) selectFile(payload.file);
        } catch (error) {
            console.error("The last plot could not be loaded", error);
            showEmpty("The last plot could not be loaded.");
        } finally {
            setLoading(false);
        }
    }

    function shiftMonth(delta) {
        if (!currentMonth) return;
        currentMonth = new Date(currentMonth.getFullYear(), currentMonth.getMonth() + delta, 1);
        renderCalendar();
    }

    document.getElementById("calendar-prev")?.addEventListener("click", () => shiftMonth(-1));
    document.getElementById("calendar-next")?.addEventListener("click", () => shiftMonth(1));
    document.getElementById("calendar-latest")?.addEventListener("click", () => {
        if (!dayKeys.length) return;
        const latest = days[dayKeys[0]][0].name;
        selectFile(latest);
        fetchPlot(latest);
    });
    download?.addEventListener("click", (event) => {
        if (!selectedFile) event.preventDefault();
    });

    // Read the address before the first render writes it back.
    const requested = new URLSearchParams(window.location.search).get("file");
    if (dayKeys.length) selectDate(dayKeys[0]);
    if (requested && dayOfFile(requested)) {
        selectFile(requested);
        fetchPlot(requested);
    } else {
        fetchLastPlot();
    }
}());
