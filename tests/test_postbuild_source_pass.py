from pathlib import Path

import pytest

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


def test_clean_build_does_not_rescan_source_tree_after_graph_finalize():
    book = parse_file(FIXTURES / "sample.xml")
    tracked = _track_div_items(book.versions[0])

    data = conversion.build_tf_data([book])

    assert data.validate() == []
    assert sum(items.iterations for items in tracked) == 2 * len(tracked)


def test_preflight_blank_unit_record_must_match_exactly_one_graph_unit():
    book = parse_file(FIXTURES / "sample.xml")
    data = conversion.build_tf_data([book])
    mismatched_shapes = ((
        conversion._VersionTreeShape(
            has_units=True,
            has_non_core_items=False,
            known_blank_unit_refs=("not-a-source-ref",),
        ),
    ),)

    with pytest.raises(
        ValueError,
        match=r"known missing unit id Sample/Sample at not-a-source-ref: expected exactly one graph unit, found 0",
    ):
        conversion._mark_known_missing_unit_ids(data, [book], mismatched_shapes)
