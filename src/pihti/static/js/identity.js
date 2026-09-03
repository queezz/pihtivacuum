(function () {
    "use strict";

    const form = document.getElementById("identity-form");
    const status = document.getElementById("identity-status");
    if (!form || !status) return;

    form.addEventListener("submit", async (event) => {
        event.preventDefault();
        status.textContent = "Selecting operator…";
        const data = new FormData(form);
        const response = await fetch("/api/identify", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({username: data.get("username")})
        });
        const result = await response.json().catch(() => ({}));
        if (response.ok) {
            window.location.replace("/");
            return;
        }
        status.textContent = result.message || "The operator could not be selected.";
    });
}());
