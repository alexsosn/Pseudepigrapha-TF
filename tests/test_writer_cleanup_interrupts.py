from __future__ import annotations

from pathlib import Path

import pytest

import pseudepigrapha_tf.writer as writer
from pseudepigrapha_tf.graph import build_tf_data
from pseudepigrapha_tf.parser import parse_file


FIXTURE = Path(__file__).parent / "fixtures" / "sample.xml"


class CompleteStageFabric:
    def __init__(self, *args, **kwargs):
        pass

    def save(self, **kwargs):
        stage = Path(kwargs["location"])
        for name, text in (
            ("oslots.tf", "new oslots\n"),
            ("otype.tf", "new otype\n"),
            ("new_feature.tf", "new only\n"),
        ):
            (stage / name).write_text(text, encoding="utf-8")
        return True


class FalseStageFabric:
    def __init__(self, *args, **kwargs):
        pass

    def save(self, **kwargs):
        stage = Path(kwargs["location"])
        (stage / "partial.tf").write_text("partial stage\n", encoding="utf-8")
        return False


class RaisingStageFabric:
    error: BaseException | None = None

    def __init__(self, *args, **kwargs):
        pass

    def save(self, **kwargs):
        stage = Path(kwargs["location"])
        (stage / "partial.tf").write_text("partial stage\n", encoding="utf-8")
        assert self.__class__.error is not None
        raise self.__class__.error


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


def _seed_writer_output(tmp_path: Path) -> tuple[Path, dict[str, bytes]]:
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


def _inject_stage_cleanup_failure(monkeypatch, tmp_path: Path, cleanup_error: BaseException) -> None:
    original_rmtree = writer.shutil.rmtree

    def fail_stage_cleanup(path, *args, **kwargs):
        candidate = Path(path)
        is_stage = (
            candidate.parent == tmp_path
            and candidate.name.startswith(".pseudepigrapha-tf-")
            and not candidate.name.startswith(".pseudepigrapha-tf-backup-")
        )
        if is_stage:
            raise cleanup_error
        return original_rmtree(path, *args, **kwargs)

    monkeypatch.setattr(writer.shutil, "rmtree", fail_stage_cleanup)


def _standard_write_with_stage_cleanup_failure(monkeypatch, tmp_path: Path, cleanup_error: BaseException):
    import tf.fabric

    output, _ = _seed_writer_output(tmp_path)
    monkeypatch.setattr(tf.fabric, "Fabric", CompleteStageFabric)
    _inject_stage_cleanup_failure(monkeypatch, tmp_path, cleanup_error)

    data = build_tf_data([parse_file(FIXTURE)])
    with pytest.warns(RuntimeWarning, match="staging directory cleanup failed"):
        try:
            result = writer.write_tf(data, output)
        except BaseException as exc:
            pytest.fail(
                f"post-commit stage cleanup {type(exc).__name__} escaped write_tf: {exc}"
            )

    assert result is True
    assert (output / "otype.tf").read_bytes() == b"new otype\n"
    assert (output / "oslots.tf").read_bytes() == b"new oslots\n"
    assert (output / "new_feature.tf").read_bytes() == b"new only\n"
    assert not (output / "obsolete.tf").exists()
    assert (output / "conversion-report.json").read_bytes() == b'{"old": true}\n'


def test_stage_cleanup_oserror_after_commit_cannot_turn_write_into_failure(monkeypatch, tmp_path):
    _standard_write_with_stage_cleanup_failure(
        monkeypatch,
        tmp_path,
        OSError("stage cleanup failed"),
    )


def test_stage_cleanup_interrupt_after_commit_cannot_turn_write_into_failure(monkeypatch, tmp_path):
    _standard_write_with_stage_cleanup_failure(
        monkeypatch,
        tmp_path,
        KeyboardInterrupt("stage cleanup interrupted"),
    )


def test_stage_cleanup_failure_cannot_turn_false_serializer_result_into_exception(monkeypatch, tmp_path):
    import tf.fabric

    output, before = _seed_writer_output(tmp_path)
    monkeypatch.setattr(tf.fabric, "Fabric", FalseStageFabric)
    _inject_stage_cleanup_failure(monkeypatch, tmp_path, OSError("stage cleanup failed"))

    data = build_tf_data([parse_file(FIXTURE)])
    with pytest.warns(RuntimeWarning, match="staging directory cleanup failed"):
        assert writer.write_tf(data, output) is False

    assert {path.name: path.read_bytes() for path in output.iterdir()} == before


def test_stage_cleanup_failure_cannot_replace_serializer_exception(monkeypatch, tmp_path):
    import tf.fabric

    output, before = _seed_writer_output(tmp_path)
    serializer_error = OSError("serializer boom")
    RaisingStageFabric.error = serializer_error
    monkeypatch.setattr(tf.fabric, "Fabric", RaisingStageFabric)
    _inject_stage_cleanup_failure(
        monkeypatch,
        tmp_path,
        KeyboardInterrupt("stage cleanup interrupted"),
    )

    data = build_tf_data([parse_file(FIXTURE)])
    with pytest.warns(RuntimeWarning, match="staging directory cleanup failed"):
        with pytest.raises(OSError) as caught:
            writer.write_tf(data, output)

    assert caught.value is serializer_error
    assert {path.name: path.read_bytes() for path in output.iterdir()} == before


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


def test_nonfatal_warning_hook_baseexception_cannot_escape(monkeypatch):
    warning_interrupt = KeyboardInterrupt("warning hook interrupted")

    def interrupting_showwarning(*args, **kwargs):
        raise warning_interrupt

    monkeypatch.setattr(writer.warnings, "showwarning", interrupting_showwarning)

    assert writer._warn_nonfatal("cleanup diagnostic") is None
