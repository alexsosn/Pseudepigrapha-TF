"""The package must not advertise an end-of-life Python runtime."""
from __future__ import annotations

import tomllib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_package_floor_excludes_end_of_life_python_310():
    package = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    # First researched maintenance target is 3.12. This deliberately fails on
    # the old '>=3.10' metadata before changing the package declaration.
    assert package["requires-python"] == ">=3.12"
    assert package["dependencies"] == ["text-fabric[github]>=13.1,<14"]
