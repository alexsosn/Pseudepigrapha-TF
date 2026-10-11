# Issue #209 — enforce finite, standards-compliant public metadata scalars

Frozen source-grounded research and implementation plan. Commit this before RED regression tests and production modifications.

## Research

The public `intros.json` loader in `src/pseudepigrapha_tf/metadata.py` uses `json.loads(..., object_pairs_hook=_unique_json_object)`, so Python extensions `NaN`, `Infinity`, and `-Infinity` become IEEE non-finite floats. Even syntactically JSON-valid `1e9999` overflows to `float('inf')` at decode time. `_require_scalar()` accepts any float and `_encode_scalar()` defaults to `json.dumps(allow_nan=True)`, producing `NaN` or `Infinity` in TF `intro_*_json` features. This violates their declared lossless JSON-scalar encoding contract, including downstream independent strict JSON consumers.

Exact behavior reproduced in Python: `json.loads('NaN') -> nan`, `json.loads('1e9999') -> inf`, and `json.dumps(float('inf')) -> 'Infinity'`. In `tests/test_public_metadata.py`, normal `version: 1.0` and rich strings/null are covered, but non-finite tokens and floating exponent overflow are not. Historical catalogue loader `classifications.py` has a different typed schema and does not need changes.

## Frozen TDD and implementation gates

1. RED-only new `tests/test_public_metadata_finite_json.py` with temporary root `One.xml` and `intros.json`:
   - `NaN`, `Infinity`, `-Infinity` in `documents.One.xml` scalar fields must yield a clear `ValueError` during loading;
   - `1e9999` in `version`, and separately in top-level `_meta`, must fail (not silently become `inf`);
   - direct `_encode_scalar` of `nan` and positive/negative `inf` must raise rather than serialize invalid JSON;
   - valid finite large exponent `1e308`, ordinary number, escaped content, null/booleans must be unaffected, and resulting scalar encoding parseable as strict JSON.
2. Commit tests **only**, observe intentionally failing GitHub Actions unit job (RED) with unmodified existing suite still passing.
3. Narrow GREEN change only to `metadata.py`: reject Python-specific non-JSON constants through `parse_constant`; validate `parse_float` values with `math.isfinite` to reject overflow anywhere in the source; guard `_require_scalar` for non-finite programmatic input; set `json.dumps(allow_nan=False)` for direct encoder defense. Keep location-rich error diagnostics where possible.
4. Run complete unit suite and pinned upstream OCP build/semantic audits, canonical archive stage, stock offline Text-Fabric reload, app and comparison acceptance on exact head. Verified pinned input must have no changed feature values.
5. Conduct **logically separate** skeptical PR review against actual code/data and RED+GREEN evidence: check JSON grammar, nested `_meta` overflow, finite value preservation, exception types, untrusted source attribution, false lossless claims, and release-identity invariance. Post review on exact final SHA and merge only after full CI green.

## Out of scope

No change to TF schema, scholarly source text, pinned OCP revision, release version (prepared 1.1.0 / 1.1), GitHub publication workflow, or historical taxonomy. Public release issue #206 remains open until release/tag and Agora pin exist.
