/* Side rails below the desktop breakpoint become drawers: the same DOM,
 * summoned by the toggles above the content, dismissed by Escape, the
 * backdrop, or the in-drawer Close button. */
(function () {
    "use strict";

    const DRAWER_QUERY = "(max-width: 1199px)";

    function closeDrawers() {
        document.querySelectorAll(".rail.drawer-open").forEach((rail) => rail.classList.remove("drawer-open"));
        document.querySelectorAll("[data-drawer]").forEach((button) => button.setAttribute("aria-expanded", "false"));
        const backdrop = document.querySelector(".drawer-backdrop");
        if (backdrop) backdrop.hidden = true;
    }

    function openDrawer(id) {
        if (!window.matchMedia(DRAWER_QUERY).matches) return;
        closeDrawers();
        const rail = document.getElementById(id);
        const button = document.querySelector(`[data-drawer="${id}"]`);
        const backdrop = document.querySelector(".drawer-backdrop");
        if (!rail || !backdrop) return;
        rail.classList.add("drawer-open");
        if (button) button.setAttribute("aria-expanded", "true");
        backdrop.hidden = false;
        rail.setAttribute("tabindex", "-1");
        rail.focus({preventScroll: true});
    }

    function setup() {
        document.querySelectorAll("[data-drawer]").forEach((button) => {
            button.addEventListener("click", () => {
                const rail = document.getElementById(button.dataset.drawer);
                if (rail?.classList.contains("drawer-open")) closeDrawers();
                else openDrawer(button.dataset.drawer);
            });
        });
        document.querySelector(".drawer-backdrop")?.addEventListener("click", closeDrawers);
        document.querySelectorAll(".drawer-close").forEach((button) => button.addEventListener("click", closeDrawers));
        document.addEventListener("keydown", (event) => { if (event.key === "Escape") closeDrawers(); });
        window.matchMedia(DRAWER_QUERY).addEventListener("change", (event) => { if (!event.matches) closeDrawers(); });
        setupOperator();
    }

    /* The operator selector lives in the top bar on every page: choosing a name
       labels the changes that follow, and "Read only" gives the label back. */
    function setupOperator() {
        const select = document.getElementById("operator-select");
        if (!select) return;
        select.addEventListener("change", async () => {
            const chosen = select.value;
            if (chosen === (select.dataset.current || "")) return;
            select.disabled = true;
            try {
                const response = chosen
                    ? await fetch("/api/identify", {
                        method: "POST",
                        headers: {"Content-Type": "application/json"},
                        body: JSON.stringify({username: chosen})
                    })
                    : await fetch("/api/identity/clear", {method: "POST"});
                if (response.ok) {
                    window.location.reload();
                    return;
                }
            } catch (error) {
                console.error("The operator could not be changed", error);
            }
            select.value = select.dataset.current || "";
            select.disabled = false;
        });
    }

    window.pihtiRails = {openDrawer, closeDrawers};
    if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", setup);
    else setup();
}());
