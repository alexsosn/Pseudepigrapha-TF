# Issue 137 — final full-corpus correctness and completeness audit

## Research findings

Issue #137 is a 1.0 scholarly-data gate. The current codebase already contains substantial independent source-to-graph auditing, so this work must close concrete coverage gaps rather than create another certification framework.

### Existing source-grounded coverage

The current conversion report independently reads the pinned OCP XML source and compares it with the generated TF graph for:

- source-file hashes and textual versions;
- division specifications and nested divisions;
- units and source references, including the one known blank unit id;
- primary and alternative reading payloads/reconstruction;
- manuscript and resource metadata/ownership;
- annotated mixed XML word content;
- ellipses and orphan readings;
- section coverage and duplicate source-reference handling;
- generated-translation exclusion, provenance, and unit alignment;
- source/license identity.

Unknown modeled XML attributes fail closed. Mixed XML elements that intentionally preserve arbitrary markup retain that markup inside audited source payloads.

`intros.json` is separately decoded from raw bytes and compared exactly with `document_metadata` nodes/features. The historical classification fixture is also independently projected and compared with the attached TF features/vocabularies/provenance.

The pinned full-corpus CI already converts the exact OCP snapshot, requires every semantic report check to pass, reloads TF, exercises difficult graph cases through `Apparatus` and `Translations`, reloads all public `WorkMetadata` values exactly, starts the tracked advanced app, and exercises the 1 Enoch comparison workflow.

### Upstream inventory closure

At pinned OCP commit `c939dcbacad78c5d18d2c4282cad23c47e19ac07`, `static/docs/` contains the canonical top-level XML files plus `intros.json`. Other top-level non-XML entries are not additional scholarly datasets:

- `grammateus.dtd` is the XML schema/DTD;
- `tags` is an Exuberant Ctags index;
- `.TJob.xml.un~` is an editor/backup artifact;
- `backups/` and `drafts/` are explicitly non-canonical historical/draft material.

The supported corpus scope therefore remains canonical top-level XML + public `intros.json`, with the separately packaged public-only historical classification extraction already documented by its own provenance.

### Concrete remaining gap

The full-corpus job verifies historical-classification parity in the conversion report, and unit tests verify the packaged historical fixture, but it does **not** reload the generated full corpus through the public `HistoricalClassifications` researcher API and compare every serialized classification record/vocabulary against the fixture.

That leaves one researcher-facing layer less strongly closed than:

- `WorkMetadata`, which is fully reloaded and compared against `intros.json` in pinned CI;
- `Apparatus`, which is exercised against difficult real passages in pinned CI;
- `Translations`, which is exercised after full-corpus reload and in the comparison acceptance script.

## Frozen plan

1. Add a focused pinned full-corpus acceptance helper for scholarly metadata/classification closure. It must load only the public `HistoricalClassifications.REQUIRED_FEATURES` plus Text-Fabric warp data, instantiate `HistoricalClassifications`, and independently load the packaged classification fixture.
2. Compare **every** classified work record from the serialized TF API with the fixture-derived expected record:
   - `historical_doc_id`;
   - exact ordered genre labels;
   - exact ordered biblical-figure labels.
3. Compare the API's complete controlled genre and biblical-figure vocabularies with the fixture vocabularies and verify reverse query helpers (`works_by_genre`, `works_by_figure`) reproduce the expected work sets.
4. Reuse the existing `tests/pinned_comparison_acceptance.py` invocation in `pinned-upstream-integration` and have it call the classification helper against the same materialization. Do not modify the workflow or perform a second OCP conversion.
5. Add a deterministic contract test first. RED on current `main` must prove that the existing pinned comparison acceptance path does not yet call the classification helper.
6. Keep production conversion/data-model code unchanged unless the new acceptance run finds a real mismatch. If it does, create a focused correctness issue/regression before changing production semantics.
7. Record the supported upstream source-scope conclusion in the eventual 1.0 researcher documentation (#139), not by adding release/certification machinery here.

## TDD gates

### RED

Before implementation, add a contract regression requiring the existing pinned full-corpus comparison acceptance path to call the new historical-classification helper. Current `main` must fail because `pinned_comparison_acceptance.py` has no classification API verification. The first RED commit used a direct workflow-invocation assertion; before GREEN that contract was narrowed to the cheaper and more maintainable invariant above, still RED against `main` and still proving the same full-corpus coverage requirement.

### GREEN

Add the acceptance helper and call it from the existing pinned comparison acceptance script. The helper must fail closed on missing/incomplete classifications, vocabulary drift, value drift, or reverse-index drift.

### Full tests

Require:

- unit/Text-Fabric suite green;
- full-corpus contract tests green;
- exact pinned OCP conversion and all semantic checks green;
- full-corpus TF reload green;
- new classification API acceptance green;
- existing apparatus/translation/public-metadata/comparison/app gates green.

## Independent adversarial review gate

After the exact PR head is green, perform a logically separate skeptical review from the opposite trust direction. Challenge at least:

- whether the new check merely compares TF against a derivative of TF instead of the independent packaged fixture;
- whether it checks every classified work or only samples;
- whether controlled vocabularies can drift while records happen to remain decodable;
- whether reverse query indexes can silently omit/misassign works;
- whether selective loading accidentally relies on unrelated features;
- whether the change added another full conversion or workflow lane;
- whether this work has expanded into release/provenance machinery instead of scholarly correctness.

Any blocker must become a new RED regression, followed by fix, full gates, and a fresh exact-head adversarial review.

## Definition of done for this slice of #137

The serialized full corpus is independently proven to expose historical classifications exactly through the researcher-facing API, closing the only identified full-corpus API parity gap. If the new full-corpus run finds no underlying data defect, #137 can then be closed on the basis of the existing comprehensive source/graph parity suite plus this final API closure, with remaining documentation work handed to #139.
