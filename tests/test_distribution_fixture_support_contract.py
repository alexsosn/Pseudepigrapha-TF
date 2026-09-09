from __future__ import annotations

from pathlib import Path


POSITIVE_BASELINE_MODULES = (
    "test_distribution_directory_validation.py",
    "test_distribution_feature_set.py",
    "test_distribution_manifest.py",
    "test_distribution_provenance_closure.py",
    "test_distribution_staging.py",
)


def test_nominal_distribution_fixtures_do_not_reimplement_canonical_profile_builders():
    """Keep the complete positive release profile in one test-support source."""

    tests = Path(__file__).parent
    offenders = []
    for name in POSITIVE_BASELINE_MODULES:
        source = (tests / name).read_text(encoding="utf-8")
        if "def _canonical_generic(" in source or "def _canonical_otype_payload(" in source:
            offenders.append(name)

    assert offenders == [], (
        "canonical positive distribution fixture builders are duplicated in: "
        + ", ".join(offenders)
    )
