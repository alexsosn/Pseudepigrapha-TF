# Corpus license/provenance research for #77

## Exact source boundary

Pseudepigrapha-TF currently pins OCP commit `c939dcbacad78c5d18d2c4282cad23c47e19ac07` and records the checkout SHA in generated Text-Fabric metadata.

The OCP dual-license clarification was introduced by commit `8c8c2c55a2c55ba4b23ac506956f98dcc25045b2` on 2026-09-01 with commit message:

> Dual-license: GPL v3 for software, CC BY 4.0 for text editions in static/docs (issue #34)

The selected Pseudepigrapha-TF pin is seven commits ahead of that change and has `8c8c2c55…` as its merge base, so the clarification is part of the exact converted source snapshot.

## Upstream license scope

At the selected pin, OCP's README and license files state two separate scopes:

- Grammateus3/application software, web2py controllers/views, JavaScript, CSS and build scripts: GNU GPL v3 (`LICENSE.GPL`).
- Text editions and TEI XML files under `static/docs/`: Creative Commons Attribution 4.0 International (`LICENSE.CC-BY-4.0`).

The README specifically says that reuse/adaptation of the text editions requires attribution to the Online Critical Pseudepigrapha and the individual editor named in each document's header metadata. It also gives the general project citation:

`Ian W. Scott and Ken M. Penner, eds. The Online Critical Pseudepigrapha. Atlanta: Society of Biblical Literature / Online: pseudepigrapha.org.`

This ticket should therefore describe the transformed corpus content as `CC-BY-4.0` only for material derived from OCP `static/docs/`. It must not relabel OCP software, third-party software, or Pseudepigrapha-TF's converter code as CC BY.

## Downstream software license

Pseudepigrapha-TF's repository `LICENSE` is MIT and `pyproject.toml` declares `license = {text = "MIT"}`. That is the converter/package software license and remains unchanged.

## Existing provenance/attribution surfaces

Current code already provides useful pieces that should be reused rather than duplicated:

- `source.detect_git_commit()` records the actual source checkout SHA.
- `build_tf_data(... upstream_repository, upstream_commit, converter_version)` stores `upstreamRepository`, `upstreamCommit`, and `converterVersion` in generic TF metadata.
- `build_conversion_report()` mirrors those three fields under `provenance`.
- `metadata.load_public_metadata()` and `attach_public_metadata()` preserve OCP `intros.json` values, including per-work `citation` and `copyright` fields, losslessly on `document_metadata` nodes.
- parsed source versions retain `author` and other source metadata.
- the README already documents the exact OCP pin and explains that the converter software and source data are separate artifacts, but it does not yet expose the OCP text license as generated-corpus metadata.

The writer passes generic Text-Fabric metadata through serialization, so corpus-level provenance fields are the appropriate durable location for the license identifier and attribution source.

## Current gaps

Generated TF metadata does not currently contain a corpus-content license identifier, license URL/reference, general attribution/citation, or a separate converter-software license field. The conversion report likewise has repository/SHA/converter version but no content-license or software-license distinction. A consumer who receives generated `.tf` files without the GitHub README therefore cannot discover the license governing the transformed OCP text.

There is also no deterministic consistency check preventing a future code change from pairing the pinned OCP source identity with a contradictory content-license claim.

## Provenance matrix

| Material | Canonical downstream value | Evidence |
| --- | --- | --- |
| Pseudepigrapha-TF converter/package | `MIT` | repository `LICENSE`, `pyproject.toml` |
| OCP application/software | `GPL-3.0` / GPL v3 | OCP `LICENSE.GPL`, README |
| OCP `static/docs/` text editions transformed into TF | `CC-BY-4.0` | OCP `LICENSE.CC-BY-4.0`, README |
| Corpus source repository | `https://github.com/OnlineCriticalPseudepigrapha/Online-Critical-Pseudepigrapha` | current converter canonical source |
| Supported pinned source SHA | `c939dcbacad78c5d18d2c4282cad23c47e19ac07` | #72 / README / CI source boundary |
| General text attribution | OCP project + Scott/Penner citation | OCP README |
| Per-work attribution | existing `citation`, `copyright`, version/editor metadata where supplied | OCP `intros.json` and XML |

## Generated translations

The OCP license statement scopes CC BY 4.0 to text editions and TEI XML files under `static/docs/`; the selected snapshot's generated English/French versions live inside those XML files. #76 is responsible for their semantic provenance and inclusion policy. #77 should not invent a distinct copyright status for generated translations. If #76 later includes them, they inherit the corpus source/license metadata only to the extent of the upstream `static/docs/` licensing statement, while their machine-generation provenance remains separate.

## Research conclusions

1. The exact OCP pin used by Pseudepigrapha-TF contains the explicit dual-license clarification.
2. `CC-BY-4.0` is source-grounded for transformed OCP `static/docs/` text content; it is not the converter software license.
3. MIT remains the Pseudepigrapha-TF software license.
4. Existing `intros.json`/XML metadata already carries per-work citation/editor/copyright information and should remain the detailed attribution source.
5. Corpus-level license/provenance should be emitted once in generic TF metadata and mirrored into the conversion report, with a deterministic validation contract tied to the supported upstream repository/SHA.