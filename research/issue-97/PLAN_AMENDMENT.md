# Issue #97 — plan amendment: infrastructure vs live release

This amendment is authoritative where it narrows `PLAN.md` after the immutable-release research completed.

## Existing release boundary

`v0.1.0` is already an immutable public release and contains no canonical TF assets. It must **not** be retrofitted, re-tagged, or used as the publication identity for artifacts built from the later source tree.

Issue #97 therefore delivers the tested **distribution contract and release machinery**. It may use synthetic/candidate release identities in unit/integration tests, but it does not declare `v0.1.0` to contain a corpus and it does not choose the next public release number prematurely.

The actual new release cut and real network-backed `tf.app.use()` proof are owned by follow-up #104 after this infrastructure is merged on a fully green `main`.

## Revised acceptance boundary for #97

Before #97 can merge, it must prove locally and in CI:

- deterministic manifest creation and fail-closed verification;
- exact canonical archive/report binding;
- exact per-feature identity or equivalent deterministic extracted-TF identity sufficient to compare an Agora rebuild without relying on ZIP container reproducibility;
- staging produces the native `tf-D.zip`, separate report, and manifest from one validated materialization;
- a release workflow contract uses a release wheel and immutable OCP pin, stages/verifies all assets before publication, and cannot silently publish from mutable upstream HEAD;
- a release-candidate archive can be extracted/loaded with stock Text-Fabric APIs locally, with metadata/provenance verification and no dependence on committed `tf/D` data;
- existing full pinned corpus, semantic, app, apparatus, translation, public-metadata, classification and license gates remain green;
- the temporary research-size workflow is removed;
- exact-head adversarial review finds no remaining blocker.

The **live** GitHub Release creation, fresh remote cache download, explicit immutable release checkout, subsequent `checkout="local"` proof, and Agora registry update are post-merge release-operation gates in #104. A failure there is a release blocker and must feed back into the contract rather than being bypassed manually.

## Manifest enhancement for rebuild equivalence

The manifest v1 must bind both:

1. the exact canonical ZIP asset (`sha256`, byte size), and
2. the extracted TF feature set independently of ZIP container metadata.

For every top-level `*.tf` entry, record filename, SHA-256, and byte size in deterministic filename order. Compute an aggregate feature-set digest over those normalized records. This allows:

- exact verification of the published archive;
- exact verification of extracted/local files;
- deterministic comparison of Agora output to canonical TF feature bytes;
- no false promise that two independently created ZIP containers have identical bytes.

`conversion-report.json` remains a separate manifest-bound asset and is not included in the native Text-Fabric archive.