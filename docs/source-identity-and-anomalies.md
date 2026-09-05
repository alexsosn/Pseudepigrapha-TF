# Source identity and anomaly policy

Pseudepigrapha-TF preserves OCP source identity rather than silently normalizing malformed or incomplete records.

## Blank attributes

The pinned Grammateus DTD declares many attributes as `CDATA #REQUIRED`, but requiredness guarantees presence, not a non-empty value. OCP also uses empty strings as legitimate metadata, so the converter does **not** apply a blanket non-empty rule.

Modern source XML fails loudly when a blank or whitespace-only value would erase researcher-visible identity:

- `book/@filename`
- `ms/@abbrev`
- `div/@number`
- `unit/@id`
- `reading/@option`

By contrast, empty metadata such as `version/@title`, `version/@author`, `ms/@language`, `ms/@show`, and witness-free `reading/@mss=""` remains preservable when the surrounding source structure is valid.

Direct `Book` models are checked again before graph construction so callers cannot bypass source validation for work, division, unit, or reading identities. Manuscript objects with blank abbreviations may exist as unaddressable metadata in direct models, but they are never entered into witness lookup.

## Pinned missing unit ID

The pinned OCP revision used by CI (`2d1d14d23434a784d377ff7f4409ccdb2d18aafb`) contains one genuine exception: `AdamEve.xml`, version `Latin (Mozley)`, source reference `26:0`, has a literal `<unit id="">`. The surrounding source has unit IDs `26` and `28`; the converter therefore does **not** infer `27`.

That unit is preserved with its ordinary text and source location but without a `unit_id` feature. Its TF `unit` node carries:

- `is_missing_unit_id=1`
- `is_source_anomaly=1`

The source exception requires the exact pinned `AdamEve.xml` bytes (SHA-256 `a63275351e2349ce8a31b7427a28b80db034be670ba545e2398832a3d9ac6358`) in addition to the expected source file, work, version, division path, and literal empty value. After XML validation, the parser carries that approval with an internal marker; direct `Book` models cannot opt into the exception by supplying matching public `source_path` or `source_sha256` fields. A whitespace-only ID, changed source bytes, or the same blank record at another provenance fails validation.

The independent conversion report compares the raw blank-ID record with marked TF units. CI requires exactly one such source and graph record in the pinned corpus, and then reloads the generated corpus through Text-Fabric 13.1 to verify that the marker survives serialization while `unit_id` remains absent.

## Other pinned structural anomalies

Known source structures are preserved explicitly instead of being silently discarded or editorially reassigned:

- `Aristob.xml` uses upstream `<elipsis>` markers. They become TF `ellipsis` nodes while retaining the literal `source_tag=elipsis`.
- `PssSol.xml` contains direct `<reading>` children of `<div>`. They become `orphan_reading` nodes and are not assigned to a guessed neighboring unit.
- Empty source `<div>` elements remain `div` nodes with `is_empty_div=1`; technical Text-Fabric anchors never create fake text sections.

Unsupported source children, unsupported attributes, ambiguous duplicate manuscript abbreviations, and unrecognized blank identity fields fail loudly before conversion. Record-specific exceptions are added only after pinned-source research plus a dedicated regression test.
