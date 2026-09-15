import json

import pytest

from pihti.recordings import companion_paths, load_recording


def write(tmp_path, prefix, text, stamp="20260101_120000"):
    path = tmp_path / (prefix + "_" + stamp + ".csv")
    path.write_text(text, encoding="utf-8")
    return path


def channels(payload):
    return {series["id"]: series for series in payload["series"]}


def test_variable_preamble_units_all_channels_and_mode_conversion(tmp_path):
    path = write(tmp_path, "cu", "# Title, demo\n# Columns , date,IGmode,IGmode_Pu2,Pd_c,Pu2_c,MFC1_c,new_sensor,Ip_c\n# extra metadata\n# [Data]\n2026-01-01 12:00:00,0,1,2,133.32236842105263,3,12,nan\n2026-01-01 12:00:01,1,9,133.32236842105263,4,2,13,inf\n")
    payload = load_recording(path)
    data = channels(payload)
    assert data["cu:Pd_c"]["y"] == [2, 1]
    assert data["cu:Pu2_c"]["y"] == [1, None]
    assert data["cu:MFC1_c"]["unit"] == "V"
    assert data["cu:new_sensor"]["unit"] == "unknown"
    assert data["cu:Ip_c"]["y"] == [None, None]
    assert payload["sources"][0]["rows"] == 2
    json.dumps(payload, allow_nan=False)


def test_companions_gaps_and_explicit_local_clock(tmp_path):
    path = write(tmp_path, "cu", "# Columns,date,Ip_c,Ip_flags\n2026-01-01 12:00:00,1,instrument_off\n")
    write(tmp_path, "kikusui", "# schema: demo\ndate,voltage_v,current_a,output_on,status,query_ms\n2026-01-01T12:00:00+09:00,2,3,1,ok,8\n2026-01-01T12:00:01+09:00,4,5,1,unavailable,10\n")
    write(tmp_path, "pid", "date,error_a\n2026-01-01 12:00:00,0.5\n")
    write(tmp_path, "kikusui", "date,voltage_v\n", "20260101_130000")
    payload = load_recording(path)
    data = channels(payload)
    assert len(payload["sources"]) == 3
    assert data["cu:Ip_c"]["y"] == [None]
    assert data["kikusui:voltage_v"]["y"] == [2, None]
    assert data["kikusui:query_ms"]["y"] == [8, 10]
    assert data["kikusui:voltage_v"]["x"][0] == data["cu:Ip_c"]["x"][0]
    assert payload["time_label"] == "Recorder local time"


def test_ambiguous_offsets_rejected(tmp_path):
    path = write(tmp_path, "kikusui", "date,voltage_v,status\n2026-01-01T12:00:00+09:00,1,ok\n2026-01-01T12:00:01+08:00,1,ok\n")
    with pytest.raises(ValueError, match="ambiguous"):
        load_recording(path)


def test_escape_symlink_rejected(tmp_path):
    folder = tmp_path / "recordings"
    folder.mkdir()
    path = write(folder, "cu", "# Columns,date,Ip_c\n")
    external = write(tmp_path, "kikusui", "date,voltage_v\n")
    try:
        (folder / external.name).symlink_to(external)
    except OSError:
        pytest.skip("Creating symlinks requires permission on this host")
    with pytest.raises(ValueError, match="directory"):
        companion_paths(path)


def test_bad_name_and_header_are_rejected(tmp_path):
    with pytest.raises(ValueError, match="unavailable"):
        companion_paths(tmp_path / "../other.csv")
    path = write(tmp_path, "cu", "2026-01-01 12:00:00,3\n")
    with pytest.raises(ValueError, match="header"):
        load_recording(path)


def test_legacy_file_has_no_companions(tmp_path):
    path = tmp_path / "cu_notes.csv"
    path.write_text("# Columns,date,Ip_c\n2026-01-01 12:00:00,1\n")
    write(tmp_path, "kikusui", "date,voltage_v\n")
    assert companion_paths(path) == [path]
    assert len(load_recording(path)["sources"]) == 1


def test_multiline_sidecar_text_and_instrument_off_columns(tmp_path):
    path = write(tmp_path, "cu", "# Columns,date,Pu,Pu_c,Pu_off\n"
                 "2026-01-01 12:00:00,3,4,1\n"
                 "2026-01-01 12:00:01,3,4,0\n")
    write(tmp_path, "kikusui", 'date,voltage_v,status,error,identity\n'
          '2026-01-01T12:00:00+09:00,2,ok,"first\n# second",supply\n')
    data = channels(load_recording(path))
    assert data["cu:Pu"]["y"] == [None, 3]
    assert data["cu:Pu_c"]["y"] == [None, 4]
    assert data["cu:Pu_off"]["y"] == [1, 0]
    assert data["kikusui:voltage_v"]["y"] == [2]


def test_invalid_timestamp_breaks_line_and_unknown_numeric_missingness_is_noted(tmp_path):
    path = write(tmp_path, "cu", "# Columns,date,new_sensor\n"
                 "2026-01-01 12:00:00,2\ninvalid,3\n"
                 "2026-01-01 12:00:02,broken\n2026-01-01 12:00:03,4\n")
    payload = load_recording(path)
    data = channels(payload)["cu:new_sensor"]
    assert data["x"][1] is None
    assert data["y"] == [2, None, None, 4]
    assert any("1 rows have invalid timestamps" in note for note in payload["notes"])
    assert any("1 missing or non-numeric" in note for note in payload["notes"])
    assert sum("No same-run Kikusui" in note for note in payload["notes"]) == 1



def test_linear_torr_is_not_rescaled_when_range_changes(tmp_path):
    path = write(tmp_path, "cu", "# Columns,date,IGmode,IGscale,Pd_c,IGmode_Pu2,IGscale_Pu2,Pu2_c\n"
                 "2026-01-01 12:00:00,0,-6,2e-6,0,-7,3e-7\n"
                 "2026-01-01 12:00:01,0,-7,2e-7,0,-6,3e-6\n")
    payload = load_recording(path)
    data = channels(payload)
    assert data["cu:Pd_c"]["y"] == [2e-6, 2e-7]
    assert data["cu:Pu2_c"]["y"] == [3e-7, 3e-6]
    assert data["cu:IGscale"]["label"] == "Downstream ion gauge range exponent"
    assert data["cu:IGscale_Pu2"]["label"] == "Upstream ion gauge range exponent"
    assert data["cu:IGscale"]["y"] == [-6, -7]
    assert "-6 means 10^-6 Torr" in data["cu:IGscale"]["meaning"]
    assert not any("Pa-mode" in note for note in payload["notes"])


def test_kikusui_labels_keep_units_separate(tmp_path):
    path = write(tmp_path, "kikusui", "date,voltage_v,current_a,status\n"
                 "2026-01-01T12:00:00+09:00,2,3,ok\n")
    data = channels(load_recording(path))
    assert data["kikusui:voltage_v"]["label"] == "Cathode supply voltage"
    assert data["kikusui:voltage_v"]["unit"] == "V"
    assert data["kikusui:current_a"]["label"] == "Cathode current (Ic)"


def test_groups_range_summary_and_missing_mode_note(tmp_path):
    path = write(tmp_path, "cu", "# Columns,date,Pu_c,Bu_c,Pd_c,IGmode,IGscale,Ip_c,Ip\n"
                 "2026-01-01 12:00:00,1e-6,2e-6,3e-6,,-6,1,2\n"
                 "2026-01-01 12:00:01,1e-6,2e-6,3e-6,9,-7,1,2\n"
                 "2026-01-01 12:00:02,1e-6,2e-6,3e-6,0,-6,1,2\n")
    write(tmp_path, "kikusui", "date,voltage_v,current_a,plasma_target_a,status\n"
          "2026-01-01T12:00:00+09:00,2,3,4,ok\n")
    payload = load_recording(path)
    data = channels(payload)
    assert data["cu:Pu_c"]["group"] == "Pressure"
    assert data["cu:Bu_c"]["unit"] == "Torr"
    assert data["cu:Ip_c"]["group"] == "Plasma current"
    assert data["cu:Ip"]["group"] == "Raw signals"
    assert data["kikusui:voltage_v"]["group"] == "Cathode voltage"
    assert data["kikusui:current_a"]["group"] == "Cathode current"
    assert data["cu:IGscale"]["summary"] == "10^-6, 10^-7 Torr"
    assert data["cu:Pd_c"]["y"] == [None, None, 3e-6]
    assert any("2 ion gauge pressure readings have missing or invalid" in note
               for note in payload["notes"])
