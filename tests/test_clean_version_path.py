from pathlib import Path

from pseudepigrapha_tf import conversion
from pseudepigrapha_tf.parser import parse_file

FIXTURES = Path(__file__).parent / "fixtures"


def test_clean_textual_version_reuses_model_and_skips_anomaly_pass(monkeypatch):
    book = parse_file(FIXTURES / "sample.xml")
    source_version = book.versions[0]
    same_version_identity = False
    anomaly_calls = 0
    original_add_version = conversion._add_version
    original_add_anomalies = conversion._add_textual_source_anomalies

    def counted_add_version(builder, add_book, version, version_id, book_index, version_index):
        nonlocal same_version_identity
        same_version_identity = version is source_version
        return original_add_version(
            builder,
            add_book,
            version,
            version_id,
            book_index,
            version_index,
        )

    def counted_add_anomalies(*args, **kwargs):
        nonlocal anomaly_calls
        anomaly_calls += 1
        return original_add_anomalies(*args, **kwargs)

    monkeypatch.setattr(conversion, "_add_version", counted_add_version)
    monkeypatch.setattr(conversion, "_add_textual_source_anomalies", counted_add_anomalies)

    data = conversion.build_tf_data([book])

    assert data.validate() == []
    assert (same_version_identity, anomaly_calls) == (True, 0)
