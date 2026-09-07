from __future__ import annotations

from pathlib import Path


# Temporary fail-closed transform; removed by its green runner.
ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "src" / "pseudepigrapha_tf" / "apparatus.py"
text = PATH.read_text(encoding="utf-8")


def replace_once(old: str, new: str, label: str) -> None:
    global text
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected exactly one match, found {count}")
    text = text.replace(old, new, 1)


replace_once(
    '''    def _is_generated_book(self, book_node: int) -> bool:\n        version_kind = getattr(self.api.F, "version_kind", None)\n        return version_kind is not None and version_kind.v(book_node) == "generated_translation"\n''',
    '''    def _is_generated_book(self, book_node: int) -> bool:\n        version_kind = self._require_feature("version_kind")\n        value = self._required_feature_value(version_kind, "version_kind", book_node)\n        return value == "generated_translation"\n''',
    "generated-book load contract",
)

replace_once(
    '        synthetic_witness = getattr(self.api.F, "synthetic_witness", None)\n',
    '        synthetic_witness = self._require_feature("synthetic_witness")\n',
    "witness inventory synthetic feature",
)
replace_once(
    '                    if synthetic_witness is None or synthetic_witness.v(node) != 1\n',
    '                    if synthetic_witness.v(node) != 1\n',
    "witness inventory synthetic filter",
)

replace_once(
    '        synthetic_witness = getattr(self.api.F, "synthetic_witness", None)\n',
    '        synthetic_witness = self._require_feature("synthetic_witness")\n',
    "unit apparatus synthetic feature",
)
replace_once(
    '                    if synthetic_witness is None or synthetic_witness.v(manuscript) != 1\n',
    '                    if synthetic_witness.v(manuscript) != 1\n',
    "unit apparatus synthetic filter",
)

replace_once(
    '        synthetic_witness = getattr(self.api.F, "synthetic_witness", None)\n',
    '        synthetic_witness = self._require_feature("synthetic_witness")\n',
    "passage synthetic feature",
)
replace_once(
    '                        if synthetic_witness is None or synthetic_witness.v(manuscript) != 1\n',
    '                        if synthetic_witness.v(manuscript) != 1\n',
    "passage synthetic filter",
)

replace_once(
    '        version_kind = getattr(self.api.F, "version_kind", None)\n',
    '        version_kind = self._require_feature("version_kind")\n',
    "work-passage version kind feature",
)
replace_once(
    '                    and (version_kind is None or version_kind.v(node) != "generated_translation")\n',
    '                    and version_kind.v(node) != "generated_translation"\n',
    "work-passage generated filter",
)

PATH.write_text(text, encoding="utf-8")
