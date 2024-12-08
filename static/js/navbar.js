fetch('/navbar')  // Fetch navbar HTML from the Flask route
    .then(response => response.text())
    .then(data => {
        const navbarElement = document.getElementById('navbar');
        navbarElement.innerHTML = data;  // Insert the navbar HTML into the page
    })
    .catch(error => console.error('Error loading navbar:', error));

// Toggle the navigation items visibility
function toggleNavbar() {
    const navbarItems = document.getElementById('navbarItems');
    const toggleIcon = document.getElementById('toggleIcon');

    navbarItems.classList.toggle('show');

    if (navbarItems.classList.contains('show')) {
        toggleIcon.innerHTML = '&#10005'; // Set the cross symbol when toggled
    } else {
        toggleIcon.innerHTML = '&#9776;'; // Set the default symbol when untoggled
    }
}