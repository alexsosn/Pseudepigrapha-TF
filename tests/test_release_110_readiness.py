from __future__ import annotations

import json
import re
import tomllib
from pathlib import Path

import pseudepigrapha_tf
from pseudepigrapha_tf.cli import _parser
from pseudepigrapha_tf.release_identity import CONVERTER_VERSION, TF_DATA_VERSION


ROOT = Path(__file__).resolve().parents[1]
PACKAGE_VERSION = "1.1.0"
DATA_VERSION = "1.1"
RELEASE_TAG = "v1.1.0"


def _app_data_version() -> str:
    text = (ROOT / "app" / "config.yaml").read_text(encoding="utf-8")
    match = re.search(
        r"(?ms)^provenanceSpec:\s*$.*?^\s+version:\s*[\"']?([^\"'\s#]+)",
        text,
    )
    assert match is not None
    return match.group(1)


def test_current_owned_release_identity_is_1_1_and_coherent() -> None:
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


def test_normal_full_corpus_ci_exercises_current_1_1_identity() -> None:
    text = (ROOT / ".github" / "workflows" / "test.yml").read_text(encoding="utf-8")

    assert "dist/pseudepigrapha_tf-1.1.0-py3-none-any.whl" in text
    assert "/tmp/pseudepigrapha-tf/1.1" in text
    assert "converter_version='1.1.0'" in text
    assert "data_version='1.1'" in text
    assert "converterVersion'] == '1.1.0'" in text
    assert "version'] == '1.1'" in text


def test_publisher_targets_current_1_1_identity_and_release_notes() -> None:
    text = (ROOT / ".github" / "workflows" / "publish-corpus-release.yml").read_text(
        encoding="utf-8"
    )

    assert "expected_converter_version='1.1.0'" in text
    assert "expected_data_version='1.1'" in text
    assert "if data_version != '1.1':" in text
    assert "--notes-file research/issue-206/RELEASE_NOTES.md" in text
    assert "research/issue-142/RELEASE_NOTES.md" not in text


def test_1_1_release_notes_exist_and_describe_researcher_gates() -> None:
    notes = ROOT / "research" / "issue-206" / "RELEASE_NOTES.md"
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


def test_agora_materialization_docs_do_not_deny_published_derived_corpus() -> None:
    text = (ROOT / "docs" / "agora-materialization.md").read_text(encoding="utf-8").lower()

    obsolete_claims = (
        "without redistributing ocp source xml or a generated text-fabric corpus",
        "not ocp xml and not generated tf data",
    )
    for claim in obsolete_claims:
        assert claim not in text

    assert "published" in text
    assert "derived" in text


def test_current_local_user_examples_follow_1_1_data_identity() -> None:
    tf_app = (ROOT / "docs" / "tf-app.md").read_text(encoding="utf-8")
    runtime = (ROOT / "docs" / "runtime-footprint.md").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")

    assert "current TF data release identity is `1.1`" in tf_app
    assert "pseudepigrapha-tf browse tf/1.1 --app app" in tf_app

    selective = runtime.split("## Lower-memory selective loading", 1)[1]
    assert 'Fabric(locations=["tf/1.1"]' in selective
    assert 'Fabric(locations=["tf/1.0"]' not in selective

    rebuild = readme.split("## Rebuild from OCP", 1)[1]
    assert "--output tf/1.1" in rebuild
    assert "--output tf/1.0" not in rebuild


def test_primary_public_acquisition_is_not_frozen_to_previous_release() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    acquisition = readme.split("## Get and load the published corpus", 1)[1].split(
        "## Query a passage", 1
    )[0]

    assert '"alexsosn/Pseudepigrapha-TF"' in acquisition
    assert '"alexsosn/Pseudepigrapha-TF:v0.2.0"' not in acquisition
    assert 'checkout="v0.2.0"' not in acquisition
    assert '"alexsosn/Pseudepigrapha-TF:v1.0.0"' not in acquisition
    assert 'checkout="v1.0.0"' not in acquisition
    assert "latest public release" in acquisition.lower()


def test_release_ready_readme_uses_1_1_for_current_local_workflows() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")

    browse = readme.split("## Browse and compare", 1)[1].split("## Resource expectations", 1)[0]
    resources = readme.split("## Resource expectations", 1)[1].split(
        "## Metadata and feature reference", 1
    )[0]

    assert "tf-1.1.zip" in browse
    assert "/tmp/pseudepigrapha-tf/1.1" in browse
    assert "tf-1.0.zip" not in browse
    assert "/tmp/pseudepigrapha-tf/1.0" not in browse

    assert "currently published `v0.2.0`" not in resources
    assert "intended for the next publication" not in resources
    assert "v0.2.0" in resources
    assert "1.1" in resources


def test_runtime_measurement_note_is_timeless_after_1_0_publication() -> None:
    runtime = (ROOT / "docs" / "runtime-footprint.md").read_text(encoding="utf-8")
    lowered = runtime.lower()

    assert "1.0 corpus" in lowered
    assert "not yet a published github release" not in lowered
    assert "intended for the next corpus publication" not in lowered
    assert "optimized corpus is not yet published" not in lowered
    assert "measured before" in lowered or "pre-publication" in lowered


def test_runtime_figures_are_not_silently_reattributed_to_1_1() -> None:
    # 1.1 changes manuscript metadata only and was not re-measured. Existing
    # figures must stay attributed to the corpus they were actually measured on
    # rather than being relabelled for the new release identity.
    runtime = (ROOT / "docs" / "runtime-footprint.md").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")

    assert "1.0 corpus" in runtime.lower()
    assert "1.1 corpus (measured" not in runtime.lower()
    assert "The 1.1 corpus output is smaller" not in readme


def test_published_v1_0_0_remains_an_explicit_historical_baseline() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    runtime = (ROOT / "docs" / "runtime-footprint.md").read_text(encoding="utf-8")

    assert "v1.0.0" in readme or "1.0 corpus" in readme
    assert "v0.2.0" in runtime
