from __future__ import annotations

from pathlib import Path

import pytest

import pseudepigrapha_tf.writer as writer


def _seed_transaction(tmp_path: Path) -> tuple[Path, Path, dict[str, bytes]]:
    output = tmp_path / "tf"
    stage = tmp_path / "stage"
    output.mkdir()
    stage.mkdir()
    for name, text in (
        ("otype.tf", "old otype\n"),
        ("oslots.tf", "old oslots\n"),
        ("obsolete.tf", "old obsolete\n"),
        ("conversion-report.json", '{"old": true}\n'),
    ):
        (output / name).write_text(text, encoding="utf-8")
    for name, text in (
        ("oslots.tf", "new oslots\n"),
        ("otype.tf", "new otype\n"),
        ("new_feature.tf", "new only\n"),
    ):
        (stage / name).write_text(text, encoding="utf-8")
    before = {path.name: path.read_bytes() for path in output.iterdir()}
    return stage, output, before


def test_cleanup_interrupt_after_successful_rollback_preserves_original_error(monkeypatch, tmp_path):
    stage, output, before = _seed_transaction(tmp_path)
    original_replace = Path.replace
    original_rmdir = Path.rmdir
    install_error = OSError("install boom")
    cleanup_interrupt = KeyboardInterrupt("cleanup interrupted")
    staged_moves = 0

    def fail_second_staged_move(self: Path, target):
        nonlocal staged_moves
        target = Path(target)
        if self.parent == stage and target.parent == output:
            staged_moves += 1
            if staged_moves == 2:
                raise install_error
        return original_replace(self, target)

    def interrupt_backup_cleanup(self: Path):
        if self.parent == tmp_path and self.name.startswith(".pseudepigrapha-tf-backup-"):
            raise cleanup_interrupt
        return original_rmdir(self)

    monkeypatch.setattr(Path, "replace", fail_second_staged_move)
    monkeypatch.setattr(Path, "rmdir", interrupt_backup_cleanup)

    with pytest.raises(OSError) as caught:
        writer._install_staged_tf_features(stage, output)

    assert caught.value is install_error
    assert {path.name: path.read_bytes() for path in output.iterdir()} == before


def test_cleanup_interrupt_after_commit_cannot_turn_committed_install_into_failure(monkeypatch, tmp_path):
    stage, output, before = _seed_transaction(tmp_path)
    original_rmtree = writer.shutil.rmtree
    cleanup_interrupt = KeyboardInterrupt("cleanup interrupted")

    def interrupt_backup_cleanup(path, *args, **kwargs):
        candidate = Path(path)
        if candidate.parent == tmp_path and candidate.name.startswith(".pseudepigrapha-tf-backup-"):
            raise cleanup_interrupt
        return original_rmtree(path, *args, **kwargs)

    monkeypatch.setattr(writer.shutil, "rmtree", interrupt_backup_cleanup)

    assert writer._install_staged_tf_features(stage, output) is None
    assert (output / "otype.tf").read_bytes() == b"new otype\n"
    assert (output / "oslots.tf").read_bytes() == b"new oslots\n"
    assert (output / "new_feature.tf").read_bytes() == b"new only\n"
    assert not (output / "obsolete.tf").exists()
    assert (output / "conversion-report.json").read_bytes() == before["conversion-report.json"]
