# Issue #215: Reject a nonzero JSON number silently rounded to zero

Frozen, code-grounded research and TDD plan — commit this before the regression tests.

## Research evidence

`src/pseudepigrapha_tf/metadata.py` uses `json.loads(..., parse_float=_parse_finite_json_float)`. Current `_parse_finite_json_float` calls `float(literal)` and checks `math.isfinite`, correctly rejecting `1e9999`, but not `1e-9999`, `-1e-9999`, `1e-324`, which become `0.0`/`-0.0`. CPython `Decimal("1e-9999")` is nonzero; floating underflow irreversibly changes an original nonzero JSON scalar to zero. The same parsing path accepts metadata title, version, citation, named fields, and `_meta`, so all are susceptible. `_encode_scalar` serializes the corrupted zero as `0.0`.

This error is distinct from the #209 overflow/non-finite boundary and from ordinary finite binary64 rounding. The project permits JSON scalar values in public OCP metadata and claims faithful TF JSON-scalar preservation; silent nonzero→zero is not acceptable. The currently pinned public `intros.json` contains only finite numbers in the ordinary range; no change to pinned scholarly values is intended.

## RED-first tests

- Create `tests/test_public_metadata_numeric_underflow.py`, reuse actual source-layout rules with `One.xml` declaring `filename="One"`, replace selected raw `intros.json` numeric token with `1e-9999`, `-1e-9999`, `1e-324` and include both a top-level `version`, nested supported `fields.status`, and `_meta.counter`.
- Assert `load_public_metadata` raises a meaningful `ValueError` mentioning the source file and numeric underflow, not silently returning 0.
- Positive controls: syntactically exact `0e-9999`, `-0e-9999`, `0.000e-99999` must remain valid zeros; representable subnormal `5e-324` must remain nonzero, as must `1e308` and normal finite floats.
- Existing NaN/Infinity/overlarge exponent behavior and scalar encoding tests stay intact.
- Commit tests only and inspect actual GitHub Actions RED failures before claiming TDD satisfied.

## Minimal GREEN

In `_parse_finite_json_float`, after float finite check, if parsed `value == 0.0`, inspect only the *mantissa* portion of the JSON numeric literal (before `e`/`E`) for any decimal digit 1–9. Because `json.loads` guarantees valid numeric syntax at this hook, an all-zero mantissa represents a real zero no matter what exponent; any nonzero mantissa which becomes a zero float represents underflow and must be rejected. No arbitrary-precision Decimal conversion or costly exponent expansion needed. Keep float API, JSON audit, metadata layout and nonfinite overflow logic unchanged.

## Final gates and adversarial review

Require exact SHA GREEN GitHub Actions unit-and-tf plus complete pinned upstream conversion/semantic audit, packaged corpus archives, stock offline Text-Fabric reload and 1 Enoch comparison. Independently scrutinize (1) upper/lower exponent, (2) negative zero, (3) subnormal threshold, (4) `_meta` and field paths, (5) existing #209 overflow, (6) source SHA and 1.1 identities, (7) misleading 'lossless binary64' wording. Post source-backed skeptical review directly on PR; merge only if gates pass, with exact-head SHA protection. Release publication remains issue #206.
