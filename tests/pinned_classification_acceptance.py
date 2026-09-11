from __future__ import annotations

from pathlib import Path
import sys

from tf.fabric import Fabric

from pseudepigrapha_tf import HistoricalClassifications
from pseudepigrapha_tf.classifications import load_historical_classifications


def verify(tf_dir: Path) -> None:
    TF = Fabric(locations=[str(tf_dir)], modules=[""], silent="deep")
    api = TF.load(" ".join(HistoricalClassifications.REQUIRED_FEATURES), silent="deep")
    assert api is not None

    expected = load_historical_classifications()
    actual = HistoricalClassifications(api)

    assert actual.keys() == tuple(sorted(expected.documents))

    for work_id, document in expected.documents.items():
        assert actual[work_id] == {
            "historical_doc_id": document.historical_doc_id,
            "genres": tuple(expected.genres[identifier] for identifier in document.genre_ids),
            "biblical_figures": tuple(
                expected.biblical_figures[identifier]
                for identifier in document.biblical_figure_ids
            ),
        }, work_id

    expected_genres = tuple(sorted(expected.genres.values()))
    expected_figures = tuple(sorted(expected.biblical_figures.values()))
    assert actual.genres() == expected_genres
    assert actual.figures() == expected_figures

    for label in expected_genres:
        works = tuple(
            sorted(
                work_id
                for work_id, document in expected.documents.items()
                if any(expected.genres[identifier] == label for identifier in document.genre_ids)
            )
        )
        assert actual.works_by_genre(label) == works, label

    for label in expected_figures:
        works = tuple(
            sorted(
                work_id
                for work_id, document in expected.documents.items()
                if any(
                    expected.biblical_figures[identifier] == label
                    for identifier in document.biblical_figure_ids
                )
            )
        )
        assert actual.works_by_figure(label) == works, label


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: pinned_classification_acceptance.py TF_DIR")
    verify(Path(sys.argv[1]))
