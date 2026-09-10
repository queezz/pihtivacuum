const assert = require('node:assert/strict');
const {readFileSync} = require('node:fs');
const {join} = require('node:path');
const vm = require('node:vm');
const test = require('node:test');

const source = readFileSync(join(__dirname, '../src/pihti/static/js/diagram.js'), 'utf8');
const paintCode = source.slice(source.indexOf('    let predictionRequest = 0;'),
    source.indexOf('    /* -- practice:'));

function fixture() {
    const writes = [], paints = [], requests = [];
    const message = {textContent: ''};
    const container = {dataset: {paint: 'loading'}, setAttribute() {}, querySelector: () => message};
    const elements = Object.fromEntries(['valve', 'gauge'].map(id => [id, {
        style: new Proxy({}, {set(object, key, value) { writes.push([id, key, value]); object[key] = value; return true; }})
    }]));
    const context = vm.createContext({
        elementsConfig: [{id: 'valve', colors: {active: 'green'}}, {id: 'gauge', colors: {active: 'amber'}}],
        plumbing: {}, predictionPending: false, vacuumState: {}, lastPrediction: null,
        window: {historyMode: true}, console: {error() {}},
        document: {getElementById: id => id === 'diagram-container' ? container : elements[id]},
        normalizedStatus: value => value,
        fetch: () => new Promise(resolve => requests.push(resolve)),
        paintPrediction: result => { paints.push(result); context.lastPrediction = result; },
    });
    vm.runInContext(paintCode, context);
    return {context, writes, paints, requests, container, message};
}
const prediction = {elements: {valve: {fill: 'blue'}}};

test('first paint waits for prediction and never assigns the legacy valve green', async () => {
    const f = fixture();
    const work = f.context.applyState({valve: 'active', gauge: 'active'}, 'first');
    assert.deepEqual(f.writes, []);
    assert.equal(f.container.dataset.paint, 'loading');
    f.requests[0]({ok: true, json: async () => prediction});
    await work;
    assert.deepEqual(f.writes, [['gauge', 'fill', 'amber']]);
    assert.deepEqual(f.paints, [prediction]);
    assert.equal(f.container.dataset.paint, 'ready');
});

test('a slow older History response cannot repaint the newer selected moment', async () => {
    const f = fixture();
    const first = f.context.applyState({gauge: 'inactive'}, 'first');
    const second = f.context.applyState({gauge: 'active'}, 'second');
    f.requests[1]({ok: true, json: async () => prediction});
    await second;
    f.requests[0]({ok: true, json: async () => ({elements: {valve: {fill: 'red'}}})});
    await first;
    assert.deepEqual(f.paints, [prediction]);
    assert.deepEqual(f.writes, [['gauge', 'fill', 'amber']]);
});

test('failed initial prediction stays unpainted and names the load failure', async () => {
    const f = fixture();
    const work = f.context.applyState({valve: 'active'}, 'first');
    f.requests[0]({ok: false});
    await work;
    assert.deepEqual(f.writes, []);
    assert.deepEqual(f.paints, []);
    assert.equal(f.container.dataset.paint, 'error');
    assert.match(f.message.textContent, /could not be loaded/);
});

test('failed History selection cannot leave the previous moment posing as the selected one', async () => {
    const f = fixture();
    f.context.applyState({gauge: 'active'}, 'first', prediction);
    const work = f.context.applyState({gauge: 'inactive'}, 'second');
    f.requests[0]({ok: false});
    await work;
    assert.equal(f.container.dataset.paint, 'error');
    assert.deepEqual(f.paints, [prediction]);
});
