from __future__ import annotations

import json
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_agora_materializer_manifest_declares_ocp_to_tf_contract():
    manifest = json.loads((ROOT / "agora.materializer.json").read_text(encoding="utf-8"))
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]

    assert manifest["schema_version"] == 1
    assert manifest["plugin"]["id"] == "pseudepigrapha-tf"
    assert manifest["plugin"]["version"] == project["version"]

    materializer = manifest["materializers"][0]
    assert materializer["id"] == "ocp-text-fabric"
    assert materializer["input"] == {
        "type": "directory",
        "required_globs": ["*.xml"],
        "allow_symlinks": False,
    }
    assert materializer["execution"]["type"] == "python-module"
    assert materializer["execution"]["module"] == "pseudepigrapha_tf.cli"
    assert materializer["execution"]["args"] == [
        "convert",
        "{source}",
        "--output",
        "{output}",
    ]
    assert materializer["execution"]["network"] == "deny"
    assert materializer["output"]["format"] == "text-fabric"
    assert {
        "otype.tf",
        "oslots.tf",
        "conversion-report.json",
    } <= set(materializer["output"]["required_paths"])

    acquisitions = {item["type"]: item for item in materializer["acquisition"]}
    assert acquisitions["git"]["url"].endswith("Online-Critical-Pseudepigrapha.git")
    assert acquisitions["git"]["ref"] == "2d1d14d23434a784d377ff7f4409ccdb2d18aafb"
    assert acquisitions["git"]["subpath"] == "static/docs"
    assert acquisitions["user-local"]["path_type"] == "directory"
