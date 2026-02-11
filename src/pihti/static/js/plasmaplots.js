$(document).ready(function () {
    const plotKey = 'lastPlotHtml'; // Key for indexedDB
    const dbName = 'PlotCache';
    const storeName = 'plots';

    // IndexedDB helper functions
    function openDatabase() {
        return new Promise((resolve, reject) => {
            const request = indexedDB.open(dbName, 1);
            request.onupgradeneeded = function () {
                const db = request.result;
                if (!db.objectStoreNames.contains(storeName)) {
                    db.createObjectStore(storeName, { keyPath: 'key' });
                }
            };
            request.onsuccess = function () {
                resolve(request.result);
            };
            request.onerror = function () {
                reject(request.error);
            };
        });
    }

    function savePlotToDB(key, plotHtml) {
        return openDatabase().then(db => {
            return new Promise((resolve, reject) => {
                const tx = db.transaction(storeName, 'readwrite');
                const store = tx.objectStore(storeName);
                store.put({ key: key, plot: plotHtml });
                tx.oncomplete = () => resolve();
                tx.onerror = () => reject(tx.error);
            });
        });
    }

    function loadPlotFromDB(key) {
        return openDatabase().then(db => {
            return new Promise((resolve, reject) => {
                const tx = db.transaction(storeName, 'readonly');
                const store = tx.objectStore(storeName);
                const request = store.get(key);
                request.onsuccess = () => resolve(request.result?.plot || null);
                request.onerror = () => reject(request.error);
            });
        });
    }

    // Load the last plot from indexedDB on page load
    loadPlotFromDB(plotKey)
        .then(cachedPlot => {
            if (cachedPlot) {
                $('#plotArea').html(cachedPlot);
            } else {
                fetchLastPlot();
            }
        })
        .catch(error => console.error('Error loading plot from DB:', error));

    // Function to fetch the last plot from the server
    function fetchLastPlot() {
        $('#loading-overlay').show(); // Show spinner
        $.ajax({
            url: '/get_last_plot',
            method: 'GET',
            success: function (response) {
                const plotHtml = response.plot;
                $('#plotArea').html(plotHtml); // Display plot
                savePlotToDB(plotKey, plotHtml).catch(err =>
                    console.error('Error saving plot to DB:', err)
                );
            },
            error: function (xhr, status, error) {
                console.error('Error fetching the last plot:', error);
                $('#plotArea').html('<p>Error loading plot.</p>');
            },
            complete: function () {
                $('#loading-overlay').hide(); // Hide spinner
            }
        });
    }

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

    // Function to fetch and display a new plot
    function fetchPlot(file) {
        $('#loading-overlay').show(); // Show spinner
        $.ajax({
            url: '/plot',
            method: 'POST',
            data: { file: file },
            success: function (response) {
                const plotHtml = response.plot;
                $('#plotArea').html(plotHtml); // Display plot
                savePlotToDB(plotKey, plotHtml).catch(err =>
                    console.error('Error saving plot to DB:', err)
                );
            },
            error: function (xhr, status, error) {
                console.error('Error fetching plot:', error);
                alert('Failed to load plot.');
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
