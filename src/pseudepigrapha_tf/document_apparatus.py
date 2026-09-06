from __future__ import annotations

import json

from .apparatus import Apparatus as _CoreApparatus
from .source import INTRO_FIELDS


class Apparatus(_CoreApparatus):
    """Core apparatus API plus OCP document-level scholarly metadata access."""

    @staticmethod
    def _decode_json_feature(feature, name: str, node: int, *, required: bool = False):
        value = feature.v(node)
        if value is None:
            if required:
                raise ValueError(f"feature {name!r} has no value for work node {node}")
            return None
        try:
            return json.loads(value)
        except (TypeError, json.JSONDecodeError) as exc:
            raise ValueError(f"feature {name!r} has invalid JSON for work node {node}") from exc

    def work_metadata(self, work: str) -> dict[str, object]:
        """Return exact public OCP ``intros.json`` metadata for one work.

        Text-Fabric 13.1 cannot safely transport raw carriage returns in string
        features. The corpus therefore stores source strings JSON-encoded on one
        ``work`` node; this method reverses that transport encoding and returns
        the original HTML/text values, including CRLF, tabs and backslashes.
        """

        work = str(work)
        ocp_book = self._require_feature("ocp_book")
        source_file = self._require_feature("source_file")
        field_order_feature = self._require_feature("intro_field_order")
        title_feature = self._require_feature("intro_title_json")
        version_feature = self._require_feature("intro_version_json")
        citation_feature = self._require_feature("intro_citation_json")
        metadata_only_feature = self._require_feature("is_metadata_only_work")
        version_of = self._require_edge("version_of")

        matches = tuple(
            node
            for node in self.api.F.otype.s("work")
            if str(ocp_book.v(node) or "") == work
        )
        if not matches:
            raise KeyError(f"OCP work not found in loaded Text-Fabric data: {work!r}")
        if len(matches) != 1:
            raise ValueError(f"duplicate work nodes for OCP work {work!r}: {matches}")
        node = matches[0]

        field_order_value = field_order_feature.v(node)
        if field_order_value is None:
            field_order: list[str] = []
        else:
            try:
                field_order = json.loads(field_order_value)
            except (TypeError, json.JSONDecodeError) as exc:
                raise ValueError(f"intro_field_order has invalid JSON for work node {node}") from exc
            if not isinstance(field_order, list) or any(
                not isinstance(name, str) or name not in INTRO_FIELDS for name in field_order
            ):
                raise ValueError(f"intro_field_order is invalid for work node {node}: {field_order!r}")
            if len(field_order) != len(set(field_order)):
                raise ValueError(f"intro_field_order contains duplicate fields for work node {node}")

        fields: dict[str, str] = {}
        for name in field_order:
            feature_name = f"intro_{name}_json"
            feature = self._require_feature(feature_name)
            decoded = self._decode_json_feature(feature, feature_name, node, required=True)
            if not isinstance(decoded, str):
                raise ValueError(f"feature {feature_name!r} does not decode to a string for work node {node}")
            fields[name] = decoded

        owners = tuple(version_of.t(node))
        has_text = any(self.api.F.otype.v(owner) == "book" for owner in owners)
        metadata_title = self._decode_json_feature(title_feature, "intro_title_json", node)
        metadata_version = self._decode_json_feature(version_feature, "intro_version_json", node)
        citation = self._decode_json_feature(citation_feature, "intro_citation_json", node)
        if citation is not None and not isinstance(citation, str):
            raise ValueError(f"intro_citation_json does not decode to a string for work node {node}")

        return {
            "node": node,
            "work": work,
            "source_file": str(self._required_feature_value(source_file, "source_file", node)),
            "metadata_title": metadata_title,
            "metadata_version": metadata_version,
            "fields": fields,
            "citation": citation,
            "has_text": has_text,
            "metadata_only": metadata_only_feature.v(node) == 1,
        }
