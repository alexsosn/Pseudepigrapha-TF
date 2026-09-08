from __future__ import annotations

import json
from pathlib import Path
import tomllib

from pseudepigrapha_tf import __version__
from pseudepigrapha_tf.cli import _parser


PINNED_OCP_COMMIT = "c939dcbacad78c5d18d2c4282cad23c47e19ac07"
PINNED_ADAMEVE_SHA256 = "b5e20471d7e1b531df49d81acd19462ee92192c3e20019cb110215611d7b9817"
OLD_OCP_COMMIT = "2d1d14d23434a784d377ff7f4409ccdb2d18aafb"


def test_release_versions_and_default_dataset_path_are_consistent() -> None:
    pyproject = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))

    assert pyproject["project"]["version"] == "0.2.0"
    assert __version__ == "0.2.0"

    args = _parser().parse_args(["convert", "source"])
    assert args.output == Path("tf/0.2")


def test_readme_documents_noneditable_runtime_install() -> None:
    readme = Path("README.md").read_text(encoding="utf-8")
    install_section = readme.split("## Install", 1)[1].split("## Convert OCP", 1)[0]

    assert "pip install ." in install_section


def test_release_source_identity_is_consistent_across_current_contract() -> None:
    manifest = json.loads(Path("agora.materializer.json").read_text(encoding="utf-8"))
    git_acquisition = next(
        item
        for item in manifest["materializers"][0]["acquisition"]
        if item["type"] == "git"
    )
    assert git_acquisition["ref"] == PINNED_OCP_COMMIT

    workflow = Path(".github/workflows/test.yml").read_text(encoding="utf-8")
    readme = Path("README.md").read_text(encoding="utf-8")
    agora_doc = Path("docs/agora-materialization.md").read_text(encoding="utf-8")
    anomaly_doc = Path("docs/source-identity-and-anomalies.md").read_text(encoding="utf-8")

    for current_contract in (workflow, readme, agora_doc, anomaly_doc):
        assert PINNED_OCP_COMMIT in current_contract
        assert OLD_OCP_COMMIT not in current_contract

    assert PINNED_ADAMEVE_SHA256 in anomaly_doc
