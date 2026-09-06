# Generated corpus licensing and attribution

Pseudepigrapha-TF distinguishes the license of this repository's converter software from the license of source text transformed into a Text-Fabric corpus.

## Converter software

The Python converter, tests, and repository-authored software are licensed under the **MIT License**. See [`LICENSE`](LICENSE) and `pyproject.toml`.

## OCP text content in the supported corpus build

The reproducible corpus build uses Online Critical Pseudepigrapha (OCP) commit:

`c939dcbacad78c5d18d2c4282cad23c47e19ac07`

OCP commit `8c8c2c55a2c55ba4b23ac506956f98dcc25045b2` explicitly clarified the upstream license boundary. That commit is an ancestor of the supported corpus pin:

- OCP application/software: GNU GPL v3;
- OCP text editions and TEI XML files under `static/docs/`: **Creative Commons Attribution 4.0 International (CC BY 4.0)**.

The generated Text-Fabric corpus transforms material from that `static/docs/` scope. It does not change the license of the Pseudepigrapha-TF converter, and it does not relabel OCP application software as CC BY.

Pinned upstream license evidence:

- `https://github.com/OnlineCriticalPseudepigrapha/Online-Critical-Pseudepigrapha/blob/c939dcbacad78c5d18d2c4282cad23c47e19ac07/LICENSE.CC-BY-4.0`
- `https://github.com/OnlineCriticalPseudepigrapha/Online-Critical-Pseudepigrapha/blob/c939dcbacad78c5d18d2c4282cad23c47e19ac07/LICENSE.GPL`
- `https://github.com/OnlineCriticalPseudepigrapha/Online-Critical-Pseudepigrapha/blob/c939dcbacad78c5d18d2c4282cad23c47e19ac07/README.md#license`

## Attribution

OCP supplies this general citation:

> Ian W. Scott and Ken M. Penner, eds. The Online Critical Pseudepigrapha. Atlanta: Society of Biblical Literature / Online: pseudepigrapha.org.

OCP also requires attribution to the individual editor identified for an edition. Pseudepigrapha-TF preserves source version/editor metadata and, when OCP `intros.json` is present, preserves each work's `citation` and `copyright` values losslessly on its `document_metadata` node. Researchers redistributing or adapting corpus text should retain the general OCP attribution together with the relevant per-work/editor attribution supplied by OCP.

## Machine-generated OCP translations

The selected OCP XML snapshot contains English and French versions created by OCP's translation workflow. They live inside the upstream `static/docs/` XML scope. Their machine-generation and alignment provenance is a separate semantic concern from this corpus-level license record; Pseudepigrapha-TF does not invent a distinct copyright status for them. Their inclusion/provenance behavior is tracked independently from this license boundary.

## Source-identity attestation and nonstandard checkouts

The CLI independently checks both the Git commit containing the supplied source directory and the cleanliness of that directory. The verified CC-BY profile is emitted only when the detected checkout commit agrees with the recorded commit, the source directory has no tracked, untracked, or ignored filesystem changes, and the resulting source tuple is the researched OCP pin above.

`--upstream-commit` remains available for research/custom provenance, but it cannot force a verified license claim. A non-Git source directory, a mismatching override, a dirty source directory, or any source tuple without a researched license profile remains convertible and is marked `sourceIdentityStatus=unverified` and/or `contentLicenseStatus=unverified`. Verified-only CC-BY fields are omitted and machine-readable diagnostics record the mismatch or dirty-tree condition.

The cleanliness rule is intentionally conservative because the converter reads source files from the filesystem. An untracked XML file or a local edit means the converted bytes are no longer proven to be the pinned upstream snapshot even when Git HEAD itself still equals the supported SHA.

A future OCP source refresh should add a new verified provenance profile only after checking the license evidence for that exact source tuple.

## Generated metadata fields

For the exact supported, clean OCP checkout, generic Text-Fabric metadata records:

- `sourceIdentityStatus=verified`
- `contentLicense=CC-BY-4.0`
- `contentLicenseStatus=verified`
- `contentLicenseUrl`
- `contentLicenseSource`
- `contentLicenseScope`
- `converterSoftwareLicense=MIT`
- `upstreamSoftwareLicense=GPL-3.0`
- `upstreamRepository`
- `upstreamCommit`
- `upstreamLicenseCommit`
- `contentAttribution`
- `contentCitation`

`conversion-report.json` mirrors the same provenance in snake_case. The semantic audit checks that the verified/unverified license shape is consistent with the independently attested source-identity status; a mismatching, dirty, or non-Git checkout cannot retain the verified CC-BY fields merely by supplying the supported SHA as an override.
