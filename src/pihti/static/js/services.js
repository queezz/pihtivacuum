/* Services: the three PIHTI surfaces, each with its state as this machine
 * could learn it, a link, and the lab line that starts it. The board asks
 * the server, never a neighbour, so no address travels into the page. */
(function () {
    "use strict";

    const board = document.getElementById("services-board");
    const checked = document.getElementById("services-checked");
    const refresh = document.getElementById("services-refresh");
    if (!board) return;

    const STATE_WORD = {
        "ok": "ok",
        "degraded": "degraded",
        "down": "down",
        "unreachable": "unreachable",
        "not configured": "not configured",
    };

    function card(row) {
        const article = document.createElement("article");
        article.className = `service-card state-${row.state.replace(/\s+/g, "-")}`;
        const head = document.createElement("div");
        head.className = "service-head";
        const name = document.createElement("h2");
        name.textContent = row.name;
        const chip = document.createElement("span");
        chip.className = "state-chip";
        chip.textContent = STATE_WORD[row.state] || row.state;
        head.append(name, chip);
        const facts = document.createElement("dl");
        facts.className = "facts";
        const add = (term, value, mono) => {
            const dt = document.createElement("dt");
            dt.textContent = term;
            const dd = document.createElement("dd");
            if (mono) dd.className = "mono";
            dd.textContent = value;
            facts.append(dt, dd);
        };
        add("Version", row.version || "—", true);
        add("Says", row.detail || "—");
        add("Start", `lab ${row.alias}`, true);
        const actions = document.createElement("p");
        actions.className = "service-actions";
        if (row.alias === "pihti-diagram") {
            actions.textContent = "This is the service you are reading.";
            actions.className += " muted";
        } else if (row.url) {
            const link = document.createElement("a");
            link.className = "button";
            link.href = row.url;
            link.textContent = `Open ${row.name}`;
            actions.append(link);
        } else {
            actions.textContent = "No address on this machine.";
            actions.className += " muted";
        }
        article.append(head, facts, actions);
        return article;
    }

    async function load(fresh) {
        if (refresh) refresh.disabled = true;
        try {
            const response = await fetch(fresh ? "/api/neighbours?fresh=1" : "/api/neighbours");
            const payload = await response.json();
            board.replaceChildren(...payload.services.map(card));
            if (checked) checked.textContent = `Checked ${payload.checked_at}.`;
        } catch (error) {
            console.error("The services board could not be loaded", error);
            if (checked) checked.textContent = "The check itself failed; reload the page.";
        } finally {
            if (refresh) refresh.disabled = false;
        }
    }

    refresh?.addEventListener("click", () => load(true));
    load(false);
    window.setInterval(() => { if (!document.hidden) load(false); }, 30000);
}());
