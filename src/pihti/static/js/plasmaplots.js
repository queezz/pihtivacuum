/* Plot: the file list in the left rail is the control, the plot is the
 * content, the right rail states which file and channels the plot shows. */
(function () {
    "use strict";

    const plotArea = document.getElementById("plotArea");
    const overlay = document.getElementById("loading-overlay");
    const download = document.getElementById("downloadBtn");
    const fileButtons = Array.from(document.querySelectorAll("#file-list button[data-file]"));
    let selectedFile = null;

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
            note.textContent = meta ? "The last plot was made before its file was recorded." : "No plot yet. Choose a file on the left.";
            return;
        }
        document.getElementById("plot-file").textContent = meta.file;
        document.getElementById("plot-recorded").textContent = recordedFromName(meta.file);
        document.getElementById("plot-generated").textContent = meta.generated_at || "—";
        document.getElementById("plot-linear").textContent = (meta.linear || []).join(", ") || "—";
        document.getElementById("plot-log").textContent = (meta.log || []).join(", ") || "—";
    }

    function markSelected(file) {
        selectedFile = fileButtons.some((button) => button.dataset.file === file) ? file : null;
        fileButtons.forEach((button) => button.setAttribute("aria-pressed", String(button.dataset.file === selectedFile)));
        if (download) {
            download.setAttribute("aria-disabled", String(!selectedFile));
            download.href = selectedFile ? `/download_controlunit_csv?file=${encodeURIComponent(selectedFile)}` : "#";
        }
    }

    function writeAddress() {
        window.history.replaceState(null, "", selectedFile ? `/plasmaplots?file=${encodeURIComponent(selectedFile)}` : "/plasmaplots");
    }

    async function fetchPlot(file) {
        setLoading(true);
        try {
            const response = await fetch("/plot", {method: "POST", body: new URLSearchParams({file})});
            const payload = await response.json();
            if (!response.ok) throw new Error(payload.error || `Request failed (${response.status})`);
            installPlotHtml(payload.plot);
            renderContext(payload);
            try { localStorage.setItem("lastFile", file); } catch (error) { /* storage unavailable */ }
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
                showEmpty(fileButtons.length ? "No plot yet. Choose a file on the left." : "No plot available.");
                renderContext(null);
                return;
            }
            installPlotHtml(payload.plot);
            renderContext(payload);
            if (payload.file) markSelected(payload.file);
        } catch (error) {
            console.error("The last plot could not be loaded", error);
            showEmpty("The last plot could not be loaded.");
        } finally {
            setLoading(false);
        }
    }

    fileButtons.forEach((button) => {
        button.addEventListener("click", () => {
            markSelected(button.dataset.file);
            writeAddress();
            fetchPlot(button.dataset.file);
            window.pihtiRails?.closeDrawers();
        });
    });

    download?.addEventListener("click", (event) => {
        if (!selectedFile) event.preventDefault();
    });

    const requested = new URLSearchParams(window.location.search).get("file");
    if (requested && fileButtons.some((button) => button.dataset.file === requested)) {
        markSelected(requested);
        fetchPlot(requested);
    } else {
        fetchLastPlot();
    }
}());
