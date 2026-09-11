from __future__ import annotations

from pathlib import Path
import tomllib


def test_runtime_dependency_installs_text_fabric_github_backend() -> None:
    pyproject = tomllib.loads(Path('pyproject.toml').read_text(encoding='utf-8'))
    dependencies = tuple(pyproject['project']['dependencies'])

    assert any(
        dependency.startswith('text-fabric[github]')
        for dependency in dependencies
    ), (
        'normal Pseudepigrapha-TF installation must include Text-Fabric\'s '
        'GitHub backend because the supported corpus acquisition path downloads '
        'the public GitHub release'
    )
