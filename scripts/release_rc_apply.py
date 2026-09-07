from pathlib import Path


readme = Path("README.md")
readme_text = readme.read_text(encoding="utf-8")
old_install = '''## Install

Python 3.10+ is required.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
```

## Convert OCP
'''
new_install = '''## Install

Python 3.10+ is required.

For normal use from a repository checkout, install the runtime package non-editably:

```bash
python -m venv .venv
source .venv/bin/activate
pip install .
```

For development and the test suite, use the editable development install instead:

```bash
pip install -e '.[dev]'
```

## Convert OCP
'''
assert old_install in readme_text, "README install section changed unexpectedly"
readme.write_text(readme_text.replace(old_install, new_install, 1), encoding="utf-8")

workflow = Path(".github/workflows/test.yml")
workflow_text = workflow.read_text(encoding="utf-8")
old_pinned_install = '''      - name: Install
        run: pip install -e '.[dev]'
      - name: Clone pinned OCP source
'''
new_pinned_install = '''      - name: Build release wheel
        run: |
          python -m pip install build
          python -m build --wheel
      - name: Install release wheel in fresh environment
        run: |
          python -m venv /tmp/pseudepigrapha-tf-release-venv
          /tmp/pseudepigrapha-tf-release-venv/bin/python -m pip install --upgrade pip
          /tmp/pseudepigrapha-tf-release-venv/bin/python -m pip install dist/pseudepigrapha_tf-0.1.0-py3-none-any.whl
          echo "/tmp/pseudepigrapha-tf-release-venv/bin" >> "$GITHUB_PATH"
      - name: Verify installed release contract
        run: |
          cd /tmp
          python - <<'PY'
          from importlib.metadata import version
          from pathlib import Path

          import pseudepigrapha_tf
          from pseudepigrapha_tf.classifications import load_historical_classifications

          assert version('pseudepigrapha-tf') == '0.1.0'
          assert pseudepigrapha_tf.__version__ == '0.1.0'
          installed = Path(pseudepigrapha_tf.__file__).resolve()
          assert '/tmp/pseudepigrapha-tf-release-venv/' in str(installed), installed
          classifications = load_historical_classifications()
          assert classifications.documents
          assert classifications.source_file == 'ocp_classifications_2017.json'
          PY
          pseudepigrapha-tf --help >/tmp/pseudepigrapha-tf-help.txt
          grep -q 'Convert Online Critical Pseudepigrapha XML to Text-Fabric' /tmp/pseudepigrapha-tf-help.txt
      - name: Clone pinned OCP source
'''
assert workflow_text.count(old_pinned_install) == 1, "pinned install block changed unexpectedly"
workflow.write_text(
    workflow_text.replace(old_pinned_install, new_pinned_install, 1),
    encoding="utf-8",
)
