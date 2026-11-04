"""Guard the documented pinned comparison benchmark reproducibility recipe."""

from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

from pseudepigrapha_tf.release_identity import TF_DATA_VERSION


DOC = Path("docs/comparison-performance-benchmark.md")
WORKFLOW = Path(".github/workflows/test.yml")


def _reproduce_shell() -> str:
    text = DOC.read_text(encoding="utf-8")
    section = text.split("\n## Reproduce\n", 1)[1].split("\n## Cases and fields\n", 1)[0]
    return section.split("```bash\n", 1)[1].split("\n```", 1)[0]


def test_benchmark_recipe_resolves_current_installed_tf_data_version_for_both_paths():
    script = _reproduce_shell()
    assignment = (
        'DATA_VERSION="$(python -c \'from pseudepigrapha_tf.release_identity '
        'import TF_DATA_VERSION; print(TF_DATA_VERSION)\')"'
    )
    assert assignment in script
    assert script.index("python -m pip install -e '.[dev]'") < script.index(assignment)
    assert '--output "/tmp/pseudepigrapha-tf/${DATA_VERSION}"' in script
    assert (
        'python tests/pinned_comparison_acceptance.py '
        '"/tmp/pseudepigrapha-tf/${DATA_VERSION}"'
    ) in script
    assert "/tmp/pseudepigrapha-tf/1.0" not in script


def test_benchmark_recipe_shell_parses_and_matches_pinned_upstream_checkout():
    script = _reproduce_shell()
    workflow = WORKFLOW.read_text(encoding="utf-8")
    pinned = re.search(r"git -C /tmp/ocp checkout ([0-9a-f]{40})", workflow)
    assert pinned, "CI must pin the OCP checkout"
    sha = pinned.group(1)
    assert f"git -C /tmp/ocp checkout {sha}" in script
    assert f"--upstream-commit {sha}" in script

    bash = shutil.which("bash")
    if bash:
        subprocess.run([bash, "-n"], input=script, text=True, check=True)
        line = next(line for line in script.splitlines() if line.startswith("DATA_VERSION="))
        result = subprocess.run(
            [bash, "-eu", "-c", line + '\nprintf "%s" "$DATA_VERSION"'],
            capture_output=True,
            text=True,
            check=True,
        )
        assert result.stdout == TF_DATA_VERSION
