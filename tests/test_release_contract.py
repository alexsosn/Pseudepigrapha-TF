from __future__ import annotations

from pathlib import Path
import tomllib

from pseudepigrapha_tf import __version__
from pseudepigrapha_tf.cli import _parser


def test_release_versions_and_default_dataset_path_are_consistent() -> None:
    pyproject = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))

    assert pyproject["project"]["version"] == "0.1.0"
    assert __version__ == "0.1.0"

    args = _parser().parse_args(["convert", "source"])
    assert args.output == Path("tf/0.1")


def test_readme_documents_noneditable_runtime_install() -> None:
    readme = Path("README.md").read_text(encoding="utf-8")
    install_section = readme.split("## Install", 1)[1].split("## Convert OCP", 1)[0]

    assert "pip install ." in install_section
