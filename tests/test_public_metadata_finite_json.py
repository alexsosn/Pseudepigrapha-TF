"""RED-first non-finite intros.json scalar regression tests (issue #209)."""

from __future__ import annotations

import json
import math
from pathlib import Path

import pytest

from pseudepigrapha_tf.metadata import _encode_scalar, load_public_metadata


def _source(tmp_path: Path, *, field: str, token: str) -> Path:
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "One.xml").write_text(
        '<book filename="One" title="One"></book>', encoding="utf-8"
    )
    payload = {
        "_meta": {"exported": "2026-10-11", "counter": 0.0},
        "documents": {
            "One.xml": {
                "title": "One",
                "version": 1.0,
                "citation": "Citation",
                "fields": {"status": 0.0},
            }
        },
    }
    raw = json.dumps(payload, ensure_ascii=False)
    old = {
        "version": '"version": 1.0',
        "title": '"title": "One"',
        "citation": '"citation": "Citation"',
        "status": '"status": 0.0',
        "_meta.counter": '"counter": 0.0',
    }[field]
    name = field.rsplit(".", 1)[-1]
    assert raw.count(old) == 1, (field, raw)
    raw = raw.replace(old, f'"{name}": {token}', 1)
    (docs / "intros.json").write_text(raw, encoding="utf-8")
    return docs


@pytest.mark.parametrize(
    "field,token",
    [
        ("version", "NaN"),
        ("title", "Infinity"),
        ("citation", "-Infinity"),
        ("status", "NaN"),
        ("version", "1e9999"),
        ("_meta.counter", "1e9999"),
    ],
)
def test_loader_rejects_nonfinite_json_constants_and_overflow(
    tmp_path: Path, field: str, token: str
) -> None:
    docs = _source(tmp_path, field=field, token=token)
    with pytest.raises(ValueError, match="non-finite|out of range|invalid JSON constant"):
        load_public_metadata(docs)


@pytest.mark.parametrize("value", [float("nan"), float("inf"), -float("inf")])
def test_encoder_rejects_programmatic_nonfinite_metadata(value: float) -> None:
    with pytest.raises(ValueError):
        _encode_scalar(value)


def test_large_finite_json_numeric_and_other_valid_scalars_are_preserved(tmp_path: Path) -> None:
    docs = _source(tmp_path, field="version", token="1e308")
    corpus = load_public_metadata(docs)
    document = corpus.documents["One.xml"]
    assert math.isfinite(document.version)
    assert document.version == 1e308
    encoded = _encode_scalar(document.version)
    assert json.loads(
        encoded,
        parse_constant=lambda token: (_ for _ in ()).throw(
            AssertionError(f"invalid JSON constant: {token}")
        ),
    ) == 1e308
    for valid in ("alpha\u0000beta", True, False, None, 2, 1.25):
        assert json.loads(_encode_scalar(valid)) == valid
