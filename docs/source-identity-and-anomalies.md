# Source identity and anomaly policy

Pseudepigrapha-TF preserves OCP source identity rather than silently normalizing malformed or incomplete records.

When loading an OCP source *directory*, every non-empty top-level `WorkId.xml` must declare that exact `WorkId` in its `<book filename="WorkId">` attribute, including case. This is enforced whether or not the optional `intros.json` metadata export is present; a mismatched name fails rather than silently changing researcher-facing work identity. Individual in-memory `parse_bytes()` calls can still parse text without a filesystem name. Empty `.xml` placeholders retain their documented skip behavior.

## Modern root language compatibility (OCP 2026 candidate)

New upstream OCP `5Ezra.xml` and `6Ezra.xml` have `<book language="Latin">`
in addition to the same `language="Latin"` on their sole modern
`<version>`. The converter accepts this redundant root metadata when it
is nonblank and **every** direct modern version declares the identical
language. The existing wrapped-legacy exception is retained for OCP sources
whose generated translation versions naturally use different languages.
Missing or contradictory source-version languages still fail validation.
The language continues to be recorded on the source version's native TF
features; there is no inferred book-level language when editions disagree.

This narrowly scoped parser compatibility change does **not** mean that the
new OCP snapshot has been imported or released. See issue #228 for the
remaining inventory, TEI, provenance, native TF, and acceptance gates.
In particular, namespaced `ApDan_TEI.xml` is not Grammateus XML and
`CithDavid.xml` has additional unsupported source vocabulary.

## OCP 2026 candidate: public author/editor metadata

The upstream OCP `intros.json` at
`853a64b623de296d2b8532a43593607772e7c45a` introduces sparse
top-level `author` and `editor` strings on 17 documents. The converter
now preserves each supplied JSON scalar, including its presence, as
`intro_author_json` and `intro_editor_json` on native
`document_metadata` nodes. The independent raw-JSON-vs-TF audit compares
these keys too. No author or editor is inferred for documents lacking them.

The **published v1.1** dataset does not contain these two features and its
existing `WorkMetadata.REQUIRED_FEATURES` selective-load contract is
unchanged. On a *newer dataset containing the features*, explicitly load
`WorkMetadata.OPTIONAL_FEATURES` in addition to `REQUIRED_FEATURES`
before constructing `WorkMetadata(api)`, then `M["5Ezra"]["author"]`
can return the newly supplied source value. Do not request the optional
features from the older published corpus.

The in-repository 2026 candidate acceptance stages 60 of 67 nonempty
root-level XML files, with six compact-dialect files and the separate
`ApDan_TEI.xml` intentionally blocked from the *staging test only*.
Its 55 public metadata documents have exact values preserved. The six
excluded books' metadata values are omitted from this temporary staging
source, with the expected omitted identities asserted; this is **not** a
lossless full-corpus migration or a release. The original complete upstream
`intros.json` and XML files remain unchanged.

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

The pinned OCP revision used by CI (`c939dcbacad78c5d18d2c4282cad23c47e19ac07`) contains one genuine exception: `AdamEve.xml`, version `Latin (Mozley)`, source reference `26:0`, has a literal `<unit id="">`. The surrounding source has unit IDs `26` and `28`; the converter therefore does **not** infer `27`.

That unit is preserved with its ordinary text and source location but without a `unit_id` feature. Its TF `unit` node carries:

- `is_missing_unit_id=1`
- `is_source_anomaly=1`

The source exception requires the exact release-pinned `AdamEve.xml` bytes (SHA-256 `b5e20471d7e1b531df49d81acd19462ee92192c3e20019cb110215611d7b9817`) in addition to the expected source file, work, version, division path, and literal empty value. After XML validation, the parser carries that approval with an internal marker; direct `Book` models cannot opt into the exception by supplying matching public `source_path` or `source_sha256` fields. A whitespace-only ID, changed source bytes, or the same blank record at another provenance fails validation.

The independent conversion report compares the raw blank-ID record with marked TF units. CI requires exactly one such source and graph record in the pinned corpus, and then reloads the generated corpus through Text-Fabric 13.1 to verify that the marker survives serialization while `unit_id` remains absent.

A converter source checkout is also marked **unverified** when the Git index marks files under the OCP source directory `assume-unchanged` or `skip-worktree`. Git porcelain status can report a modified XML file as clean under either flag; the converter additionally inspects `git ls-files -v` and trusts only ordinary tracked entries. If Git cannot inspect the index, provenance remains unverified; conversion itself is still permitted. This is a conservative attestation policy for sparse/flagged worktrees and does not claim to protect against files changing concurrently after source loading.

## Other pinned structural anomalies


The pinned corpus also has five `ms` records whose `language` attribute is **absent** despite the modern DTD requirement: ClMal/Jewish Antiquities/Niese, ClMal/Praep. Evang./Mras, Eup/Praep. Evang. (Frag. 3)/Mras, and Ps-Eup/Praep. Evang. (Frag. 1, 2)/Mras. The converter retains these omissions without inventing a language. Each allowance requires an exact source basename, work identity, version title, manuscript abbreviation, **and SHA-256 digest of the complete reviewed XML**. For the pinned `c939dcb...` source, ClMal, Eup and Ps-Eup each have a separately reviewed SHA-256 in `KNOWN_MISSING_MANUSCRIPT_LANGUAGE`. A changed source file reusing the same identifiers fails required-attribute validation; an updated snapshot must be reviewed and explicitly whitelisted before conversion.

Known source structures are preserved explicitly instead of being silently discarded or editorially reassigned:

- `Aristob.xml` uses upstream `<elipsis>` markers. They become TF `ellipsis` nodes while retaining the literal `source_tag=elipsis`.
- `PssSol.xml` contains direct `<reading>` children of `<div>`. They become `orphan_reading` nodes and are not assigned to a guessed neighboring unit.
- Empty source `<div>` elements remain `div` nodes with `is_empty_div=1`; technical Text-Fabric anchors never create fake text sections.

Unsupported source children, unsupported attributes, ambiguous duplicate manuscript abbreviations, and unrecognized blank identity fields fail loudly before conversion. Record-specific exceptions are added only after pinned-source research plus a dedicated regression test.
