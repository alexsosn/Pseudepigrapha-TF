# Generated translations: exact-source research for #76

## Source boundary

This research is pinned to:

- Pseudepigrapha-TF base: `0194a51e7024db754d35fcf3b321d78a5ed9a4d4`
- OCP snapshot: `c939dcbacad78c5d18d2c4282cad23c47e19ac07`
- research workflow evidence: `generated-translations-research` run 9 on head `d39d2c991cb0e5b888911c6d2d320bf85737263c`

The inventory is generated from the exact OCP checkout by `scripts/inspect_generated_translations.py` and `scripts/inspect_translation_omissions.py`; the workflow preserves the full JSON reports as an artifact so the summarized counts below remain auditable.

## Upstream generation semantics

At the selected OCP snapshot, `scripts/generate_translations.py` records model `openrouter/google/gemini-3.7-flash` and constructs generated versions with a structural provenance marker:

- exactly one synthetic manuscript with abbreviation `OCP-Trans`;
- every generated reading cites exactly `OCP-Trans`;
- the generated version copies the source division declaration and fragment attribute;
- generated unit ids are `<language-prefix>_<source-unit-id>` (`en_` / `fr_` in the selected corpus);
- generated text is produced from the source version's option-0 reading (falling back to the first reading);
- source versions whose language is English or the target language are skipped;
- translation batches and returned translations are keyed by the *bare unit id*, not by full structural path.

The converter must therefore classify generated status from the strict `OCP-Trans` structure, never from language or title.

## Exact selected-snapshot inventory

The selected snapshot contains:

| item | count |
| --- | ---: |
| non-empty XML documents | 38 |
| non-generated source versions | 118 |
| documents with generated translations | 38 |
| generated versions | 231 |
| generated units | 54,143 |
| English generated versions | 115 |
| French generated versions | 116 |
| English generated units | 27,040 |
| French generated units | 27,103 |
| English `[...]` generated readings | 1,402 |
| French empty generated readings | 1,476 |

There is exactly one genuine non-generated English version: `4Q548.xml`, version title `English`, 29 units. It must remain an ordinary source version. Because the generator skips English source versions, `4Q548.xml` has a generated French version but no generated English version; this explains the 115/116 English/French count difference.

## Source-version mapping

Using full division path plus source unit id as a multiset signature:

- unmatched generated versions: **0**;
- structurally ambiguous generated versions: **0**;
- generated versions whose source multiset matches but sequence order differs: **4**.

The four order-drift versions are:

- `4Ezra.xml` — `Syriac (English)` → source `Syriac`;
- `4Ezra.xml` — `Syriac (French)` → source `Syriac`;
- `SibOr.xml` — `English` → source `Greek`;
- `SibOr.xml` — `Greek (French)` → source `Greek`.

Consequently, position alone cannot be the unit-alignment contract. Version mapping is unambiguous on the selected snapshot, but unit alignment must be identity-based and occurrence-aware rather than a positional zip.

## Duplicate ids and generator collisions

Nine source versions contain duplicate *bare* unit ids. Three source versions contain duplicate `(division path, unit id)` identities. These are genuine upstream structures and cannot be normalized away.

Because the upstream generator sends and receives a JSON mapping keyed only by bare unit id, duplicate ids can collide inside a translation batch. The selected snapshot contains:

- 18 generated versions with generator-key collisions;
- 20 collision groups;
- 856 generated unit occurrences participating in collision groups;
- 6 generated versions with duplicate full `(path, unit id)` identities.

Some collision groups contain the same injected text for every duplicate occurrence; others do not. The largest observed groups include repeated ids in `Aristob.xml` and `JosAsen.xml`. This is an upstream generation-quality property, not converter corruption. Pseudepigrapha-TF must preserve the generated text byte-for-semantic-text exactly as supplied, expose collision diagnostics/provenance, and must not pretend that a bare generated unit id is a unique source-unit key.

For explicit generated-unit → source-unit edges, the safe key is `(full division path, stripped source unit id, occurrence ordinal within that identity)`. Where source/generated sequence order differs, both sides should be indexed independently by this occurrence-aware identity before creating edges. If an identity's source/generated multiplicities differ, conversion must diagnose/fail instead of guessing.

## Empty/placeholder readings

The exact snapshot contains different omission-output conventions across generation history:

- English generated readings contain 1,402 literal `[...]` placeholders and no empty readings;
- French generated readings contain 1,476 empty readings and no literal `[...]` placeholders.

The source-side inventory reports 986 empty source units for each target-language mapping, while the omission reconciliation reports 906 cases where generated marker/emptiness does not simply match source emptiness. These include source strings that themselves contain ellipsis-like text and translated units that are empty despite non-empty source text.

Therefore generated empty/placeholder text must be preserved as upstream generated content. It must not be promoted into textual-critical witness omission semantics, and the converter must not infer source lacunae from generated translation emptiness.

## Research conclusions

1. Generated translations are useful aligned parallel text, but they must remain semantically distinct from critical/source versions.
2. `OCP-Trans` is a synthetic generation witness and must not appear in default historical-witness/apparatus results.
3. Every generated version in the selected snapshot has exactly one source-version candidate, including multi-version works.
4. Unit alignment is supportable for the entire selected snapshot only with full structural identity plus duplicate-occurrence ordinal; order-only and bare-id-only mappings are invalid.
5. The generated text must be preserved exactly even where upstream generator collisions or omission behavior look defective.
6. Genuine English/French source material must be classified structurally, not by language.
7. Generation model/method claims must remain tied to the exact pinned OCP snapshot and generator source; the converter must not claim a model from language/title heuristics or moving upstream state.
