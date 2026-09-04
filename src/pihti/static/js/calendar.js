/* One month calendar for a rail card, shared by History (days with diagram
 * changes) and Plot (days with control-unit files). The caller owns the
 * state; this only draws a month and reports which day was pressed. */
(function () {
    "use strict";

    const pad = (value) => String(value).padStart(2, "0");
    const isoDate = (date) => `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`;

    function monthOf(dateStr) {
        const [year, month] = dateStr.split("-").map(Number);
        return new Date(year, month - 1, 1);
    }

    /* options: grid, label (elements); month (Date, first of month); counts
     * ({"YYYY-MM-DD": n}); selected ("YYYY-MM-DD" or null); onSelect(dateStr);
     * noun ("change" / "file") for the day's accessible label. */
    function render(options) {
        const {grid, label, month, counts, selected, onSelect} = options;
        const noun = options.noun || "item";
        if (!grid || !label || !month) return;
        const year = month.getFullYear();
        const monthIndex = month.getMonth();
        label.textContent = month.toLocaleDateString(undefined, {month: "long", year: "numeric"});
        const maxCount = Math.max(1, ...Object.values(counts || {}));
        const daysInMonth = new Date(year, monthIndex + 1, 0).getDate();
        const today = isoDate(new Date());
        const cells = ["Su", "Mo", "Tu", "We", "Th", "Fr", "Sa"].map((name) => {
            const head = document.createElement("div");
            head.className = "cal-head";
            head.textContent = name;
            return head;
        });
        for (let i = 0; i < new Date(year, monthIndex, 1).getDay(); i += 1) {
            const empty = document.createElement("div");
            empty.className = "cal-empty";
            cells.push(empty);
        }
        for (let day = 1; day <= daysInMonth; day += 1) {
            const dateStr = `${year}-${pad(monthIndex + 1)}-${pad(day)}`;
            const count = (counts || {})[dateStr] || 0;
            const cell = document.createElement("button");
            cell.type = "button";
            cell.className = "cal-day" + (count ? " has-events" : "") + (dateStr === today ? " today" : "");
            cell.dataset.date = dateStr;
            cell.textContent = String(day);
            cell.setAttribute("aria-pressed", String(dateStr === selected));
            cell.setAttribute("aria-label", `${dateStr}, ${count} ${noun}${count === 1 ? "" : "s"}`);
            if (count) {
                const intensity = 0.18 + 0.55 * Math.min(1, count / maxCount);
                cell.style.backgroundColor = `rgba(126, 184, 247, ${intensity.toFixed(2)})`;
            }
            cell.addEventListener("click", () => onSelect(dateStr));
            cells.push(cell);
        }
        grid.replaceChildren(...cells);
    }

    window.pihtiCalendar = {render, monthOf, isoDate, todayStr: () => isoDate(new Date())};
}());
