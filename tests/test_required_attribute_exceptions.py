import pytest

from pseudepigrapha_tf.conversion import build_tf_data
from pseudepigrapha_tf.parser import InvalidSourceError, parse_bytes
from pseudepigrapha_tf.semantic_audit import build_conversion_report
from pseudepigrapha_tf.source import load_source_directory


KNOWN_MISSING_MS_LANGUAGE = (
    ("ClMal.xml", "ClMal", "Jewish Antiquities", "Niese"),
    ("ClMal.xml", "ClMal", "Praep. Evang.", "Mras"),
    ("Eup.xml", "Eup", "Praep. Evang. (Frag. 3)", "Mras"),
    ("Ps-Eup.xml", "Ps-Eup", "Praep. Evang. (Frag. 1)", "Mras"),
    ("Ps-Eup.xml", "Ps-Eup", "Praep. Evang. (Frag. 2)", "Mras"),
)


def _source(*, book_filename: str, version_title: str, manuscript_abbrev: str) -> bytes:
    return f'''<book filename="{book_filename}" title="Required-attribute exception fixture" textStructure="fragmentary">
  <version title="{version_title}" author="Eusebius" language="Greek">
    <divisions><division label="Paragraph"/></divisions>
    <manuscripts><ms abbrev="{manuscript_abbrev}" show="yes"><name>{manuscript_abbrev}</name></ms></manuscripts>
    <text><div number="1"><unit id="1"><reading option="0" mss="{manuscript_abbrev} ">alpha</reading></unit></div></text>
  </version>
</book>'''.encode()


@pytest.mark.parametrize(
    ("source_name", "book_filename", "version_title", "manuscript_abbrev"),
    KNOWN_MISSING_MS_LANGUAGE,
)
def test_known_missing_manuscript_language_stays_unknown_and_audited(
    tmp_path,
    source_name,
    book_filename,
    version_title,
    manuscript_abbrev,
):
    path = tmp_path / source_name
    path.write_bytes(
        _source(
            book_filename=book_filename,
            version_title=version_title,
            manuscript_abbrev=manuscript_abbrev,
        )
    )

    books, warnings = load_source_directory(tmp_path)
    assert warnings == []
    manuscript = books[0].versions[0].manuscripts[0]
    assert manuscript.language == ""

    graph = build_tf_data(books)
    manuscript_node = next(
        node
        for node, kind in graph.node_features["otype"].items()
        if kind == "manuscript"
    )
    assert graph.node_features.get("ms_language", {}).get(manuscript_node, "") == ""

    report = build_conversion_report(tmp_path, books, graph)
    assert report["status"] == "ok", report["failed_checks"]
    assert report["semantic_checks"]["manuscripts"] is True


def test_known_file_and_book_do_not_exempt_other_version_record():
    with pytest.raises(
        InvalidSourceError,
        match=r"Eup.xml: missing required attribute language on <ms>",
    ):
        parse_bytes(
            _source(
                book_filename="Eup",
                version_title="Praep. Evang. (Frag. 4)",
                manuscript_abbrev="Mras",
            ),
            source_path="Eup.xml",
        )


def test_known_file_book_and_version_do_not_exempt_other_manuscript_record():
    with pytest.raises(
        InvalidSourceError,
        match=r"Eup.xml: missing required attribute language on <ms>",
    ):
        parse_bytes(
            _source(
                book_filename="Eup",
                version_title="Praep. Evang. (Frag. 3)",
                manuscript_abbrev="Other",
            ),
            source_path="Eup.xml",
        )
