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

Extend `build_tf_data()` / `_metadata()` so a build from the exact verified source tuple exposes generic metadata with explicit scopes:

- `contentLicense = CC-BY-4.0`;
- `contentLicenseStatus = verified`;
- `contentLicenseUrl` pointing to the OCP CC BY license evidence;
- `contentLicenseScope = OCP static/docs text editions and TEI XML files`;
- `converterSoftwareLicense = MIT`;
- `upstreamSoftwareLicense = GPL-3.0`;
- `upstreamRepository` and exact `upstreamCommit` (already present);
- `upstreamLicenseCommit = 8c8c2c55…`;
- `contentAttribution` / `contentCitation` with the upstream project citation.

Per-document citation/editor/copyright information remains on existing `document_metadata` and source-version metadata. The generic corpus metadata points researchers to those owning records rather than flattening editor strings globally.

## Source/license consistency

The canonical CC BY assertion is verified only for the researched source tuple: canonical OCP repository plus exact supported pin.

The existing converter intentionally supports nonstandard checkouts and an `--upstream-commit` override. Preserve that behavior while failing closed on *license claims*:

- canonical repository + exact supported pin: emit the verified canonical corpus-license profile;
- missing commit, another OCP commit, or another repository: conversion may proceed, but generic metadata must say `contentLicenseStatus = unverified`, must not emit `contentLicense = CC-BY-4.0`, and must include a concise machine-readable diagnostic identifying the unverified source tuple;
- no unknown source tuple may inherit the verified license merely because its repository name resembles OCP;
- a future source refresh adds a new verified profile only in a source-grounded change that updates the supported pin/evidence.

This preserves research and custom-conversion ergonomics while preventing an overbroad license assertion. Low-level synthetic fixtures with no real Git commit remain usable and are explicitly unverified rather than rejected.

## Conversion report

Mirror the graph's generic corpus provenance into `report["provenance"]` and add a semantic consistency check. The report must never derive its license independently from README strings.

For a verified pinned build report at least:

- `upstream_repository`;
- `upstream_commit`;
- `content_license`;
- `content_license_status`;
- `content_license_scope`;
- `converter_software_license`;
- `upstream_software_license`;
- `upstream_license_commit`;
- `content_attribution` / citation;
- existing converter version.

For an unverified tuple, report the same source identity plus `content_license_status = unverified` and the diagnostic, while omitting any verified CC-BY identifier/scope/evidence fields. The semantic check succeeds only when the metadata shape matches the expected verified-or-unverified profile for the supplied tuple; contradictory combinations fail.

## Serialization/reload

Text-Fabric generic metadata is already passed through `Fabric.save`. Add real-TF tests that write and reload the generated corpus and assert the generic fields through the loaded TF metadata/API surface used by existing integration tests.

The public metadata attachment must not overwrite corpus provenance. Per-work `intro_citation_json` and `intro_copyright_json` must still round-trip unchanged.

## Repository/package/docs surfaces

- Keep root `LICENSE` and `pyproject.toml` as MIT for converter software.
- Add a README licensing/provenance section that distinguishes converter MIT from generated corpus CC BY 4.0 and links attribution to the OCP project/per-work metadata.
- Document the exact supported OCP pin and the evidence commit, without suggesting that arbitrary third-party XML or future OCP commits automatically receive the same profile.
- Document that nonstandard source tuples are marked license-unverified rather than blocked or guessed.
- No generated corpus data or upstream license file is vendored into the repository.

There is currently no checked-in Hugging Face data card or release data artifact to update. If one is added later, it should consume the same provenance constants/profile rather than duplicate values.

## TDD sequence

Before production changes, add red tests proving current behavior lacks:

1. canonical `CC-BY-4.0` corpus content license in generic TF metadata for the exact supported source tuple;
2. separate `MIT` converter software license and upstream GPL software license;
3. exact repository/pin/license-evidence commit tuple;
4. general OCP attribution/citation metadata;
5. conversion-report parity with graph provenance;
6. explicit `unverified` status and absence of a CC-BY claim for a non-pinned source tuple;
7. consistency validation rejecting a contradictory verified license/source tuple;
8. real Text-Fabric save/reload preservation of generic provenance;
9. coexistence with existing per-document citation/copyright metadata without mutation.

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
- nonstandard-checkout regression proving conversion remains possible without a guessed license;
- current performance sanity (constant-size provenance validation must not add corpus-scale scans).

## Logically independent adversarial review

On the exact green head, a separate reviewer pass must re-read the upstream licensing commit/files and challenge:

- accidental relabeling of MIT converter code as CC BY;
- accidental relabeling of OCP software as CC BY;
- a CC BY claim broader than `static/docs/` text editions/TEI XML;
- stale or moving source SHA;
- assertion of the profile for an unverified arbitrary commit;
- accidental breakage of nonstandard conversion ergonomics;
- missing general/per-work attribution paths;
- disagreement among TF generic metadata, conversion report, README and package metadata;
- serialization loss of generic metadata;
- assumptions about generated translations beyond the upstream licensing statement.

Any blocker becomes a red regression or research correction, followed by implementation, full gates, and another exact-head adversarial pass.