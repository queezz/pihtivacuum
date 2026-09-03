// Toggle the navigation items visibility
function toggleNavbar() {
    const navbarItems = document.getElementById('navbarItems');
    const toggleIcon = document.getElementById('toggleIcon');
    const toggleButton = document.querySelector('.navbar-toggle');

    if (!navbarItems || !toggleIcon || !toggleButton) return;

    navbarItems.classList.toggle('show');
    const isOpen = navbarItems.classList.contains('show');
    toggleButton.setAttribute('aria-expanded', String(isOpen));
    toggleButton.setAttribute('aria-label', isOpen ? 'Close navigation' : 'Open navigation');

    if (isOpen) {
        toggleIcon.innerHTML = '&#10005'; // Set the cross symbol when toggled
    } else {
        toggleIcon.innerHTML = '&#9776;'; // Set the default symbol when untoggled
    }
}

document.addEventListener('DOMContentLoaded', () => {
    document.querySelector('.navbar-toggle')?.addEventListener('click', toggleNavbar);
});
