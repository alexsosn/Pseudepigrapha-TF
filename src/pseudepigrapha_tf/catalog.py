"""Local lookup of upstream clavis claims against existing native TF source books.

A filename match is not a verified scholarly equivalence. The crosswalk stays
external to the corpus; no catalogue or dossier text is redistributed here.
"""
from __future__ import annotations

import csv
from hashlib import sha256
from io import StringIO
import re
from typing import Any


_COLUMNS = (
    "ocp_canon_id", "cavt_no", "cant_no", "standard_title", "section",
    "primary_language", "denis_ref", "ditommaso_ref", "otp_ref", "apot_ref",
    "sparks_ref", "ocp_xml", "dossier", "status", "category",
)
_CANON_ID = re.compile(r"CAVT-(?:[0-9]{3}|JH-[0-9]{2})")
_XML_FILENAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]*\.xml")
_SHA256 = re.compile(r"[0-9a-f]{64}")
REQUIRED_FEATURES = (
    "source_file", "source_sha256", "ocp_book", "version_id", "version_kind",
)


def _read_crosswalk(raw: bytes) -> list[dict[str, str]]:
    try:
        reader = csv.reader(StringIO(raw.decode("utf-8-sig"), newline=""), strict=True)
        header = next(reader, None)
        if header != list(_COLUMNS):
            raise ValueError("unexpected OCP crosswalk CSV header")
        rows: list[dict[str, str]] = []
        seen: set[str] = set()
        for values in reader:
            if len(values) != len(_COLUMNS):
                raise ValueError(f"malformed crosswalk row at line {reader.line_num}")
            row = dict(zip(_COLUMNS, values, strict=True))
            canon_id = row["ocp_canon_id"]
            filename = row["ocp_xml"]
            if not _CANON_ID.fullmatch(canon_id) or canon_id in seen:
                raise ValueError(f"invalid or duplicate canonical ID: {canon_id!r}")
            if filename and not _XML_FILENAME.fullmatch(filename):
                raise ValueError(f"invalid declared XML basename: {filename!r}")
            if not row["standard_title"].strip() or not row["status"].strip():
                raise ValueError(f"missing title or status for {canon_id}")
            seen.add(canon_id)
            rows.append(row)
    except (UnicodeError, csv.Error) as error:
        raise ValueError(f"invalid UTF-8 OCP crosswalk CSV: {error}") from error
    if not rows:
        raise ValueError("empty OCP crosswalk CSV")
    return rows


def _source_versions(api: Any) -> dict[str, list[dict[str, str]]]:
    """Index exact file names, not work titles, and exclude both translation kinds."""
    F = api.F
    features = {name: getattr(F, name, None) for name in ("otype", *REQUIRED_FEATURES)}
    missing = [name for name, feature in features.items() if feature is None]
    if missing:
        raise ValueError("catalogue lookup requires loaded TF features: " + ", ".join(missing))
    result: dict[str, list[dict[str, str]]] = {}
    seen_versions: set[str] = set()
    file_identities: dict[str, tuple[str, str]] = {}
    for node in features["otype"].s("book"):
        kind = features["version_kind"].v(node)
        if kind in {"parallel_translation", "generated_translation"}:
            continue
        if kind != "source":
            raise ValueError(f"unknown TF book version_kind at node {node}: {kind!r}")
        values = {
            name: features[name].v(node)
            for name in ("source_file", "source_sha256", "ocp_book", "version_id")
        }
        if not all(isinstance(value, str) and value for value in values.values()):
            raise ValueError(f"incomplete TF source identity at book node {node}")
        filename = values["source_file"]
        digest = values["source_sha256"]
        version_id = values["version_id"]
        if not _XML_FILENAME.fullmatch(filename) or not _SHA256.fullmatch(digest):
            raise ValueError(f"invalid TF source filename or SHA-256 at book node {node}")
        if version_id in seen_versions:
            raise ValueError(f"duplicate TF source version ID: {version_id!r}")
        identity = (values["ocp_book"], digest)
        if filename in file_identities and file_identities[filename] != identity:
            raise ValueError(f"conflicting TF source identities for {filename!r}")
        file_identities[filename] = identity
        seen_versions.add(version_id)
        result.setdefault(filename, []).append({
            "ocp_book": values["ocp_book"],
            "version_id": version_id,
            "source_sha256": digest,
        })
    return result


def catalog_lookup(
    api: Any, raw: bytes, *, canon_id: str | None = None,
) -> dict[str, Any]:
    """Return local catalogue claims and exact TF filename matches.

    Even a match does not establish a scholarly equivalence or the crosswalk's
    version relative to the TF source. No title matching, alias inference,
    dataset modification, or rights attestation is performed.
    """
    rows = _read_crosswalk(raw)
    versions = _source_versions(api)
    claims: dict[str, list[str]] = {}
    for row in rows:
        if row["ocp_xml"]:
            claims.setdefault(row["ocp_xml"], []).append(row["ocp_canon_id"])
    counts = {
        "catalog_records": len(rows),
        "exact_tf_match": 0,
        "declared_filename_not_in_tf": 0,
        "no_declared_filename": 0,
        "matched_tf_files": len(versions.keys() & claims.keys()),
        "unmatched_tf_files": len(versions.keys() - claims.keys()),
    }
    records = []
    for row in rows:
        filename = row["ocp_xml"]
        status = (
            "no_declared_filename" if not filename else
            "exact_tf_match" if filename in versions else
            "declared_filename_not_in_tf"
        )
        counts[status] += 1
        if canon_id is None or row["ocp_canon_id"] == canon_id:
            records.append({
                **row,
                "match_status": status,
                "same_filename_catalog_ids": claims.get(filename, []),
                "tf_source_versions": versions.get(filename, []),
            })
    if canon_id is not None and not records:
        raise ValueError(f"unknown canonical ID: {canon_id!r}")
    return {
        "crosswalk_sha256": sha256(raw).hexdigest(),
        "match_basis": "exact_source_filename_only",
        "redistribution_permission": "not_attested",
        "counts": counts,
        "unmatched_tf_files": sorted(versions.keys() - claims.keys()),
        "records": records,
    }
