from pathlib import Path


def test_readme_documents_historical_classification_query_api():
    root = Path(__file__).resolve().parents[1]
    readme = (root / "README.md").read_text(encoding="utf-8")

    assert "HistoricalClassifications" in readme
    assert "works_by_genre" in readme
    assert "works_by_figure" in readme
    assert "docs/historical-classifications.md" in readme
