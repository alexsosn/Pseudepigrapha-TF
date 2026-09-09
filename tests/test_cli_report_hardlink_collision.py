from pathlib import Path

import pytest

from pseudepigrapha_tf import cli

FIXTURES = Path(__file__).parent / "fixtures"


def test_failed_audit_rejects_external_report_hardlink_to_existing_tf_feature(monkeypatch, tmp_path):
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    (source_dir / "sample.xml").write_text(
        (FIXTURES / "sample.xml").read_text(encoding="utf-8"),
        encoding="utf-8",
    )

    output = tmp_path / "tf"
    output.mkdir()
    feature = output / "otype.tf"
    sentinel = b"@node\n@valueType=str\n1\told-word\n"
    feature.write_bytes(sentinel)
    (output / "oslots.tf").write_bytes(b"@edge\n1\t1\n")

    # Path resolution cannot distinguish this external pathname from an ordinary
    # report, but writing it in place mutates the same inode as OUTPUT/otype.tf.
    report_path = tmp_path / "external-report.json"
    report_path.hardlink_to(feature)
    assert report_path.samefile(feature)

    failed_report = {
        "status": "failed",
        "failed_checks": ["forced_failure"],
        "diagnostics": {"duplicate_section_addresses": []},
    }
    monkeypatch.setattr(
        cli,
        "build_conversion_report",
        lambda source, books, data: failed_report,
    )

    def writer_must_not_run(data, output_dir):
        raise AssertionError("Text-Fabric writer must not run for a report collision")

    monkeypatch.setattr(cli, "_write_prevalidated_tf", writer_must_not_run)

    with pytest.raises(ValueError, match="report.*Text-Fabric|Text-Fabric.*report"):
        try:
            cli.main(
                [
                    "convert",
                    str(source_dir),
                    "--output",
                    str(output),
                    "--report",
                    str(report_path),
                    "--upstream-commit",
                    "test-commit",
                ]
            )
        finally:
            # The pre-existing corpus must survive even when the semantic audit
            # fails and would otherwise publish the diagnostic report directly.
            assert feature.read_bytes() == sentinel

    assert report_path.samefile(feature)
