# Issue #109 implementation plan

Research source: `research/issue-109/RESEARCH.md`.

The implementation keeps the existing Text-Fabric graph and `Apparatus` / `Translations` semantics authoritative. Work proceeds RED-first and each gate must be observable in CI before moving to the next one.

## 1. RED gate — comparison semantics

Add focused tests before implementing comparison behavior.

Create `tests/test_passage_comparison.py` with deterministic fake providers or a compact fake TF API covering two source versions, multiple witnesses, explicit omission, unattested coverage, one metadata-only version, and generated translations attached to different source ids.

Required failing assertions:

1. source-version choices contain source/critical versions and exclude generated translations;
2. two selected source versions remain distinct for the same work/chapter/verse;
3. a selected source version missing that section remains present as `not_present`;
4. metadata-only versions are exposed separately and cannot become comparison cards;
5. witness rows for the same verse can contain different reading text;
6. explicit omission and unattested states survive as distinct segment states;
7. generated translations are grouped only under their explicit `source_id`;
8. translation units retain source/translation alignment and passage order;
9. no witness reading can be synthesized from a manuscript node or its `oslots` anchor;
10. HTML places translation content inside/below its source-version card and renders explicit omission/unattested/not-present labels;
11. HTML escapes source metadata/text supplied as strings;
12. responsive layout classes/static stylesheet contract exists.

A minimal interface scaffold may be added in the RED commit only so failures reach semantic assertions; it must not implement the expected behavior.

Open a draft PR after the RED commit and record the expected failing workflow result before production implementation.

## 2. Pure view-model layer

Add `src/pseudepigrapha_tf/comparison.py` (or equivalently named focused module) with a public builder around the existing helpers.

Recommended public API:

```python
build_passage_comparison(
    api,
    work,
    chapter,
    verse,
    *,
    selected_versions=None,
    selected_witnesses=None,
)
```

The builder instantiates `Apparatus(api)` and `Translations(api)` and returns a presentation-only dictionary/dataclass structure.

### Source version handling

- Call `Apparatus.work_passage()` exactly once per requested passage.
- Retain every textual source/critical version as a choice.
- Never include `version_kind=generated_translation` in source choices; `Apparatus` already enforces this, and the view-model must not reintroduce them.
- Preserve `available` and `not_present` from the semantic API.
- Keep metadata-only versions in a separate collection.
- Default to at most two comparison cards, preferring available versions, while preserving explicit user selection even when a selected version is `not_present`.

### Primary source text

For each available source version, derive display text from the unit records returned by `Apparatus.work_passage()`:

- select the single `primary=True` reading per unit;
- preserve explicit empty primary readings as omission markers in the segment model rather than silently deleting the locus;
- never read manuscript `oslots` or `T.text(manuscript)`.

Fail closed on malformed semantic results such as multiple primary readings for one unit.

### Witness view

Convert the returned per-witness `segments` into explicit presentation segments. Keep `reading`, `omission`, and `unattested` states verbatim.

Default witness display is bounded (target: up to four) and prefers declared witnesses marked for display. Explicit witness selections are honored if they exist for that version.

Each witness row exposes siglum, name, language, completeness/coverage, and segment states. Do not flatten an incomplete witness into a complete-looking string.

### Translation grouping

- Call `Translations.versions(work=work)` once.
- Group records by their explicit `source_id`.
- For translations belonging to source versions represented in the page, call `Translations.passage(id, chapter, verse)`.
- Preserve aligned unit order and both `source_text` and `translation_text` in the view-model.
- If the generated section is absent, retain the translation metadata with status `not_present`.
- Generation marker/method/model/language remain available as secondary metadata.

No grouping heuristic based on title suffixes, author, language, node order, or version naming is allowed.

## 3. Deterministic HTML renderer

Add a renderer separate from TF traversal, e.g. `render_passage_comparison(model, ...)`.

Requirements:

- use semantic HTML (`main`, `nav`, `section`, headings, tables/lists/details as appropriate);
- escape all corpus-derived strings and query-derived values;
- render selected source versions as version cards in one comparison container;
- show source primary text first;
- show generated translations immediately under source primary text, using compact `details`/toggle controls for multiple translations;
- render manuscript comparison below translation/source text, with explicit state labels for omission/unattested;
- show `not present` for selected source versions without the requested passage;
- show metadata-only versions only in a secondary non-comparison block;
- provide source-version and witness selection controls;
- preserve selections in navigation URLs;
- link back to the normal TF browser/root.

Keep markup tests targeted at semantic relationships/classes/labels, not a complete snapshot.

Add `app/static/comparison.css` for a responsive grid and narrow-screen stacked cards. Do not require JavaScript for core comparison semantics.

## 4. Passage navigation and selection inventory

Add small topology-only helpers that inspect TF section structure, not scholarly edges.

- enumerate OCP works from non-generated textual `book` nodes using `ocp_book`;
- select a stable available source book as navigation context for the current passage;
- derive previous/next `(chapter, verse)` from that book's `verse` descendants and `T.sectionFromNode()`;
- preserve selected source versions and witness selections in generated links;
- if no work is selected, render a work chooser instead of guessing a manuscript/version node.

Do not require all source versions to have identical section coverage.

## 5. Integrate with the stock TF Flask browser

Add a small web integration module, e.g. `src/pseudepigrapha_tf/web.py`.

Expose a testable function such as:

```python
register_comparison_route(flask_app, tf_app)
```

which adds `/compare` to an already-created TF Flask app. The route reads query parameters, builds the view-model, renders HTML, and returns a normal Flask response.

For a runnable local browser, add a helper/CLI path that deliberately reuses TF's own browser components:

- `findApp` to load the tracked app plus local materialized TF data;
- `makeTfKernel`;
- `Web` and `factory` from `tf.browser.web`;
- `runWeb` for serving.

Then call `register_comparison_route()` on that same Flask application.

The normal TF routes must remain unchanged. Add an integration test proving `/` and `/compare` coexist on the same Flask app.

Because TF 13.1 has no public corpus-route hook, wrap/import this internal surface in one module only and add a compatibility diagnostic/test. Do not scatter `tf.browser.*` imports through application logic.

## 6. CLI ergonomics

Extend the existing `pseudepigrapha-tf` subcommand parser with a `browse` command rather than adding an unrelated executable.

Proposed contract:

```text
pseudepigrapha-tf browse TF_DATA --app APP_DIR [--version 0.1] [--port PORT] [--debug]
```

- `TF_DATA` is the materialized TF feature directory.
- `--app` defaults to the tracked local `app/` directory when present; if absent, fail with an actionable message instead of silently loading the wrong app.
- `--version` defaults to `0.1` for the current release contract.
- serving delegates to Text-Fabric's `runWeb`.

Existing `convert` behavior and help must remain backward-compatible.

If wheel-only app packaging proves necessary for a usable release launcher, treat that as a separately evidenced distribution concern rather than duplicating `app/config.yaml` inside the Python package during #109.

## 7. Real Text-Fabric and pinned-upstream gates

### Local real-TF integration

Materialize existing test fixtures and load the tracked `app/` via the same `findApp` path used by `tests/test_tf_app_rendering.py`. Register the comparison route on a stock TF Flask app and exercise it with Flask's test client.

Assert:

- stock root route still responds;
- `/compare` renders source-version controls without generated versions mixed in;
- differing manuscript readings originate from `Apparatus` results, never manuscript anchor text;
- omission/unattested labels survive into HTML where the fixture supplies them.

### Pinned full corpus

Extend `pinned-upstream-integration` after the existing full conversion/reload step.

Use 1 Enoch 1:2 as a known case:

- assert source choices include at least Ethiopic and another textual 1 Enoch version while generated English/French ids are excluded from that selector;
- assert Ethiopic witnesses `p` and `Bertalotto` have different text at the known apparatus unit in the comparison model;
- assert generated English/French translation records are attached by `source_id` to their source cards;
- assert at least one generated translation passage has aligned units whose source ids/text correspond to the requested source passage;
- render HTML and assert generated translation content occurs inside the matching source-version card, not as a peer source card.

Discovery may use the semantic APIs to find the exact generated ids produced by conversion; do not hard-code generated book-name suffix rules.

## 8. Documentation

Update `docs/tf-app.md` to make `/compare`/`pseudepigrapha-tf browse` the documented scholarly passage workflow and retain the generic browser for query, graph, feature, and technical-node inspection.

Include concise examples for:

- selecting work/chapter/verse;
- comparing source versions;
- selecting witnesses;
- reading omission/unattested states;
- expanding aligned generated translations;
- returning to generic TF browsing.

Do not imply that the old generic `/passage` pane can aggregate versions.

## 9. Verification gates

Before review, require green:

- full `pytest` unit/real-TF suite;
- pinned full OCP conversion and semantic parity job;
- release-wheel fresh-install checks;
- comparison full-corpus assertions;
- existing app display-policy and technical-anchor regressions;
- no new serialized feature/node/edge changes.

Record the exact PR head SHA reviewed.

## 10. Logically independent adversarial review

After all tests are green, perform a fresh review from issue #109 acceptance criteria and the exact PR diff rather than from implementation intent.

The reviewer must challenge at minimum:

- any path that could derive witness text from technical `oslots` or `T.text(manuscript)`;
- generated translations leaking into source selectors;
- title/name heuristics substituting for `translation_of`;
- translation passage attached to the wrong source occurrence;
- collapsing omission, unattested, and not-present states;
- incomplete witnesses rendered as complete prose;
- malformed/missing primary-reading handling;
- selection/query values producing unescaped HTML or invalid identifiers;
- broad/unbounded rendering with many versions or witnesses;
- narrow-screen usability;
- dependence on undocumented TF internals outside the one integration wrapper;
- regression of ordinary TF browser routes;
- tests that exercise only fake data and miss the pinned corpus workflow.

Any blocker found in review becomes a new RED regression before the fix. Rerun all gates and repeat the independent review on the new exact head. Only a green, blocker-free reviewed head is eligible for finalization.
