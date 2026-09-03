document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('fileForm');
    const dropdown = document.getElementById('fileDropdown');
    const downloadButton = document.getElementById('downloadBtn');
    const plotArea = document.getElementById('plotArea');
    const loadingOverlay = document.getElementById('loading-overlay');

    function setLoading(isLoading) {
        if (loadingOverlay) loadingOverlay.style.display = isLoading ? 'flex' : 'none';
    }

    function installPlotHtml(html) {
        if (!plotArea) return;
        plotArea.innerHTML = html;
        plotArea.querySelectorAll('script').forEach(oldScript => {
            const script = document.createElement('script');
            for (const attribute of oldScript.attributes) {
                script.setAttribute(attribute.name, attribute.value);
            }
            script.textContent = oldScript.textContent;
            oldScript.replaceWith(script);
        });
    }

    async function fetchLastPlot() {
        setLoading(true);
        try {
            const response = await fetch('/get_last_plot');
            const payload = await response.json();
            if (response.ok || response.status === 404) {
                installPlotHtml(payload.plot || '<p>No plot available. Please generate one.</p>');
                return;
            }
            throw new Error(payload.error || `Request failed (${response.status})`);
        } catch (error) {
            console.error('Unable to load the last plot:', error);
            installPlotHtml('<p>The last plot could not be loaded.</p>');
        } finally {
            setLoading(false);
        }
    }

    async function fetchPlot(file) {
        setLoading(true);
        try {
            const body = new URLSearchParams({file});
            const response = await fetch('/plot', {method: 'POST', body});
            const payload = await response.json();
            if (!response.ok) throw new Error(payload.error || `Request failed (${response.status})`);
            installPlotHtml(payload.plot);
        } catch (error) {
            console.error('Unable to generate the plot:', error);
            alert('Failed to generate the selected plot.');
        } finally {
            setLoading(false);
        }
    }

    if (dropdown) {
        const lastFile = localStorage.getItem('lastFile');
        if (lastFile && Array.from(dropdown.options).some(option => option.value === lastFile)) {
            dropdown.value = lastFile;
        }
    }

    form?.addEventListener('submit', event => {
        event.preventDefault();
        const selectedFile = dropdown?.value;
        if (!selectedFile) return;
        localStorage.setItem('lastFile', selectedFile);
        fetchPlot(selectedFile);
    });

    downloadButton?.addEventListener('click', () => {
        const selectedFile = dropdown?.value;
        if (!selectedFile) return;
        window.location.href = `/download_controlunit_csv?file=${encodeURIComponent(selectedFile)}`;
    });

    fetchLastPlot();
});
