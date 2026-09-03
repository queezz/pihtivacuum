from __future__ import annotations

import sys
import tempfile
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))


def pytest_configure(config):
    if config.option.basetemp:
        return
    scratch = tempfile.TemporaryDirectory(prefix="pihti-diagram-pytest-")
    config._pihti_scratch = scratch
    config.option.basetemp = str(Path(scratch.name) / "run")
    config.add_cleanup(scratch.cleanup)
