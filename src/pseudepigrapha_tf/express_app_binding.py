from __future__ import annotations

from pathlib import Path
from zipfile import BadZipFile, ZipFile

from .distribution import (
    DEFAULT_REPOSITORY_NAME,
    DEFAULT_REPOSITORY_OWNER,
    EXPRESS_NAME,
    DistributionContractError,
    _EXPRESS_CHECKOUT_NAME,
    _EXPRESS_EXCLUDE,
    _collect_app_payloads,
    _require_repository_component,
    _safe_relative_parts,
    _validate_express_member,
)


def validate_express_app_directory(
    express_archive: str | Path,
    *,
    app_directory: str | Path,
    repository_owner: str = DEFAULT_REPOSITORY_OWNER,
    repository_name: str = DEFAULT_REPOSITORY_NAME,
) -> None:
    """Bind the app subtree in complete.zip to an exact checked-out app tree.

    Structural release validation and native TF byte equivalence remain the
    responsibility of ``validate_distribution``. This check supplies the
    independent release-checkout evidence that an archive hash alone cannot:
    every non-checkout app member must have exactly the same path and bytes as
    the tracked app directory after applying Text-Fabric's express exclusions.
    """

    express_archive = Path(express_archive)
    if express_archive.name != EXPRESS_NAME:
        raise DistributionContractError(
            f"Text-Fabric express archive filename must be {EXPRESS_NAME!r}, got {express_archive.name!r}"
        )
    if not express_archive.is_file():
        raise DistributionContractError(f"missing Text-Fabric express archive: {express_archive}")

    repository_owner = _require_repository_component(repository_owner, "repository owner")
    repository_name = _require_repository_component(repository_name, "repository name")
    expected = _collect_app_payloads(Path(app_directory))
    app_prefix = f"{repository_owner}/{repository_name}/app/"
    actual: dict[str, bytes] = {}

    try:
        with ZipFile(express_archive) as zf:
            infos = zf.infolist()
            names = [info.filename for info in infos]
            if len(set(names)) != len(names):
                raise DistributionContractError("Text-Fabric express archive contains duplicate members")
            for info in infos:
                _validate_express_member(info)
                name = info.filename
                if not name.startswith(app_prefix):
                    continue
                relative = name[len(app_prefix):]
                parts = _safe_relative_parts(relative, "Text-Fabric app member")
                if any(part in _EXPRESS_EXCLUDE for part in parts):
                    raise DistributionContractError(
                        f"Text-Fabric express archive contains excluded app member {name!r}"
                    )
                if relative == _EXPRESS_CHECKOUT_NAME:
                    continue
                actual[relative] = zf.read(info)
    except DistributionContractError:
        raise
    except (OSError, BadZipFile, RuntimeError, KeyError) as exc:
        raise DistributionContractError(f"could not verify Text-Fabric express app payloads: {exc}") from exc

    if set(actual) != set(expected):
        missing = sorted(set(expected) - set(actual))
        extra = sorted(set(actual) - set(expected))
        raise DistributionContractError(
            "Text-Fabric express app member set differs from tracked checkout; "
            f"missing={missing}, extra={extra}"
        )
    for name, expected_payload in expected.items():
        if actual[name] != expected_payload:
            raise DistributionContractError(
                f"Text-Fabric express app payload {name!r} differs from tracked checkout"
            )
