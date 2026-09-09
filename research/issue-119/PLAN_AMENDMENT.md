# Issue #119 — plan amendment: keep shared fixtures inside pytest's test import root

Status: **amended after observed GREEN-gate failure and before corrective implementation**.

## Observed failure

Fresh exact-head CI on `0fe5a34f2be86dacda40ee78a2faf76adbeaaf1a` against current `main` (`be074c0a269fb20a0340d6a04fa9ab05a86ee906`) disproved one research assumption. The pinned full-corpus integration completed successfully, but the unit job failed during collection with six instances of:

```text
ModuleNotFoundError: No module named 'test_support'
```

The failing imports came from all refactored distribution-test modules plus the shared-fixture contract test.

`pyproject.toml` uses a `src/` runtime layout and does not configure repository-root Python paths. Installing `pseudepigrapha-tf` editable therefore exposes `src/pseudepigrapha_tf`, not an arbitrary repository-root PEP 420 namespace. The earlier claim that `test_support/` would automatically be importable under pytest was incorrect.

## Corrected test-only boundary

Keep the helper outside `src/` and inside pytest's test import root:

```text
tests/distribution_support.py
```

The six consumers import it as:

```python
from distribution_support import ...
```

This preserves the intended boundaries:

- no runtime `pseudepigrapha_tf` module is added;
- the wheel/fresh-install surface remains unchanged;
- no `tests/__init__.py` package is introduced;
- no `conftest.py` helper API is created;
- negative provenance/authenticity tests remain independent of the positive helper.

## Corrective implementation

1. copy the existing helper implementation from `test_support/distribution.py` to `tests/distribution_support.py` unchanged;
2. update only the six test-module imports from `test_support.distribution` to `distribution_support`;
3. remove the now-invalid repository-root helper file;
4. keep the structural drift and fresh-mapping tests unchanged;
5. do not modify production source or package metadata.

## Corrected GREEN gate

Require on the exact corrected head:

- collection succeeds;
- full unit/Text-Fabric suite passes;
- pinned OCP integration passes completely;
- fresh wheel install remains green, proving the helper is not required as runtime API;
- changed-file inventory contains no `src/pseudepigrapha_tf/*` changes.

## Review additions

The independent reviewer must additionally challenge:

- whether `distribution_support` resolves because pytest intentionally exposes the test directory rather than because packaging accidentally ships it;
- whether running the distribution tests through normal repository pytest collection still works without `tests/__init__.py`;
- whether the helper remains unavailable/irrelevant to the installed runtime package;
- whether this import fix changed any scholarly/release semantics rather than only test fixture plumbing.

All previous anti-circularity and fixture-drift review checks remain required.