const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const code = fs.readFileSync('src/pihti/static/js/plot-workspace.js', 'utf8');
function node() {
    return {children: [], clientWidth: 700, textContent: '', handlers: {},
        append(...items) { for (const item of items) { item.remove(); item.parent = this; this.children.push(item); } },
        remove() { if (this.parent) { this.parent.children.splice(this.parent.children.indexOf(this), 1); this.parent = null; } },
        insertBefore(item, next) { item.remove(); item.parent = this; const i = this.children.indexOf(next); this.children.splice(i < 0 ? this.children.length : i, 0, item); },
        get firstChild() { return this.children[0]; },
        get nextSibling() { return this.parent?.children[this.parent.children.indexOf(this) + 1]; },
        querySelector(selector) { return this.children.find(c => '.' + c.className === selector); },
        setAttribute() {}, getBoundingClientRect() { return {height: 400}; },
        getContext() { return {measureText: t => ({width: t.length * 6})}; },
        on(name, callback) { this.handlers[name] = callback; }, click() {}};
}
async function workspace(file = 'cu_test.csv', storage = new Map()) {
    const root = node(), messages = [], graphs = new Set(), blobs = [];
    const sample = {file, series: [
        {id: 'cu:Bu_c', column: 'Bu_c', label: 'Baratron', unit: 'Torr', group: 'Pressure', source: 'cu', x: ['2026-09-15T12:00:00','2026-09-15T12:00:01','2026-09-15T12:00:02'], y: [-0.0003, 0.0007, null]},
        {id: 'cu:MFC1_c', column: 'MFC1_c', label: 'MFC', unit: 'V', group: 'Signals', source: 'cu', x: ['2026-09-15T12:00:00'], y: [2], default_visible: false},
        {id: 'cu:set', column: 'set', label: 'Setpoint', unit: 'V', group: 'Signals', source: 'cu', x: ['2026-09-15T12:00:00'], y: [3], default_visible: false}
    ]};
    let listener;
    const parent = {postMessage: m => messages.push(m)};
    const window = {parent, location: {origin: 'http://test'}, addEventListener: (_, cb) => { listener = cb; }};
    const draw = async (plot, data, layout) => { plot.data = data; plot.layout = layout; graphs.add(plot); };
    const Plotly = {newPlot: draw, react: draw, purge: plot => graphs.delete(plot), relayout: async () => {}};
    window.Plotly = Plotly;
    vm.runInNewContext(code, {window, Plotly, console, document: {getElementById: id => id === 'charts' ? root : {textContent: JSON.stringify(sample)}, createElement: node}, localStorage: {getItem: k => storage.get(k), setItem: (k,v) => storage.set(k,v)}, Blob, URL: {createObjectURL: blob => {blobs.push(blob); return 'blob:test';}, revokeObjectURL() {}}, setTimeout() {}, clearTimeout() {}});
    const settle = () => new Promise(resolve => setImmediate(resolve));
    await settle();
    return {sample, graphs, blobs, messages, storage, async command(action, values = {}) { listener({origin: 'http://test', source: parent, data: {type: 'pihti-plot-command', action, ...values}}); await settle(); }, latest: () => messages.at(-1), trace: id => [...graphs].flatMap(p => p.data).find(t => t.uid === id)};
}
test('manual Baratron correction preserves samples, gaps, export and per-recording zero', async () => {
    const w = await workspace();
    await w.command('scale', {panel:'panel-0', value:'linear'});
    assert.equal(w.trace('series-0').y[0], -0.0003);
    await w.command('zero', {series:'cu:Bu_c', offset:-0.0003});
    assert.equal(w.trace('series-0').y[0], 0);
    assert.equal(w.trace('series-0').y[1], 0.001);
    assert.equal(w.trace('series-0').y[2], null);
    assert.equal(w.sample.series[0].y[0], -0.0003);
    assert.match(w.trace('series-0').name, /zero corrected/);
    await w.command('export-curves');
    const csv = await w.blobs.at(-1).text();
    assert.match(csv, /"-0.0003","-0.0003","0"\r\n/);
    assert.match(csv, /"0.0007","-0.0003","0.001"\r\n/);
    assert.match(csv, /"Torr",,"-0.0003",\r\n/);
    const same = await workspace('cu_test.csv', w.storage);
    assert.equal(same.latest().series[0].zero_offset, -0.0003);
    const other = await workspace('cu_other.csv', w.storage);
    assert.equal(other.latest().series[0].zero_applied, false);
    await w.command('scale', {panel:'panel-0', value:'log'});
    assert.equal(w.trace('series-0').y[0], null);
    await w.command('reset-zero', {series:'cu:Bu_c'});
    assert.equal(w.latest().series[0].zero_applied, false);
});
test('pressure, MFC signal and setpoint share a chart with independent unit axes', async () => {
    const w = await workspace();
    await w.command('compare', {series:['cu:Bu_c','cu:MFC1_c','cu:set']});
    assert.equal(w.graphs.size, 1);
    const plot = [...w.graphs][0];
    assert.equal(plot.layout.yaxis.type, 'log');
    assert.equal(plot.layout.yaxis2.type, 'linear');
    assert.equal(plot.data[0].yaxis, 'y');
    assert.equal(plot.data[1].yaxis, 'y2');
    assert.equal(plot.data[2].yaxis, 'y2');
    assert.ok(plot.data.every(t => /^series-\d+$/.test(t.uid)));
    await w.command('scale', {panel:w.latest().panels[0].id, axis:'right', value:'log'});
    assert.equal([...w.graphs][0].layout.yaxis2.type, 'log');
});

