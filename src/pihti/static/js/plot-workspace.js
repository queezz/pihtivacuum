/* Recording-only Plotly workspace. Original samples never change when a view changes. */
(function () {
    "use strict";
    const root = document.getElementById("charts");
    if (!root) return;
    function fail(error) {
        root.textContent = error;
        window.parent.postMessage({type: "pihti-plot-error", error}, window.location.origin);
    }
    let recording;
    try { recording = JSON.parse(document.getElementById("recording-data").textContent); }
    catch (_) { fail("This recording could not be read."); return; }
    if (recording.error) { fail(String(recording.error)); return; }
    if (!window.Plotly) { fail("The chart library could not be loaded."); return; }
    const series = (recording.series || []).filter(s => s && Array.isArray(s.x) && Array.isArray(s.y));
    const colors = ["#7eb8f7", "#66c2a5", "#d6ad63", "#c9796b", "#bd9ce8", "#83ced1", "#e5a3c7", "#b6c879"];
    const charts = new Map();
    const escape = value => String(value == null ? "" : value).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
    const schema = JSON.stringify(series.map(s => [s.id, s.unit, s.group]));
    let hash = 2166136261;
    for (let i = 0; i < schema.length; i++) hash = Math.imul(hash ^ schema.charCodeAt(i), 16777619);
    const storageKey = "pihti.plot.workspace.v3." + (hash >>> 0).toString(16);
    const zeroStorageKey = "pihti.plot.zero.v1." + JSON.stringify(recording.file || "");
    let offsets = Object.create(null);
    let panels, placement, visible, drag, timeRange = null, rendering = false;
    let queue = Promise.resolve();
    let revision = 0;
    let ready = false, lastHeight = 0, lastWidth = 0, resizeTimer;
    const panelLabel = (name, unit) => `${name}${unit ? " · " + unit : " · unit not recorded"}`;

    function defaults() {
        panels = []; placement = Object.create(null); visible = Object.create(null); drag = "zoom"; timeRange = null;
        const groups = new Map();
        for (const s of series) {
            const key = JSON.stringify([s.group, s.unit]);
            if (!groups.has(key)) {
                const panel = {id: "panel-" + panels.length, label: panelLabel(s.group || s.label, s.unit), unit: s.unit || "", scale: s.unit === "Torr" ? "log" : "linear", active: false};
                groups.set(key, panel); panels.push(panel);
            }
            const panel = groups.get(key);
            placement[s.id] = panel.id;
            visible[s.id] = s.default_visible !== false;
            panel.active ||= visible[s.id];
        }
    }
    function restore() {
        try {
            const saved = JSON.parse(localStorage.getItem(storageKey));
            if (!saved || saved.schema !== schema || !Array.isArray(saved.panels)) return;
            const ids = new Set();
            if (!saved.panels.length || saved.panels.length > series.length * 2) return;
            if (!saved.panels.every(p => p && typeof p.id === "string" && !ids.has(p.id) && ids.add(p.id) && typeof p.label === "string" && typeof p.unit === "string" && ["log", "linear"].includes(p.scale)
                && (p.secondaryUnit === undefined || (typeof p.secondaryUnit === "string" && p.secondaryUnit !== p.unit && ["log", "linear"].includes(p.secondaryScale))))) return;
            if (!series.every(s => saved.panels.some(p => p.id === saved.placement?.[s.id] && accepts(p, s.unit || "")) && typeof saved.visible?.[s.id] === "boolean")) return;
            panels = saved.panels.map(p => ({id: p.id, label: p.label, unit: p.unit, scale: p.scale, active: Boolean(p.active),
                ...(p.secondaryUnit === undefined ? {} : {secondaryUnit: p.secondaryUnit, secondaryScale: p.secondaryScale})}));
            for (const s of series) { placement[s.id] = saved.placement[s.id]; visible[s.id] = saved.visible[s.id]; }
            for (const p of panels) p.active ||= series.some(s => placement[s.id] === p.id && visible[s.id]);
            drag = saved.drag === "pan" ? "pan" : "zoom";
        } catch (_) { /* Storage may be disabled or from an older view schema. */ }
    }
    function save() {
        try { localStorage.setItem(storageKey, JSON.stringify({schema, panels, placement, visible, drag})); }
        catch (_) { /* A private browser still gets a working workspace. */ }
    }
    function saveZeros() {
        if (!recording.file) return;
        try { localStorage.setItem(zeroStorageKey, JSON.stringify({schema, offsets})); } catch (_) { /* Browser-local only. */ }
    }
    function restoreZeros() {
        if (!recording.file) return;
        try {
            const saved = JSON.parse(localStorage.getItem(zeroStorageKey));
            if (!saved || saved.schema !== schema) return;
            for (const s of series) {
                if (typeof saved.offsets?.[s.id] !== "number" || !Number.isFinite(saved.offsets[s.id])) continue;
                offsets[s.id] = saved.offsets[s.id];
            }
        } catch (_) { /* Malformed saved correction never changes recorded samples. */ }
    }
    function offsetFor(s) { return offsets[s.id] || 0; }
    function adjusted(s, value) { return typeof value === "number" && Number.isFinite(value) ? value - offsetFor(s) : null; }
    function send(type = "pihti-plot-ready", extra = {}) {
        if (type === "pihti-plot-ready" && !ready) return;
        lastHeight = Math.ceil(root.getBoundingClientRect().height + 16);
        window.parent.postMessage({type, file: recording.file,
            series: series.map(({x, y, ...s}) => ({...s, panel: placement[s.id], visible: visible[s.id],
                zero_offset: offsetFor(s), zero_applied: Object.prototype.hasOwnProperty.call(offsets, s.id)})),
            panels: panels.map(p => ({...p})), sources: recording.sources || [], notes: recording.notes || [],
            time_label: recording.time_label, time_range: timeRange, drag, height: lastHeight, ...extra}, window.location.origin);
    }
    function schedule(work) {
        queue = queue.then(work).catch(error => {
            console.error("Plot rendering failed", error);
            send("pihti-plot-error", {error: "That chart change could not be completed. Try resetting the view."});
        });
    }
    function members(panel) { return series.filter(s => placement[s.id] === panel.id); }
    function accepts(panel, unit) { return panel.unit === unit || panel.secondaryUnit === unit; }
    function secondary(panel, s) { return panel.secondaryUnit !== undefined && panel.secondaryUnit === (s.unit || ""); }
    function scaleFor(panel, s) { return secondary(panel, s) ? panel.secondaryScale : panel.scale; }
    function notice(panel, node) {
        const omitted = members(panel).filter(s => visible[s.id] && scaleFor(panel, s) === "log").reduce((n, s) => n + s.y.filter(y => adjusted(s, y) !== null && adjusted(s, y) <= 0).length, 0);
        node.textContent = omitted ? `${omitted.toLocaleString()} zero or negative samples omitted on log scale.` : "";
        node.hidden = !omitted;
    }
    function trace(s, panel) {
        const applied = Object.prototype.hasOwnProperty.call(offsets, s.id);
        const unit = s.unit ? " " + escape(s.unit) : "";
        return {type: "scatter", mode: "lines", uid: "series-" + series.indexOf(s), name: escape(s.label) + (applied ? " (zero corrected)" : ""), x: s.x,
            y: s.y.map(y => { const value = adjusted(s, y); return scaleFor(panel, s) === "log" && value <= 0 ? null : value; }),
            ...(applied ? {customdata: s.y} : {}),
            yaxis: secondary(panel, s) ? "y2" : "y",
            visible: visible[s.id] ? true : "legendonly", connectgaps: false,
            line: {color: colors[series.indexOf(s) % colors.length], width: 1.6},
            hovertemplate: `%{x}<br>${escape(s.label)}${applied ? " corrected" : ""}: %{y:.6g}${unit}`
                + (applied ? `<br>Uncorrected: %{customdata:.6g}${unit}<br>Zero offset: ${offsetFor(s).toPrecision(6)}${unit}` : "") + "<extra></extra>"};
    }
    async function syncTime(origin, event) {
        let update;
        if (event["xaxis.autorange"]) { timeRange = null; update = {"xaxis.autorange": true}; }
        else {
            const range = event["xaxis.range"] || [event["xaxis.range[0]"], event["xaxis.range[1]"]];
            if (range[0] == null || range[1] == null) return;
            timeRange = range.slice(); update = {"xaxis.range": timeRange, "xaxis.autorange": false};
        }
        rendering = true;
        try { await Promise.all([...charts.values()].filter(c => c.plot !== origin).map(c => Plotly.relayout(c.plot, update))); }
        finally { rendering = false; }
        send();
    }
    function wire(panel, chart) {
        chart.plot.on("plotly_relayout", event => { if (!rendering) schedule(() => syncTime(chart.plot, event)); });
        // Plotly resolves the single/double-click delay itself. Read its settled
        // visibility rather than racing a custom toggle against isolation.
        chart.plot.on("plotly_restyle", event => {
            if (rendering || !Object.prototype.hasOwnProperty.call(event[0], "visible")) return;
            for (const t of chart.plot.data) {
                const s = series[Number(t.uid.slice(7))];
                if (s) visible[s.id] = t.visible !== "legendonly" && t.visible !== false;
            }
            save();
            const current = panels.find(p => p.id === panel.id);
            if (current) notice(current, chart.note);
            send();
        });
    }
    function legendRoom(items, width) {
        const ctx = document.createElement("canvas").getContext("2d");
        ctx.font = "12px Aptos, Calibri, sans-serif";
        let rows = 1, used = 0;
        for (const s of items) {
            const size = Math.min(width, Math.ceil(ctx.measureText(s.label + (Object.prototype.hasOwnProperty.call(offsets, s.id) ? " (zero corrected)" : "")).width) + 62);
            if (used && used + size > width) { rows++; used = 0; }
            used += size;
        }
        return rows * 26 + 16;
    }
    async function render() {
        rendering = true;
        try {
            // Do not detach or purge a plot while Plotly still owns a pending
            // autosize pass. New membership gets a fresh graph; old graphs stay
            // mounted until every replacement has finished drawing.
            const retired = [];
            for (const panel of panels.filter(p => p.active && members(p).length)) {
                let chart = charts.get(panel.id);
                const signature = JSON.stringify([members(panel).map(s => s.id), panel.unit, panel.secondaryUnit]);
                if (chart && chart.signature !== signature) { retired.push(chart); chart = null; }
                const fresh = !chart;
                if (fresh) {
                    const section = document.createElement("section"); section.className = "plot-panel";
                    const heading = document.createElement("h2"); heading.className = "plot-panel-heading";
                    const plot = document.createElement("div"); plot.className = "plot-chart";
                    const note = document.createElement("p"); note.className = "plot-panel-note"; note.setAttribute("role", "status");
                    section.append(heading, plot, note); chart = {section, heading, plot, note, signature};
                    root.append(section);
                }
                chart.heading.textContent = panel.label;
                notice(panel, chart.note);
                const axis = {gridcolor: "rgba(255,255,255,0.08)", zerolinecolor: "rgba(255,255,255,0.16)", automargin: true};
                const hasRight = panel.secondaryUnit !== undefined;
                const legendHeight = legendRoom(members(panel), Math.max(140, root.clientWidth - (hasRight ? 140 : 90)));
                const layout = {autosize: true, height: 320 + legendHeight, margin: {l: 62, r: hasRight ? 66 : 18, t: 12, b: 64 + legendHeight},
                    paper_bgcolor: "#161b22", plot_bgcolor: "#11161d", font: {family: "Aptos, Calibri, system-ui, sans-serif", size: 12, color: "#d2d8df"},
                    dragmode: drag, hovermode: "x unified", uirevision: `${revision}:${panel.id}:${panel.scale}:${panel.secondaryScale || ""}`,
                    xaxis: {...axis, title: {text: escape(recording.time_label || "Recorded time")}, type: "date", ...(timeRange ? {range: timeRange, autorange: false} : {autorange: true})},
                    yaxis: {...axis, title: {text: escape(panel.unit || "Unit not recorded")}, type: panel.scale,
                        ...(panel.scale === "log" || panel.unit === "Torr" ? {tickformat: ".1e", exponentformat: "e", showexponent: "all"} : {})},
                    ...(hasRight ? {yaxis2: {...axis, title: {text: escape(panel.secondaryUnit || "Unit not recorded")},
                        overlaying: "y", side: "right", showgrid: false, zeroline: false, type: panel.secondaryScale,
                        ...(panel.secondaryScale === "log" || panel.secondaryUnit === "Torr" ? {tickformat: ".1e", exponentformat: "e", showexponent: "all"} : {})}} : {}),
                    legend: {orientation: "h", x: 0, y: -0.26, xanchor: "left", yanchor: "top", font: {size: 12}, itemclick: "toggle", itemdoubleclick: "toggleothers"},
                    showlegend: true, transition: {duration: 0}};
                await Plotly[fresh ? "newPlot" : "react"](chart.plot, members(panel).map(s => trace(s, panel)), layout,
                    {responsive: false, displaylogo: false, displayModeBar: false, scrollZoom: false, doubleClick: "reset", showTips: false});
                charts.set(panel.id, chart);
                if (fresh) wire(panel, chart);
            }
            for (const [id, chart] of charts) {
                if (!panels.some(p => p.id === id && p.active && members(p).length)) { retired.push(chart); charts.delete(id); }
            }
            for (const chart of retired) { Plotly.purge(chart.plot); chart.section.remove(); }
            let previous = null;
            for (const panel of panels) {
                const section = charts.get(panel.id)?.section;
                if (!section) continue;
                const next = previous ? previous.nextSibling : root.firstChild;
                if (section !== next) root.insertBefore(section, next);
                previous = section;
            }
            let empty = root.querySelector(".plot-workspace-empty");
            if (!charts.size && !empty) { empty = document.createElement("p"); empty.className = "plot-workspace-empty"; root.append(empty); }
            if (empty) { if (charts.size) empty.remove(); else empty.textContent = series.length ? "Choose a curve in Arrange curves to open a chart." : "No numeric samples are available in this recording."; }
        } finally { rendering = false; }
        ready = true;
        lastWidth = root.clientWidth;
        send();
    }
    async function image() {
        const images = [];
        for (const panel of panels) {
            const chart = charts.get(panel.id); if (!chart) continue;
            const url = await Plotly.toImage(chart.plot, {format: "png", width: 1400, height: Math.max(450, chart.plot.layout.height), scale: 1});
            const img = new Image(); img.src = url; await img.decode(); images.push({img, panel});
        }
        if (!images.length) return;
        const canvas = document.createElement("canvas"); canvas.width = 1400; canvas.height = images.reduce((height, entry) => height + entry.img.height + 42, 48);
        const ctx = canvas.getContext("2d"); ctx.fillStyle = "#161b22"; ctx.fillRect(0, 0, canvas.width, canvas.height);
        ctx.fillStyle = "#d2d8df"; ctx.font = "18px sans-serif"; ctx.fillText(recording.file || "Recording", 24, 30);
        let imageTop = 48;
        images.forEach(({img, panel}) => {
            const corrected = members(panel).some(s => visible[s.id] && Object.prototype.hasOwnProperty.call(offsets, s.id));
            ctx.fillText(panel.label + (corrected ? " · zero corrected" : ""), 24, imageTop + 28);
            ctx.drawImage(img, 0, imageTop + 42); imageTop += img.height + 42;
        });
        const blob = await new Promise(resolve => canvas.toBlob(resolve, "image/png"));
        if (!blob) throw new Error("Image export failed");
        const url = URL.createObjectURL(blob), link = document.createElement("a");
        link.href = url; link.download = (recording.file || "recording").replace(/\.[^.]+$/, "") + "-plots.png"; link.click();
        setTimeout(() => URL.revokeObjectURL(url), 30000);
    }
    function exportCurves() {
        const cell = value => value == null ? "" : '"' + String(value).replace(/"/g, '""') + '"';
        const rows = ["recorder_local_time,source,column,unit,uncorrected_value,zero_offset,value\r\n"];
        for (const s of series.filter(s => visible[s.id])) {
            for (let i = 0; i < Math.max(s.x.length, s.y.length); i++) {
                rows.push([s.x[i], s.source, s.column || s.id, s.unit, s.y[i], offsetFor(s), adjusted(s, s.y[i])].map(cell).join(",") + "\r\n");
            }
        }
        const url = URL.createObjectURL(new Blob(rows, {type: "text/csv;charset=utf-8"}));
        const link = document.createElement("a"); link.href = url;
        link.download = (recording.file || "recording").replace(/\.[^.]+$/, "") + "-visible-curves.csv"; link.click();
        setTimeout(() => URL.revokeObjectURL(url), 30000);
    }
    async function command(message) {
        const panel = panels.find(p => p.id === message.panel);
        if (["zero", "reset-zero"].includes(message.action)) {
            const selected = series.find(s => s.id === message.series);
            if (!selected) { send("pihti-plot-error", {error: "Choose an available curve to correct its zero."}); return; }
            if (message.action === "reset-zero") { delete offsets[selected.id]; }
            else if (message.action === "zero") {
                if (typeof message.offset !== "number" || !Number.isFinite(message.offset)) {
                    send("pihti-plot-error", {error: "Enter a finite zero offset in the curve's unit."}); return;
                }
                offsets[selected.id] = message.offset;
            }
            saveZeros(); revision++;
        } else if (message.action === "compare") {
            const requested = Array.isArray(message.series) ? [...new Set(message.series)] : [];
            const selected = requested.map(id => series.find(s => s.id === id));
            if (!selected.length || selected.some(s => !s)) {
                send("pihti-plot-error", {error: "Choose at least one available curve to plot together."}); return;
            }
            const units = [...new Set(selected.map(s => s.unit || ""))];
            if (units.length > 2) {
                send("pihti-plot-error", {error: "A comparison supports two units: one on each side. Choose curves with no more than two different units."}); return;
            }
            if (units.includes("Torr")) units.sort((a, b) => a === "Torr" ? -1 : b === "Torr" ? 1 : 0);
            const unit = units[0];
            let n = 0; while (panels.some(p => p.id === "comparison-" + n)) n++;
            const target = {id: "comparison-" + n,
                label: units.length === 2 ? `${unit === "Torr" && units[1] === "V" ? "Pressure & signals " + (n + 1) : "Comparison " + (n + 1)} · ${units.map(u => u || "unit not recorded").join(" / ")}`
                    : panelLabel((unit === "Torr" ? "Pressure comparison " : unit === "A" ? "Current comparison " : "Comparison ") + (n + 1), unit),
                unit, scale: unit === "Torr" ? "log" : "linear", active: true,
                ...(units.length === 2 ? {secondaryUnit: units[1], secondaryScale: "linear"} : {})};
            panels.unshift(target);
            for (const s of selected) { placement[s.id] = target.id; visible[s.id] = true; }
            panels = panels.filter(p => members(p).length);
            for (const p of panels) p.active = members(p).some(s => visible[s.id]);
        } else if (message.action === "scale" && panel && ["log", "linear"].includes(message.value)) {
            if (message.axis === "right") {
                if (panel.secondaryUnit === undefined) return;
                panel.secondaryScale = message.value;
            } else panel.scale = message.value;
        }
        else if (message.action === "drag" && ["pan", "zoom"].includes(message.value)) drag = message.value;
        else if (message.action === "visibility" && series.some(s => s.id === message.series) && typeof message.visible === "boolean") {
            visible[message.series] = message.visible;
            if (message.visible) panels.find(p => p.id === placement[message.series]).active = true;
        } else if (message.action === "move") {
            const selected = series.find(s => s.id === message.series); if (!selected) return;
            let target = panel;
            if (message.panel === "new") {
                let n = 0; while (panels.some(p => p.id === "custom-" + n)) n++;
                target = {id: "custom-" + n, label: panelLabel(selected.label, selected.unit), unit: selected.unit || "", scale: selected.unit === "Torr" ? "log" : "linear", active: true}; panels.push(target);
            }
            if (!target || !accepts(target, selected.unit || "")) return;
            placement[selected.id] = target.id; visible[selected.id] = true; target.active = true;
            panels = panels.filter(p => members(p).length);
            for (const p of panels) p.active = members(p).some(s => visible[s.id]);
        } else if (message.action === "reorder" && panel && [-1, 1].includes(message.direction)) {
            const active = panels.filter(p => p.active), index = active.indexOf(panel), other = active[index + message.direction];
            if (other) { const a = panels.indexOf(panel), b = panels.indexOf(other); [panels[a], panels[b]] = [panels[b], panels[a]]; }
        } else if (message.action === "reset") { timeRange = null; revision++; }
        else if (message.action === "defaults") { defaults(); offsets = Object.create(null); saveZeros(); revision++; }
        else if (message.action === "image") { await image(); return; }
        else if (message.action === "export-curves") { exportCurves(); return; }
        else return;
        save(); await render();
    }
    window.addEventListener("message", event => {
        if (event.origin !== window.location.origin || event.source !== window.parent || event.data?.type !== "pihti-plot-command") return;
        schedule(() => command(event.data));
    });
    defaults(); restore(); restoreZeros(); schedule(render);
    if (window.ResizeObserver) new ResizeObserver(() => {
        if (!ready || rendering) return;
        if (root.clientWidth !== lastWidth) {
            clearTimeout(resizeTimer);
            resizeTimer = setTimeout(() => schedule(render), 100);
        } else if (Math.ceil(root.getBoundingClientRect().height + 16) !== lastHeight) send();
    }).observe(root);
}());
