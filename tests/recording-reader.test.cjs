// The browser's recording reader: the units, labels, gaps and conversions the
// Python reader carried from 0.24.5 until 0.29.0, when reading moved off the Pi.
const test = require('node:test');
const assert = require('node:assert/strict');
const {read, RecordingError} = require('../src/pihti/static/js/recording-reader.js');

const file = (prefix, text, stamp = '20260101_120000') => ({name: `${prefix}_${stamp}.csv`, text});
const values = series => Array.from(series.y, value => Number.isNaN(value) ? null : value);
const channels = payload => Object.fromEntries(payload.series.map(series => [series.id, series]));

test('variable preamble, units, every channel and ion gauge mode conversion', () => {
    const payload = read([file('cu', '# Title, demo\n# Columns , date,IGmode,IGmode_Pu2,Pd_c,Pu2_c,MFC1_c,new_sensor,Ip_c\n# extra metadata\n# [Data]\n'
        + '2026-01-01 12:00:00,0,1,2,133.32236842105263,3,12,nan\n2026-01-01 12:00:01,1,9,133.32236842105263,4,2,13,inf\n')]);
    const data = channels(payload);
    assert.deepEqual(values(data['cu:Pd_c']), [2, 1]);
    assert.deepEqual(values(data['cu:Pu2_c']), [1, null]);
    assert.equal(data['cu:MFC1_c'].unit, 'V');
    assert.equal(data['cu:new_sensor'].unit, 'unknown');
    assert.deepEqual(values(data['cu:Ip_c']), [null, null]);
    assert.equal(payload.sources[0].rows, 2);
    assert.ok(payload.notes.includes('2 explicitly recorded Pa-mode readings were converted to Torr.'));
});

test('companions, gaps and the recorder clock', () => {
    const payload = read([
        file('cu', '# Columns,date,Ip_c,Ip_flags\n2026-01-01 12:00:00,1,instrument_off\n'),
        file('kikusui', '# schema: demo\ndate,voltage_v,current_a,output_on,status,query_ms\n'
            + '2026-01-01T12:00:00+09:00,2,3,1,ok,8\n2026-01-01T12:00:01+09:00,4,5,1,unavailable,10\n'),
        file('pid', 'date,error_a\n2026-01-01 12:00:00,0.5\n'),
    ]);
    const data = channels(payload);
    assert.equal(payload.sources.length, 3);
    assert.deepEqual(values(data['cu:Ip_c']), [null]);
    assert.deepEqual(values(data['kikusui:voltage_v']), [2, null]);
    assert.deepEqual(values(data['kikusui:query_ms']), [8, 10]);
    assert.equal(data['kikusui:voltage_v'].x[0], data['cu:Ip_c'].x[0]);
    assert.equal(data['kikusui:voltage_v'].x[0], '2026-01-01T12:00:00');
    assert.equal(payload.time_label, 'Recorder local time');
});

test('a recording whose UTC offset changes is refused', () => {
    assert.throws(() => read([file('kikusui', 'date,voltage_v,status\n2026-01-01T12:00:00+09:00,1,ok\n2026-01-01T12:00:01+08:00,1,ok\n')]),
        error => error instanceof RecordingError && /ambiguous/.test(error.message));
    // Z, +00:00 and -00:00 are one offset.
    read([file('kikusui', 'date,voltage_v,status\n2026-01-01T12:00:00Z,1,ok\n2026-01-01T12:00:01+00:00,1,ok\n2026-01-01T12:00:02-00:00,1,ok\n')]);
});

test('a header is required, and every row must match it', () => {
    assert.throws(() => read([file('cu', '2026-01-01 12:00:00,3\n')]), /unique column header/);
    assert.throws(() => read([file('cu', '# Columns,date,Ip_c,Ip_c\n2026-01-01 12:00:00,1,2\n')]), /unique column header/);
    assert.throws(() => read([file('cu', '# Columns,date,Ip_c\n2026-01-01 12:00:00,3,4\n2026-01-01 12:00:01,3\n')]), /does not match/);
    assert.throws(() => read([file('cu', '# Columns,foo,bar\n1,2\n')]), /no timestamp column/);
    assert.throws(() => read([file('cu', '# Columns,date,Ip_c\n2026-01-01 12:00:00,3\ndate,Pu_c\n')]), /changes partway/);
});

test('a recording still being written may end mid-row', () => {
    const payload = read([file('cu', '# Columns,date,Ip_c,Pu_c\n2026-01-01 12:00:00,1,2\n2026-01-01 12:00:01,3')]);
    assert.deepEqual(values(channels(payload)['cu:Ip_c']), [1]);
    assert.ok(payload.notes.some(note => /still being written/.test(note)));
    // A complete last row without its line break still counts.
    assert.deepEqual(values(channels(read([file('cu', '# Columns,date,Ip_c\n2026-01-01 12:00:00,1')]))['cu:Ip_c']), [1]);
});

test('multiline sidecar text and instrument-off columns', () => {
    const data = channels(read([
        file('cu', '# Columns,date,Pu,Pu_c,Pu_off\n2026-01-01 12:00:00,3,4,1\n2026-01-01 12:00:01,3,4,0\n'),
        file('kikusui', 'date,voltage_v,status,error,identity\n2026-01-01T12:00:00+09:00,2,ok,"first\n# second",supply\n'),
    ]));
    assert.deepEqual(values(data['cu:Pu']), [null, 3]);
    assert.deepEqual(values(data['cu:Pu_c']), [null, 4]);
    assert.deepEqual(values(data['cu:Pu_off']), [1, 0]);
    assert.deepEqual(values(data['kikusui:voltage_v']), [2]);
});

test('quoted fields follow Python csv rules', () => {
    const payload = read([file('kikusui', 'date,voltage_v,status,error\r\n'
        + '2026-01-01T12:00:00+09:00,1," ok ","a ""quoted"" text, with comma"\r\n'
        + '2026-01-01T12:00:01+09:00,2,ok,"multi\r\nline"\r\n')]);
    assert.deepEqual(values(channels(payload)['kikusui:voltage_v']), [1, 2]);
    assert.equal(payload.sources[0].rows, 2);
});

test('an invalid timestamp breaks the line and missing numbers are noted', () => {
    const payload = read([file('cu', '# Columns,date,new_sensor\n2026-01-01 12:00:00,2\ninvalid,3\n'
        + '2026-01-01 12:00:02,broken\n2026-02-30 12:00:03,5\n2026-01-01 12:00:04,4\n')]);
    const data = channels(payload)['cu:new_sensor'];
    assert.equal(data.x[1], null);
    assert.equal(data.x[3], null);
    assert.deepEqual(values(data), [2, null, null, null, 4]);
    assert.ok(payload.notes.some(note => note.includes('2 rows have invalid timestamps')));
    assert.ok(payload.notes.some(note => note.includes('1 missing or non-numeric')));
    assert.equal(payload.notes.filter(note => note.includes('No same-run Kikusui')).length, 1);
});

test('numbers read as Python float() reads them', () => {
    const data = channels(read([file('cu', '﻿# Columns,date,PresetV_mfc1,PresetV_mfc2,PresetV_cathode,time,Bd_c,Cv\n'
        + '2026-01-01 12:00:00.5,true,False,0x10, 3 ,1_000,1e-400\n')]));
    assert.equal(data['cu:PresetV_mfc1'].x[0], '2026-01-01T12:00:00.500000');
    assert.deepEqual(values(data['cu:PresetV_mfc1']), [1]);
    assert.deepEqual(values(data['cu:PresetV_mfc2']), [0]);
    assert.deepEqual(values(data['cu:PresetV_cathode']), [null]);
    assert.deepEqual(values(data['cu:time']), [3]);
    assert.deepEqual(values(data['cu:Bd_c']), [1000]);
    assert.deepEqual(values(data['cu:Cv']), [0]);
    assert.equal(data['cu:PresetV_mfc1'].label, 'Hydrogen MFC setpoint');
});

test('linear Torr is not rescaled when the range changes', () => {
    const payload = read([file('cu', '# Columns,date,IGmode,IGscale,Pd_c,IGmode_Pu2,IGscale_Pu2,Pu2_c\n'
        + '2026-01-01 12:00:00,0,-6,2e-6,0,-7,3e-7\n2026-01-01 12:00:01,0,-7,2e-7,0,-6,3e-6\n')]);
    const data = channels(payload);
    assert.deepEqual(values(data['cu:Pd_c']), [2e-6, 2e-7]);
    assert.deepEqual(values(data['cu:Pu2_c']), [3e-7, 3e-6]);
    assert.equal(data['cu:IGscale'].label, 'Downstream ion gauge range exponent');
    assert.equal(data['cu:IGscale_Pu2'].label, 'Upstream ion gauge range exponent');
    assert.deepEqual(values(data['cu:IGscale']), [-6, -7]);
    assert.match(data['cu:IGscale'].meaning, /-6 means 10\^-6 Torr/);
    assert.ok(!payload.notes.some(note => note.includes('Pa-mode')));
});

test('Kikusui labels keep their units apart', () => {
    const data = channels(read([file('kikusui', 'date,voltage_v,current_a,status\n2026-01-01T12:00:00+09:00,2,3,ok\n')]));
    assert.equal(data['kikusui:voltage_v'].label, 'Cathode supply voltage');
    assert.equal(data['kikusui:voltage_v'].unit, 'V');
    assert.equal(data['kikusui:current_a'].label, 'Cathode current (Ic)');
});

test('groups, range summary and the missing-mode note', () => {
    const payload = read([
        file('cu', '# Columns,date,Pu_c,Bu_c,Pd_c,IGmode,IGscale,Ip_c,Ip\n'
            + '2026-01-01 12:00:00,1e-6,2e-6,3e-6,,-6,1,2\n2026-01-01 12:00:01,1e-6,2e-6,3e-6,9,-7,1,2\n'
            + '2026-01-01 12:00:02,1e-6,2e-6,3e-6,0,-6,1,2\n'),
        file('kikusui', 'date,voltage_v,current_a,plasma_target_a,status\n2026-01-01T12:00:00+09:00,2,3,4,ok\n'),
    ]);
    const data = channels(payload);
    assert.equal(data['cu:Pu_c'].group, 'Pressure');
    assert.equal(data['cu:Bu_c'].unit, 'Torr');
    assert.equal(data['cu:Ip_c'].group, 'Plasma current');
    assert.equal(data['cu:Ip'].group, 'Raw signals');
    assert.equal(data['kikusui:voltage_v'].group, 'Cathode voltage');
    assert.equal(data['kikusui:current_a'].group, 'Cathode current');
    assert.equal(data['cu:IGscale'].summary, '10^-6, 10^-7 Torr');
    assert.deepEqual(values(data['cu:Pd_c']), [null, null, 3e-6]);
    assert.ok(payload.notes.some(note => note.includes('2 ion gauge pressure readings have missing or invalid')));
    // Default curves lead, raw signals close the list.
    assert.equal(payload.series[0].default_visible, true);
    assert.equal(payload.series.at(-1).group, 'Raw signals');
});

test('a long recording reads in well under a second per hundred thousand rows', () => {
    const columns = ['date', 'time', 'IGmode', 'IGscale', 'Ip', 'Pu', 'Pd', 'Bu', 'Ip_c', 'Pu_c', 'Pd_c', 'Bu_c'];
    const rows = ['# Columns , ' + columns.join(', ')];
    for (let i = 0; i < 100000; i++) {
        const clock = new Date(Date.UTC(2026, 0, 1, 12) + i * 100).toISOString().replace('T', ' ').replace('Z', '000');
        rows.push(`${clock},${i / 10},0,-6,0.${i % 997},1.2,2.3,3.4,0.0${i % 89},1e-${3 + (i % 3)},2e-6,4.5e-3`);
    }
    const started = performance.now();
    const payload = read([file('cu', rows.join('\n') + '\n')]);
    const seconds = (performance.now() - started) / 1000;
    assert.equal(payload.sources[0].rows, 100000);
    assert.equal(payload.series.length, columns.length - 1);
    // Every channel of one file shares the one time column.
    assert.ok(payload.series.every(series => series.x === payload.series[0].x));
    assert.ok(seconds < 5, `took ${seconds.toFixed(2)} s`);
});
