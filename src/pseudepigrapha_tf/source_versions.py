from __future__ import annotations

from xml.etree import ElementTree as ET


GENERATED_TRANSLATION_MARKER = "OCP-Trans"


class GeneratedTranslationClassificationError(ValueError):
    """Raised when OCP-Trans provenance is present but structurally ambiguous."""


def is_wrapped_legacy_version(version: ET.Element) -> bool:
    """Return whether an upstream <version> wraps the old chapter/verse dialect.

    OCP's translation generator wraps legacy root content in a <version> before
    appending generated translations, but deliberately leaves the original
    chapter/verse body intact and does not synthesize a <divisions> block for
    that source version.
    """

    text = version.find("text")
    return (
        version.tag == "version"
        and version.find("divisions") is None
        and text is not None
        and text.find("chapter") is not None
    )


def is_generated_translation_version(version: ET.Element) -> bool:
    """Classify an upstream generated translation by its explicit provenance.

    Upstream's generator creates exactly one synthetic manuscript named
    ``OCP-Trans`` and makes every generated reading cite exactly that witness.
    The marker is therefore usable as provenance, but only when the surrounding
    structure is internally consistent.  Any mixed/partial use is rejected so
    a source edition cannot disappear merely because it happens to mention the
    reserved marker.
    """

    manuscripts = list(version.findall("manuscripts/ms"))
    manuscript_abbrevs = [ms.get("abbrev", "") for ms in manuscripts]
    readings = list(version.iter("reading"))
    reading_witnesses = [tuple(r.get("mss", "").split()) for r in readings]

    marker_in_manuscripts = GENERATED_TRANSLATION_MARKER in manuscript_abbrevs
    marker_in_readings = any(
        GENERATED_TRANSLATION_MARKER in witnesses for witnesses in reading_witnesses
    )
    if not marker_in_manuscripts and not marker_in_readings:
        return False

    title = version.get("title", "")
    context = f"version {title!r}" if title else "version"
    if manuscript_abbrevs != [GENERATED_TRANSLATION_MARKER]:
        raise GeneratedTranslationClassificationError(
            f"{context}: OCP-Trans generated translation marker is mixed with other manuscripts"
        )
    if not readings:
        raise GeneratedTranslationClassificationError(
            f"{context}: OCP-Trans generated translation marker has no readings"
        )
    for witnesses in reading_witnesses:
        if witnesses != (GENERATED_TRANSLATION_MARKER,):
            raise GeneratedTranslationClassificationError(
                f"{context}: OCP-Trans generated translation marker is mixed with other reading witnesses"
            )
    return True
