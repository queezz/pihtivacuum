let elementsConfig = []; // Declare elementsConfig globally

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
    console.log(confirmToggle)
    if (confirmToggle) {
        const userConfirmed = confirm(`Confirm opening/closing of ${element.id}?`);
        if (!userConfirmed) {
            console.log(`${element.id} toggle cancelled.`);
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
        .then(data => console.log('Server response:', data))
        .catch(error => console.error('Error sending data to server:', error));
}



// Function to handle showing tooltips
function showTooltip(tooltip, event, text) {
    tooltip.style.display = 'block';
    tooltip.style.left = `${event.pageX + 10}px`;
    tooltip.style.top = `${event.pageY + 10}px`;
    tooltip.innerText = text;
}

// Function to attach event listeners to specified elements
function attachEventListeners(elementsConfig, tooltipId) {
    const tooltip = document.getElementById(tooltipId);

    if (!tooltip) {
        console.error(`No tooltip element with ID '${tooltipId}' found.`);
        return;
    }

    elementsConfig.forEach(({ id, colors, confirmToggle }) => {
        const element = document.getElementById(id);
        element.style.cursor = 'pointer';

        if (!element) {
            console.error(`No element with ID '${id}' found in the SVG.`);
            return;
        }

        // Toggle status on click
        element.addEventListener('click', () => toggleElementStatus(element, colors, confirmToggle));

        // Tooltip on hover
        element.addEventListener('mouseenter', (event) => showTooltip(tooltip, event, id));
        element.addEventListener('mouseleave', () => { tooltip.style.display = 'none'; });
    });
}

// Function to save the current status of all elements to a file
function saveElementStatus(elementsConfig) {
    const statusData = elementsConfig.map(({ id, colors }) => {
        const element = document.getElementById(id);
        const currentFill = rgbToHex(element.style.fill || window.getComputedStyle(element).fill);
        const status = currentFill === colors.active ? 'active' : 'inactive';
        return { id, status };
    });

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

// Load the SVG dynamically
fetch('diagram.svg')
    .then(response => response.text())
    .then(svg => {
        const container = document.getElementById('diagram-container');
        container.innerHTML = svg;

        // Define elements with their specific colors
        const elementsConfig = [
            { id: 'GVU', colors: { active: '#9bf08d', inactive: 'gray' }, confirmToggle: true },
            { id: 'GVD', colors: { active: '#9bf08d', inactive: 'gray' }, confirmToggle: true },
            { id: 'GVBD', colors: { active: '#9bf08d', inactive: 'gray' }, confirmToggle: true },
            { id: 'GVBU', colors: { active: '#9bf08d', inactive: 'gray' }, confirmToggle: true },
            { id: 'TMPU', colors: { active: 'yellow', inactive: 'gray' }, confirmToggle: true },
            { id: 'TMPD', colors: { active: 'yellow', inactive: 'gray' }, confirmToggle: true },
            { id: 'RoughD', colors: { active: 'yellow', inactive: 'gray' }, confirmToggle: true },
            { id: 'RoughU', colors: { active: 'yellow', inactive: 'gray' }, confirmToggle: true },
            { id: 'Rough-Bypass', colors: { active: 'yellow', inactive: 'gray' }, confirmToggle: true },
            { id: 'valve_qms', colors: { active: '#9bf08d', inactive: 'gray' }, confirmToggle: false },
            { id: 'Membrane', colors: { active: '#9bf08d', inactive: 'gray' }, confirmToggle: false },
            { id: 'bypass-l1', colors: { active: '#9bf08d', inactive: 'gray' }, confirmToggle: false },
            { id: 'bypass-l2', colors: { active: '#9bf08d', inactive: 'gray' }, confirmToggle: false },
            { id: 'bypass-vcr-u', colors: { active: '#9bf08d', inactive: 'gray' }, confirmToggle: false },
            { id: 'bypass-vcr-d', colors: { active: '#9bf08d', inactive: 'gray' }, confirmToggle: false },

            { id: 'gasline-main', colors: { active: '#9bf08d', inactive: 'gray' }, confirmToggle: false },
            { id: 'gasline-h', colors: { active: '#9bf08d', inactive: 'gray' }, confirmToggle: false },
            { id: 'gasline-o', colors: { active: '#9bf08d', inactive: 'gray' }, confirmToggle: false },
            { id: 'gasline-ar', colors: { active: '#9bf08d', inactive: 'gray' }, confirmToggle: false },
            { id: 'flow-calibration-valve', colors: { active: '#9bf08d', inactive: 'gray' }, confirmToggle: false },


            { id: 'gaspanel-valve-h', colors: { active: '#9bf08d', inactive: 'gray' }, confirmToggle: false },
            { id: 'gaspanel-valve-o', colors: { active: '#9bf08d', inactive: 'gray' }, confirmToggle: false },
            { id: 'gaspanel-valve-ar', colors: { active: '#9bf08d', inactive: 'gray' }, confirmToggle: false },
            { id: 'gaspanel-valve-n', colors: { active: '#9bf08d', inactive: 'gray' }, confirmToggle: false },

            { id: 'gaspanel-valve-vent', colors: { active: '#9bf08d', inactive: 'gray' }, confirmToggle: false },
            { id: 'gaspanel-valve-pump', colors: { active: '#9bf08d', inactive: 'gray' }, confirmToggle: false },
            { id: 'gaspanel-pump-vent', colors: { active: '#9bf08d', inactive: 'gray' }, confirmToggle: false },
            { id: 'gaspanel-pump', colors: { active: '#9bf08d', inactive: 'gray' }, confirmToggle: false },


        ];

        document.querySelectorAll('.non-clickable').forEach(element => {
            element.style.pointerEvents = 'none';
        });

        // document.querySelectorAll('.clickable').forEach(element => {
        //     element.style.cursor = 'pointer';
        // });

        // Attach event listeners
        attachEventListeners(elementsConfig, 'tooltip');
    })
    .catch(error => console.error('Error loading SVG:', error));
