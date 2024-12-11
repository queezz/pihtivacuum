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

// Function to attach event listeners to specified elements and set initial state
function attachEventListeners(elementsConfig, state, tooltipId) {
    const tooltip = document.getElementById(tooltipId);

    if (!tooltip) {
        console.error(`No tooltip element with ID '${tooltipId}' found.`);
        return;
    }

    fetch('/get_current_user')
        .then(response => response.json())
        .then(data => {
            const isAuthenticated = data.is_authenticated;

            elementsConfig.forEach(({ id, colors, confirmToggle }) => {
                const elementDiv = document.getElementById(id);

                if (!elementDiv) {
                    console.error(`No element with ID '${id}' found in the SVG.`);
                    return;
                }

                elementDiv.style.cursor = isAuthenticated ? "pointer" : "not-allowed";

                if (isAuthenticated) {
                    // Toggle status on click
                    elementDiv.addEventListener("click", () =>
                        toggleElementStatus(elementDiv, colors, confirmToggle)
                    );

                    // Tooltip on hover
                    elementDiv.addEventListener("mouseenter", (event) =>
                        showTooltip(tooltip, event, id)
                    );

                    elementDiv.addEventListener("mouseleave", () => {
                        tooltip.style.display = "none";
                    });
                }
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
function fetchAndUpdateStates() {
    if (isInteracting) {
        console.log("Skipping state update during user interaction.");
        return;
    }
    // Fetch the current state of all elements
    fetch('/elements-state')
        .then(response => response.json())
        .then(state => {
            // console.log('Current elements state:', state);
            vacuumstate = state;

            // Use the configuration to update elements' status in SVG
            elementsConfig.forEach(element => {
                const elementDiv = document.getElementById(element.id);
                if (!elementDiv) {
                    console.error(`No element with ID '${element.id}' found.`);
                    return;
                }

                const elementState = state[element.id];
                // If element state is missing, assign inactive
                const status = elementState ? elementState : 'inactive';
                const fillColor =
                    status === 'active' ? element.colors.active : element.colors.inactive;
                // console.log('id:', element.id, 'state:', state[element.id], 'status', status)
                // Set initial fill color based on loaded state
                if (elementDiv.style.fill !== fillColor) {
                    elementDiv.style.fill = fillColor;
                    // console.log(`Set initial fill for ${element.id} to: ${fillColor}`);
                }
            });

        })
        .catch(error => console.error('Error fetching element states:', error));
}


// Function to load the SVG and update the status colors correctly
fetch('diagram.svg')
    .then(response => response.text())
    .then(svg => {
        const container = document.getElementById('diagram-container');
        container.innerHTML = svg;

        document.querySelectorAll('.non-clickable').forEach(element => {
            element.style.pointerEvents = 'none';
        });

        // Fetch the configuration
        fetch('/elements-config')
            .then(response => response.json())
            .then(config => {
                elementsConfig = config;
                fetchAndUpdateStates();
                // Attach event listeners after setting initial states with state passed as argument
                attachEventListeners(elementsConfig, vacuumstate, 'tooltip');
                setInterval(fetchAndUpdateStates, 5000);

            })
            .catch(error => console.error('Error fetching configuration:', error));
    })
    .catch(error => console.error('Error loading SVG:', error));