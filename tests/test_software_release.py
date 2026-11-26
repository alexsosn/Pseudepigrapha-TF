from pathlib import Path
import json
import tomllib

import yaml


ROOT = Path(__file__).resolve().parents[1]


def test_software_release_is_distinct_from_legacy_data_release():
    project = tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]
    manifest = json.loads((ROOT / "agora.materializer.json").read_text())
    assert project["version"] == manifest["plugin"]["version"] == "1.2.0"
    assert manifest["materializers"][0]["acquisition"][0]["ref"] == (
        "853a64b623de296d2b8532a43593607772e7c45a"
    )
    text = (ROOT / ".github/workflows/test.yml").read_text()
    job = yaml.safe_load(text)["jobs"]["publish-software-1-2"]
    assert set(job["needs"]) == {"unit-and-tf", "python-314-installed-wheel-smoke",
                                "pinned-upstream-integration"}
    assert "github.event_name == 'push'" in job["if"]
    assert "refs/heads/main" in job["if"]
    assert job["permissions"] == {"contents": "write"}
    commands = "\n".join(step.get("run", "") for step in job["steps"])
    assert "gh release create" in commands
    assert "--latest=false" in commands
    assert "--target" in commands
    assert "zipfile" in commands
    assert "complete.zip" not in commands
    assert "tf-1.1.zip" not in commands
    assert "--clobber" not in commands
