"""RED-first 1.1 release identity contract (issue #206).

These tests were committed after research/issue-206/RESEARCH_PLAN.md and
before any production or historical-contract edits.
"""

from __future__ import annotations

import json
import re
import tomllib
from pathlib import Path

from pseudepigrapha_tf import __version__
from pseudepigrapha_tf.cli import _parser
from pseudepigrapha_tf.release_identity import CONVERTER_VERSION, TF_DATA_VERSION


ROOT = Path(__file__).resolve().parents[1]


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_1_1_owned_release_identity_is_coherent():
    project = tomllib.loads(_read("pyproject.toml"))["project"]
    materializer = json.loads(_read("agora.materializer.json"))
    app = _read("app/config.yaml")
    version = re.search(
        r'(?ms)^provenanceSpec:\s*$.*?^\s+version:\s*["\']?([^"\'\s#]+)',
        app,
    )
    assert version is not None
    assert __version__ == CONVERTER_VERSION == project["version"] == materializer["plugin"]["version"] == "1.1.0"
    assert TF_DATA_VERSION == version.group(1) == "1.1"
    assert _parser().parse_args(["convert", "source"]).output == Path("tf/1.1")
    assert materializer["materializers"][0]["acquisition"][0]["ref"] == (
        "c939dcbacad78c5d18d2c4282cad23c47e19ac07"
    )


def test_1_1_normal_full_corpus_ci_targets_new_install_and_dataset():
    text = _read(".github/workflows/test.yml")
    assert "pseudepigrapha_tf-1.1.0-py3-none-any.whl" in text
    assert "/tmp/pseudepigrapha-tf/1.1" in text
    assert "CANDIDATE_RELEASE_TAG: v1.1.0-ci" in text
    assert "converter_version='1.1.0'" in text
    assert "data_version='1.1'" in text
    assert "version=\"1.1\"" in text
    assert "assert generic['version'] == '1.1'" in text
    assert "c939dcbacad78c5d18d2c4282cad23c47e19ac07" in text


def test_1_1_publisher_binds_version_and_release_notes():
    text = _read(".github/workflows/publish-corpus-release.yml")
    assert "expected_converter_version='1.1.0'" in text
    assert "expected_data_version='1.1'" in text
    assert "if data_version != '1.1':" in text
    assert "assert generic['version'] == '1.1'" in text
    assert "assert generic['converterVersion'] == '1.1.0'" in text
    assert "--notes-file research/issue-206/RELEASE_NOTES.md" in text
    assert "--verify-tag" in text
    assert "--clobber" not in text


def test_1_1_release_notes_explain_data_version_change():
    notes = _read("research/issue-206/RELEASE_NOTES.md").lower()
    for term in ("v1.1.0", "tf-1.1.zip", "tsol", "manuscript", "upstream", "version"):
        assert term in notes


def test_1_1_local_user_examples_and_historical_benchmarks():
    readme = _read("README.md")
    app_docs = _read("docs/tf-app.md")
    runtime = _read("docs/runtime-footprint.md")
    browse = readme.split("## Browse and compare", 1)[1].split("## Resource expectations", 1)[0]
    rebuild = readme.split("## Rebuild from OCP", 1)[1]
    selective = runtime.split("## Lower-memory selective loading", 1)[1]
    assert "tf-1.1.zip" in browse
    assert "/tmp/pseudepigrapha-tf/1.1" in browse
    assert "--output tf/1.1" in rebuild
    assert "current TF data release identity is `1.1`" in app_docs
    assert "pseudepigrapha-tf browse tf/1.1 --app app" in app_docs
    assert 'Fabric(locations=["tf/1.1"]' in selective
    assert "1.0 corpus" in runtime  # Historical measurements are not rebranded
    assert "v0.2.0" in runtime
