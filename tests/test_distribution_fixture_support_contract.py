from __future__ import annotations

from pathlib import Path

import pytest

from pseudepigrapha_tf.provenance import (
    OCP_PIN,
    OCP_REPOSITORY,
    corpus_license_metadata,
    report_provenance,
)
from distribution_support import (
    canonical_generic,
    canonical_otype_payload,
    canonical_report_provenance,
)


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


def test_shared_positive_fixture_tracks_every_canonical_verified_profile_field():
    generic = canonical_generic()
    expected_profile = corpus_license_metadata(
        OCP_REPOSITORY,
        OCP_PIN,
        source_identity_verified=True,
    )

    assert {key: generic[key] for key in expected_profile} == expected_profile
    assert canonical_report_provenance() == report_provenance(generic)

    payload = canonical_otype_payload()
    for key, value in generic.items():
        assert f"@{key}={value}\n".encode("utf-8") in payload


def test_shared_report_fixture_keeps_hostile_omission_explicit_and_isolated():
    baseline = canonical_report_provenance()
    omitted = canonical_report_provenance(omit=("content_attribution",))

    assert "content_attribution" in baseline
    assert "content_attribution" not in omitted
    assert {
        key: value for key, value in baseline.items() if key != "content_attribution"
    } == omitted
    assert "content_attribution" in canonical_report_provenance()


def test_shared_report_fixture_rejects_unknown_omission_key():
    """A hostile omission must fail if it no longer names a real baseline field."""

    with pytest.raises(KeyError, match="not_a_real_provenance_key"):
        canonical_report_provenance(omit=("not_a_real_provenance_key",))


def test_shared_generic_fixture_returns_fresh_state_for_each_test():
    mutated = canonical_generic()
    mutated["contentLicense"] = "HOSTILE-TEST-VALUE"

    assert canonical_generic()["contentLicense"] != "HOSTILE-TEST-VALUE"
