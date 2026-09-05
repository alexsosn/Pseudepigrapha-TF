from pathlib import Path
from types import SimpleNamespace

import pytest

from pseudepigrapha_tf import Apparatus
from pseudepigrapha_tf.conversion import build_tf_data
from pseudepigrapha_tf.parser import parse_file
from pseudepigrapha_tf.writer import write_tf

FIXTURES = Path(__file__).parent / "fixtures"


class Feature:
    def __init__(self, values):
        self.values = values

    def v(self, node):
        return self.values.get(node)


class Edge:
    def __init__(self, forward):
        self.inverse = {}
        for source, targets in forward.items():
            for target in targets:
                self.inverse.setdefault(target, []).append(source)

    def t(self, node):
        return tuple(self.inverse.get(node, ()))


class Oslots:
    """Mirror Text-Fabric's special OslotsFeature API: .s(), never .f()."""

    def __init__(self, values):
        self.values = values

    def s(self, node):
        return tuple(self.values.get(node, ()))


def _api(*, reading_text=True, is_primary=True, variant_edge=True):
    features = {}
    if reading_text:
        features["reading_text"] = Feature({11: "alpha", 12: "beta"})
    if is_primary:
        features["is_primary"] = Feature({11: 1, 12: 0})
    edges = {"oslots": Oslots({11: (1, 2), 12: (1, 2)})}
    if variant_edge:
        edges["variant_word_of"] = Edge({13: {12}})
    return SimpleNamespace(F=SimpleNamespace(**features), E=SimpleNamespace(**edges))


def test_primary_reading_does_not_require_variant_edge_when_corpus_has_none(tmp_path):
    pytest.importorskip("tf")
    from tf.fabric import Fabric

    data = build_tf_data([parse_file(FIXTURES / "one_division.xml")])
    output = tmp_path / "tf"
    assert write_tf(data, output)
    TF = Fabric(locations=[str(output)], modules=[""], silent="deep")
    # one_division.xml contains no alternative tokens, so variant_word_of is not
    # serialized at all. Primary token access must still work.
    api = TF.load("reading_text is_primary g_word_utf8", silent="deep")
    assert api is not None

    reading = next(iter(api.F.otype.s("reading")))
    tokens = Apparatus(api).reading_tokens(reading)
    assert [api.F.g_word_utf8.v(node) for node in tokens] == ["abc", "def"]


def test_nonprimary_text_without_variant_edge_fails_clearly():
    with pytest.raises(ValueError, match="variant_word_of"):
        Apparatus(_api(variant_edge=False)).reading_tokens(12)


def test_nonprimary_text_with_empty_variant_edge_fails_as_inconsistent_graph():
    api = _api()
    api.E.variant_word_of = Edge({})
    with pytest.raises(ValueError, match="no variant_word tokens"):
        Apparatus(api).reading_tokens(12)


@pytest.mark.parametrize(("feature", "message"), [("reading_text", "reading_text"), ("is_primary", "is_primary")])
def test_reading_tokens_reports_missing_required_feature(feature, message):
    kwargs = {feature: False}
    with pytest.raises(ValueError, match=message):
        Apparatus(_api(**kwargs)).reading_tokens(11)
