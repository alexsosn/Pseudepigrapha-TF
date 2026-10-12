"""Executable Bash syntax regression for the guarded v1.1 release launcher (#218).

The GitHub Actions launcher failed in its 200:200 case arm after full green
corpus CI because its YAML-decoded heredoc delimiter was not flush-left.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from textwrap import dedent

import yaml


LAUNCH = Path(__file__).resolve().parents[1] / ".github/workflows/launch-v1-1-release.yml"


def _bash_syntax(script: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["bash", "-n"], input=script, text=True, capture_output=True, check=False)


def test_launcher_real_yaml_run_scripts_parse_as_bash():
    """Validate decoded runner scripts, not raw YAML substring matches."""
    config = yaml.safe_load(LAUNCH.read_text(encoding="utf-8"))
    steps = config["jobs"]["launch"]["steps"]
    scripts = [(step["name"], step["run"]) for step in steps if "run" in step]
    assert len(scripts) >= 2
    assert any("Probe immutable tag and release" in name for name, _ in scripts)
    for name, script in scripts:
        assert isinstance(script, str), name
        checked = _bash_syntax(script)
        assert checked.returncode == 0, f"{name}: {checked.stderr}"
        assert not checked.stderr, f"{name}: {checked.stderr}"


def test_bash_syntax_gate_detects_indented_heredoc_in_case_arm():
    bad = dedent("""\
        case x in
          x)
            python - <<'PY'
            print("okay")
            PY
            ;;
        esac
    """)
    good = dedent("""\
        case x in
          x)
            python - <<'PY'
    print("okay")
    PY
            ;;
        esac
    """)
    broken = _bash_syntax(bad)
    assert broken.returncode != 0
    assert "here-document" in broken.stderr
    valid = _bash_syntax(good)
    assert valid.returncode == 0, valid.stderr
    assert not valid.stderr
