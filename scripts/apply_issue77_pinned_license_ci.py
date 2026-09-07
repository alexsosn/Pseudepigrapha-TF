from pathlib import Path

path = Path('.github/workflows/test.yml')
text = path.read_text(encoding='utf-8')

old = """          assert report['provenance']['upstream_commit'] == 'c939dcbacad78c5d18d2c4282cad23c47e19ac07'\n          assert report['source']['versions'] == report['graph']['versions']\n"""
new = """          assert report['provenance']['upstream_repository'] == 'https://github.com/OnlineCriticalPseudepigrapha/Online-Critical-Pseudepigrapha'\n          assert report['provenance']['upstream_commit'] == 'c939dcbacad78c5d18d2c4282cad23c47e19ac07'\n          assert report['provenance']['source_identity_status'] == 'verified'\n          assert report['provenance']['content_license_status'] == 'verified'\n          assert report['provenance']['content_license'] == 'CC-BY-4.0'\n          assert report['provenance']['converter_software_license'] == 'MIT'\n          assert report['provenance']['upstream_software_license'] == 'GPL-3.0'\n          assert report['provenance']['upstream_license_commit'] == '8c8c2c55a2c55ba4b23ac506956f98dcc25045b2'\n          assert report['provenance']['content_license_source'].endswith('/blob/c939dcbacad78c5d18d2c4282cad23c47e19ac07/LICENSE.CC-BY-4.0')\n          assert 'content_license_diagnostic' not in report['provenance']\n          assert 'source_identity_diagnostic' not in report['provenance']\n          assert report['semantic_checks']['corpus_license_provenance'] is True\n          assert report['source']['versions'] == report['graph']['versions']\n"""
assert old in text
text = text.replace(old, new, 1)

old = """          assert tuple(api.T.sectionTypes) == ('book', 'chapter', 'verse')\n\n          synthetic = [\n"""
new = """          assert tuple(api.T.sectionTypes) == ('book', 'chapter', 'verse')\n\n          generic = api.TF.features['otype'].metaData\n          assert generic['sourceIdentityStatus'] == 'verified'\n          assert generic['contentLicenseStatus'] == 'verified'\n          assert generic['contentLicense'] == 'CC-BY-4.0'\n          assert generic['converterSoftwareLicense'] == 'MIT'\n          assert generic['upstreamSoftwareLicense'] == 'GPL-3.0'\n          assert generic['upstreamCommit'] == 'c939dcbacad78c5d18d2c4282cad23c47e19ac07'\n          assert generic['upstreamLicenseCommit'] == '8c8c2c55a2c55ba4b23ac506956f98dcc25045b2'\n          assert 'contentLicenseDiagnostic' not in generic\n          assert 'sourceIdentityDiagnostic' not in generic\n\n          synthetic = [\n"""
assert old in text
text = text.replace(old, new, 1)

path.write_text(text, encoding='utf-8')
