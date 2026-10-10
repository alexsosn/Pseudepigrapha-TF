"""Fault-injection contract: report publication and TF features are one CLI generation."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from pseudepigrapha_tf import cli
from pseudepigrapha_tf.distribution import feature_directory_identity


FIXTURE = Path(__file__).parent / "fixtures" / "sample.xml"


class CompleteStageFabric:
    """Save a new generation without expensive corpus serialization."""

    save_count = 0

    def __init__(self, *args, **kwargs):
        pass

    def save(self, **kwargs):
        self.__class__.save_count += 1
        stage = Path(kwargs["location"])
        (stage / "otype.tf").write_bytes(b"new type\n")
        (stage / "oslots.tf").write_bytes(b"new slots\n")
        (stage / "new-only.tf").write_bytes(b"new feature\n")
        return True


def setup_case(tmp_path, monkeypatch):
    import tf.fabric

    source = tmp_path / "source"
    source.mkdir()
    (source / "sample.xml").write_bytes(FIXTURE.read_bytes())
    output = tmp_path / "tf"
    output.mkdir()
    (output / "otype.tf").write_bytes(b"previous type\n")
    (output / "oslots.tf").write_bytes(b"previous slots\n")
    (output / "removed-in-new.tf").write_bytes(b"previous feature\n")
    (output / "conversion-report.json").write_bytes(b'{"status":"previous"}\n')
    (output / "researcher-notes.txt").write_bytes(b"retain user sidecar\n")
    old = {p.name: p.read_bytes() for p in output.iterdir()}
    CompleteStageFabric.save_count = 0
    monkeypatch.setattr(tf.fabric, "Fabric", CompleteStageFabric)
    return source, output, old


def convert(source, output):
    return cli.main(
        ["convert", str(source), "--output", str(output), "--upstream-commit", "test-commit"]
    )


def test_feature_identity_failure_after_install_restores_old_complete_generation(monkeypatch, tmp_path):
    source, output, old = setup_case(tmp_path, monkeypatch)

    def fail_after_install(_output):
        # Prove this failure happens *after* new TF files really are visible.
        assert (output / "otype.tf").read_bytes() == b"new type\n"
        assert (output / "new-only.tf").read_bytes() == b"new feature\n"
        raise OSError("feature identity failure after TF install")

    monkeypatch.setattr(cli, "feature_directory_identity", fail_after_install)
    with pytest.raises(OSError, match="feature identity failure after TF install"):
        convert(source, output)

    assert CompleteStageFabric.save_count == 1
    assert {p.name: p.read_bytes() for p in output.iterdir()} == old


def test_final_report_rename_failure_restores_old_tf_and_report(monkeypatch, tmp_path):
    source, output, old = setup_case(tmp_path, monkeypatch)
    original_replace = Path.replace
    injected = []

    def fail_report_publication(self, target):
        target = Path(target)
        if self.parent.name.startswith(".pseudepigrapha-tf-report-") and target == output / "conversion-report.json":
            assert (output / "otype.tf").read_bytes() == b"new type\n"
            injected.append(self)
            raise OSError("report publication failed")
        return original_replace(self, target)

    monkeypatch.setattr(Path, "replace", fail_report_publication)
    with pytest.raises(OSError, match="report publication failed"):
        convert(source, output)

    assert len(injected) == 1
    assert CompleteStageFabric.save_count == 1
    assert {p.name: p.read_bytes() for p in output.iterdir()} == old


def test_interrupt_during_report_publication_restores_old_generation(monkeypatch, tmp_path):
    source, output, old = setup_case(tmp_path, monkeypatch)
    original_replace = Path.replace

    def interrupt_report_publish(self, target):
        target = Path(target)
        if self.parent.name.startswith(".pseudepigrapha-tf-report-") and target == output / "conversion-report.json":
            raise KeyboardInterrupt("report publication interrupted")
        return original_replace(self, target)

    monkeypatch.setattr(Path, "replace", interrupt_report_publish)
    with pytest.raises(KeyboardInterrupt, match="report publication interrupted"):
        convert(source, output)

    assert CompleteStageFabric.save_count == 1
    assert {p.name: p.read_bytes() for p in output.iterdir()} == old


def test_successful_report_publication_still_binds_exact_tf_generation(monkeypatch, tmp_path):
    source, output, _old = setup_case(tmp_path, monkeypatch)
    assert convert(source, output) == 0
    assert CompleteStageFabric.save_count == 1
    report = json.loads((output / "conversion-report.json").read_text(encoding="utf-8"))
    assert report["status"] == "ok"
    assert report["text_fabric"] == feature_directory_identity(output)
    assert (output / "researcher-notes.txt").read_bytes() == b"retain user sidecar\n"
    assert not (output / "removed-in-new.tf").exists()
    assert (output / "new-only.tf").read_bytes() == b"new feature\n"


def test_failed_report_commit_plus_failed_rollback_retains_recoverable_backup(monkeypatch, tmp_path):
    source, output, old = setup_case(tmp_path, monkeypatch)
    original_replace = Path.replace
    report_failed = False
    rollback_failed = False

    def fail_report_then_restore(self, target):
        nonlocal report_failed, rollback_failed
        target = Path(target)
        if self.parent.name.startswith(".pseudepigrapha-tf-report-") and target == output / "conversion-report.json":
            report_failed = True
            raise OSError("report finalization exception")
        if (
            report_failed
            and not rollback_failed
            and self.parent.name.startswith(".pseudepigrapha-tf-backup-")
            and self.suffix == ".tf"
            and target.parent == output
        ):
            rollback_failed = True
            raise OSError("TF rollback exception")
        return original_replace(self, target)

    monkeypatch.setattr(Path, "replace", fail_report_then_restore)
    with pytest.raises(RuntimeError, match="rollback also failed") as caught:
        convert(source, output)

    assert report_failed and rollback_failed
    assert "report finalization exception" in str(caught.value)
    assert "TF rollback exception" in str(caught.value)
    assert (output / "conversion-report.json").read_bytes() == old["conversion-report.json"]
    backup_dirs = [
        d for d in tmp_path.iterdir()
        if d.is_dir() and d.name.startswith(".pseudepigrapha-tf-backup-")
    ]
    assert backup_dirs, "recoverable old TF generation must survive a failed rollback"
    assert any(
        p.read_bytes() == old["otype.tf"]
        for d in backup_dirs for p in d.glob("*.tf")
    )


def test_failed_report_commit_does_not_leave_new_generation_for_fresh_output(monkeypatch, tmp_path):
    source, output, old = setup_case(tmp_path, monkeypatch)
    for name in ("otype.tf", "oslots.tf", "removed-in-new.tf"):
        (output / name).unlink()
    original_replace = Path.replace

    def fail_report(self, target):
        if self.parent.name.startswith(".pseudepigrapha-tf-report-"):
            raise OSError("report unavailable")
        return original_replace(self, target)

    monkeypatch.setattr(Path, "replace", fail_report)
    with pytest.raises(OSError, match="report unavailable"):
        convert(source, output)

    assert not list(output.glob("*.tf"))
    assert (output / "conversion-report.json").read_bytes() == old["conversion-report.json"]
    assert (output / "researcher-notes.txt").read_bytes() == old["researcher-notes.txt"]
