from pathlib import Path

from pseudepigrapha_tf import conversion
from pseudepigrapha_tf.model import Div
from pseudepigrapha_tf.parser import parse_file

FIXTURES = Path(__file__).parent / "fixtures"


class _TrackingItems(list):
    def __init__(self, values):
        super().__init__(values)
        self.iterations = 0

    def __iter__(self):
        self.iterations += 1
        return super().__iter__()


def _track_div_items(version):
    tracked = []
    stack = list(version.divs)
    while stack:
        div = stack.pop()
        children = [item for item in div.items if isinstance(item, Div)]
        items = _TrackingItems(div.items)
        div.items = items
        tracked.append(items)
        stack.extend(children)
    return tracked


def test_model_preflight_traverses_each_div_once_before_graph_mutation(monkeypatch):
    book = parse_file(FIXTURES / "sample.xml")
    tracked = _track_div_items(book.versions[0])
    iterations_at_first_mutation = None
    original_builder = conversion._Builder

    class TrackingBuilder(original_builder):
        def node(self, *args, **kwargs):
            nonlocal iterations_at_first_mutation
            if iterations_at_first_mutation is None:
                iterations_at_first_mutation = sum(items.iterations for items in tracked)
            return super().node(*args, **kwargs)

    monkeypatch.setattr(conversion, "_Builder", TrackingBuilder)

    data = conversion.build_tf_data([book])

    assert data.validate() == []
    assert iterations_at_first_mutation == len(tracked)
