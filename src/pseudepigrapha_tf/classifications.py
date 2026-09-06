from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from importlib.resources import files
from pathlib import Path
from typing import Any, Mapping

from .graph import TFData

_FIXTURE_NAME = "ocp_classifications_2017.json"
_TOP_LEVEL_KEYS = frozenset({"source", "genres", "biblical_figures", "documents"})
_SOURCE_KEYS = frozenset(
    {
        "repository",
        "historical_commit",
        "historical_commit_date",
        "storage_sqlite_git_blob",
        "storage_sqlite_sha256",
        "status",
    }
)
_VOCAB_KEYS = frozenset({"id", "label"})
_DOCUMENT_KEYS = frozenset(
    {"historical_doc_id", "work_id", "genre_ids", "biblical_figure_ids"}
)

_FEATURE_DOC_ID = "historical_ocp_doc_id"
_FEATURE_GENRES = "historical_genres_json"
_FEATURE_FIGURES = "historical_biblical_figures_json"

_PROVENANCE_KEYS = {
    "repository": "historicalClassificationsSourceRepository",
    "historical_commit": "historicalClassificationsCommit",
    "historical_commit_date": "historicalClassificationsCommitDate",
    "storage_sqlite_git_blob": "historicalClassificationsSqliteBlob",
    "storage_sqlite_sha256": "historicalClassificationsSqliteSha256",
    "status": "historicalClassificationsStatus",
}
_FIXTURE_SHA_KEY = "historicalClassificationsFixtureSha256"


@dataclass(frozen=True)
class HistoricalClassificationDocument:
    historical_doc_id: int
    work_id: str
    genre_ids: tuple[int, ...]
    biblical_figure_ids: tuple[int, ...]


@dataclass(frozen=True)
class HistoricalClassificationCorpus:
    source: Mapping[str, str]
    genres: Mapping[int, str]
    biblical_figures: Mapping[int, str]
    documents: Mapping[str, HistoricalClassificationDocument]
    source_sha256: str
    source_file: str


def _unique_json_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON object key {key!r}")
        result[key] = value
    return result


def _decode_json(raw: bytes, *, source_name: str) -> Any:
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError(f"{source_name}: invalid UTF-8 JSON: {exc}") from exc
    try:
        return json.loads(text, object_pairs_hook=_unique_json_object)
    except json.JSONDecodeError as exc:
        raise ValueError(f"{source_name}: invalid JSON: {exc}") from exc
    except ValueError as exc:
        raise ValueError(f"{source_name}: {exc}") from exc


def _fixture_bytes(path: str | Path | None) -> tuple[bytes, str]:
    if path is None:
        resource = files("pseudepigrapha_tf").joinpath("data", _FIXTURE_NAME)
        return resource.read_bytes(), _FIXTURE_NAME
    source = Path(path)
    return source.read_bytes(), source.name


def _require_object(value: Any, *, location: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{location}: expected object")
    return value


def _require_exact_keys(value: Mapping[str, Any], expected: frozenset[str], *, location: str) -> None:
    unknown = set(value) - expected
    missing = expected - set(value)
    if unknown:
        raise ValueError(f"{location}: unknown keys {sorted(unknown)!r}")
    if missing:
        raise ValueError(f"{location}: missing keys {sorted(missing)!r}")


def _require_positive_int(value: Any, *, location: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ValueError(f"{location}: expected positive integer")
    return value


def _require_nonempty_string(value: Any, *, location: str) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{location}: expected non-empty string")
    return value


def _parse_vocabulary(rows: Any, *, kind: str) -> dict[int, str]:
    if not isinstance(rows, list):
        raise ValueError(f"{kind}: expected array")
    by_id: dict[int, str] = {}
    seen_labels: set[str] = set()
    for index, raw_row in enumerate(rows):
        row = _require_object(raw_row, location=f"{kind}[{index}]")
        _require_exact_keys(row, _VOCAB_KEYS, location=f"{kind}[{index}]")
        identifier = _require_positive_int(row["id"], location=f"{kind}[{index}].id")
        label = _require_nonempty_string(row["label"], location=f"{kind}[{index}].label")
        if identifier in by_id:
            raise ValueError(f"duplicate {kind} id {identifier}")
        if label in seen_labels:
            raise ValueError(f"duplicate {kind} label {label!r}")
        by_id[identifier] = label
        seen_labels.add(label)
    return by_id


def _parse_id_list(value: Any, *, vocabulary: Mapping[int, str], location: str, kind: str) -> tuple[int, ...]:
    if not isinstance(value, list):
        raise ValueError(f"{location}: expected array")
    result: list[int] = []
    seen: set[int] = set()
    for index, raw_id in enumerate(value):
        identifier = _require_positive_int(raw_id, location=f"{location}[{index}]")
        if identifier in seen:
            raise ValueError(f"{location}: duplicate {kind} id {identifier}")
        if identifier not in vocabulary:
            raise ValueError(f"{location}: unknown {kind} id {identifier}")
        result.append(identifier)
        seen.add(identifier)
    return tuple(result)


def load_historical_classifications(
    path: str | Path | None = None,
) -> HistoricalClassificationCorpus:
    """Load and strictly validate the public-only 2017 OCP classification fixture."""

    raw, source_name = _fixture_bytes(path)
    payload = _require_object(_decode_json(raw, source_name=source_name), location=source_name)
    _require_exact_keys(payload, _TOP_LEVEL_KEYS, location=source_name)

    source = _require_object(payload["source"], location="source")
    _require_exact_keys(source, _SOURCE_KEYS, location="source")
    clean_source = {
        key: _require_nonempty_string(value, location=f"source.{key}")
        for key, value in source.items()
    }

    genres = _parse_vocabulary(payload["genres"], kind="genre")
    figures = _parse_vocabulary(payload["biblical_figures"], kind="biblical figure")

    raw_documents = payload["documents"]
    if not isinstance(raw_documents, list):
        raise ValueError("documents: expected array")
    documents: dict[str, HistoricalClassificationDocument] = {}
    doc_ids: set[int] = set()
    for index, raw_document in enumerate(raw_documents):
        document = _require_object(raw_document, location=f"documents[{index}]")
        _require_exact_keys(document, _DOCUMENT_KEYS, location=f"documents[{index}]")
        historical_doc_id = _require_positive_int(
            document["historical_doc_id"], location=f"documents[{index}].historical_doc_id"
        )
        work_id = _require_nonempty_string(document["work_id"], location=f"documents[{index}].work_id")
        if historical_doc_id in doc_ids:
            raise ValueError(f"duplicate historical document id {historical_doc_id}")
        if work_id in documents:
            raise ValueError(f"duplicate historical work {work_id!r}")
        genre_ids = _parse_id_list(
            document["genre_ids"],
            vocabulary=genres,
            location=f"documents[{index}].genre_ids",
            kind="genre",
        )
        figure_ids = _parse_id_list(
            document["biblical_figure_ids"],
            vocabulary=figures,
            location=f"documents[{index}].biblical_figure_ids",
            kind="biblical figure",
        )
        documents[work_id] = HistoricalClassificationDocument(
            historical_doc_id=historical_doc_id,
            work_id=work_id,
            genre_ids=genre_ids,
            biblical_figure_ids=figure_ids,
        )
        doc_ids.add(historical_doc_id)

    return HistoricalClassificationCorpus(
        source=clean_source,
        genres=genres,
        biblical_figures=figures,
        documents=documents,
        source_sha256=hashlib.sha256(raw).hexdigest(),
        source_file=source_name,
    )


def _metadata_nodes_by_work(data: TFData) -> dict[str, int]:
    result: dict[str, int] = {}
    otype = data.node_features.get("otype", {})
    works = data.node_features.get("ocp_book", {})
    for node, kind in otype.items():
        if kind != "document_metadata":
            continue
        work_id = works.get(node)
        if not isinstance(work_id, str) or not work_id:
            raise ValueError(f"document_metadata node {node} lacks ocp_book identity")
        if work_id in result:
            raise ValueError(f"duplicate document_metadata work identity {work_id!r}")
        result[work_id] = node
    return result


def attach_historical_classifications(
    data: TFData,
    classifications: HistoricalClassificationCorpus,
) -> None:
    """Attach historical catalogue classifications to existing work metadata nodes."""

    existing = data.node_features.get(_FEATURE_DOC_ID, {})
    if existing:
        raise ValueError("historical OCP classifications are already attached")

    metadata_nodes = _metadata_nodes_by_work(data)
    missing = sorted(set(classifications.documents) - set(metadata_nodes))
    if missing:
        raise ValueError(
            "historical classification work has no matching document_metadata node: "
            + ", ".join(missing)
        )

    doc_ids = data.node_features.setdefault(_FEATURE_DOC_ID, {})
    genre_values = data.node_features.setdefault(_FEATURE_GENRES, {})
    figure_values = data.node_features.setdefault(_FEATURE_FIGURES, {})

    for work_id, document in classifications.documents.items():
        node = metadata_nodes[work_id]
        doc_ids[node] = document.historical_doc_id
        genre_values[node] = json.dumps(
            [classifications.genres[identifier] for identifier in document.genre_ids],
            ensure_ascii=False,
        )
        figure_values[node] = json.dumps(
            [classifications.biblical_figures[identifier] for identifier in document.biblical_figure_ids],
            ensure_ascii=False,
        )

    data.metadata[_FEATURE_DOC_ID] = {
        "valueType": "int",
        "description": "published OCP docs.id from the historical 2017 classification snapshot",
    }
    data.metadata[_FEATURE_GENRES] = {
        "valueType": "str",
        "description": "JSON array of exact public OCP genre labels from the historical 2017 catalogue",
    }
    data.metadata[_FEATURE_FIGURES] = {
        "valueType": "str",
        "description": "JSON array of exact public OCP biblical-figure labels from the historical 2017 catalogue",
    }

    generic = data.metadata.setdefault("", {})
    for source_key, metadata_key in _PROVENANCE_KEYS.items():
        generic[metadata_key] = classifications.source[source_key]
    generic[_FIXTURE_SHA_KEY] = classifications.source_sha256

    failures = data.validate()
    if failures:
        raise ValueError(
            "invalid Text-Fabric graph after historical classification attachment: "
            + "; ".join(failures)
        )


class HistoricalClassifications:
    """Selective-load query API for historical OCP catalogue classifications."""

    REQUIRED_FEATURES = (
        "ocp_book",
        _FEATURE_DOC_ID,
        _FEATURE_GENRES,
        _FEATURE_FIGURES,
    )

    def __init__(self, api: Any) -> None:
        self.api = api
        self._records: dict[str, dict[str, Any]] = {}
        self._by_genre: dict[str, set[str]] = {}
        self._by_figure: dict[str, set[str]] = {}

        for node in api.F.otype.s("document_metadata"):
            historical_doc_id = getattr(api.F, _FEATURE_DOC_ID).v(node)
            if historical_doc_id is None:
                continue
            work_id = api.F.ocp_book.v(node)
            if not work_id:
                raise ValueError(f"classified document_metadata node {node} lacks ocp_book")
            work_id = str(work_id)
            if work_id in self._records:
                raise ValueError(f"duplicate classified work identity {work_id!r}")
            genres = self._decode_label_array(node, _FEATURE_GENRES)
            figures = self._decode_label_array(node, _FEATURE_FIGURES)
            record = {
                "historical_doc_id": int(historical_doc_id),
                "genres": genres,
                "biblical_figures": figures,
            }
            self._records[work_id] = record
            for label in genres:
                self._by_genre.setdefault(label, set()).add(work_id)
            for label in figures:
                self._by_figure.setdefault(label, set()).add(work_id)

    def _decode_label_array(self, node: int, feature: str) -> tuple[str, ...]:
        raw = getattr(self.api.F, feature).v(node)
        if raw is None:
            raise ValueError(f"classified document_metadata node {node} lacks {feature}")
        try:
            value = json.loads(raw)
        except (TypeError, json.JSONDecodeError) as exc:
            raise ValueError(f"node {node} has invalid {feature}: {exc}") from exc
        if not isinstance(value, list) or any(not isinstance(item, str) or not item for item in value):
            raise ValueError(f"node {node} has invalid {feature} label array")
        return tuple(value)

    def get(self, work: str, default: Any = None) -> Any:
        key = work[:-4] if work.endswith(".xml") else work
        return self._records.get(key, default)

    def for_work(self, work: str, default: Any = None) -> Any:
        return self.get(work, default)

    def __getitem__(self, work: str) -> dict[str, Any]:
        value = self.get(work)
        if value is None:
            raise KeyError(work)
        return value

    def keys(self) -> tuple[str, ...]:
        return tuple(sorted(self._records))

    def works_by_genre(self, label: str) -> tuple[str, ...]:
        return tuple(sorted(self._by_genre.get(label, ())))

    def works_by_figure(self, label: str) -> tuple[str, ...]:
        return tuple(sorted(self._by_figure.get(label, ())))

    def genres(self) -> tuple[str, ...]:
        return tuple(sorted(self._by_genre))

    def figures(self) -> tuple[str, ...]:
        return tuple(sorted(self._by_figure))


def _raw_projection(path: str | Path | None) -> tuple[dict[str, Any], dict[str, str], str, set[str], set[str]]:
    raw, source_name = _fixture_bytes(path)
    payload = _require_object(_decode_json(raw, source_name=source_name), location=source_name)
    source = _require_object(payload.get("source"), location="source")

    genre_rows = payload.get("genres")
    figure_rows = payload.get("biblical_figures")
    document_rows = payload.get("documents")
    if not isinstance(genre_rows, list) or not isinstance(figure_rows, list) or not isinstance(document_rows, list):
        raise ValueError(f"{source_name}: invalid classification inventory arrays")

    genres = {row["id"]: row["label"] for row in genre_rows}
    figures = {row["id"]: row["label"] for row in figure_rows}
    projection: dict[str, Any] = {}
    for row in document_rows:
        work_id = row["work_id"]
        if work_id in projection:
            raise ValueError(f"{source_name}: duplicate work {work_id!r}")
        try:
            genre_labels = [genres[identifier] for identifier in row["genre_ids"]]
            figure_labels = [figures[identifier] for identifier in row["biblical_figure_ids"]]
        except KeyError as exc:
            raise ValueError(f"{source_name}: dangling vocabulary id {exc.args[0]!r}") from exc
        projection[work_id] = {
            "historical_doc_id": row["historical_doc_id"],
            "genres": genre_labels,
            "biblical_figures": figure_labels,
        }

    clean_source = {key: str(source.get(key, "")) for key in _PROVENANCE_KEYS}
    return (
        projection,
        clean_source,
        hashlib.sha256(raw).hexdigest(),
        set(genres.values()),
        set(figures.values()),
    )


def _graph_projection(data: TFData) -> tuple[dict[str, Any], list[str], list[str]]:
    result: dict[str, Any] = {}
    errors: list[str] = []
    duplicates: list[str] = []
    otype = data.node_features.get("otype", {})
    works = data.node_features.get("ocp_book", {})
    doc_ids = data.node_features.get(_FEATURE_DOC_ID, {})
    genres = data.node_features.get(_FEATURE_GENRES, {})
    figures = data.node_features.get(_FEATURE_FIGURES, {})

    for node, kind in otype.items():
        if kind != "document_metadata":
            continue
        has_any = node in doc_ids or node in genres or node in figures
        if not has_any:
            continue
        work_id = works.get(node)
        if not isinstance(work_id, str) or not work_id:
            errors.append(f"node {node}: missing ocp_book")
            continue
        if work_id in result:
            duplicates.append(work_id)
            continue
        if node not in doc_ids or node not in genres or node not in figures:
            errors.append(f"{work_id}: incomplete historical classification feature set")
            continue
        try:
            genre_labels = json.loads(genres[node])
            figure_labels = json.loads(figures[node])
            if not isinstance(genre_labels, list) or not isinstance(figure_labels, list):
                raise ValueError("classification labels must decode as arrays")
            if any(not isinstance(label, str) for label in [*genre_labels, *figure_labels]):
                raise ValueError("classification label arrays contain non-string values")
        except (TypeError, ValueError, json.JSONDecodeError) as exc:
            errors.append(f"{work_id}: {exc}")
            continue
        result[work_id] = {
            "historical_doc_id": doc_ids[node],
            "genres": genre_labels,
            "biblical_figures": figure_labels,
        }
    return result, errors, duplicates


def augment_conversion_report_with_historical_classifications(
    report: dict[str, Any],
    data: TFData,
    path: str | Path | None = None,
) -> dict[str, Any]:
    """Audit historical classification fixture independently against the TF graph."""

    raw, source, fixture_sha, genre_vocab, figure_vocab = _raw_projection(path)
    graph, decode_errors, duplicate_works = _graph_projection(data)
    generic = data.metadata.get("", {})

    graph_genres = {label for record in graph.values() for label in record["genres"]}
    graph_figures = {label for record in graph.values() for label in record["biblical_figures"]}

    checks = report.setdefault("semantic_checks", {})
    checks["historical_classification_documents"] = set(raw) == set(graph) and not duplicate_works
    checks["historical_classification_values"] = raw == graph and not decode_errors and not duplicate_works
    checks["historical_classification_vocabulary"] = (
        genre_vocab == graph_genres and figure_vocab == graph_figures
    )
    checks["historical_classification_provenance"] = all(
        generic.get(metadata_key) == source[source_key]
        for source_key, metadata_key in _PROVENANCE_KEYS.items()
    ) and generic.get(_FIXTURE_SHA_KEY) == fixture_sha

    source_section = report.setdefault("source", {})
    graph_section = report.setdefault("graph", {})
    source_section["historical_classified_works"] = len(raw)
    source_section["historical_genre_assignments"] = sum(len(record["genres"]) for record in raw.values())
    source_section["historical_biblical_figure_assignments"] = sum(
        len(record["biblical_figures"]) for record in raw.values()
    )
    source_section["historical_genre_labels"] = len(genre_vocab)
    source_section["historical_biblical_figure_labels"] = len(figure_vocab)
    graph_section["historical_classified_works"] = len(graph)
    graph_section["historical_genre_assignments"] = sum(len(record["genres"]) for record in graph.values())
    graph_section["historical_biblical_figure_assignments"] = sum(
        len(record["biblical_figures"]) for record in graph.values()
    )
    graph_section["historical_genre_labels"] = len(graph_genres)
    graph_section["historical_biblical_figure_labels"] = len(graph_figures)

    provenance = report.setdefault("provenance", {})
    provenance["historical_classifications_commit"] = generic.get(
        _PROVENANCE_KEYS["historical_commit"], ""
    )
    provenance["historical_classifications_fixture_sha256"] = generic.get(_FIXTURE_SHA_KEY, "")
    report.setdefault("diagnostics", {})["historical_classifications"] = {
        "source_status": source.get("status", ""),
        "decode_errors": decode_errors,
        "duplicate_graph_works": duplicate_works,
    }

    failed = [name for name, ok in checks.items() if not ok]
    report["failed_checks"] = failed
    report["status"] = "ok" if not failed else "failed"
    return report
