"""RED-first regressions: valid JSON numbers must not silently underflow to zero."""

from __future__ import annotations

import json
import math
from pathlib import Path

import pytest

from pseudepigrapha_tf.metadata import _encode_scalar, load_public_metadata


def _docs(tmp_path: Path, *, location: str, token: str) -> Path:
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "One.xml").write_text(
        '<book filename="One" title="One"></book>', encoding="utf-8"
    )
    payload = {
        "_meta": {"counter": 1.0},
        "documents": {
            "One.xml": {
                "title": "One",
                "version": 1.0,
                "citation": "Citation",
                "fields": {"status": 1.0},
            },
        },
    }
    raw = json.dumps(payload, ensure_ascii=False)
    name, replacement = {
        "title": ("title", '"title": "One"'),
        "version": ("version", '"version": 1.0'),
        "citation": ("citation", '"citation": "Citation"'),
        "status": ("status", '"status": 1.0'),
        "_meta.counter": ("counter", '"counter": 1.0'),
    }[location]
    assert raw.count(replacement) == 1
    raw = raw.replace(replacement, f'"{name}": {token}', 1)
    (docs / "intros.json").write_text(raw, encoding="utf-8")
    return docs


@pytest.mark.parametrize(
    ("location", "token"),
    [
        ("version", "1e-9999"),
        ("version", "-1e-9999"),
        ("version", "1e-324"),
        ("status", "1E-9999"),
        ("citation", "-1e-324"),
        ("title", "1e-9999"),
        ("_meta.counter", "1e-9999"),
    ],
)
def test_public_json_rejects_nonzero_numeric_underflow(
    tmp_path: Path, location: str, token: str
) -> None:
    docs = _docs(tmp_path, location=location, token=token)
    with pytest.raises(ValueError, match=r"intros[.]json.*underflow.*nonzero"):
        load_public_metadata(docs)


@pytest.mark.parametrize(
    ("token", "expected"),
    [
        ("0e-9999", 0.0),
        ("-0e-9999", -0.0),
        ("0.000e-99999", 0.0),
        ("-0.000E+99999", -0.0),
        ("5e-324", 5e-324),
        ("1e308", 1e308),
    ],
)
def test_public_json_keeps_true_zeros_and_representable_nonzero_numbers(
    tmp_path: Path, token: str, expected: float
) -> None:
    docs = _docs(tmp_path, location="version", token=token)
    document = load_public_metadata(docs).documents["One.xml"]
    assert document.version == expected
    if expected == 0.0:
        assert math.copysign(1.0, document.version) == math.copysign(1.0, expected)
    else:
        assert document.version != 0.0
    assert json.loads(_encode_scalar(document.version)) == expected
