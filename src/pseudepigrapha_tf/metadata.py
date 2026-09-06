from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping
from xml.etree import ElementTree as ET

from .graph import TFData

PUBLIC_METADATA_FIELDS = (
    "introduction",
    "provenance",
    "themes",
    "status",
    "manuscripts",
    "bibliography",
    "corrections",
    "sigla",
    "copyright",
)

_TOP_LEVEL_FEATURES = {
    "title": "intro_title_json",
    "version": "intro_version_json",
    "citation": "intro_citation_json",
}
_FIELD_FEATURES = {name: f"intro_{name}_json" for name in PUBLIC_METADATA_FIELDS}
ALL_INTRO_FEATURES = tuple(_TOP_LEVEL_FEATURES.values()) + tuple(_FIELD_FEATURES.values())
_ALLOWED_ENTRY_KEYS = frozenset({"title", "version", "citation", "fields"})
_REQUIRED_ENTRY_KEYS = frozenset({"title", "version", "fields"})
_JSON_SCALAR_TYPES = (str, int, float, bool, type(None))


@dataclass(frozen=True)
class PublicMetadataDocument:
    filename: str
    title: Any
    version: Any
    citation: Any
    citation_present: bool
    fields: Mapping[str, Any]

    @property
    def work_id(self) -> str:
        return self.filename[:-4] if self.filename.endswith(".xml") else self.filename

    def as_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "title": self.title,
            "version": self.version,
        }
        if self.citation_present:
            result["citation"] = self.citation
        result["fields"] = dict(self.fields)
        return result


@dataclass(frozen=True)
class PublicMetadataCorpus:
    documents: Mapping[str, PublicMetadataDocument]
    source_sha256: str
    source_meta: Mapping[str, Any]
    source_file: str = "intros.json"


def _require_scalar(value: Any, *, location: str) -> Any:
    if not isinstance(value, _JSON_SCALAR_TYPES):
        raise ValueError(f"{location}: expected JSON scalar, got {type(value).__name__}")
    return value


def _validate_xml_identities(source_dir: Path) -> set[str]:
    filenames: set[str] = set()
    for xml_path in sorted(source_dir.glob("*.xml")):
        if xml_path.name.startswith("."):
            continue
        filenames.add(xml_path.name)
        raw = xml_path.read_bytes()
        if not raw.strip():
            continue
        try:
            root = ET.fromstring(raw)
        except ET.ParseError as exc:
            raise ValueError(f"{xml_path.name}: cannot validate XML work identity: {exc}") from exc
        declared = root.attrib.get("filename", "")
        expected = xml_path.stem
        if declared != expected:
            raise ValueError(
                f"{xml_path.name}: XML root filename identity {declared!r} does not match {expected!r}"
            )
    return filenames


def load_public_metadata(path: str | Path) -> PublicMetadataCorpus:
    """Load and strictly map the committed public OCP ``intros.json`` export.

    Mapping is by exact root-level XML filename. Long source strings are kept as
    Python values here; JSON-scalar escaping happens only at the TF boundary so
    the researcher-facing API can return the original values verbatim.
    """

    source_dir = Path(path)
    intro_path = source_dir / "intros.json"
    raw = intro_path.read_bytes()
    source_sha256 = hashlib.sha256(raw).hexdigest()
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"{intro_path.name}: invalid UTF-8 JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise ValueError("intros.json: top level must be an object")
    documents = payload.get("documents")
    if not isinstance(documents, dict):
        raise ValueError("intros.json: documents must be an object")
    source_meta = payload.get("_meta", {})
    if not isinstance(source_meta, dict):
        raise ValueError("intros.json: _meta must be an object when present")

    xml_filenames = _validate_xml_identities(source_dir)
    parsed: dict[str, PublicMetadataDocument] = {}
    for filename, entry in documents.items():
        if not isinstance(filename, str) or not filename.endswith(".xml"):
            raise ValueError(f"intros.json document key must be an XML filename: {filename!r}")
        if filename not in xml_filenames:
            raise ValueError(f"intros.json document {filename} has no matching root-level XML source")
        if not isinstance(entry, dict):
            raise ValueError(f"{filename}: metadata entry must be an object")
        unknown = set(entry) - _ALLOWED_ENTRY_KEYS
        missing = _REQUIRED_ENTRY_KEYS - set(entry)
        if unknown:
            raise ValueError(f"{filename}: unknown public metadata keys: {sorted(unknown)!r}")
        if missing:
            raise ValueError(f"{filename}: missing required public metadata keys: {sorted(missing)!r}")

        fields = entry["fields"]
        if not isinstance(fields, dict):
            raise ValueError(f"{filename}: fields must be an object")
        unknown_fields = set(fields) - set(PUBLIC_METADATA_FIELDS)
        if unknown_fields:
            raise ValueError(f"{filename}: unknown public metadata fields: {sorted(unknown_fields)!r}")
        clean_fields = {
            key: _require_scalar(value, location=f"{filename}.fields.{key}")
            for key, value in fields.items()
        }
        citation_present = "citation" in entry
        citation = (
            _require_scalar(entry["citation"], location=f"{filename}.citation")
            if citation_present
            else None
        )
        parsed[filename] = PublicMetadataDocument(
            filename=filename,
            title=_require_scalar(entry["title"], location=f"{filename}.title"),
            version=_require_scalar(entry["version"], location=f"{filename}.version"),
            citation=citation,
            citation_present=citation_present,
            fields=clean_fields,
        )

    return PublicMetadataCorpus(
        documents=parsed,
        source_sha256=source_sha256,
        source_meta=dict(source_meta),
        source_file=intro_path.name,
    )


def _encode_scalar(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False)


def _encoded_features(document: PublicMetadataDocument) -> dict[str, str]:
    features = {
        _TOP_LEVEL_FEATURES["title"]: _encode_scalar(document.title),
        _TOP_LEVEL_FEATURES["version"]: _encode_scalar(document.version),
    }
    if document.citation_present:
        features[_TOP_LEVEL_FEATURES["citation"]] = _encode_scalar(document.citation)
    for name, value in document.fields.items():
        features[_FIELD_FEATURES[name]] = _encode_scalar(value)
    return features


def _intro_feature_description(name: str) -> str:
    if name == "intro_title_json":
        return "JSON-scalar encoded public OCP document title from intros.json"
    if name == "intro_version_json":
        return "JSON-scalar encoded public OCP document edition version from intros.json"
    if name == "intro_citation_json":
        return "JSON-scalar encoded per-document OCP citation from intros.json"
    field = name[len("intro_") : -len("_json")]
    return f"JSON-scalar encoded public OCP {field} field from intros.json"


def attach_public_metadata(data: TFData, metadata: PublicMetadataCorpus) -> None:
    """Attach one lossless work-level TF node per public metadata document."""

    if not metadata.documents:
        return
    max_slot = data.max_slot
    if max_slot < 1:
        raise ValueError("public metadata cannot be attached to a TF graph with no word slot")
    if any(kind == "document_metadata" for kind in data.node_features.get("otype", {}).values()):
        raise ValueError("public document metadata is already attached")

    # A textual work uses its own first slot as a technical anchor. JSON-only
    # works such as 3Macc reuse corpus slot 1 without becoming TF text sections.
    work_anchors: dict[str, int] = {}
    for slot, work_id in data.node_features.get("ocp_book", {}).items():
        if slot <= max_slot:
            work_anchors.setdefault(str(work_id), slot)

    otype = data.node_features.setdefault("otype", {})
    oslots = data.edge_features.setdefault("oslots", {})
    next_node = data.max_node + 1
    for filename in sorted(metadata.documents):
        document = metadata.documents[filename]
        node = next_node
        next_node += 1
        otype[node] = "document_metadata"
        oslots[node] = {work_anchors.get(document.work_id, 1)}
        data.node_features.setdefault("ocp_book", {})[node] = document.work_id
        data.node_features.setdefault("source_file", {})[node] = filename
        label = document.title if isinstance(document.title, str) and document.title else document.work_id
        data.node_features.setdefault("intro_label", {})[node] = str(label)
        for feature, value in _encoded_features(document).items():
            data.node_features.setdefault(feature, {})[node] = value

    # Keep the selective-load API stable even when a particular snapshot has no
    # values for one of the public fields.
    for feature in ALL_INTRO_FEATURES:
        data.node_features.setdefault(feature, {})
        data.metadata[feature] = {
            "valueType": "str",
            "description": _intro_feature_description(feature),
        }
    data.metadata.setdefault("intro_label", {
        "valueType": "str",
        "description": "short display label for an OCP document_metadata node",
    })
    data.metadata.setdefault("source_file", {
        "valueType": "str",
        "description": "stable source path relative to the supplied OCP docs directory",
    })
    data.metadata.setdefault("ocp_book", {
        "valueType": "str",
        "description": "stable OCP work identifier",
    })
    data.metadata.setdefault("otext", {})["fmt:document_metadata-default"] = "{intro_label}"

    generic = data.metadata.setdefault("", {})
    generic["introsSource"] = metadata.source_file
    generic["introsSha256"] = metadata.source_sha256
    exported = metadata.source_meta.get("exported")
    if exported is not None:
        generic["introsExported"] = str(exported)

    failures = data.validate()
    if failures:
        raise ValueError("invalid Text-Fabric graph after public metadata attachment: " + "; ".join(failures))


class WorkMetadata:
    """Convenient decoder/index for work-level public OCP metadata."""

    REQUIRED_FEATURES = (
        "ocp_book",
        "source_file",
        *ALL_INTRO_FEATURES,
    )

    def __init__(self, api: Any) -> None:
        self.api = api
        self._nodes: dict[str, int] = {}
        for node in api.F.otype.s("document_metadata"):
            source_file = api.F.source_file.v(node)
            work_id = api.F.ocp_book.v(node)
            if not source_file or not work_id:
                raise ValueError(f"document_metadata node {node} lacks source identity")
            for key in (str(work_id), str(source_file)):
                if key in self._nodes:
                    raise ValueError(f"duplicate public metadata identity {key!r}")
                self._nodes[key] = node

    def _decode(self, node: int, feature: str) -> Any:
        raw = getattr(self.api.F, feature).v(node)
        if raw is None:
            raise KeyError(feature)
        return json.loads(raw)

    def get(self, work: str, default: Any = None) -> Any:
        node = self._nodes.get(work)
        if node is None and work.endswith(".xml"):
            node = self._nodes.get(work[:-4])
        elif node is None:
            node = self._nodes.get(f"{work}.xml")
        if node is None:
            return default

        result: dict[str, Any] = {
            "title": self._decode(node, _TOP_LEVEL_FEATURES["title"]),
            "version": self._decode(node, _TOP_LEVEL_FEATURES["version"]),
        }
        citation_raw = getattr(self.api.F, _TOP_LEVEL_FEATURES["citation"]).v(node)
        if citation_raw is not None:
            result["citation"] = json.loads(citation_raw)
        fields: dict[str, Any] = {}
        for name, feature in _FIELD_FEATURES.items():
            raw = getattr(self.api.F, feature).v(node)
            if raw is not None:
                fields[name] = json.loads(raw)
        result["fields"] = fields
        return result

    def __getitem__(self, work: str) -> dict[str, Any]:
        value = self.get(work, None)
        if value is None:
            raise KeyError(work)
        return value

    def keys(self) -> tuple[str, ...]:
        return tuple(sorted(key for key in self._nodes if not key.endswith(".xml")))


def _raw_public_metadata(source_dir: Path) -> tuple[dict[str, Any], str, dict[str, Any]]:
    intro_path = source_dir / "intros.json"
    raw = intro_path.read_bytes()
    payload = json.loads(raw.decode("utf-8"))
    documents = payload.get("documents", {})
    if not isinstance(documents, dict):
        raise ValueError("intros.json: documents must be an object")
    source_meta = payload.get("_meta", {})
    if not isinstance(source_meta, dict):
        source_meta = {"_invalid_meta": source_meta}
    return documents, hashlib.sha256(raw).hexdigest(), source_meta


def _graph_public_metadata(data: TFData) -> tuple[dict[str, Any], list[str], list[str]]:
    documents: dict[str, Any] = {}
    errors: list[str] = []
    duplicates: list[str] = []
    otype = data.node_features.get("otype", {})
    source_files = data.node_features.get("source_file", {})

    for node, kind in otype.items():
        if kind != "document_metadata":
            continue
        filename = source_files.get(node)
        if not isinstance(filename, str) or not filename:
            errors.append(f"node {node}: missing source_file")
            continue
        if filename in documents:
            duplicates.append(filename)
            continue
        entry: dict[str, Any] = {}
        try:
            for key, feature in _TOP_LEVEL_FEATURES.items():
                raw = data.node_features.get(feature, {}).get(node)
                if raw is not None:
                    entry[key] = json.loads(str(raw))
            fields: dict[str, Any] = {}
            for key, feature in _FIELD_FEATURES.items():
                raw = data.node_features.get(feature, {}).get(node)
                if raw is not None:
                    fields[key] = json.loads(str(raw))
            entry["fields"] = fields
        except (TypeError, ValueError, json.JSONDecodeError) as exc:
            errors.append(f"{filename}: {exc}")
        documents[filename] = entry
    return documents, errors, duplicates


def _public_scalar_count(documents: Mapping[str, Any]) -> int:
    count = 0
    for entry in documents.values():
        if not isinstance(entry, dict):
            continue
        count += sum(1 for key in ("title", "version", "citation") if key in entry)
        fields = entry.get("fields", {})
        if isinstance(fields, dict):
            count += len(fields)
    return count


def augment_conversion_report_with_public_metadata(
    report: dict[str, Any],
    source_dir: str | Path,
    data: TFData,
) -> dict[str, Any]:
    """Audit raw ``intros.json`` independently and merge parity into a report."""

    source_dir = Path(source_dir)
    intro_path = source_dir / "intros.json"
    if not intro_path.exists():
        return report

    raw_documents, raw_sha256, source_meta = _raw_public_metadata(source_dir)
    graph_documents, decode_errors, duplicate_files = _graph_public_metadata(data)
    generic = data.metadata.get("", {})

    checks = report.setdefault("semantic_checks", {})
    checks["public_metadata_documents"] = (
        set(raw_documents) == set(graph_documents) and not duplicate_files
    )
    checks["public_metadata_values"] = (
        raw_documents == graph_documents and not decode_errors and not duplicate_files
    )
    checks["public_metadata_provenance"] = (
        generic.get("introsSource") == intro_path.name
        and generic.get("introsSha256") == raw_sha256
    )

    report.setdefault("source", {})["public_metadata_documents"] = len(raw_documents)
    report["source"]["public_metadata_scalars"] = _public_scalar_count(raw_documents)
    report.setdefault("graph", {})["document_metadata"] = sum(
        1 for kind in data.node_features.get("otype", {}).values() if kind == "document_metadata"
    )
    report["graph"]["public_metadata_scalars"] = _public_scalar_count(graph_documents)
    report["intros_sha256"] = raw_sha256
    report.setdefault("provenance", {})["intros_source"] = generic.get("introsSource", "")
    report["provenance"]["intros_sha256"] = generic.get("introsSha256", "")
    report.setdefault("diagnostics", {})["public_metadata"] = {
        "source_meta": source_meta,
        "decode_errors": decode_errors,
        "duplicate_graph_files": duplicate_files,
    }

    failed = [name for name, ok in checks.items() if not ok]
    report["failed_checks"] = failed
    report["status"] = "ok" if not failed else "failed"
    return report
