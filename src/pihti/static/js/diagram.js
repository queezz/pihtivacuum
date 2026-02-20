let elementsConfig = []; // Declare elementsConfig globally
let isInteracting = false; // Flag to track user interactions

function rgbToHex(rgb) {
    const match = rgb.match(/^rgb\((\d+),\s*(\d+),\s*(\d+)\)$/);
    if (!match) return rgb; // Return original value if not an RGB color

    const hex = match
        .slice(1) // Get the R, G, B values
        .map((x) => parseInt(x).toString(16).padStart(2, '0')) // Convert to hex and pad
        .join('');
    return `#${hex}`;
}

// Function to handle toggling fill color
function toggleElementStatus(element, colors, confirmToggle) {
    isInteracting = true; // Mark interaction as active
    console.log(confirmToggle)
    if (confirmToggle) {
        const userConfirmed = confirm(`Confirm opening/closing of ${element.id}?`);
        if (!userConfirmed) {
            console.log(`${element.id} toggle cancelled.`);
            isInteracting = false;
            return;
        }
    }

    // Determine the new status based on the current fill color
    const currentFill = rgbToHex(element.style.fill || window.getComputedStyle(element).fill);
    const newStatus = currentFill === colors.active ? 'inactive' : 'active';
    const newFill = newStatus === 'active' ? colors.active : colors.inactive;
    element.style.fill = newFill;
    console.log(`${element.id} fill changed to: ${newFill}`);

    // Send the update to the backend
    fetch('/update', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ id: element.id, status: newStatus })
    })
        .then(response => response.json())
        .then(data => {
            console.log('Server response:', data);
            isInteracting = false;
        })
        .catch(error => {
            console.error('Error sending data to server:', error);
            isInteracting = false;
        });
}

// Function to handle showing tooltips
function showTooltip(tooltip, event, text) {
    tooltip.style.display = 'block';
    tooltip.style.left = `${event.pageX + 10}px`;
    tooltip.style.top = `${event.pageY + 10}px`;
    tooltip.innerText = text;
}

// Function to attach event listeners. Click uses delegation; hover uses mouseenter/mouseleave per element so the tooltip hides as soon as the pointer leaves that element (or its group).
// In history mode: SVG is fully non-interactive (pointer-events: none).
function attachEventListeners(elementsConfig, state, tooltipId) {
    if (window.historyMode) {
        const container = document.getElementById('diagram-container');
        if (container) container.style.pointerEvents = 'none';
        return;
    }

    const tooltip = document.getElementById(tooltipId);
    if (!tooltip) return;

    const configById = {};
    elementsConfig.forEach(c => { configById[c.id] = c; });

    function findConfiguredElement(el, root) {
        let cur = el;
        while (cur && cur !== root) {
            if (cur.id && configById[cur.id]) return cur;
            cur = cur.parentElement;
        }
        return null;
    }

    fetch('/get_current_user')
        .then(response => response.json())
        .then(data => {
            const isAuthenticated = data.is_authenticated;
            const container = document.getElementById('diagram-container');
            if (!container) return;

            elementsConfig.forEach(({ id }) => {
                const el = document.getElementById(id);
                if (!el) return;
                el.style.cursor = isAuthenticated ? "pointer" : "not-allowed";
                if (!isAuthenticated) return;
                // mouseenter/mouseleave so tooltip hides when leaving this element (e.g. to another SVG child), not only when leaving the whole SVG
                el.addEventListener("mouseenter", (e) => showTooltip(tooltip, e, id));
                el.addEventListener("mouseleave", () => {
                    tooltip.style.display = "none";
                });
            });

            if (!isAuthenticated) return;

            container.addEventListener("click", (e) => {
                const target = findConfiguredElement(e.target, container);
                if (!target) return;
                const config = configById[target.id];
                toggleElementStatus(target, config.colors, config.confirmToggle);
            });
        })
        .catch(error => console.error('Error fetching user status:', error));
}
// Function to save the current status of all elements to a file
function saveElementStatus(elementsConfig) {
    const statusData = elementsConfig.map(({ id, colors }) => {
        const element = document.getElementById(id);

        if (!element) {
            console.error(`No element with ID '${id}' found in the SVG.`);
            return null;
        }

        const currentFill = rgbToHex(
            element.style.fill || window.getComputedStyle(element).fill);

        const status = currentFill === colors.active ? "active" : "inactive";

        return { id, status };

    }).filter(Boolean);  		 // Remove any null entries due to missing elements

    const blob = new Blob([JSON.stringify(statusData, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);

    const link = document.createElement('a');
    link.href = url;
    link.download = 'element_status.json';
    link.click();

    URL.revokeObjectURL(url);
    console.log('Status saved:', statusData);
}

// Function to log element status changes
function logStatusChange(element, newFill) {
    const timestamp = new Date().toISOString();
    const logEntry = `${timestamp} - ${element.id} changed to: ${newFill}`;
    console.log(logEntry);

    // Optionally append logs to a downloadable file
    const logBlob = new Blob([`${logEntry}\n`], { type: 'text/plain' });
    const logUrl = URL.createObjectURL(logBlob);

    const logLink = document.createElement('a');
    logLink.href = logUrl;
    logLink.download = 'status_log.txt';
    logLink.style.display = 'none'; // Hide the download link
    document.body.appendChild(logLink);
    logLink.click();
    document.body.removeChild(logLink);
}

let vacuumstate = [];

/**
 * Apply a state dict to the SVG diagram. State format: { id: 'active'|'inactive' }.
 * Reuses existing coloring logic; does not mutate elementsConfig.
 * Exposed on window for history replay.
 */
function applyState(state) {
    if (!elementsConfig || elementsConfig.length === 0) return;
    elementsConfig.forEach(element => {
        const elementDiv = document.getElementById(element.id);
        if (!elementDiv) return;
        const status = (state[element.id] === 'active' || state[element.id] === true)
            ? 'active'
            : 'inactive';
        const fillColor = status === 'active' ? element.colors.active : element.colors.inactive;
        elementDiv.style.fill = fillColor;
    });
}

function fetchAndUpdateStates() {
    if (isInteracting) {
        console.log("Skipping state update during user interaction.");
        return;
    }
    fetch('/elements-state')
        .then(response => response.json())
        .then(state => {
            vacuumstate = state;
            applyState(state);
        })
        .catch(error => console.error('Error fetching element states:', error));
}


// Expose applyState for history replay
window.applyState = applyState;

// Function to load the SVG and update the status colors correctly
fetch('/static/diagram.svg')
    .then(response => response.text())
    .then(svg => {
        const container = document.getElementById('diagram-container');
        if (!container) return;
        container.innerHTML = svg;

        if (window.historyMode) {
            container.style.pointerEvents = 'none';
        }

        document.querySelectorAll('.non-clickable').forEach(element => {
            element.style.pointerEvents = 'none';
        });

        // Fetch the configuration
        fetch('/elements-config')
            .then(response => response.json())
            .then(config => {
                elementsConfig = config;
                fetchAndUpdateStates();
                attachEventListeners(elementsConfig, vacuumstate, 'tooltip');
                if (!window.historyMode) {
                    setInterval(fetchAndUpdateStates, 5000);
                }
            })
            .catch(error => console.error('Error fetching configuration:', error));
    })
    .catch(error => console.error('Error loading SVG:', error));