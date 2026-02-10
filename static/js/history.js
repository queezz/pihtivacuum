/**
 * History timeline — load events, render list, apply state on click.
 * Calendar activity panel: jump to day, month navigation.
 */
(function () {
    let events = [];
    let selectedIdx = null;
    let currentMonth = null;
    let dailyActivity = {};

    function loadEvents() {
        return fetch('/history/events')
            .then(r => r.json())
            .then(data => {
                events = data;
                dailyActivity = computeDailyActivity(events);
                setDefaultMonth();
                renderCalendar();
                renderList();
                attachCalendarListeners();
            })
            .catch(err => console.error('Error loading history events:', err));
    }

    function computeDailyActivity(evts) {
        const byDate = {};
        evts.forEach(e => {
            const date = (e.ts || '').split(' ')[0];
            if (date) byDate[date] = (byDate[date] || 0) + 1;
        });
        return byDate;
    }

    function setDefaultMonth() {
        if (events.length === 0) {
            currentMonth = new Date();
            return;
        }
        const lastTs = events[events.length - 1].ts;
        const d = new Date(lastTs);
        currentMonth = new Date(d.getFullYear(), d.getMonth(), 1);
    }

    function renderCalendar() {
        const grid = document.getElementById('calendar-grid');
        const label = document.getElementById('calendar-month-label');
        if (!grid || !label) return;

        const year = currentMonth.getFullYear();
        const month = currentMonth.getMonth();
        label.textContent = currentMonth.toLocaleDateString(undefined, { month: 'long', year: 'numeric' });

        const firstDay = new Date(year, month, 1);
        const lastDay = new Date(year, month + 1, 0);
        const startPad = firstDay.getDay();
        const daysInMonth = lastDay.getDate();

        const maxCount = Math.max(1, ...Object.values(dailyActivity));

        grid.innerHTML = '';
        const dayNames = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
        dayNames.forEach(d => {
            const h = document.createElement('div');
            h.className = 'calendar-cell calendar-header';
            h.textContent = d;
            grid.appendChild(h);
        });

        for (let i = 0; i < startPad; i++) {
            const cell = document.createElement('div');
            cell.className = 'calendar-cell calendar-outside';
            grid.appendChild(cell);
        }

        for (let d = 1; d <= daysInMonth; d++) {
            const dateStr = `${year}-${String(month + 1).padStart(2, '0')}-${String(d).padStart(2, '0')}`;
            const count = dailyActivity[dateStr] || 0;
            const cell = document.createElement('div');
            cell.className = 'calendar-cell calendar-day';
            cell.dataset.date = dateStr;
            if (count > 0) {
                const intensity = Math.min(1, count / maxCount);
                cell.style.backgroundColor = `rgba(0, 123, 255, ${0.15 + 0.6 * intensity})`;
                cell.title = `${dateStr}: ${count} event(s)`;
            }
            cell.textContent = d;
            cell.addEventListener('click', () => jumpToDate(dateStr));
            grid.appendChild(cell);
        }
    }

    function jumpToDate(dateStr) {
        const ul = document.getElementById('history-events');
        if (!ul) return;
        const first = ul.querySelector(`li[data-date="${dateStr}"]`);
        if (first) first.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }

    function attachCalendarListeners() {
        document.getElementById('calendar-prev')?.addEventListener('click', () => {
            currentMonth.setMonth(currentMonth.getMonth() - 1);
            renderCalendar();
        });
        document.getElementById('calendar-next')?.addEventListener('click', () => {
            currentMonth.setMonth(currentMonth.getMonth() + 1);
            renderCalendar();
        });
    }

    function renderList() {
        const ul = document.getElementById('history-events');
        if (!ul) return;
        ul.innerHTML = '';
        [...events].reverse().forEach((e, displayIdx) => {
            const idx = events.length - 1 - displayIdx;
            const dateStr = (e.ts || '').split(' ')[0];
            const li = document.createElement('li');
            li.className = 'history-event' + (selectedIdx === idx ? ' selected' : '');
            li.dataset.idx = idx;
            li.dataset.date = dateStr || '';
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
