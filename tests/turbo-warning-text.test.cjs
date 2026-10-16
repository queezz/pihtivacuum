const assert = require('node:assert/strict');
const {readFileSync} = require('node:fs');
const {join} = require('node:path');
const vm = require('node:vm');
const test = require('node:test');

// The banner's turbo sentence and the vessel readout's state word, run as the
// page runs them (owner, 2026-10-07: metered process gas is the designed mode).
const source = readFileSync(join(__dirname, '../src/pihti/static/js/diagram.js'), 'utf8');
const between = (start, end) => source.slice(source.indexOf(start), source.indexOf(end));
const code = [
    between('    function warningText(', '    async function toggleElementStatus('),
    between('    function inSentence(', '    /* What the prediction finds each vessel'),
    between('    function stateWord(', '    function stateColour('),
].join('\n');

function page() {
    const context = vm.createContext({
        displayName: id => ({TMPU: 'Plasma turbo pump (TMPU)', TMPD: 'QMS turbo pump (TMPD)'})[id] || id,
        plumbing: {states: [{id: 'gas', label: 'Gas'}, {id: 'upstream-high-vacuum', label: 'High vacuum, plasma side'}]},
    });
    vm.runInContext(code, context);
    return context;
}

const turbo = extra => ({kind: 'turbo', id: 'TMPU', volume: 'plasma-turbo-line', state: 'gas', level: 1, ...extra});

test('gas that skipped every meter is named unmetered, held gas unroughed', () => {
    const {warningText} = page();
    assert.match(warningText([turbo({unmetered: true})]), /: unmetered gas reaches the plasma turbo pump \(TMPU\), which is marked running\./);
    assert.match(warningText([turbo()]), /: unroughed gas reaches the plasma turbo pump \(TMPU\)/);
    assert.match(warningText([turbo({state: 'air', level: 2})]), /: air reaches the plasma turbo pump/);
    const both = warningText([turbo({state: 'air', level: 2}), {...turbo({unmetered: true}), id: 'TMPD'}]);
    assert.match(both, /: air or unmetered gas reaches the plasma turbo pump \(TMPU\) and QMS turbo pump \(TMPD\), which are marked running\./);
});

test('metered process gas reads as an operating state in the vessel readout', () => {
    const {connectionStateWord} = page();
    assert.equal(connectionStateWord({state: 'gas', metered_only: true}), 'gas · metered');
    assert.equal(connectionStateWord({state: 'gas', metered_only: false}), 'gas');
    assert.equal(connectionStateWord({state: 'upstream-high-vacuum', slow_route_only: true}), 'high vacuum · slow route');
});
