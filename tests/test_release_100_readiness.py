from __future__ import annotations

import json
import re
import tomllib
from pathlib import Path

import pseudepigrapha_tf
from pseudepigrapha_tf.cli import _parser
from pseudepigrapha_tf.release_identity import CONVERTER_VERSION, TF_DATA_VERSION


ROOT = Path(__file__).resolve().parents[1]
PACKAGE_VERSION = "1.0.0"
DATA_VERSION = "1.0"
RELEASE_TAG = "v1.0.0"


def _app_data_version() -> str:
    text = (ROOT / "app" / "config.yaml").read_text(encoding="utf-8")
    match = re.search(
        r"(?ms)^provenanceSpec:\s*$.*?^\s+version:\s*[\"']?([^\"'\s#]+)",
        text,
    )
    assert match is not None
    return match.group(1)


def test_current_owned_release_identity_is_1_0_and_coherent() -> None:
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    materializer = json.loads((ROOT / "agora.materializer.json").read_text(encoding="utf-8"))
    args = _parser().parse_args(["convert", "source"])

    assert project["project"]["version"] == PACKAGE_VERSION
    assert "Text-Fabric corpus" in project["project"]["description"]
    assert pseudepigrapha_tf.__version__ == PACKAGE_VERSION
    assert CONVERTER_VERSION == PACKAGE_VERSION
    assert TF_DATA_VERSION == DATA_VERSION
    assert materializer["plugin"]["version"] == PACKAGE_VERSION
    assert _app_data_version() == DATA_VERSION
    assert args.output == Path(f"tf/{DATA_VERSION}")


def test_normal_full_corpus_ci_exercises_current_1_0_identity() -> None:
    text = (ROOT / ".github" / "workflows" / "test.yml").read_text(encoding="utf-8")

    assert "dist/pseudepigrapha_tf-1.0.0-py3-none-any.whl" in text
    assert "/tmp/pseudepigrapha-tf/1.0" in text
    assert "converter_version='1.0.0'" in text
    assert "data_version='1.0'" in text
    assert "converterVersion'] == '1.0.0'" in text
    assert "version'] == '1.0'" in text


def test_publisher_targets_current_1_0_identity_and_release_notes() -> None:
    text = (ROOT / ".github" / "workflows" / "publish-corpus-release.yml").read_text(
        encoding="utf-8"
    )

    assert "expected_converter_version='1.0.0'" in text
    assert "expected_data_version='1.0'" in text
    assert "if data_version != '1.0':" in text
    assert "--notes-file research/issue-142/RELEASE_NOTES.md" in text
    assert "research/issue-104/RELEASE_NOTES.md" not in text


def test_1_0_release_notes_exist_and_describe_researcher_gates() -> None:
    notes = ROOT / "research" / "issue-142" / "RELEASE_NOTES.md"
    assert notes.is_file()
    text = notes.read_text(encoding="utf-8")

    assert RELEASE_TAG in text
    for concept in (
        "correctness",
        "translation",
        "install",
        "memory",
        "web",
        "documentation",
    ):
        assert concept in text.lower()


def test_historical_v0_2_public_release_verification_is_retained() -> None:
    text = (ROOT / "tests" / "test_release_live_verification_contract.py").read_text(
        encoding="utf-8"
    )
    readme = (ROOT / "README.md").read_text(encoding="utf-8")

    assert "published-release verifier" in text
    assert "v0.2.0" in readme
