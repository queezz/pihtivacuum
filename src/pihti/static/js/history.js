/**
 * History timeline — load events, render list, apply state on click.
 * Calendar activity panel: jump to day, month navigation.
 */
(function () {
    let events = [];
    let selectedIdx = null;
    let selectedDate = null;
    let currentMonth = null;
    let dailyActivity = {};

    function todayStr() {
        const d = new Date();
        return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
    }

    function loadEvents() {
        return fetch('/history/events')
            .then(r => r.json())
            .then(data => {
                events = data;
                dailyActivity = computeDailyActivity(events);
                setDefaultMonthAndDate();
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

    function setDefaultMonthAndDate() {
        if (events.length === 0) {
            currentMonth = new Date();
            selectedDate = todayStr();
            return;
        }
        const lastTs = events[events.length - 1].ts;
        const d = new Date(lastTs);
        currentMonth = new Date(d.getFullYear(), d.getMonth(), 1);
        selectedDate = (lastTs || '').split(' ')[0] || todayStr();
    }

    function renderCalendar() {
        const grid = document.getElementById('calendar-grid');
        const label = document.getElementById('calendar-month-label');
        if (!grid || !label) return;

        const year = currentMonth.getFullYear();
        const month = currentMonth.getMonth();
        label.textContent = currentMonth.toLocaleDateString(undefined, { month: 'long', year: 'numeric' });

        const firstDay = new Date(year, month, 1);
        const startPad = firstDay.getDay();
        const daysInMonth = new Date(year, month + 1, 0).getDate();
        const maxCount = Math.max(1, ...Object.values(dailyActivity));

        const cells = [];
        ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'].forEach(d => cells.push({ type: 'header', text: d }));
        for (let i = 0; i < startPad; i++) cells.push({ type: 'outside' });
        for (let d = 1; d <= daysInMonth; d++) {
            const dateStr = `${year}-${String(month + 1).padStart(2, '0')}-${String(d).padStart(2, '0')}`;
            cells.push({ type: 'day', date: dateStr, day: d, count: dailyActivity[dateStr] || 0 });
        }
        const padEnd = Math.max(0, 42 - (cells.length - 7));
        for (let i = 0; i < padEnd; i++) cells.push({ type: 'outside' });

        grid.innerHTML = '';
        cells.forEach(c => {
            const cell = document.createElement('div');
            if (c.type === 'header') {
                cell.className = 'calendar-cell calendar-header';
                cell.textContent = c.text;
            } else if (c.type === 'outside') {
                cell.className = 'calendar-cell calendar-outside';
            } else {
                cell.className = 'calendar-cell calendar-day' + (selectedDate === c.date ? ' calendar-selected' : '');
                cell.dataset.date = c.date;
                cell.textContent = c.day;
                if (c.count > 0) {
                    const intensity = Math.min(1, c.count / maxCount);
                    cell.style.backgroundColor = `rgba(0, 123, 255, ${0.15 + 0.6 * intensity})`;
                    cell.title = `${c.date}: ${c.count} event(s)`;
                }
                cell.addEventListener('click', () => selectDate(c.date));
            }
            grid.appendChild(cell);
        });
    }

    function selectDate(dateStr) {
        selectedDate = dateStr;
        renderCalendar();
        renderList();
    }

    function goToToday() {
        selectedDate = todayStr();
        const now = new Date();
        currentMonth = new Date(now.getFullYear(), now.getMonth(), 1);
        renderCalendar();
        renderList();
    }

    function attachCalendarListeners() {
        document.getElementById('calendar-prev')?.addEventListener('click', () => {
            currentMonth = new Date(currentMonth.getFullYear(), currentMonth.getMonth() - 1, 1);
            renderCalendar();
        });
        document.getElementById('calendar-next')?.addEventListener('click', () => {
            currentMonth = new Date(currentMonth.getFullYear(), currentMonth.getMonth() + 1, 1);
            renderCalendar();
        });
        document.getElementById('calendar-today')?.addEventListener('click', goToToday);
        document.getElementById('calendar-toggle')?.addEventListener('click', () => {
            const wrapper = document.getElementById('calendar-wrapper');
            const btn = document.getElementById('calendar-toggle');
            if (wrapper && btn) {
                wrapper.classList.toggle('collapsed');
                btn.textContent = wrapper.classList.contains('collapsed') ? '\u25B6' : '\u25BC';
                btn.setAttribute('aria-label', wrapper.classList.contains('collapsed') ? 'Expand calendar' : 'Collapse calendar');
            }
        });
    }

    function renderList() {
        const ul = document.getElementById('history-events');
        const noEvents = document.getElementById('history-no-events');
        if (!ul || !noEvents) return;

        const filtered = events.filter(e => ((e.ts || '').split(' ')[0]) === selectedDate);
        ul.innerHTML = '';
        noEvents.style.display = 'none';

        if (filtered.length === 0) {
            noEvents.style.display = 'block';
            return;
        }
        [...filtered].reverse().forEach((e, displayIdx) => {
            const idx = events.indexOf(e);
            const li = document.createElement('li');
            li.className = 'history-event' + (selectedIdx === idx ? ' selected' : '');
            li.dataset.idx = idx;
            li.dataset.date = selectedDate;
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
