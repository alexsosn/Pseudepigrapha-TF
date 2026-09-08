from __future__ import annotations

from pathlib import Path

from pseudepigrapha_tf import cli
from pseudepigrapha_tf.release_identity import TF_DATA_VERSION


def test_cli_parser_exposes_browse_on_same_command_surface():
    args = cli._parser().parse_args(
        [
            "browse",
            "/tmp/tf",
            "--app",
            "/tmp/app",
            "--version",
            "0.1",
            "--port",
            "8123",
            "--debug",
        ]
    )

    assert args.command == "browse"
    assert args.data == Path("/tmp/tf")
    assert args.app == Path("/tmp/app")
    assert args.version == "0.1"
    assert args.port == 8123
    assert args.debug is True


def test_cli_browse_default_version_tracks_release_identity():
    args = cli._parser().parse_args(["browse", "/tmp/tf"])

    assert args.version == TF_DATA_VERSION
    assert args.app == Path("app")


def test_cli_browse_delegates_to_stock_tf_comparison_runner(monkeypatch):
    captured = {}

    def fake_runner(data_path, app_path, *, version, port, debug):
        captured.update(
            data_path=data_path,
            app_path=app_path,
            version=version,
            port=port,
            debug=debug,
        )
        return 23

    monkeypatch.setattr(cli, "run_local_comparison_browser", fake_runner, raising=False)

    result = cli.main(
        [
            "browse",
            "/tmp/tf",
            "--app",
            "/tmp/app",
            "--version",
            "0.1",
            "--port",
            "8123",
        ]
    )

    assert result == 23
    assert captured == {
        "data_path": Path("/tmp/tf"),
        "app_path": Path("/tmp/app"),
        "version": "0.1",
        "port": 8123,
        "debug": False,
    }
