# Corpus license/provenance implementation plan for #77

This plan follows `docs/corpus-license-provenance-research.md`. Production changes begin only after test-only regressions establish the missing contract.

## Canonical source of truth

Add a small `provenance.py` module containing immutable, source-grounded constants and validation helpers for the supported corpus build:

- Pseudepigrapha-TF software license: `MIT`;
- OCP software license: `GPL-3.0` (descriptive upstream provenance only);
- OCP transformed text-content license: `CC-BY-4.0`;
- canonical OCP repository URL;
- supported pinned OCP SHA `c939dcbacad78c5d18d2c4282cad23c47e19ac07`;
- dual-license evidence commit `8c8c2c55a2c55ba4b23ac506956f98dcc25045b2`;
- stable license/source URLs pinned to source evidence where practical;
- general OCP attribution/citation string grounded in the upstream README.

No full license text is copied into TF nodes.

## TF generic metadata

Extend `build_tf_data()` / `_metadata()` so generated corpora expose generic metadata fields with explicit scopes:

- `contentLicense = CC-BY-4.0`;
- `contentLicenseUrl` pointing to the OCP CC BY license file/evidence;
- `contentLicenseScope = OCP static/docs text editions and TEI XML files`;
- `converterSoftwareLicense = MIT`;
- `upstreamSoftwareLicense = GPL-3.0`;
- `upstreamRepository` and exact `upstreamCommit` (already present);
- `upstreamLicenseCommit = 8c8c2c55…`;
- `contentAttribution` / `contentCitation` with the upstream project citation.

Per-document citation/editor/copyright information remains on existing `document_metadata` and source-version metadata. The generic corpus metadata points researchers to those owning records rather than flattening editor strings globally.

## Source/license consistency

The canonical CC BY assertion is valid for the supported OCP repository at the supported pin. Add a validation helper invoked by the production build path:

- canonical repository + exact supported pin: emit canonical corpus-license metadata;
- canonical repository with no commit: do not silently claim reproducible pinned provenance; raise for the CLI/build path that promises the supported corpus;
- canonical repository with another commit, or another repository with the canonical license claim: fail closed unless an explicit future provenance profile is added in code after research.

This intentionally narrows `--upstream-commit` for release/canonical builds. A future source refresh must update the provenance profile in the same PR that changes the supported pin; arbitrary moving commits cannot inherit a license assertion merely by sharing a repository name.

To keep low-level unit construction usable for synthetic fixtures, expose provenance validation as an explicit helper and have the CLI canonical conversion path call it before graph construction. Tests that build small in-memory graphs may pass an explicit validated provenance mapping or omit corpus license metadata when they are not modeling a canonical OCP build.

## Conversion report

Mirror the exact generic corpus metadata into `report["provenance"]` and add a semantic check that the graph's canonical source/license tuple equals the expected profile. The report must never derive its license independently from README strings.

At minimum report:

- `upstream_repository`;
- `upstream_commit`;
- `content_license`;
- `content_license_scope`;
- `converter_software_license`;
- `upstream_software_license`;
- `upstream_license_commit`;
- `content_attribution` / citation;
- existing converter version.

A mismatched or missing canonical tuple becomes a failed semantic check rather than a warning.

## Serialization/reload

Text-Fabric generic metadata is already passed through `Fabric.save`. Add real-TF tests that write and reload the generated corpus and assert the generic fields through the loaded TF metadata/API surface used by existing integration tests.

The public metadata attachment must not overwrite corpus provenance. Per-work `intro_citation_json` and `intro_copyright_json` must still round-trip unchanged.

## Repository/package/docs surfaces

- Keep root `LICENSE` and `pyproject.toml` as MIT for converter software.
- Add a README licensing/provenance section that distinguishes converter MIT from generated corpus CC BY 4.0 and links attribution to the OCP project/per-work metadata.
- Document the exact supported OCP pin and the evidence commit, without suggesting that arbitrary third-party XML or future OCP commits automatically receive the same profile.
- No generated corpus data or upstream license file is vendored into the repository.

There is currently no checked-in Hugging Face data card or release data artifact to update. If one is added later, it should consume the same provenance constants/profile rather than duplicate values.

## TDD sequence

Before production changes, add red tests proving current behavior lacks:

1. canonical `CC-BY-4.0` corpus content license in generic TF metadata;
2. separate `MIT` converter software license and upstream GPL software license;
3. exact repository/pin/license-evidence commit tuple;
4. general OCP attribution/citation metadata;
5. conversion-report parity with graph provenance;
6. fail-closed behavior for a non-pinned source/license combination;
7. real Text-Fabric save/reload preservation of generic provenance;
8. coexistence with existing per-document citation/copyright metadata without mutation.

Observe an isolated red commit before adding implementation.

## Full gates

After implementation:

- unit suite;
- real Text-Fabric serialization/reload;
- exact pinned OCP conversion;
- semantic parity/report gate;
- public metadata parity/reload gate;
- existing apparatus and source reconstruction gates;
- README/package consistency check where deterministic;
- current performance sanity (constant-size provenance validation must not add corpus-scale scans).

## Logically independent adversarial review

On the exact green head, a separate reviewer pass must re-read the upstream licensing commit/files and challenge:

- accidental relabeling of MIT converter code as CC BY;
- accidental relabeling of OCP software as CC BY;
- a CC BY claim broader than `static/docs/` text editions/TEI XML;
- stale or moving source SHA;
- assertion of the profile for an unverified arbitrary commit;
- missing general/per-work attribution paths;
- disagreement among TF generic metadata, conversion report, README and package metadata;
- serialization loss of generic metadata;
- assumptions about generated translations beyond the upstream licensing statement.

Any blocker becomes a red regression or research correction, followed by implementation, full gates, and another exact-head adversarial pass.