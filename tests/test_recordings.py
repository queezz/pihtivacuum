"""Pairing and header reading; the samples are read in the browser.

Units, labels, gaps and conversions moved to `static/js/recording-reader.js`
in 0.29.0, and their tests to `tests/recording-reader.test.cjs`.
"""
import pytest

from pihti.recordings import companion_paths, recording_columns


def write(tmp_path, prefix, text, stamp="20260101_120000"):
    path = tmp_path / (prefix + "_" + stamp + ".csv")
    path.write_text(text, encoding="utf-8")
    return path


def test_companions_come_in_recorder_order(tmp_path):
    pid = write(tmp_path, "pid", "date,error_a\n")
    path = write(tmp_path, "cu", "# Columns,date,Ip_c\n")
    kikusui = write(tmp_path, "kikusui", "date,voltage_v\n")
    write(tmp_path, "kikusui", "date,voltage_v\n", "20260101_130000")
    assert companion_paths(path) == [path, kikusui, pid]
    assert companion_paths(kikusui) == [path, kikusui, pid]


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
    with pytest.raises(ValueError, match="timestamp"):
        recording_columns(path)


def test_legacy_file_has_no_companions(tmp_path):
    path = tmp_path / "cu_notes.csv"
    path.write_text("# Columns,date,Ip_c\n2026-01-01 12:00:00,1\n")
    write(tmp_path, "kikusui", "date,voltage_v\n")
    assert companion_paths(path) == [path]


def test_header_is_read_without_the_samples(tmp_path):
    path = write(tmp_path, "cu", "# Title , demo\n# Columns , date, Ip_c, Pu_c\n# [Data]\n"
                 "2026-01-01 12:00:00,1,2\nthis row is never read,\n")
    assert recording_columns(path) == ["date", "Ip_c", "Pu_c"]
    sidecar = write(tmp_path, "kikusui", "# schema: demo\ndate,voltage_v\n2026-01-01T12:00:00+09:00,2\n")
    assert recording_columns(sidecar) == ["date", "voltage_v"]
