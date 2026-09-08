from __future__ import annotations

from typing import Mapping


DOCUMENTATION_CATEGORY_KEY = "documentationCategory"

DOCUMENTATION_CATEGORIES = (
    "Text-Fabric warp and section/text features",
    "Source/version identity and provenance",
    "Apparatus and witness features/relations",
    "Generated-translation features/relations",
    "Public work metadata",
    "Historical classifications",
    "Preserved anomalies / technical anchors",
    "Remaining source-preserved XML attributes/content",
)

_SECTION_FEATURES = frozenset(
    {
        "otype",
        "book",
        "chapter",
        "verse",
        "g_word_utf8",
        "prefix_utf8",
        "trailer_utf8",
        "boundary_utf8",
        "chapter_index",
        "verse_index",
        "section_occurrence",
    }
)
_IDENTITY_FEATURES = frozenset(
    {
        "source_file",
        "source_sha256",
        "source_ref",
        "source_ref_parts",
        "source_tag",
        "source_child_index",
        "ocp_book",
        "version_id",
        "version_title",
        "version_kind",
        "version_fragment",
        "language",
        "title",
        "author",
        "text_structure",
        "division_labels",
        "division_delimiters",
        "division_texts",
    }
)
_APPARATUS_FEATURES = frozenset(
    {
        "reading_text",
        "reading_xml",
        "reading_index",
        "reading_option",
        "reading_option_source",
        "is_primary",
        "is_omission",
        "mss",
        "ms_abbrev",
        "ms_name",
        "ms_name_xml",
        "ms_language",
        "ms_show",
        "manuscript_index",
        "undefined_manuscript",
        "variant_position",
        "unit_id",
        "unit_index",
        "unit_linebreak",
        "token_count",
        "bibliography",
        "bibliography_xml",
    }
)
_GENERATED_FEATURES = frozenset(
    {
        "generated_language",
        "generation_marker",
        "generation_method",
        "generation_model",
        "synthetic_witness",
    }
)
_ANOMALY_FEATURES = frozenset(
    {
        "is_empty_div",
        "is_gap",
        "is_metadata_only",
        "is_missing_unit_id",
        "is_source_anomaly",
        "ellipsis_text",
    }
)


def documentation_category(name: str, *, kind: str) -> str:
    """Return the canonical researcher-facing category for a TF feature/relation."""

    if name.startswith("intro_"):
        return "Public work metadata"
    if name.startswith("historical_"):
        return "Historical classifications"
    if kind == "edge":
        if name == "oslots":
            return "Text-Fabric warp and section/text features"
        if name in {"translation_of", "translation_unit_of"}:
            return "Generated-translation features/relations"
        if name in {
            "reading_of",
            "variant_word_of",
            "witness",
            "manuscript_of",
            "resource_of",
            "parent",
        }:
            return "Apparatus and witness features/relations"
    if name in _SECTION_FEATURES:
        return "Text-Fabric warp and section/text features"
    if name in _IDENTITY_FEATURES:
        return "Source/version identity and provenance"
    if name in _APPARATUS_FEATURES:
        return "Apparatus and witness features/relations"
    if name in _GENERATED_FEATURES:
        return "Generated-translation features/relations"
    if name in _ANOMALY_FEATURES:
        return "Preserved anomalies / technical anchors"
    return "Remaining source-preserved XML attributes/content"


def with_documentation_category(
    name: str,
    *,
    kind: str,
    metadata: Mapping[str, str] | None = None,
) -> dict[str, str]:
    """Copy feature metadata and attach the canonical documentation category."""

    result = dict(metadata or {})
    result.setdefault(DOCUMENTATION_CATEGORY_KEY, documentation_category(name, kind=kind))
    return result
