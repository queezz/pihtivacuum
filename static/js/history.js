/**
 * History timeline — load events, render list, apply state on click.
 * No SVG reinitialization; only updates classes/colors via applyState().
 */
(function () {
    let events = [];
    let selectedIdx = null;

    function loadEvents() {
        return fetch('/history/events')
            .then(r => r.json())
            .then(data => {
                events = data;
                renderList();
            })
            .catch(err => console.error('Error loading history events:', err));
    }

    function renderList() {
        const ul = document.getElementById('history-events');
        if (!ul) return;
        ul.innerHTML = '';
        [...events].reverse().forEach((e, displayIdx) => {
            const idx = events.length - 1 - displayIdx;
            const li = document.createElement('li');
            li.className = 'history-event' + (selectedIdx === idx ? ' selected' : '');
            li.dataset.idx = idx;
            li.innerHTML = `
                <span class="history-ts">${escapeHtml(e.ts)}</span>
                <span class="history-id">${escapeHtml(e.id)}</span>
                <span class="history-status ${e.state ? 'active' : 'inactive'}">${e.state ? 'active' : 'inactive'}</span>
                <span class="history-user">${escapeHtml(e.user)}</span>
            `;
            li.addEventListener('click', () => selectEvent(idx));
            ul.appendChild(li);
        });
    }

    function escapeHtml(s) {
        const div = document.createElement('div');
        div.textContent = s;
        return div.innerHTML;
    }

    function selectEvent(idx) {
        if (idx < 0 || idx >= events.length) return;
        selectedIdx = idx;
        renderList();

        fetch(`/history/state/${idx}`)
            .then(r => r.json())
            .then(data => {
                const state = data.state;
                if (!state || typeof window.applyState !== 'function') return;
                const stateForApply = {};
                for (const [id, val] of Object.entries(state)) {
                    stateForApply[id] = val ? 'active' : 'inactive';
                }
                window.applyState(stateForApply);
            })
            .catch(err => console.error('Error fetching history state:', err));
    }

    document.addEventListener('DOMContentLoaded', loadEvents);
})();
