from __future__ import annotations

from pathlib import Path

path = Path(__file__).resolve().parents[1] / "src" / "pseudepigrapha_tf" / "apparatus.py"
text = path.read_text(encoding="utf-8")
old = '''        for unit in units:\n            source_ref = str(self._feature("source_ref", unit, ""))\n'''
new = '''        for unit in units:\n            self._reject_generated_unit(unit)\n            source_ref = str(self._feature("source_ref", unit, ""))\n'''
count = text.count(old)
if count != 1:
    raise RuntimeError(f"private passage context loop: expected 1 match, found {count}")
path.write_text(text.replace(old, new), encoding="utf-8")
