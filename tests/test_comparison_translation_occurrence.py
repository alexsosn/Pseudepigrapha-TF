from __future__ import annotations

import pytest

from pseudepigrapha_tf import comparison


class FakeApparatus:
    def __init__(self, api):
        self.api = api

    def work_passage(self, work, chapter, verse):
        return {
            "work": str(work),
            "title": "Work",
            "reference": (str(chapter), str(verse)),
            "versions": {
                "Work__Greek": {
                    "node": 1,
                    "id": "Work__Greek",
                    "title": "Greek",
                    "language": "Greek",
                    "author": "",
                    "status": "available",
                    "witnesses": {},
                    "passage": {
                        "reference": ("Work__Greek", str(chapter), str(verse)),
                        "verse_node": 101,
                        "source_refs": ("1:2",),
                        "units": (
                            {
                                "node": 11,
                                "unit": "u1",
                                "source_ref": "1:2",
                                "readings": (
                                    {
                                        "node": 21,
                                        "text": "alpha",
                                        "primary": True,
                                        "omission": False,
                                        "witness_nodes": (),
                                        "witnesses": (),
                                    },
                                ),
                            },
                        ),
                        "witnesses": {},
                    },
                },
            },
            "metadata_only_versions": {},
        }


class FakeTranslations:
    def __init__(self, api):
        self.api = api

    def versions(self, *, work=None, language=None):
        return (
            {
                "node": 201,
                "id": "Work__Greek__translation__English",
                "work": "Work",
                "title": "English",
                "language": "English",
                "source_node": 1,
                "source_id": "Work__Greek",
                "generation_marker": "OCP-Trans",
                "generation_method": "llm",
                "generation_model": "model-x",
            },
        )

    def passage(self, generated_book, chapter, verse):
        return {
            "reference": (str(generated_book), str(chapter), str(verse)),
            "book_node": 201,
            "source_book_node": 1,
            "units": (
                {
                    "translation_unit": 301,
                    # Correct source book, but this unit belongs to a different
                    # source passage/occurrence than Work__Greek 1:2.
                    "source_unit": 999,
                    "translation_unit_id": "en-1",
                    "source_unit_id": "elsewhere",
                    "source_ref": "9:9",
                    "translation_text": "wrongly aligned",
                    "source_text": "other passage",
                },
            ),
        }


def test_comparison_rejects_translation_unit_from_another_source_occurrence(monkeypatch):
    monkeypatch.setattr(comparison, "Apparatus", FakeApparatus)
    monkeypatch.setattr(comparison, "Translations", FakeTranslations)

    with pytest.raises(ValueError, match="outside requested source passage"):
        comparison.build_passage_comparison(
            object(),
            "Work",
            "1",
            "2",
            selected_versions=("Work__Greek",),
        )
