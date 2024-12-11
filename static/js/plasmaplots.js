$(document).ready(function () {
    // Load the last plot on page load
    fetch('/get_last_plot')
        .then(response => response.json())
        .then(data => {
            $('#plotArea').html(data.plot);
        })
        .catch(error => {
            console.error('Error fetching the last plot:', error);
        });

    // On page load, pre-select the last file if it exists
    const lastFile = localStorage.getItem('lastFile');
    if (lastFile) {
        $('#fileDropdown').val(lastFile); // Pre-select the last file in dropdown
    }

    // Form submission handler
    $('#fileForm').on('submit', function (e) {
        e.preventDefault();

        const selectedFile = $('#fileDropdown').val();
        localStorage.setItem('lastFile', selectedFile); // Save selected file
        fetchPlot(selectedFile);
    });

    // Function to fetch and display plot
    function fetchPlot(file) {
        $('#loading-overlay').show(); // Show spinner
        $.ajax({
            url: '/plot',
            method: 'POST',
            data: { file: file },
            success: function (response) {
                $('#plotArea').html(response.plot); // Display plot
            },
            error: function (xhr, status, error) {
                console.error('Error:', error);
            },
            complete: function () {
                $('#loading-overlay').hide(); // Hide spinner
            }
        });
    }

    // Download button handling
    $('#downloadBtn').on('click', function () {
        const selectedFile = $('#fileDropdown').val();
        if (!selectedFile) {
            alert('No file selected.');
            return;
        }
        window.location.href = '/download_controlunit_csv?file=' + encodeURIComponent(selectedFile);
    });
});
