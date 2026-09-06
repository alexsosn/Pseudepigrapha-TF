from __future__ import annotations

from pseudepigrapha_tf.graph import TFData
from pseudepigrapha_tf.metadata import (
    PublicMetadataCorpus,
    PublicMetadataDocument,
    attach_public_metadata,
)


def test_metadata_attachment_reads_max_slot_constant_times(monkeypatch):
    data = TFData(
        node_features={
            "otype": {1: "word", 2: "word", 3: "word", 4: "book"},
            "ocp_book": {1: "One", 2: "One", 3: "Two", 4: "One"},
        },
        edge_features={"oslots": {4: {1, 2, 3}}},
        metadata={"": {}, "otext": {}},
    )
    document = PublicMetadataDocument(
        filename="One.xml",
        title="One",
        version=1.0,
        citation=None,
        citation_present=False,
        fields={},
    )
    metadata = PublicMetadataCorpus(
        documents={"One.xml": document},
        source_sha256="0" * 64,
        source_meta={},
    )

    original = TFData.max_slot.fget
    assert original is not None
    calls = 0

    def counted_max_slot(self):
        nonlocal calls
        calls += 1
        return original(self)

    monkeypatch.setattr(TFData, "max_slot", property(counted_max_slot))

    attach_public_metadata(data, metadata)

    # One lookup in attach_public_metadata plus one in the final full graph
    # validation. The number must not grow with the number of ocp_book nodes.
    assert calls <= 2
