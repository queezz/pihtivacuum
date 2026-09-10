const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const source = fs.readFileSync(path.join(__dirname, '../src/pihti/static/js/history.js'), 'utf8');
const events = [
    {ts: '2026-09-09 12:00:00', id: 'valve', state: false, user: 'Example'},
    {ts: '2026-09-10 12:00:00', id: 'valve', state: true, user: 'Example'},
];

async function open({search = '', saved, rows = events, fail = false, storageThrows = false, cachedDiagram = false} = {}) {
    const nodes = new Map(), listeners = {};
    const element = () => ({
        children: [], textContent: '', hidden: false, value: '', dataset: {},
        classList: {toggle() {}}, setAttribute() {}, removeAttribute() {},
        addEventListener() {}, querySelector() { return null; }, querySelectorAll() { return []; },
        closest() { return null; }, append(...items) { this.children.push(...items); },
        replaceChildren(...items) { this.children = items; },
    });
    const get = id => { if (!nodes.has(id)) nodes.set(id, element()); return nodes.get(id); };
    let address, calendar, applied;
    const context = {
        URLSearchParams, console: {error() {}},
        document: {
            readyState: 'loading', createElement: element, getElementById: get,
            querySelector: get, addEventListener(name, fn) { listeners[name] = fn; },
        },
        localStorage: {
            getItem() { if (storageThrows) throw Error('unavailable'); return saved; },
            setItem(_, value) { if (storageThrows) throw Error('unavailable'); saved = value; },
        },
        window: {
            location: {search}, history: {replaceState(_, __, url) { address = url; }},
            pihtiCalendar: {render(value) { calendar = value; }},
            applyState(state, moment) { applied = {state, moment}; },
        },
        fetch: async url => ({ok: !fail, json: async () => url === '/history/events' ? rows : {valve: 'active'}}),
    };
    vm.runInNewContext(source, context);
    if (cachedDiagram) context.window.pihtiDiagramReady = true;
    await listeners.DOMContentLoaded();
    if (!cachedDiagram) listeners['pihti:diagram-ready']();
    return {get, address: () => address, applied: () => applied, selectDay: day => calendar.onSelect(day)};
}

test('History paints when cached diagram resources finish before its load listener', async () => {
    const page = await open({cachedDiagram: true});
    assert.equal(page.applied().moment, events[1].ts);
});

test('first visit selects latest; memory restores an exact older event; explicit link wins', async () => {
    assert.equal((await open()).applied().moment, events[1].ts);
    assert.equal((await open({saved: events[0].ts})).applied().moment, events[0].ts);
    assert.equal((await open({saved: events[0].ts, search: '?at=2026-09-10T12:00:00'})).applied().moment, events[1].ts);
});

test('missing or unavailable memory falls back to latest', async () => {
    assert.equal((await open({saved: 'removed timestamp'})).applied().moment, events[1].ts);
    assert.equal((await open({storageThrows: true})).applied().moment, events[1].ts);
});

test('day selection reconstructs its final state and carries it over an empty day', async () => {
    const page = await open();
    page.selectDay('2026-09-09');
    assert.equal(page.applied().state.valve, 'inactive');
    page.selectDay('2026-09-11');
    assert.equal(page.applied().moment, events[1].ts);
    const restored = await open({search: page.address().split('?')[1]});
    assert.equal(restored.get('timeline-label').textContent, 'Timeline · 2026-09-11');
    assert.equal(restored.applied().moment, events[1].ts);
});

test('before history, empty history and failed loads do not masquerade as a recorded diagram', async () => {
    for (const options of [{search: '?day=2026-09-08'}, {search: '?at=2026-09-09T11:00:00'}, {rows: []}, {fail: true}]) {
        const page = await open(options);
        assert.equal(page.get('diagram-container').hidden, true);
        assert.equal(page.applied(), undefined);
    }
    assert.match((await open({fail: true})).get('history-status').textContent, /could not be loaded/);
    assert.match((await open({rows: []})).get('history-status').textContent, /No recorded changes/);
});
