"""Python 3.14 clean-wheel researcher smoke, run from outside repository.

Exercise the public CLI, Text-Fabric corpus load, primary-vs-omission witness
semantics, stock Flask browser and /compare real HTTP route. This script must
run with the installed *wheel* rather than an editable working tree.
"""
from __future__ import annotations

from importlib.metadata import distribution, version
from pathlib import Path
import shutil
import sys
import tempfile


def verify(source_fixture: Path, app_path: Path) -> None:
    assert sys.version_info >= (3, 14), sys.version
    package = distribution("pseudepigrapha-tf")
    assert package.metadata.get("Requires-Python") == ">=3.12"
    assert version("text-fabric").split(".")[0] == "13"

    from tf.fabric import Fabric
    from pseudepigrapha_tf.apparatus import Apparatus
    from pseudepigrapha_tf.cli import main
    from pseudepigrapha_tf.web import load_local_comparison_web_app

    with tempfile.TemporaryDirectory(prefix="pseudepigrapha-python-314-") as work:
        root = Path(work)
        source_dir = root / "source"
        source_dir.mkdir()
        shutil.copyfile(source_fixture, source_dir / "Sample.xml")
        tf_dir = root / "tf"
        assert main(["convert", str(source_dir), "--output", str(tf_dir)]) == 0
        assert (tf_dir / "otype.tf").is_file()
        assert (tf_dir / "conversion-report.json").is_file()

        api = Fabric(locations=[str(tf_dir)], modules=[""], silent="deep").load(
            " ".join((*Apparatus.PASSAGE_FEATURES, "book", "source_ref", "ocp_book", "version_id")),
            silent="deep",
        )
        assert api is not None
        book_nodes = tuple(
            node for node in api.F.otype.s("book")
            if api.F.ocp_book.v(node) == "Sample"
        )
        assert len(book_nodes) == 1, book_nodes
        source_book_id = api.F.book.v(book_nodes[0])
        assert api.T.nodeFromSection((source_book_id, "1", "2")) is not None
        record = Apparatus(api).passage(source_book_id, "1", "2")
        assert record["source_refs"] == ("1:2",), record["source_refs"]
        assert len(record["units"]) == 1
        assert record["witnesses"]["A"]["segments"][0]["status"] == "omission"
        assert record["witnesses"]["B"]["segments"][0]["status"] == "reading"

        flask_app = load_local_comparison_web_app(
            tf_dir, app_path, version="0.1", silent="deep",
        )
        client = flask_app.test_client()
        root_page = client.get("/")
        assert root_page.status_code == 200, root_page.get_data(as_text=True)[:600]
        landing = client.get("/compare")
        assert landing.status_code == 200
        assert '<option value="Sample">' in landing.get_data(as_text=True)
        route = client.get("/compare?work=Sample&chapter=1&verse=2")
        markup = route.get_data(as_text=True)
        assert route.status_code == 200, markup[:1600]
        assert 'class="state-omission"' in markup
        assert "πλήρης" in markup
        assert 'data-witness="A"' in markup
        assert 'data-witness="B"' in markup
        css = client.get("/data/static/comparison.css")
        assert css.status_code == 200
        assert ".source-version-card" in css.get_data(as_text=True)
        # A fixture's contradictory witness at "Heading" must remain
        # a safe HTTP 400, not silently select one of two alternatives.
        ambiguous = client.get("/compare?work=Sample&chapter=1&verse=Heading")
        assert ambiguous.status_code == 400
        assert "multiple readings at unit" in ambiguous.get_data(as_text=True)
        print(
            f"Python {sys.version_info.major}.{sys.version_info.minor} "
            f"installed wheel {package.version}, Text-Fabric {version('text-fabric')}: "
            "source passage, omission, manuscript, browser and HTTP compare PASS",
            flush=True,
        )


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit(
            "usage: modern_runtime_acceptance.py /absolute/Sample.xml /absolute/app"
        )
    verify(Path(sys.argv[1]).resolve(), Path(sys.argv[2]).resolve())
