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
        const userConfirmed = confirm(`Do you want to toggle the status of ${element.id}?`);
        if (!userConfirmed) {
            console.log(`${element.id} toggle cancelled.`);
            return;
        }
    }
    const currentFill = rgbToHex(element.style.fill || window.getComputedStyle(element).fill);
    const newFill = currentFill === colors.active ? colors.inactive : colors.active;
    element.style.fill = newFill;
    console.log(`${element.id} fill changed to: ${newFill}`);

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

        ];

        // Attach event listeners
        attachEventListeners(elementsConfig, 'tooltip');
    })
    .catch(error => console.error('Error loading SVG:', error));
