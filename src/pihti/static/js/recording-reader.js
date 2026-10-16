/* ControlUnit recordings are read here, in the reader's browser. The Pi only
 * sends the original files: parsing a long recording in Python, and sending
 * every channel its own copy of the time column, took the Pi minutes and a
 * hundred megabytes for a 39 MB file (queezz, 2026-10-16: "outsource the
 * plotting to the browser client. First fetch the data, then plot"). Units,
 * labels, gaps and conversions are the ones the Python reader decided from
 * 0.24.5 until then, unchanged; tests/recording-reader.test.cjs holds them.
 *
 * A channel's samples are a Float64Array in which NaN is a gap. The time
 * column stays the recorder's own wall clock as text, shared by every channel
 * of one file: a number would be shifted into the viewer's timezone by
 * Plotly, and the plot promises recorder local time. */
(function (scope) {
    "use strict";

    const LABELS = {
        Ip: "Plasma current", Pu: "Upstream Pfeiffer pressure",
        Pd: "Downstream ion gauge pressure", Pu2: "Upstream ion gauge pressure",
        Bu: "Upstream Baratron pressure", Bd: "Downstream Baratron pressure",
        MFC1: "Hydrogen MFC signal", MFC2: "Oxygen MFC signal",
        Ci: "Cathode ADC current signal", Cv: "Cathode ADC voltage signal",
    };
    const UNITS = {
        voltage_v: "V", current_a: "A", commanded_cathode_mv: "mV",
        plasma_target_a: "A", logger_elapsed_s: "s", query_ms: "ms",
        output_on: "0/1", time: "s", QMS_signal: "0/1",
        PresetV_mfc1: "V", PresetV_mfc2: "V", PresetV_cathode: "mV",
    };
    const DEFAULT_CHANNELS = new Set([
        "Ip_c", "Pu_c", "Pd_c", "Pu2_c", "Bu_c", "Bd_c", "voltage_v", "current_a",
    ]);
    const TELEMETRY_LABELS = {
        voltage_v: "Cathode supply voltage", current_a: "Cathode current (Ic)",
        commanded_cathode_mv: "Commanded cathode drive",
        plasma_target_a: "Plasma current target", output_on: "Supply output",
        query_ms: "Query duration", logger_elapsed_s: "Logger elapsed time",
    };
    const SETTING_LABELS = {
        PresetV_mfc1: "Hydrogen MFC setpoint",
        PresetV_mfc2: "Oxygen MFC setpoint",
        PresetV_cathode: "Commanded cathode drive",
        time: "ADC elapsed time",
        QMS_signal: "QMS trigger",
    };
    const PRESSURES = new Set(["Pu", "Pd", "Pu2", "Bu", "Bd"]);
    const PASCALS_PER_TORR = 133.32236842105263;
    // YYYY-MM-DD, any one separator, HH[:MM[:SS[.ffffff]]], then an offset:
    // what Python's datetime.fromisoformat accepted for these files.
    const STAMP = /^(\d{4})-(\d{2})-(\d{2})(?:.(\d{2})(?::(\d{2})(?::(\d{2})(?:[.,](\d{1,6}))?)?)?)?(?:([+-])(\d{2})(?::?(\d{2})(?::?(\d{2})(?:\.(\d{1,6}))?)?)?)?$/;

    const own = (table, key) => Object.prototype.hasOwnProperty.call(table, key);

    /* What is wrong with the file itself, said in a sentence for the reader;
     * anything else that throws is this code's fault, not the recording's. */
    class RecordingError extends Error {}

    function number(text) {
        const value = text.trim();
        if (!value) return NaN;
        const parsed = Number(value);
        if (Number.isFinite(parsed)) {
            // Number() also reads 0x1f, 0b1 and 0o7; a recording means none of them.
            const radix = value[0] === "0" ? value[1] : "";
            return radix && "xXbBoO".includes(radix) ? NaN : parsed;
        }
        const lower = value.toLowerCase();
        if (lower === "true") return 1;
        if (lower === "false") return 0;
        // Python's float() also reads digits grouped by underscores: 1_000.
        if (/^[+-]?(?=\.?\d)(?:\d+(?:_\d+)*)?(?:\.(?:\d+(?:_\d+)*)?)?(?:[eE][+-]?\d+(?:_\d+)*)?$/.test(value)) {
            const grouped = Number(value.replace(/_/g, ""));
            if (Number.isFinite(grouped)) return grouped;
        }
        return NaN;
    }

    const pad = (value, width) => String(value).padStart(width, "0");

    function daysIn(year, month) {
        return [31, year % 4 === 0 && (year % 100 !== 0 || year % 400 === 0) ? 29 : 28,
            31, 30, 31, 30, 31, 31, 30, 31, 30, 31][month - 1];
    }

    /* The naive wall-clock text the plot shows, and the recorded UTC offset in
     * seconds (null when the stamp carries none), or null for an invalid stamp. */
    function stamp(text) {
        const match = STAMP.exec(String(text).replace(/Z/g, "+00:00"));
        if (!match) return null;
        const [year, month, day] = [+match[1], +match[2], +match[3]];
        const [hour, minute, second] = [+(match[4] || 0), +(match[5] || 0), +(match[6] || 0)];
        if (year < 1 || month < 1 || month > 12 || day < 1 || day > daysIn(year, month)) return null;
        if (hour > 23 || minute > 59 || second > 59) return null;
        const micro = match[7] ? +match[7].padEnd(6, "0") : 0;
        let offset = null;
        if (match[8]) {
            const [oh, om, os] = [+match[9], +(match[10] || 0), +(match[11] || 0)];
            if (oh > 23 || om > 59 || os > 59) return null;
            const fraction = match[12] ? +match[12].padEnd(6, "0") / 1e6 : 0;
            offset = (match[8] === "-" ? -1 : 1) * (oh * 3600 + om * 60 + os + fraction);
            if (offset === 0) offset = 0;  // -00:00 is +00:00
        }
        const clock = `${pad(year, 4)}-${pad(month, 2)}-${pad(day, 2)}T${pad(hour, 2)}:${pad(minute, 2)}:${pad(second, 2)}`;
        return {text: micro ? `${clock}.${pad(micro, 6)}` : clock, offset};
    }

    /* Python's "{:g}": six significant digits, trailing zeros dropped. */
    function formatG(value) {
        if (value === 0) return Object.is(value, -0) ? "-0" : "0";
        const trim = text => text.includes(".") ? text.replace(/0+$/, "").replace(/\.$/, "") : text;
        const [mantissa, power] = value.toExponential(5).split("e");
        const exponent = Number(power);
        if (exponent < -4 || exponent >= 6) {
            return `${trim(mantissa)}e${exponent < 0 ? "-" : "+"}${pad(Math.abs(exponent), 2)}`;
        }
        return trim(value.toFixed(5 - exponent));
    }

    function describe(column, source) {
        const converted = column.endsWith("_c");
        const base = converted ? column.slice(0, -2) : column;
        let label = own(LABELS, base) ? LABELS[base] : column.replace(/_/g, " ");
        let unit = own(UNITS, column) ? UNITS[column] : "unknown";
        let group = "Recorded settings";
        if (source === "kikusui") {
            group = "Kikusui telemetry";
            if (own(TELEMETRY_LABELS, column)) label = TELEMETRY_LABELS[column];
            if (column === "voltage_v") group = "Cathode voltage";
            else if (column === "current_a" || column === "plasma_target_a") group = "Cathode current";
        } else if (own(LABELS, base)) {
            group = converted ? "Converted signals" : "Raw signals";
            unit = "V";
            label += converted ? ` (${base})` : ` (${base} raw)`;
            if (converted && PRESSURES.has(base)) {
                unit = "Torr";
                group = "Pressure";
            } else if (converted && base === "Ip") {
                unit = "A";
                group = "Plasma current";
            }
        } else if (column.startsWith("IGmode")) {
            label = (column === "IGmode_Pu2" ? "Upstream" : "Downstream") + " ion gauge output mode";
            unit = "0=Torr linear; 1=Pa log";
        } else if (column.startsWith("IGscale")) {
            label = (column === "IGscale_Pu2" ? "Upstream" : "Downstream") + " ion gauge range exponent";
            unit = "exponent";
        } else if (column.endsWith("_off")) {
            const stem = column.slice(0, -4);
            unit = "0/1";
            label = (own(LABELS, stem) ? LABELS[stem] : stem) + " off";
        }
        if (own(SETTING_LABELS, column)) label = SETTING_LABELS[column];
        return {label, unit, group};
    }

    /* Hands each CSV record to `take` as an array of fields, with Python's
     * csv.reader rules: quoted fields may hold commas, doubled quotes and
     * line breaks; a blank line is an empty record. `last` is true for the
     * final record of a file whose text stops without a line break. */
    function records(text, take) {
        const unterminated = text.length > 0 && !/[\r\n]$/.test(text);
        if (!text.includes('"')) {
            // Recorder files carry no quotes: one split per line is enough.
            const lines = text.includes("\r") ? text.split(/\r\n?|\n/) : text.split("\n");
            const end = lines.length - (unterminated ? 1 : 2);
            for (let i = 0; i <= end; i++) {
                take(lines[i] ? lines[i].split(",") : [], unterminated && i === end);
            }
            return;
        }
        let record = [], field = "", state = 0;  // 0 record, 1 field, 2 unquoted, 3 quoted, 4 quote in quoted
        for (let i = 0; i < text.length; i++) {
            const c = text[i];
            if ((c === "\n" || c === "\r") && state !== 3) {
                if (state !== 0) record.push(field);
                take(record, false);
                record = []; field = ""; state = 0;
                if (c === "\r" && text[i + 1] === "\n") i++;
                continue;
            }
            if (state === 3) {
                if (c === '"') state = 4; else field += c;
            } else if (c === ",") {
                record.push(field); field = ""; state = 1;
            } else if (c === '"' && state < 2) {
                state = 3;
            } else if (c === '"' && state === 4) {
                field += c; state = 3;
            } else {
                field += c; state = 2;
            }
        }
        if (state !== 0) {
            record.push(field);
            take(record, true);
        }
    }

    function readSource(name, text) {
        if (text.charCodeAt(0) === 0xfeff) text = text.slice(1);
        let capacity = 1;
        for (let at = text.indexOf("\n"); at !== -1; at = text.indexOf("\n", at + 1)) capacity++;
        if (text.includes("\r")) capacity += text.split("\r").length;
        let columns = null, signature = "", rows = 0, partial = false;
        let numbers, stamps, offsets, statusOk, flags, stampAt, statusAt;
        function begin() {
            if (new Set(columns).size !== columns.length) throw new RecordingError("The recording needs a unique column header.");
            numbers = columns.map(() => new Float64Array(capacity));
            stamps = new Array(capacity);
            offsets = new Set();
            stampAt = columns.indexOf("date") >= 0 ? columns.indexOf("date") : columns.indexOf("timestamp");
            statusAt = columns.indexOf("status");
            statusOk = new Uint8Array(capacity);
            flags = columns.map(column => column.endsWith("_flags") ? new Uint8Array(capacity) : null);
        }
        records(text, (values, last) => {
            if (!values.length || values.every(value => !value.trim())) return;
            const first = values[0].trim();
            let heading = null;
            if (first.startsWith("#")) {
                if (first.slice(1).trim().toLowerCase() !== "columns") return;
                heading = values.slice(1).map(value => value.trim());
            } else if (first.toLowerCase() === "date" || first.toLowerCase() === "timestamp") {
                heading = values.map(value => value.trim());
            }
            if (heading) {
                if (rows && JSON.stringify(heading) !== signature) {
                    throw new RecordingError("The recording's column header changes partway through.");
                }
                if (!rows) { columns = heading; signature = JSON.stringify(heading); numbers = null; }
                return;
            }
            if (!columns) throw new RecordingError("The recording needs a unique column header.");
            if (!numbers) begin();
            if (values.length !== columns.length) {
                // A recording still being written may end mid-row.
                if (last) { partial = true; return; }
                throw new RecordingError("A recording row does not match its column header.");
            }
            for (let c = 0; c < values.length; c++) {
                numbers[c][rows] = number(values[c]);
                if (flags[c] && values[c].includes("instrument_off")) flags[c][rows] = 1;
            }
            const when = stamp(stampAt >= 0 ? values[stampAt] : "");
            stamps[rows] = when ? when.text : null;
            if (when && when.offset !== null) offsets.add(when.offset);
            if (statusAt >= 0 && values[statusAt].trim() === "ok") statusOk[rows] = 1;
            rows++;
        });
        if (!columns || !(columns.includes("date") || columns.includes("timestamp"))) {
            throw new RecordingError("The recording has no timestamp column.");
        }
        if (!numbers) begin();
        stamps.length = rows;
        return {name, columns, rows, numbers, stamps, offsets, statusOk, flags, partial};
    }

    function seriesOf(data, counts) {
        const {name, columns, rows, numbers, stamps, statusOk, flags} = data;
        const source = name.split("_")[0];
        const at = column => columns.indexOf(column);
        const result = [];
        columns.forEach((column, c) => {
            if (column === "date" || column === "timestamp") return;
            const values = numbers[c].subarray(0, rows);
            const {label, unit, group} = describe(column, source);
            if (unit === "unknown" && values.every(Number.isNaN)) return;
            const base = column.endsWith("_c") ? column.slice(0, -2) : column;
            const flagged = at(column + "_flags") >= 0 ? flags[at(column + "_flags")]
                : at(base + "_flags") >= 0 ? flags[at(base + "_flags")] : null;
            const switchedOff = at(base + "_off") >= 0 ? numbers[at(base + "_off")] : null;
            const measured = source === "kikusui" && (column === "voltage_v" || column === "current_a" || column === "output_on");
            const modeAt = column === "Pd_c" ? at("IGmode") : column === "Pu2_c" ? at("IGmode_Pu2") : null;
            const y = new Float64Array(rows);
            for (let i = 0; i < rows; i++) {
                if (stamps[i] === null) { y[i] = NaN; continue; }
                let value = values[i];
                if (Number.isNaN(value)) counts.invalidValues++;
                if (measured && !statusOk[i]) { value = NaN; counts.telemetryGaps++; }
                if ((flagged && flagged[i]) || (switchedOff && switchedOff[i] === 1)) { value = NaN; counts.offValues++; }
                if (modeAt !== null) {
                    const mode = modeAt >= 0 ? numbers[modeAt][i] : NaN;
                    if (mode === 1 && !Number.isNaN(value)) {
                        value /= PASCALS_PER_TORR;
                        counts.paValues++;
                    } else if (mode !== 0) {
                        if (!Number.isNaN(value)) counts.unknownModes++;
                        value = NaN;
                    }
                }
                y[i] = value;
            }
            const scale = column.startsWith("IGscale");
            const seen = [], known = new Set();
            for (const value of scale ? values : []) {
                if (Number.isNaN(value) || known.has(value)) continue;
                known.add(value);
                seen.push(value);
                if (seen.length === 12) break;
            }
            result.push({
                id: source + ":" + column, column, label, unit, group, source: name,
                x: stamps, y, default_visible: DEFAULT_CHANNELS.has(column),
                meaning: scale ? "Recorded linear range exponent: -6 means 10^-6 Torr; "
                    + "converted pressure already includes this multiplier." : "",
                summary: scale && seen.length ? seen.map(value => "10^" + formatG(value)).join(", ") + " Torr" : "",
            });
        });
        return result;
    }

    function rank(series) {
        if (series.default_visible) return 0;
        if (series.column.startsWith("PresetV_mfc") || series.column === "MFC1_c" || series.column === "MFC2_c") return 1;
        return series.group === "Raw signals" ? 3 : 2;
    }

    /* `files` are [{name, text}] in companion order: cu, kikusui, pid. */
    function read(files) {
        const payload = {series: [], sources: [], notes: [], time_label: "Recorder local time"};
        const counts = {invalidValues: 0, offValues: 0, telemetryGaps: 0, paValues: 0, unknownModes: 0};
        const offsets = new Set();
        const seen = new Set();
        let invalidTimes = 0, partial = 0, kikusui = false;
        for (const file of files) {
            const data = readSource(file.name, file.text);
            data.columns.forEach(column => seen.add(column));
            data.offsets.forEach(offset => offsets.add(offset));
            kikusui = kikusui || file.name.split("_")[0] === "kikusui";
            invalidTimes += data.stamps.filter(text => text === null).length;
            partial += data.partial ? 1 : 0;
            payload.sources.push({name: file.name, columns: data.columns, rows: data.rows});
            payload.series.push(...seriesOf(data, counts));
        }
        const notes = payload.notes;
        notes.push("Recorder local time; no viewer timezone conversion.");
        notes.push(kikusui
            ? "Kikusui uses local receipt time with its recorded offset; queries are sequential."
            : "No same-run Kikusui telemetry file is available.");
        if (seen.has("Pd_c") || seen.has("Pu2_c")) notes.push("Linear ion gauge pressure is recorded in Torr; range scaling is already applied.");
        if (counts.paValues) notes.push(`${counts.paValues} explicitly recorded Pa-mode readings were converted to Torr.`);
        if (counts.unknownModes) {
            notes.push(`${counts.unknownModes} ion gauge pressure readings have missing or invalid `
                + "recorded output modes and are shown as gaps.");
        }
        if (seen.has("MFC1_c") || seen.has("MFC2_c")) notes.push("MFC converted signals remain volts.");
        if (invalidTimes) notes.push(`${invalidTimes} rows have invalid timestamps; lines break at those rows.`);
        if (counts.invalidValues) notes.push(`${counts.invalidValues} missing or non-numeric channel values are gaps.`);
        if (counts.offValues) notes.push(`${counts.offValues} readings marked instrument off are gaps.`);
        if (counts.telemetryGaps) notes.push(`${counts.telemetryGaps} non-ok Kikusui measurement values are gaps.`);
        if (partial) notes.push("The last row was still being written when the file was read and is not shown.");
        if (offsets.size > 1) {
            throw new RecordingError("UTC offsets change within this recording; local-time alignment is ambiguous.");
        }
        payload.series.sort((a, b) => rank(a) - rank(b));
        return payload;
    }

    const api = {read, RecordingError};
    if (typeof module === "object" && module.exports) module.exports = api;
    else scope.PihtiRecording = api;
}(typeof self !== "undefined" ? self : this));
