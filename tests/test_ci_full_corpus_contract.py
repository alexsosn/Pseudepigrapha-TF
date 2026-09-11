from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).parents[1]
WORKFLOWS = ROOT / ".github" / "workflows"
FULL_CONVERT = "pseudepigrapha-tf convert /tmp/ocp/static/docs"
PIN = "c939dcbacad78c5d18d2c4282cad23c47e19ac07"
LOCAL_TF = "/tmp/pseudepigrapha-tf/0.2"


def _workflow_texts() -> dict[str, str]:
    return {
        path.name: path.read_text(encoding="utf-8")
        for path in sorted(WORKFLOWS.glob("*.yml"))
    } | {
        path.name: path.read_text(encoding="utf-8")
        for path in sorted(WORKFLOWS.glob("*.yaml"))
    }


def _pull_request_workflows() -> dict[str, str]:
    """Return only workflows that GitHub actually triggers for pull requests."""

    return {
        name: text
        for name, text in _workflow_texts().items()
        if "pull_request:" in text
    }


def test_pr_ci_materializes_the_exact_full_ocp_corpus_only_once():
    workflows = _pull_request_workflows()
    occurrences = {
        name: text.count(FULL_CONVERT)
        for name, text in workflows.items()
        if FULL_CONVERT in text
    }

    assert sum(occurrences.values()) == 1, occurrences
    assert occurrences == {"test.yml": 1}

    test_workflow = workflows["test.yml"]
    assert test_workflow.count(f"git -C /tmp/ocp checkout {PIN}") == 1
    assert f"--upstream-commit {PIN}" in test_workflow
    assert LOCAL_TF in test_workflow


def test_release_asset_builder_is_reusable_not_a_second_pr_full_conversion():
    workflow = _workflow_texts()["build-corpus-release-assets.yml"]

    assert "workflow_call:" in workflow
    assert "pull_request:" not in workflow
    assert workflow.count(FULL_CONVERT) == 1


def test_surviving_full_corpus_job_keeps_tracked_advanced_app_startup_coverage():
    test_workflow = _workflow_texts()["test.yml"]

    # These assertions intentionally bind advanced-app coverage to the same
    # exact local materialization that crossed the fresh release-wheel gates.
    assert "pinned-upstream-integration:" in test_workflow
    assert "from tf.advanced.app import findApp" in test_workflow
    assert "app = findApp(" in test_workflow
    assert "f\"app:{Path('app').resolve()}\"" in test_workflow
    assert f'locations=["{LOCAL_TF}"]' in test_workflow
    assert 'version="0.2"' in test_workflow
    assert 'assert app.__class__.__name__ == "TfApp"' in test_workflow
    assert "assert app.api.F.otype.maxSlot == 922922" in test_workflow
    assert 'app.api.T.nodeFromSection(("1En__Ethiopic", "1", "1"))' in test_workflow


def test_pinned_full_corpus_acceptance_verifies_serialized_historical_classification_api():
    test_workflow = _workflow_texts()["test.yml"]
    comparison = (ROOT / "tests" / "pinned_comparison_acceptance.py").read_text(
        encoding="utf-8"
    )

    # Reuse the existing acceptance invocation and its already-materialized
    # full corpus instead of creating another expensive pinned conversion.
    assert test_workflow.count(
        f"python tests/pinned_comparison_acceptance.py {LOCAL_TF}"
    ) == 1
    assert "from pinned_classification_acceptance import verify as verify_classifications" in comparison
    assert "verify_classifications(tf_dir)" in comparison


def test_duplicate_full_app_materialization_workflow_is_removed():
    assert not (WORKFLOWS / "full-app-integration.yml").exists()
