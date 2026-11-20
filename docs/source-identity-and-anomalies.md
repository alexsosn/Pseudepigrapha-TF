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

This compatibility path is included in the **unreleased 2026 candidate**.
It does **not** mean the new OCP snapshot has been published or its rights
independently verified. See issue #228 for remaining per-edition licensing,
public release, and external acquisition gates. The distinct `ApDan_TEI.xml`
is source-declared CC BY-NC and is available only as a separately licensed,
local opt-in morphology module; the six compact editions are parsed by
their own strict vocabulary and preserve editorial English separately.

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

The in-repository 2026 candidate acceptance stages **66 of 67 nonempty**
root-level XMLs, including all six compact original/English pairs, plus
all **61 public metadata records**. The 67th `ApDan_TEI.xml` supplies
a restricted and aligned morphology layer rather than an independent
textual edition, and is not bundled with the candidate core. The generated
`tei/` source mirrors are audited separately as derived representations.
CI also creates an **ephemeral source-by-source rights-evidence inventory**
with SHA-256 and Git blob hashes under issue #240; no rights evidence alone
authorizes a new data release. The published dataset remains v1.1.

## Mixed-depth T12P textual loci

The 2026 candidate `T12P.xml` declares three levels
(Testament / Chapter / Verse), but the twelve patriarch titles are
source text at the shallower `Testament / Title` address. The converter
preserves those units and the exact upstream `source_ref`, and projects
their existing text into the fixed three-level Text-Fabric API as chapter
`Reuben`, verse `Title` (for Reuben). The ordinary source
`Reuben / 1 / 1` is chapter `Reuben 1`, verse `1`.
This TF chapter projection is a technical address for the existing
source text, not an additional OCP editorial division or inferred
alignment. The same slot is never counted in both a shallow and
deep chapter. Tests check original divisions/readings, independent
section coverage, and both public TF lookup paths on real T12P XML.

## OCP 2026 compact editions and parallel English

The six newer compact XML files (CithDavid, Demetr, Justus, OrMois,
ThrenSeila, VisKenaz) use `book/@filename` with the literal `.xml`
suffix, `version/@id,@lang`, `division/@id,@title,@type` and
`manuscript/@id,@name`. The strict compact parser validates that
vocabulary and preserves the original source basename separately
from the stable TF work key, plus the version and division identifiers.

The original-language edition remains `version_kind=source`.
The source-declared English companion is
`version_kind=parallel_translation`. It is **not** marked
`generated_translation`, has no inferred generator/model and its
`Eng` label is flagged as synthetic translation provenance, never
a historical manuscript. `Translations` supplies explicit
`translation_of` and `translation_unit_of` links, matched by
actual source div and unit identifiers with multiplicity checks.
`Apparatus` excludes these parallel texts from historical witness
results. A compact-only TF corpus can load
`Translations.PARALLEL_FEATURES`; the published 1.1 corpus continues
to support `Translations.REQUIRED_FEATURES` for OCP-Trans generated text.

The source has a single `<div number="2">` containing multiple
`<unit id="2.1">, <unit id="2.2">`, and so on. The fixed TF
book/chapter/verse address is therefore the version ID, source div
number, and **exact unit ID**, for example
`("Demetr__Greek_Text_FGrH_722_Denis_1970", "2", "2.1")`
(the book ID should be resolved from `api.F.book` rather than hardcoded
by researchers). The original `unit_id` and parent div `source_ref`
remain available and the projected verse has its own exact unit
`source_ref`. These TF verse nodes do not pretend that OCP contains
additional XML divisions.

The full 2026 candidate is still **not a released corpus**. PR #233
audited a 60-work subset, and the grouped #234 gate advances that
temporary candidate to 66 nonempty root Grammateus/compact documents
with all 61 public work metadata records. The separate
`ApDan_TEI.xml` and generated `tei/` mirrors require their own
source-equivalence and license analysis before whole-source attestation
or publication.

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
