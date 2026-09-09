const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const context = {document: {readyState: 'loading', addEventListener() {}}};
vm.createContext(context);
vm.runInContext(fs.readFileSync(path.join(__dirname, '../src/pihti/static/js/history.js'), 'utf8'), context);
const event = (ts, user = 'Operator A', extra = {}) => ({ts, user, ...extra});
const groups = (events) => JSON.parse(JSON.stringify(context.pihtiGroupHistoryEvents(events.map((event, idx) => ({event, idx}))).map(g => g.map(r => r.idx))));
test('groups up to sixty seconds, preserves every original index', () => {
    assert.deepEqual(groups([event('2026-09-10 00:00:00'), event('2026-09-10 00:01:00'), event('2026-09-10 00:02:01')]), [[0, 1], [2]]);
    assert.deepEqual(groups([]), []);
});
test('operator, date, unknown attribution and invalid time are boundaries', () => {
    assert.deepEqual(groups([event('2026-09-10 23:59:59'), event('2026-09-11 00:00:00'), event('2026-09-11 00:00:01', 'Operator B'), event('2026-09-11 00:00:02', ''), event('2026-09-11 00:00:03', ''), event('invalid')]), [[0], [1], [2], [3], [4], [5]]);
});
test('practice saves remain standalone, even a one-press saved sequence', () => {
    assert.deepEqual(groups([event('2026-09-10 00:00:00'), event('2026-09-10 00:00:01', 'Operator A', {note:'practice sequence, 1 press'}), event('2026-09-10 00:00:02'), event('2026-09-10 00:00:03', 'Operator A', {changes:[{}, {}]}), event('2026-09-10 00:00:04')]), [[0], [1], [2], [3], [4]]);
});
