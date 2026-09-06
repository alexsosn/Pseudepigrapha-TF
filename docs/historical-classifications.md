# Historical OCP catalogue classifications

Pseudepigrapha-TF ships a provenance-aware layer for the public genre and biblical-figure classifications from the historical Online Critical Pseudepigrapha catalogue snapshot at `d722fb62a48782ced67c678dc111cfb1b391cc89` (2017-10-30).

This layer is explicitly **historical**. It describes the catalogue state represented by that snapshot; it is not asserted to be a current OCP taxonomy. Current works absent from the 2017 catalogue are left unclassified rather than assigned labels by inference.

## Public-source boundary

The packaged extraction contains only the public classification material needed to reconstruct the catalogue assignments:

- `docs(id, name, filename, genres, figures)`;
- `genres(id, genre)`;
- `biblical_figures(id, figure)`.

The historical SQLite database itself is not distributed. Authentication/user records, draft records, email/account information, and unrelated application tables were not queried for the extraction and are not packaged.

The recovered snapshot contains:

- 32 classified works;
- 39 genre assignments;
- 25 biblical-figure assignments;
- 11 genre labels in the complete controlled vocabulary;
- 17 biblical-figure labels in the complete controlled vocabulary.

All 32 historical work identifiers map exactly to the public `intros.json` work identifiers. Seven newer/current works — `2Bar-Syr`, `Esdl`, `Esdr`, `JosAsen`, `Jubi`, `TAbA`, and `TAbB` — have no historical row and therefore remain unclassified.

## Text-Fabric representation

Historical assignments reuse the existing `document_metadata` nodes created for public document metadata. No artificial genre/figure nodes or semantic spans are introduced.

The node features are:

- `historical_ocp_doc_id` — historical public catalogue row id;
- `historical_genres_json` — ordered JSON array of exact historical genre labels;
- `historical_biblical_figures_json` — ordered JSON array of exact historical biblical-figure labels.

The **complete** controlled vocabularies are stored in the metadata of the two classification features under `controlledVocabularyJson`. This intentionally preserves vocabulary labels that are unused by the 32 recovered assignments. Because these are non-textual catalogue vocabularies, representing them as TF feature metadata avoids fabricated nodes and fabricated `oslots` while keeping them available after ordinary Text-Fabric serialization/reload.

`3Macc` is a useful edge case: its XML source is empty, so it contributes no textual `book` node, but its historical catalogue classification remains accessible through its `document_metadata` node.

## Query API

For selective loading:

```python
from tf.fabric import Fabric
from pseudepigrapha_tf import HistoricalClassifications

TF = Fabric(locations=['tf/0.1'], modules=[''], silent='deep')
api = TF.load(' '.join(HistoricalClassifications.REQUIRED_FEATURES), silent='deep')
C = HistoricalClassifications(api)
```

Work lookup preserves the historical row id and ordered source labels:

```python
C['TJob']
# {
#   'historical_doc_id': 1,
#   'genres': ('testaments',),
#   'biblical_figures': ('Job',),
# }

C['Mois']['genres']
# (
#   'apocalypses and visionary texts',
#   'parabiblical works (re-written Bible)',
#   'testaments',
# )
```

Reverse queries return work identifiers:

```python
C.works_by_genre('testaments')
C.works_by_figure('Moses')
```

The vocabulary methods return the complete historical controlled vocabularies, not merely labels that happen to occur in assignments:

```python
C.genres()
C.figures()
```

Unknown or historically absent work identifiers can be queried without inference:

```python
C.get('JosAsen')  # None: not present in the 2017 classification snapshot
```

## Provenance and parity

Corpus-level TF metadata records:

- historical source repository;
- historical source commit and commit date;
- historical SQLite Git blob id and SHA-256;
- an explicit historical-status marker;
- SHA-256 of the packaged public-only classification fixture.

`conversion-report.json` independently rereads the packaged public fixture and verifies:

- classified-work coverage;
- every genre assignment;
- every biblical-figure assignment;
- the complete 11/17 controlled vocabularies, including unused labels;
- historical provenance metadata.

The audit does not derive its expected values from the generated graph. Any assignment, vocabulary, mapping, or provenance mismatch causes conversion to fail.
