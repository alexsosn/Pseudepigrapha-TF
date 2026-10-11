# Issue #202 — Digest-bound exemptions for missing manuscript language

Frozen research and execution plan, committed before test or production changes.

## Verified sources

- Pseudepigrapha-TF source validator: `src/pseudepigrapha_tf/source_structure.py` uses `KNOWN_MISSING_MANUSCRIPT_LANGUAGE` as a tuple whitelist for five `ms/@language` omissions; it ignores `source_sha256` for those omissions. The same validator already enforces exact SHA-256 source binding for the pinned blank `AdamEve` unit ID.
- `parser.parse_bytes()` computes the complete XML `hashlib.sha256(data).hexdigest()` and passes it into source-structure validation before any `Version` or TF graph is constructed. `audit._raw_inventory` uses the same parsing boundary.
- `tests/test_required_attribute_exceptions.py` currently constructs arbitrary short XML under these same five names, expects it to pass, and audits the resulting missing language: this demonstrates the spoofable exception.
- The exact source archive used in `.github/workflows/test.yml` is upstream OCP commit `c939dcbacad78c5d18d2c4282cad23c47e19ac07`. Fetched its `static/docs` XML at that commit and computed UTF-8 SHA-256:
  - `ClMal.xml`: `bd9e16f31a3e418ccf0d3c5b6392e01124ec757f52a5bb571a2b14e7acd49bb1`
  - `Eup.xml`: `c4dcefa833e2286d97e83b466a5a43b3046b6f2733bf373ecfb03bc1177e6052`
  - `Ps-Eup.xml`: `e28e843f1d54825bca453c134f962f2d32e33438e4b009e7755efce313b282ef`

## Scope and frozen plan

1. Change the exemption representation into a mapping from `(source name, OCP work, version title, manuscript abbrev)` to a non-empty frozen set of reviewed complete-source digests. No fallback to filename only, no inference of an omitted language, and no changes to legitimate empty `ms/@language=""`.
2. Require both the exact record tuple and the complete XML digest to bypass the otherwise-required `ms/@language` check. Leave sibling missing attributes rejected.
3. RED-only tests first: five borrowed tuples in modified small XML must now raise `InvalidSourceError`. Add one changed-byte fixture asserting that a whitelisted digest does not cover a different source. Keep positive synthetic fixture coverage by injecting **only the test fixture's exact digest** into a temporary monkeypatch of the registry; verify resulting TF manuscript feature remains absent and semantic report remains valid.
4. GREEN implementation in `source_structure.py` and explanation in `docs/source-identity-and-anomalies.md`.
5. Run suite and pinned upstream OCP integration and TF/release checks against exact branch SHA. If SHA list mismatches real pinned data, do not bypass validation: investigate actual upstream bytes and correct the frozen plan with explicit evidence.
6. Perform a separate logically independent skeptical review from the finalized diff and pinned source evidence, post review to GitHub, and merge only if no blocking findings and exact-head CI succeeds.

## Deliberate limits

This is an identity-safe permission to preserve a **missing** source value, not a claim that the language is known. Future OCP snapshots must be explicitly reviewed to extend the digest set. This ticket does not change semantic manuscript attribution or broad XML schema support.
