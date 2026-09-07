/* Services: the three PIHTI surfaces, each with its state as this machine
 * could learn it, a link, and how to start it. The board asks the server,
 * never a neighbour, so no address travels into the page.
 *
 * A start row leads with plain words and keeps the command behind a toggle
 * (fleet WEBUI.md, "meaning first; machinery behind a toggle"). Services
 * started another way carry no command at all: ControlUnit's web server is
 * opened by the rig's own GUI, and printing a `lab` line for it named a
 * command nobody can run. */
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

    /* Which commands the reader has opened. The board re-renders every thirty
     * seconds, and a disclosure that closed under a reader mid-copy would be
     * the surface taking back something they pressed, so the set outlives the
     * cards it dresses. */
    const opened = new Set();

    /* The command sits under its own sentence; the toggle, the sentence and
     * the row above them keep one position whether it is shown or hidden. */
    function startCell(row) {
        const cell = document.createElement("dd");
        const how = document.createElement("span");
        how.textContent = row.start_how || "—";
        cell.append(how);
        if (!row.start_command) return cell;
        const toggle = document.createElement("button");
        toggle.type = "button";
        toggle.className = "tiny";
        const command = document.createElement("code");
        command.className = "mono start-command";
        command.textContent = row.start_command;
        const draw = () => {
            const open = opened.has(row.alias);
            command.hidden = !open;
            toggle.setAttribute("aria-expanded", String(open));
            toggle.textContent = open ? "hide command" : "show command";
        };
        toggle.addEventListener("click", () => {
            if (opened.has(row.alias)) opened.delete(row.alias);
            else opened.add(row.alias);
            draw();
        });
        draw();
        cell.append(" ", toggle, command);
        return cell;
    }

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
        const startTerm = document.createElement("dt");
        startTerm.textContent = "Start";
        facts.append(startTerm, startCell(row));
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

    /* The rail's own disclosure: the legend is always readable, the rest of
     * the explanation waits behind one press and never moves the legend. */
    const more = document.getElementById("ensemble-more");
    const detail = document.getElementById("ensemble-detail");
    more?.addEventListener("click", () => {
        detail.hidden = !detail.hidden;
        more.setAttribute("aria-expanded", String(!detail.hidden));
        more.textContent = detail.hidden ? "More" : "Less";
    });

    refresh?.addEventListener("click", () => load(true));
    load(false);
    window.setInterval(() => { if (!document.hidden) load(false); }, 30000);
}());
