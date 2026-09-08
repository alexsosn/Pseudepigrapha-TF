from __future__ import annotations

import warnings
from pathlib import Path

import pytest

from pseudepigrapha_tf.graph import build_tf_data
from pseudepigrapha_tf.parser import parse_file
from pseudepigrapha_tf.writer import write_tf


FIXTURE = Path(__file__).parent / "fixtures" / "sample.xml"


class CompleteStageFabric:
    stage: Path | None = None

    def __init__(self, *args, **kwargs):
        pass

    def save(self, **kwargs):
        stage = Path(kwargs["location"])
        self.__class__.stage = stage
        for name, text in (
            ("oslots.tf", "new oslots\n"),
            ("otype.tf", "new otype\n"),
            ("new_feature.tf", "new-only feature\n"),
        ):
            (stage / name).write_text(text, encoding="utf-8")
        return True


def _seed_output(tmp_path: Path) -> tuple[Path, dict[str, bytes]]:
    output = tmp_path / "tf"
    output.mkdir()
    for name, text in (
        ("otype.tf", "old otype\n"),
        ("oslots.tf", "old oslots\n"),
        ("obsolete.tf", "old obsolete\n"),
        ("conversion-report.json", '{"old": true}\n'),
    ):
        (output / name).write_text(text, encoding="utf-8")
    return output, {path.name: path.read_bytes() for path in output.iterdir()}


def _assert_exact_output(output: Path, expected: dict[str, bytes]) -> None:
    assert {path.name: path.read_bytes() for path in output.iterdir()} == expected


def _standard_write(monkeypatch, output: Path) -> bool:
    import tf.fabric

    CompleteStageFabric.stage = None
    monkeypatch.setattr(tf.fabric, "Fabric", CompleteStageFabric)
    return write_tf(build_tf_data([parse_file(FIXTURE)]), output)


def test_mid_install_failure_restores_entire_previous_tf_set(monkeypatch, tmp_path):
    output, before = _seed_output(tmp_path)
    original_replace = Path.replace
    install_error = OSError("install boom")
    staged_installs = 0

    def fail_second_staged_install(self: Path, target):
        nonlocal staged_installs
        target = Path(target)
        if CompleteStageFabric.stage is not None and self.parent == CompleteStageFabric.stage and target.parent == output:
            staged_installs += 1
            if staged_installs == 2:
                raise install_error
        return original_replace(self, target)

    monkeypatch.setattr(Path, "replace", fail_second_staged_install)

    with pytest.raises(OSError) as caught:
        _standard_write(monkeypatch, output)

    assert caught.value is install_error
    assert staged_installs == 2
    _assert_exact_output(output, before)


def test_backup_failure_restores_files_already_moved_out_of_output(monkeypatch, tmp_path):
    output, before = _seed_output(tmp_path)
    original_replace = Path.replace
    backup_error = OSError("backup boom")
    backup_moves = 0

    def fail_second_backup_move(self: Path, target):
        nonlocal backup_moves
        target = Path(target)
        if self.parent == output and self.suffix == ".tf" and target.parent != output:
            backup_moves += 1
            if backup_moves == 2:
                raise backup_error
        return original_replace(self, target)

    monkeypatch.setattr(Path, "replace", fail_second_backup_move)

    with pytest.raises(OSError) as caught:
        _standard_write(monkeypatch, output)

    assert caught.value is backup_error
    assert backup_moves == 2
    _assert_exact_output(output, before)


def test_rollback_failure_reports_both_errors_and_retains_recoverable_backup(monkeypatch, tmp_path):
    output, before = _seed_output(tmp_path)
    original_replace = Path.replace
    install_error = OSError("install boom")
    rollback_error = OSError("rollback boom")
    staged_installs = 0
    install_failed = False
    rollback_failed = False

    def fail_install_then_rollback(self: Path, target):
        nonlocal staged_installs, install_failed, rollback_failed
        target = Path(target)
        stage = CompleteStageFabric.stage
        if stage is not None and self.parent == stage and target.parent == output:
            staged_installs += 1
            if staged_installs == 2:
                install_failed = True
                raise install_error
        elif (
            install_failed
            and not rollback_failed
            and self.parent != output
            and self.parent != stage
            and self.suffix == ".tf"
            and target.parent == output
        ):
            rollback_failed = True
            raise rollback_error
        return original_replace(self, target)

    monkeypatch.setattr(Path, "replace", fail_install_then_rollback)

    with pytest.raises(Exception) as caught:
        _standard_write(monkeypatch, output)

    messages: list[str] = []
    seen: set[int] = set()
    current: BaseException | None = caught.value
    while current is not None and id(current) not in seen:
        seen.add(id(current))
        messages.append(str(current))
        current = current.__cause__ or current.__context__
    diagnostic = " | ".join(messages)
    assert "install boom" in diagnostic
    assert "rollback boom" in diagnostic
    assert rollback_failed is True
    assert (output / "conversion-report.json").read_bytes() == before["conversion-report.json"]

    retained: list[Path] = []
    for directory in tmp_path.iterdir():
        if directory == output or not directory.is_dir():
            continue
        retained.extend(directory.glob("*.tf"))
    assert retained, "rollback failure must retain a recoverable backup outside the cleaned staging directory"
    old_tf_bytes = {value for name, value in before.items() if name.endswith(".tf")}
    assert any(path.read_bytes() in old_tf_bytes for path in retained)


def test_keyboard_interrupt_during_install_restores_previous_tf_set_before_reraise(monkeypatch, tmp_path):
    output, before = _seed_output(tmp_path)
    original_replace = Path.replace
    interrupt = KeyboardInterrupt("install interrupted")
    staged_installs = 0

    def interrupt_second_staged_install(self: Path, target):
        nonlocal staged_installs
        target = Path(target)
        if CompleteStageFabric.stage is not None and self.parent == CompleteStageFabric.stage and target.parent == output:
            staged_installs += 1
            if staged_installs == 2:
                raise interrupt
        return original_replace(self, target)

    monkeypatch.setattr(Path, "replace", interrupt_second_staged_install)

    with pytest.raises(KeyboardInterrupt) as caught:
        _standard_write(monkeypatch, output)

    assert caught.value is interrupt
    assert staged_installs == 2
    _assert_exact_output(output, before)


def test_successful_rollback_cleanup_failure_warns_and_reraises_original(monkeypatch, tmp_path):
    output, before = _seed_output(tmp_path)
    original_replace = Path.replace
    original_rmdir = Path.rmdir
    install_error = OSError("install boom")
    cleanup_error = OSError("backup cleanup boom")
    staged_installs = 0

    def fail_second_staged_install(self: Path, target):
        nonlocal staged_installs
        target = Path(target)
        if CompleteStageFabric.stage is not None and self.parent == CompleteStageFabric.stage and target.parent == output:
            staged_installs += 1
            if staged_installs == 2:
                raise install_error
        return original_replace(self, target)

    def fail_backup_rmdir(self: Path):
        if self.parent == tmp_path and self.name.startswith(".pseudepigrapha-tf-backup-"):
            raise cleanup_error
        return original_rmdir(self)

    monkeypatch.setattr(Path, "replace", fail_second_staged_install)
    monkeypatch.setattr(Path, "rmdir", fail_backup_rmdir)

    with pytest.warns(RuntimeWarning, match="backup cleanup boom"):
        with pytest.raises(OSError) as caught:
            _standard_write(monkeypatch, output)

    assert caught.value is install_error
    assert staged_installs == 2
    _assert_exact_output(output, before)


def test_committed_install_cleanup_failure_warns_without_turning_success_into_failure(monkeypatch, tmp_path):
    import pseudepigrapha_tf.writer as writer

    output, before = _seed_output(tmp_path)
    original_rmtree = writer.shutil.rmtree
    cleanup_error = OSError("committed backup cleanup boom")

    def fail_committed_backup_cleanup(path, *args, **kwargs):
        candidate = Path(path)
        if candidate.parent == tmp_path and candidate.name.startswith(".pseudepigrapha-tf-backup-"):
            raise cleanup_error
        return original_rmtree(path, *args, **kwargs)

    monkeypatch.setattr(writer.shutil, "rmtree", fail_committed_backup_cleanup)

    with pytest.warns(RuntimeWarning, match="committed backup cleanup boom"):
        assert _standard_write(monkeypatch, output) is True

    assert (output / "otype.tf").read_bytes() == b"new otype\n"
    assert (output / "oslots.tf").read_bytes() == b"new oslots\n"
    assert (output / "new_feature.tf").read_bytes() == b"new-only feature\n"
    assert not (output / "obsolete.tf").exists()
    assert (output / "conversion-report.json").read_bytes() == before["conversion-report.json"]
    retained = [
        path
        for directory in tmp_path.iterdir()
        if directory.is_dir() and directory != output
        for path in directory.glob("*.tf")
    ]
    assert retained, "post-commit cleanup failure must retain the old backup for manual cleanup"


def test_warning_as_error_cannot_replace_original_install_error_after_successful_rollback(monkeypatch, tmp_path):
    output, before = _seed_output(tmp_path)
    original_replace = Path.replace
    original_rmdir = Path.rmdir
    install_error = OSError("install boom")
    cleanup_error = OSError("backup cleanup boom")
    staged_installs = 0

    def fail_second_staged_install(self: Path, target):
        nonlocal staged_installs
        target = Path(target)
        if CompleteStageFabric.stage is not None and self.parent == CompleteStageFabric.stage and target.parent == output:
            staged_installs += 1
            if staged_installs == 2:
                raise install_error
        return original_replace(self, target)

    def fail_backup_rmdir(self: Path):
        if self.parent == tmp_path and self.name.startswith(".pseudepigrapha-tf-backup-"):
            raise cleanup_error
        return original_rmdir(self)

    monkeypatch.setattr(Path, "replace", fail_second_staged_install)
    monkeypatch.setattr(Path, "rmdir", fail_backup_rmdir)

    with warnings.catch_warnings():
        warnings.simplefilter("error", RuntimeWarning)
        with pytest.raises(OSError) as caught:
            _standard_write(monkeypatch, output)

    assert caught.value is install_error
    assert staged_installs == 2
    _assert_exact_output(output, before)


def test_warning_as_error_cannot_turn_committed_install_into_failure(monkeypatch, tmp_path):
    import pseudepigrapha_tf.writer as writer

    output, before = _seed_output(tmp_path)
    original_rmtree = writer.shutil.rmtree
    cleanup_error = OSError("committed backup cleanup boom")

    def fail_committed_backup_cleanup(path, *args, **kwargs):
        candidate = Path(path)
        if candidate.parent == tmp_path and candidate.name.startswith(".pseudepigrapha-tf-backup-"):
            raise cleanup_error
        return original_rmtree(path, *args, **kwargs)

    monkeypatch.setattr(writer.shutil, "rmtree", fail_committed_backup_cleanup)

    with warnings.catch_warnings():
        warnings.simplefilter("error", RuntimeWarning)
        assert _standard_write(monkeypatch, output) is True

    assert (output / "otype.tf").read_bytes() == b"new otype\n"
    assert (output / "oslots.tf").read_bytes() == b"new oslots\n"
    assert (output / "new_feature.tf").read_bytes() == b"new-only feature\n"
    assert not (output / "obsolete.tf").exists()
    assert (output / "conversion-report.json").read_bytes() == before["conversion-report.json"]
